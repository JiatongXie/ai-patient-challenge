import os
from datetime import datetime
from typing import Dict, List, Any, Optional, TypedDict, Literal

import langchain
from langchain.prompts import PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage
from openai import OpenAI
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 定义状态类型
class GameState(TypedDict):
    messages: List[Dict[str, Any]]  # 对话历史
    current_sender: Literal["patient", "body", "doctor", "system"]  # 当前消息发送者
    diagnosis: Optional[str]  # 正确的诊断
    game_over: bool  # 游戏是否结束

# 创建OpenAI客户端
client = OpenAI(
    base_url=os.getenv("API_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
    api_key=os.getenv("ARK_API_KEY"),
)

# 自定义LLM函数，使用OpenAI客户端
def invoke_llm(prompt, system_message="你是一个AI助手"):
    response = client.chat.completions.create(
        model=os.getenv("MODEL_ID", "ep-20250221232531-6qwkh"),
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# 病人角色
patient_prompt = PromptTemplate.from_template("""
你是一位去医院就诊的病人。你不知道自己得了什么病，但你能感受到身体的症状。
你需要向医生描述你的症状，并回答医生的问题。

当前对话历史:
{messages}

请以病人的身份回复医生的问题或发起对话。如果你需要询问身体的感受，请以"[询问身体]:"开头，后跟具体问题。
""")

# 身体角色
body_prompt = PromptTemplate.from_template("""
你代表病人的身体感官系统。你知道病人得了{diagnosis}，但你只能提供相关的症状感受，不能直接说出疾病名称。

当前对话历史:
{messages}

病人正在询问自己的身体感受，请使用简洁的要点形式描述与{diagnosis}相关的症状。
不要使用对话格式，不要称呼医生或病人，只需直接描述症状感受。
""")

# 系统角色
system_prompt = PromptTemplate.from_template("""
你是问诊游戏的系统，负责判断游戏是否结束，以及检查各方回复的合理性。

当前对话历史:
{messages}

当前消息: {current_message}
发送者: {sender}

请检查这条消息是否合理、是否符合发送者的角色。
判断医生的诊断是否正确（正确的诊断是：{diagnosis}）。

请按以下格式回复:
合理性: [合理/不合理]
原因: [如果不合理，请说明原因]
""")

# 病人角色提示系统消息
PATIENT_SYSTEM_MESSAGE = """
你是一位去医院就诊的病人。你不知道自己得了什么病，但你能感受到身体的症状。
请真实地扮演一个病人，使用自然的语言描述自己的症状。
回复应当简洁、符合病人的身份，避免过于专业的医学术语。

当你需要了解更多自己的身体状况时，你可以询问身体。在这种情况下，请在消息前加上"[询问身体]:"，
后面跟着具体的问题，例如：
"[询问身体]: 我的关节痛是什么感觉？"
"[询问身体]: 我的头疼是持续性的还是间歇性的？"

请记住：
1. 你不知道自己的疾病名称
2. 你只知道自己的感受和症状
3. 如果医生说出疾病名称，你不会知道它是否正确
4. 询问身体时，你将获得更准确的症状描述
"""

# 身体角色提示系统消息
BODY_SYSTEM_MESSAGE = """
你代表病人的身体感官系统。你知道病人得了特定疾病，但你只能提供相关的症状感受。
不要使用人类对话格式，不要称呼医生或病人。只需要直接描述身体感受和症状。
例如：
- "头部：剧烈疼痛，像被锤子敲击一样，尤其在光线强烈时加剧"
- "胸部：呼吸时有刺痛感，深呼吸更为明显"
- "关节：晨僵，活动后缓解，手指关节红肿"

请使用简洁的要点形式描述症状，直接从病名推导出典型的感官体验。
"""

# 系统角色提示系统消息
SYSTEM_REFEREE_MESSAGE = """
你是问诊游戏的系统裁判，职责是：
1. 判断各方回复是否合理
2. 检查医生是否正确诊断出病人的疾病
3. 决定游戏是否结束

判断诊断是否正确的规则：
- 医生必须明确说出完全匹配的疾病名称（如"患者患有关节炎"、"这是关节炎"等）
- 如果医生诊断错误（如说"肺炎"而实际是"关节炎"），必须判定为错误
- 不要被医生的自信或强势语气影响判断
- 当存在疑问时，默认为诊断不正确

以下情况不算正确诊断：
- 医生只是列举可能性（"可能是关节炎或肺炎"）
- 医生使用模糊的描述而非明确疾病名
- 医生说出完全不同的疾病名称
"""

# 定义节点函数
def patient_node(state: GameState) -> Dict:
    """病人节点，生成病人回复"""
    messages = state["messages"]
    diagnosis = state.get("diagnosis", "")
    
    # 检查医生是否刚才给出了诊断
    doctor_gave_diagnosis = False
    doctor_message = ""
    
    # 查找最后一条医生消息
    for msg in reversed(messages):
        if msg["sender"] == "doctor":
            doctor_message = msg["content"]
            # 检查医生消息是否包含可能的诊断
            diagnosis_terms = ["诊断", "判断", "认为", "确定", "可能是", "应该是", "我觉得是", "你有", "你患了"]
            doctor_gave_diagnosis = any(term in doctor_message for term in diagnosis_terms) or diagnosis.lower() in doctor_message.lower()
            break
    
    # 构建提示
    formatted_messages = "\n".join([f"{msg['sender']}: {msg['content']}" for msg in messages])
    
    special_instruction = ""
    if doctor_gave_diagnosis:
        special_instruction = """
医生似乎给出了诊断。作为病人，你不知道这个诊断是否正确。你可以:
1. 询问医生这意味着什么，或该如何治疗
2. 表达对诊断的疑惑或担忧
3. 询问医生是否确定
但记住，你不具备专业知识来评判诊断的正确性。
"""
    
    prompt = patient_prompt.format(messages=formatted_messages) + special_instruction
    
    # 获取病人回复
    content = invoke_llm(prompt, PATIENT_SYSTEM_MESSAGE)
    
    # 如果是游戏第一次开始，确保病人有一个友好的问候
    if len(messages) <= 1:
        greeting_prompt = "你是第一次去医院的病人，请用一句话友好地向医生问好，并简要描述你的主要症状。"
        content = invoke_llm(greeting_prompt, PATIENT_SYSTEM_MESSAGE)
    
    # 更新状态
    new_message = {"sender": "patient", "content": content}
    
    # 检查是否需要询问身体
    if "[询问身体]:" in content:
        print("病人询问身体")
        return {
            "messages": messages + [new_message],
            "current_sender": "body",
            "diagnosis": diagnosis,
            "game_over": False
        }
    else:
        # 不询问身体，直接进入系统检查
        print("病人直接回复")
        return {
            "messages": messages + [new_message],
            "current_sender": "system",
            "diagnosis": diagnosis,
            "game_over": False
        }

def body_node(state: GameState) -> Dict:
    """身体节点，生成身体感官响应"""
    messages = state["messages"]
    diagnosis = state.get("diagnosis", "")
    
    # 获取病人的询问
    patient_query = messages[-1]["content"].replace("[询问身体]:", "").strip()
    
    # 构建提示
    formatted_messages = "\n".join([f"{msg['sender']}: {msg['content']}" for msg in messages])
    prompt = body_prompt.format(
        messages=formatted_messages,
        diagnosis=diagnosis
    )
    
    # 获取身体回复
    content = invoke_llm(prompt, BODY_SYSTEM_MESSAGE + f"\n当前病名是：{diagnosis}。针对'{patient_query}'请描述相关的身体感受。")
    
    # 更新状态
    new_message = {"sender": "body", "content": content}
    print("身体回复病人")
    return {
        "messages": messages + [new_message],
        "current_sender": "patient",
        "diagnosis": diagnosis,
        "game_over": False
    }

def system_node(state: GameState) -> Dict:
    """系统节点，负责检查消息合理性和游戏状态"""
    messages = state["messages"]
    diagnosis = state["diagnosis"]
    
    # 如果没有消息，返回当前状态
    if not messages:
        return state
    
    current_message = messages[-1]
    
    # 检查是否是医生消息，以及是否可能包含诊断
    if current_message["sender"] == "doctor":
        # 构建特殊提示来检查诊断是否正确
        diagnosis_prompt = f"""
医生的消息: "{current_message['content']}"
正确的诊断: "{diagnosis}"

医生是否正确诊断出了疾病？请分析医生的回复是否明确指出了正确的疾病名称。
只有当医生明确指出正确疾病名称时才算正确，如果医生提到了错误的疾病，一定是不正确的。
请以"诊断正确: [是/否]"开始你的回答，并解释理由。
"""
        diagnosis_result = invoke_llm(diagnosis_prompt, "你是医学诊断评估专家，判断医生的诊断是否与标准诊断匹配。")
        print(f"诊断评估: {diagnosis_result}")
        
        # 解析诊断结果
        is_correct_diagnosis = "诊断正确: 是" in diagnosis_result
        if is_correct_diagnosis:
            print("游戏结束: 诊断正确")
            return {
                "messages": messages + [{"sender": "system", "content": f"恭喜！你正确诊断出了病人的疾病：{diagnosis}。"}],
                "current_sender": "system",
                "diagnosis": diagnosis, 
                "game_over": True
            }
    
    # 构建提示
    formatted_messages = "\n".join([f"{msg['sender']}: {msg['content']}" for msg in messages[:-1]])
    prompt = system_prompt.format(
        messages=formatted_messages,
        current_message=current_message["content"],
        sender=current_message["sender"],
        diagnosis=diagnosis
    )
    
    # 获取系统判断
    system_response = invoke_llm(prompt, SYSTEM_REFEREE_MESSAGE + f"\n正确的诊断是：{diagnosis}")
    
    # 解析系统回复
    is_reasonable = "合理" in system_response
    
    if not is_reasonable:
        # 移除不合理的消息，让发送者重试
        print(f"系统判断消息不合理: {system_response}")
        return {
            "messages": messages[:-1] + [{"sender": "system", "content": f"请重新回复，原因: {system_response}"}],
            "current_sender": current_message["sender"],
            "diagnosis": diagnosis,
            "game_over": False
        }
    elif current_message["sender"] == "patient":
        # 如果病人的回复合理，轮到医生回复
        print("病人消息已确认，轮到医生")
        return {
            "messages": messages,
            "current_sender": "doctor",
            "diagnosis": diagnosis,
            "game_over": False
        }
    elif current_message["sender"] == "doctor":
        # 如果医生的回复合理，轮到病人回复
        print("医生消息已确认，轮到病人")
        return {
            "messages": messages,
            "current_sender": "patient", 
            "diagnosis": diagnosis,
            "game_over": False
        }
    else:
        # 其他情况
        return state

def doctor_turn(state: GameState, config: Dict[str, Any] = None) -> Dict:
    """处理医生的输入"""
    messages = state["messages"]
    
    # 获取医生的消息
    message = ""
    try:
        if isinstance(config, dict):
            if "message" in config:
                message = config["message"]
            elif "doctor" in config and isinstance(config["doctor"], dict):
                message = config["doctor"].get("message", "")
    except Exception as e:
        print(f"处理医生消息时出错: {e}")
    
    if not message:
        print("警告: 医生消息为空")
        return state
    
    # 添加医生的消息
    new_message = {"sender": "doctor", "content": message}
    
    # 返回新状态
    return {
        "messages": messages + [new_message],
        "current_sender": "system",
        "diagnosis": state.get("diagnosis"),
        "game_over": state.get("game_over", False)
    }

def should_end(state: GameState) -> bool:
    return state.get("game_over", False)

def choose_next_node(state: GameState) -> str:
    if state.get("game_over", False):
        return END
    return state["current_sender"]

# 创建游戏图
def build_game_graph(diagnosis: str):
    workflow = StateGraph(GameState)
    
    # 添加节点
    workflow.add_node("patient", patient_node)
    workflow.add_node("body", body_node)
    workflow.add_node("doctor", doctor_turn)
    workflow.add_node("system", system_node)
    
    # 设置边
    workflow.add_conditional_edges("system", choose_next_node)
    workflow.add_edge("body", "patient")
    workflow.add_edge("patient", "system")
    workflow.add_edge("doctor", "system")
    
    # 设置入口
    workflow.set_entry_point("patient")
    
    # 编译
    game = workflow.compile()
    
    # 打印图结构（调试用）
    print("游戏图结构初始化完成")
    
    # 初始状态
    initial_state = {
        "messages": [{"sender": "system", "content": "游戏开始，病人即将进入诊室。"}],
        "current_sender": "patient",
        "diagnosis": diagnosis,
        "game_over": False
    }
    
    return game, initial_state

# 保存对话历史
def save_conversation(messages: List[Dict[str, Any]]):
    # 创建保存目录
    os.makedirs("conversations", exist_ok=True)
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"conversations/conversation_{timestamp}.txt"
    
    # 写入文件
    with open(filename, "w", encoding="utf-8") as f:
        for msg in messages:
            f.write(f"{msg['sender']}: {msg['content']}\n\n")
    
    return filename

# 主游戏函数
def play_doctor_game():
    # 检查环境变量
    if not os.getenv("ARK_API_KEY"):
        print("错误: 未设置ARK_API_KEY环境变量")
        print("请在.env文件中设置API密钥")
        return
        
    # 可选的疾病列表
    diseases = [
        "流感", "肺炎", "胃溃疡", "偏头痛", "扁桃体炎", 
        "高血压", "糖尿病", "关节炎", "哮喘", "过敏性鼻炎"
    ]
    
    import random
    diagnosis = random.choice(diseases)
    print(f"[调试] 本次游戏的疾病是: {diagnosis}")  # 调试信息，实际游戏中可注释掉
    
    game, initial_state = build_game_graph(diagnosis)
    state = initial_state
    
    print("="*70)
    print(" "*20 + "AI问诊小游戏")
    print("="*70)
    print("你是一名医生，需要通过询问病人症状来诊断疾病。")
    print("\n游戏规则:")
    print("1. 通过与病人交流，了解其症状")
    print("2. 当你认为已经确定诊断时，直接告诉病人诊断结果")
    print("3. 只有准确说出病名才算胜利")
    print("4. 错误的诊断不会结束游戏，你可以继续尝试")
    print("\n诊断提示:")
    print("- 当你要给出诊断时，请明确表达，如'你患有高血压'")
    print("- 可以先问诊再诊断，不必着急")
    print("- 病人可能会询问自己的身体感受，这会提供更详细的症状")
    print("\n游戏开始！")
    print("-"*70)
    
    # 首先生成病人的初始消息
    print("病人正在进入诊室...")
    patient_state = patient_node(state)
    
    # 打印病人消息
    for msg in patient_state["messages"][-1:]:
        print(f"\n👤 病人: {msg['content']}")
    
    # 标记当前轮到医生
    current_state = {
        "messages": patient_state["messages"],
        "current_sender": "doctor",
        "diagnosis": diagnosis,
        "game_over": False
    }
    
    # 游戏主循环
    while not should_end(current_state):
        if current_state["current_sender"] == "doctor":
            # 医生回合 - 获取用户输入
            doctor_input = input("\n👨‍⚕️ 医生（你）: ")
            if not doctor_input.strip():
                print("请输入有效的消息")
                continue
                
            # 处理医生输入
            doctor_state = doctor_turn(current_state, {"message": doctor_input})
            
            # 系统验证医生消息
            try:
                system_state = system_node(doctor_state)
                current_state = system_state
            except Exception as e:
                print(f"处理医生消息时出错: {e}")
                continue
                
        elif current_state["current_sender"] == "patient":
            # 病人回合
            print("\n⏳ 病人正在思考...")
            try:
                patient_state = patient_node(current_state)
                
                # 如果病人要询问身体
                if patient_state["current_sender"] == "body":
                    print("\n🔍 病人正在感知身体状况...")
                    body_state = body_node(patient_state)
                    
                    # 显示身体反馈
                    for msg in body_state["messages"][-1:]:
                        if msg["sender"] == "body":
                            print(f"\n🫀 身体感知：\n{msg['content']}")
                    
                    # 病人收到身体信息后的回应
                    patient_state = patient_node(body_state)
                
                # 系统验证病人消息
                system_state = system_node(patient_state)
                current_state = system_state
                
                # 打印病人消息
                for msg in patient_state["messages"][-1:]:
                    if msg["sender"] == "patient":
                        print(f"\n👤 病人: {msg['content']}")
                    
            except Exception as e:
                print(f"处理病人消息时出错: {e}")
                # 如果出错，轮到医生
                current_state["current_sender"] = "doctor"
        
        # 检查游戏是否结束
        if current_state.get("game_over", False):
            # 打印系统结束消息
            for msg in current_state["messages"]:
                if msg["sender"] == "system" and "恭喜" in msg["content"]:
                    print(f"\n🎉 系统: {msg['content']}")
            break
    
    # 游戏结束
    print("\n" + "="*70)
    print(" "*20 + "游戏结束!")
    if any(msg["sender"] == "system" and "恭喜" in msg["content"] for msg in current_state["messages"]):
        print(f"恭喜你成功诊断出病人的疾病: {diagnosis}")
    print("="*70)
    
    # 保存对话
    filename = save_conversation(current_state["messages"])
    print(f"\n对话已保存至: {filename}")

if __name__ == "__main__":
    play_doctor_game() 