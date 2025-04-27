import os
from datetime import datetime
from typing import Dict, List, Any, Optional, TypedDict, Literal
import hashlib

from langchain.prompts import PromptTemplate
from openai import OpenAI
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
    # 生成调用ID用于追踪请求
    call_id = hashlib.md5((prompt + system_message).encode()).hexdigest()[:8]
    
    # 记录API调用请求
    api_call_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 调用API
    response = client.chat.completions.create(
        model=os.getenv("MODEL_ID", "ep-20250221232531-6qwkh"),
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
    )
    
    # 获取回复内容
    response_content = response.choices[0].message.content
    
    return response_content

# 病人角色
patient_prompt = PromptTemplate.from_template("""
你是一位去医院就诊的病人。你不知道自己得了什么病，但你能感受到身体的症状。
你需要向医生描述你的症状，并回答医生的问题。

当前对话历史:
{messages}

请以病人的身份回复医生的问题或发起对话。如果你感到有必要询问身体的感受，请以"[询问身体]:"开头，后跟你向自己的身体确认的内心活动。
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

如果发送者是病人，请检查这条消息是否合理、是否符合病人的角色。
如果发送者是医生，医生由玩家扮演，不要评判其回复的合理性，只判断其诊断是否正确。
判断医生的诊断是否正确（正确的诊断是：{diagnosis}）。

请按以下格式回复:
发送者为病人时:
合理性: [合理/不合理]
原因: [如果不合理，请说明原因]

发送者为医生时:
诊断: [未给出诊断/诊断不正确/诊断正确]
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
1. 判断病人回复是否符合格式，比如，[询问身体]：的文本不能回复给医生，需要删除
2. 判断病人的回复是否合理，比如，病人的专业水平有限，不能说出疾病的名称，只能说出症状。
3. 检查医生是否正确诊断出病人的疾病
4. 决定游戏是否结束

判断诊断是否正确的规则：
- 医生必须明确说出完全匹配的疾病名称（如"患者患有关节炎"、"这是关节炎"等）
- 如果医生诊断错误（如说"肺炎"而实际是"关节炎"），必须判定为错误
- 不要被医生的自信或强势语气影响判断
- 当存在疑问时，默认为诊断不正确

以下情况不算正确诊断：
- 医生只是列举可能性（"可能是关节炎或肺炎"）
- 医生使用模糊的描述而非明确疾病名
- 医生说出完全不同的疾病名称

重要：医生由玩家扮演，你不应该评判医生回复的合理性。你只能评判病人回复的合理性，以及医生的诊断是否正确。
"""

# 定义节点函数
def patient_node(state: GameState) -> Dict:
    """病人节点，生成病人回复"""
    messages = state["messages"]
    diagnosis = state.get("diagnosis", "")
    
    # 检查是否刚从身体节点或系统节点返回
    last_message = messages[-1] if messages else None
    if last_message and last_message["sender"] == "body":
        # 如果最后一条消息是body的回复，说明病人正在询问身体
        # 此时，我们需要基于身体的回复生成病人对医生的回复
        
        # 构造特殊提示，帮助病人基于身体感知回复医生
        formatted_messages = "\n".join([f"{msg['sender']}: {msg['content']}" for msg in messages])
        body_response = last_message["content"]
        
        special_prompt = f"""
你是一位病人，刚才询问了自己的身体感受，得到了以下反馈:

{body_response}

请基于这些身体感受，以病人的身份回复医生。不要提及你"询问身体"这一行为，直接将身体反馈的症状自然地融入到你的回复中。
确保你的回复:
1. 只描述症状，不包含医学诊断
2. 使用普通人的语言，避免专业术语
3. 自然、真实地表达你的感受和担忧
"""
        content = invoke_llm(special_prompt, PATIENT_SYSTEM_MESSAGE)
        
        # 创建病人消息
        new_message = {"sender": "patient", "content": content}
        
        # 返回新状态，进入系统检查
        return {
            "messages": messages + [new_message],
            "current_sender": "system",  # 直接进入系统检查
            "diagnosis": diagnosis,
            "game_over": False
        }
    
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
    
    # 如果是游戏第一次开始，确保病人有一个友好的问候
    if len(messages) <= 1:
        greeting_prompt = "你是第一次去医院的病人，请用一句话友好地向医生问好，并简要描述你的主要症状。"
        content = invoke_llm(greeting_prompt, PATIENT_SYSTEM_MESSAGE)
    else:
        # 获取病人回复
        content = invoke_llm(prompt, PATIENT_SYSTEM_MESSAGE)
    
    # 更新状态
    new_message = {"sender": "patient", "content": content}
    
    # 检查是否需要询问身体
    if "[询问身体]:" in content:
        return {
            "messages": messages + [new_message],
            "current_sender": "body",
            "diagnosis": diagnosis,
            "game_over": False
        }
    else:
        # 不询问身体，直接进入系统检查
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
    diagnosis_result = None
    if current_message["sender"] == "doctor":
        # 检查是否包含疾病名称或诊断相关词语
        message_text = current_message["content"].lower()
        if (diagnosis.lower() in message_text) or any(term in message_text for term in ["诊断", "判断", "认为", "确定", "可能是", "应该是", "我觉得是", "你有", "你患了"]):
            # 构建特殊提示来检查诊断是否正确
            diagnosis_prompt = f"""
医生的消息: "{current_message['content']}"
正确的诊断: "{diagnosis}"

医生是否正确诊断出了疾病？请分析医生的回复是否明确指出了正确的疾病名称。
只有当医生明确指出正确疾病名称时才算正确，如果医生提到了错误的疾病，一定是不正确的。
请以"诊断正确: [是/否]"开始你的回答，并解释理由。
"""
            diagnosis_result = invoke_llm(diagnosis_prompt, "你是医学诊断评估专家，判断医生的诊断是否与标准诊断匹配。")
            
            # 解析诊断结果
            is_correct_diagnosis = "诊断正确: 是" in diagnosis_result
            if is_correct_diagnosis:
                return {
                    "messages": messages + [{"sender": "system", "content": f"恭喜！你正确诊断出了病人的疾病：{diagnosis}。"}],
                    "current_sender": "system",
                    "diagnosis": diagnosis, 
                    "game_over": True,
                    "system_notes": diagnosis_result  # 保存系统的思考过程
                }
    
    # 对于医生消息，无需进行合理性检查，直接返回
    if current_message["sender"] == "doctor":
        # 医生（玩家）的消息不进行合理性评判，直接轮到病人回复
        return {
            "messages": messages,
            "current_sender": "patient", 
            "diagnosis": diagnosis,
            "game_over": False,
            "system_notes": "医生消息已接收，不进行合理性评判"  # 更新系统笔记
        }
    
    # 只对病人消息进行合理性检查
    if current_message["sender"] == "patient":
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
            # 病人消息不合理，需要重新生成
            # 创建一个特殊提示来生成更合理的病人回复
            fix_prompt = f"""
前一条病人消息被系统判断为不合理，原因是: {system_response}

请根据以下对话历史，生成一个新的合理病人回复:
{formatted_messages}

问题原因总结: {system_response}

重新以病人身份回复，确保:
1. 不透露疾病名称
2. 只描述症状、感受
3. 使用普通人能理解的语言
4. 移除任何[询问身体]的标记
"""
            # 生成修正后的病人回复
            fixed_content = invoke_llm(fix_prompt, PATIENT_SYSTEM_MESSAGE + "\n请确保生成合理的病人回复，避免之前的问题。")
            
            # 创建修正后的消息，替换原来的消息
            fixed_message = {"sender": "patient", "content": fixed_content}
            
            return {
                "messages": messages[:-1] + [fixed_message],  # 替换最后一条消息
                "current_sender": "system",  # 再次检查修正后的消息
                "diagnosis": diagnosis,
                "game_over": False,
                "system_notes": f"病人消息已修正。原因: {system_response}"  # 保存系统的思考过程
            }
        else:
            # 病人消息合理，轮到医生回复
            return {
                "messages": messages,
                "current_sender": "doctor",
                "diagnosis": diagnosis,
                "game_over": False,
                "system_notes": system_response  # 保存系统的思考过程
            }
    
    # 其他情况，直接返回当前状态
    return state 