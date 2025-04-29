import os
from datetime import datetime
from typing import Dict, List, Any, Optional, TypedDict, Literal
import hashlib

from langchain.prompts import PromptTemplate
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(override=True)

# 导入配置
from config import GAME_CONFIG

# 定义状态类型
class GameState(TypedDict):
    messages: List[Dict[str, Any]]  # 对话历史
    current_sender: Literal["patient", "body", "doctor", "system"]  # 当前消息发送者
    diagnosis: Optional[str]  # 正确的诊断
    game_over: bool  # 游戏是否结束

# 创建OpenAI客户端
client = OpenAI(
    base_url=os.getenv("API_BASE_URL"),
    api_key=os.getenv("API_KEY"),
)

# 自定义LLM函数，使用OpenAI客户端
def invoke_llm(prompt, system_message="你是一个AI助手", game_id=None):
    """
    调用LLM API并记录日志

    Args:
        prompt: 用户消息
        system_message: 系统消息
        game_id: 游戏ID，用于关联API调用日志到特定游戏

    Returns:
        API响应内容
    """
    import json
    import threading

    # 确保api_logs文件夹存在
    os.makedirs("api_logs", exist_ok=True)

    # 生成调用ID用于追踪请求
    call_id = hashlib.md5((prompt + system_message).encode()).hexdigest()[:8]

    # 记录API调用请求
    api_call_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    api_call_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    api_log = f"[{api_call_time}] API请求 ID:{call_id}\n系统消息: {system_message}\n用户消息: {prompt}\n"

    # 检查是否已经有相同的调用（防止重复请求）
    if "api_logs_ids" not in globals():
        globals()["api_logs_ids"] = set()

    # 使用缓存避免重复API调用
    if "api_response_cache" not in globals():
        globals()["api_response_cache"] = {}

    # 如果相同的请求已经发过，则使用缓存的结果
    is_duplicate = False
    if call_id in globals()["api_logs_ids"]:
        api_log = f"[{api_call_time}] ‼️ 重复API请求 ID:{call_id}\n系统消息: {system_message}\n用户消息: {prompt}\n"
        print(f"警告：检测到重复API调用 ID:{call_id}，使用缓存结果")
        is_duplicate = True

        # 如果有缓存的响应，直接使用
        if call_id in globals()["api_response_cache"]:
            response_content = globals()["api_response_cache"][call_id]
            print(f"使用缓存的API响应: {call_id}")

            # 记录API返回结果（从缓存）
            api_log += f"API返回(缓存): {response_content}\n{'='*50}\n"

            # 将API调用记录添加到全局日志
            if "api_logs" not in globals():
                globals()["api_logs"] = []
            globals()["api_logs"].append(api_log)

            # 创建详细的API调用日志数据
            log_data = {
                "timestamp": api_call_time,
                "call_id": call_id,
                "is_duplicate": is_duplicate,
                "input": {
                    "system_message": system_message,
                    "user_message": prompt
                },
                "output": response_content,
                "model": os.getenv("MODEL_ID", "未指定模型"),
                "from_cache": True
            }

            # 保存日志到文件
            save_api_log(log_data, game_id, call_id, api_call_timestamp)

            return response_content

    # 将调用ID添加到已调用集合
    globals()["api_logs_ids"].add(call_id)

    # 调用API
    response = client.chat.completions.create(
        model=os.getenv("MODEL_ID"),
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
    )

    # 获取回复内容
    response_content = response.choices[0].message.content

    # 缓存响应
    globals()["api_response_cache"][call_id] = response_content

    # 记录API返回结果
    api_log += f"API返回: {response_content}\n{'='*50}\n"

    # 将API调用记录添加到全局日志
    if "api_logs" not in globals():
        globals()["api_logs"] = []
    globals()["api_logs"].append(api_log)

    # 创建详细的API调用日志数据
    log_data = {
        "timestamp": api_call_time,
        "call_id": call_id,
        "is_duplicate": is_duplicate,
        "input": {
            "system_message": system_message,
            "user_message": prompt
        },
        "output": response_content,
        "model": os.getenv("MODEL_ID", "未指定模型"),
        "from_cache": False  # 标记这是一个新的API调用，不是从缓存获取的
    }

    # 保存日志到文件
    save_api_log(log_data, game_id, call_id, api_call_timestamp)

    return response_content

def save_api_log(log_data, game_id=None, call_id=None, timestamp=None):
    """
    保存API调用日志到文件

    Args:
        log_data: 日志数据
        game_id: 游戏ID
        call_id: 调用ID
        timestamp: 时间戳
    """
    import json
    import threading
    import glob

    # 确保api_logs文件夹存在
    os.makedirs("api_logs", exist_ok=True)

    # 如果没有提供调用ID，生成一个新的
    if not call_id:
        call_id = hashlib.md5(str(log_data).encode()).hexdigest()[:8]

    # 使用线程锁防止并发写入冲突
    lock = threading.Lock()

    with lock:
        if game_id:
            # 存储游戏会话日志文件名的全局字典
            if "game_log_files" not in globals():
                globals()["game_log_files"] = {}

            # 检查是否已经有该游戏ID的日志文件
            if game_id in globals()["game_log_files"]:
                # 使用已存在的日志文件
                log_file = globals()["game_log_files"][game_id]
            else:
                # 查找是否已经存在该游戏ID的日志文件
                existing_files = glob.glob(f"api_logs/api_calls_*_{game_id}.json")

                if existing_files:
                    # 如果找到现有文件，使用第一个找到的文件
                    log_file = existing_files[0]
                else:
                    # 如果没有提供时间戳，生成一个新的
                    if not timestamp:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                    # 创建新的日志文件名
                    log_file = f"api_logs/api_calls_{timestamp}_{game_id}.json"

                # 保存到全局字典中
                globals()["game_log_files"][game_id] = log_file

            try:
                # 读取现有日志（如果存在）
                if os.path.exists(log_file):
                    with open(log_file, "r", encoding="utf-8") as f:
                        try:
                            logs = json.load(f)
                            if not isinstance(logs, list):
                                logs = [logs]  # 确保logs是一个列表
                        except json.JSONDecodeError:
                            # 如果文件为空或格式不正确，创建新的日志列表
                            logs = []
                else:
                    logs = []

                # 添加新的日志
                logs.append(log_data)

                # 写入更新后的日志
                with open(log_file, "w", encoding="utf-8") as f:
                    json.dump(logs, f, ensure_ascii=False, indent=2)

            except Exception as e:
                print(f"保存游戏API日志时出错: {e}")
                # 如果保存失败，回退到使用调用ID的文件名
                if not timestamp:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                fallback_file = f"api_logs/api_call_{timestamp}_{call_id}.json"
                with open(fallback_file, "w", encoding="utf-8") as f:
                    json.dump(log_data, f, ensure_ascii=False, indent=2)
        else:
            # 如果没有提供游戏ID，保存为单独的日志文件
            if not timestamp:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"api_logs/api_call_{timestamp}_{call_id}.json"
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)

# 病人角色
patient_prompt = PromptTemplate.from_template("""
当前对话历史:
{messages}
""")

# 身体角色
body_prompt = PromptTemplate.from_template("""
病人的疾病:{diagnosis}
当前对话历史:{messages}
""")

# 系统角色
system_prompt = PromptTemplate.from_template("""
当前对话历史:{messages}
当前消息: {current_message}
发送者: {sender}

如果发送者是病人，请检查这条消息是否符合格式要求。
如果发送者是医生，判断医生的诊断是否正确（正确的诊断是：{diagnosis}）。

请按以下格式回复:
发送者为病人时:
符合要求: 是/否

发送者为医生时:
诊断正确: 是/否
""")

# 病人角色提示系统消息
PATIENT_SYSTEM_MESSAGE = """
你是一位去医院就诊的病人。你不知道自己得了什么病，但你能感受到身体的症状。
请真实地扮演一个病人，使用自然的语言描述自己的症状。
回复应当简洁、符合病人的身份，避免过于专业的医学术语。

当你需要了解更多自己的身体状况时，你可以询问身体。在这种情况下，请使用特殊格式：
"[询问身体:你的具体问题]"
例如：
"[询问身体:我的头痛是什么感觉？]"
"[询问身体:我的胃痛是持续性的还是间歇性的？]"

重要规则：
1. 你不知道自己的疾病名称
2. 你只知道自己的感受和症状
3. 如果医生说出疾病名称，你不会知道它是否正确
4. 如果你决定询问身体，你的回复应该使用特殊格式，只包含询问身体的内容，不要在同一条消息中既回复医生又询问身体
5. 只在必要的时候询问身体
6. 你的回复应当简短直接（最多1句话）

"""

# 身体角色提示系统消息
BODY_SYSTEM_MESSAGE = """
你代表病人的身体感官系统。你知道病人得了特定疾病，但你只能提供相关的症状感受。
不要使用人类对话格式，不要称呼医生或病人。只需要直接描述身体感受和症状。
例如：
- "胸部：呼吸时有刺痛感，深呼吸更为明显"
- "关节：晨僵，活动后缓解，手指关节红肿"
或者：
- "心脏：心率正常，无明显异常"

请使用简洁的要点形式描述症状，直接从病名推导出典型的感官体验。
"""

# 系统角色提示系统消息
SYSTEM_REFEREE_MESSAGE = """
你是问诊游戏的系统裁判，职责是：
1. 判断病人回复是否符合格式，比如，[询问身体]：等带有特殊格式的文本不能回复给医生
3. 检查医生是否正确诊断出病人的疾病，决定游戏是否结束

判断诊断是否正确的规则：
- 医生必须说出匹配的疾病名称（如"患者患有关节炎"、"这是关节炎"等）
- 如果医生诊断错误（如说"肺炎"而实际是"关节炎"），必须判定为错误
- 不要被医生的自信或强势语气影响判断
- 当存在疑问时，默认为诊断不正确

以下情况不算正确诊断：
- 医生只是列举可能性（"可能是关节炎或肺炎"）
- 医生使用模糊的描述而非明确疾病名
- 医生说出完全不同的疾病名称
"""

# 定义节点函数
def patient_node(state: GameState, game_id=None) -> Dict:
    """病人节点，生成病人回复"""
    import re
    messages = state["messages"]
    diagnosis = state.get("diagnosis", "")

    # 检查是否刚从身体节点返回
    last_message = messages[-1] if messages else None
    if last_message and last_message["sender"] == "body":
        # 如果最后一条消息是body的回复，说明病人正在询问身体

        # 获取医生最近的问题，以便病人在回答时考虑
        doctor_question = ""
        for msg in reversed(messages[:-1]):  # 排除最后一条body消息
            if msg["sender"] == "doctor":
                doctor_question = msg["content"]
                break

        # 构造特殊提示，帮助病人基于身体感知回复医生
        body_response = last_message["content"]

        # 格式化完整的对话历史，排除身体消息
        formatted_messages = []
        for msg in messages:
            if msg["sender"] != "body":
                formatted_messages.append(f"{msg['sender']}: {msg['content']}")
        formatted_history = "\n".join(formatted_messages)

        special_prompt = f"""
你是一位病人，刚才询问了自己的身体感受，得到了以下反馈:

{body_response}

完整的对话历史:
{formatted_history}

医生最近的问题或回复是: "{doctor_question}"

请基于这些身体感受和完整的对话历史，以病人的身份回复医生。你的回复必须：
1. 回应医生的问题（如果有）
2. 简短直接，只描述症状，不包含医学诊断
3. 使用普通人的语言，避免专业术语
4. 自然、真实地表达你的感受
5. 不要提及你"询问身体"这一行为
6. 不要复述全部身体反馈，只选择与医生问题相关的症状
7. 确保你的回复有实际内容，不能为空
8. 不要在回复中包含任何[询问身体:xxx]格式的内容
9. 保持与之前对话的连贯性
"""
        content = invoke_llm(special_prompt, PATIENT_SYSTEM_MESSAGE, game_id)

        # 确保内容不为空
        if not content.strip():
            content = "医生，我最近感觉身体确实不太舒服，具体症状有点复杂，能否请您详细问诊？"

        # 再次检查并清理可能的询问身体内容
        content = re.sub(r'\s*\[\s*询问身体\s*:\s*.*?\]\s*', '', content)
        content = re.sub(r'\s*\[\s*询问身体\s*\]\s*:?\s*', '', content)
        content = content.strip()

        # 如果清理后内容为空，提供默认回复
        if not content.strip():
            content = "医生，根据我的感受，症状确实比较明显。您能给我一些建议吗？"

        # 创建病人消息
        new_message = {"sender": "patient", "content": content}

        # 返回新状态，进入系统检查
        return {
            "messages": messages + [new_message],
            "current_sender": "system",  # 直接进入系统检查
            "diagnosis": diagnosis,
            "game_over": False
        }

    # 不再检查医生是否给出诊断，让患者自己判断如何回应

    # 构建提示
    formatted_messages = "\n".join([f"{msg['sender']}: {msg['content']}" for msg in messages])

    # 不再添加特殊指令，让患者自己判断如何回应医生
    prompt = patient_prompt.format(messages=formatted_messages)

    # 如果是游戏第一次开始，确保病人有一个友好的问候，并基于初始症状
    if len(messages) <= 1:
        # 获取初始症状信息
        initial_symptoms = get_initial_symptoms(diagnosis, game_id)

        # 记录初始症状到日志（如果有game_id）
        if game_id and "api_logs" in globals() and game_id in globals()["api_logs"]:
            globals()["api_logs"][game_id].append(f"初始症状信息:\n{initial_symptoms}")

        # 构建包含初始症状的问候提示
        greeting_prompt = f"""
你是第一次去医院的病人，你感受到以下症状：

{initial_symptoms}

请用1句话友好地向医生问好，并简要描述你的主要症状。不要列出所有症状，只提及最明显的1-2个。
不要使用[询问身体:xxx]格式。不要直接复制症状列表，要用自然的语言描述。
"""
        content = invoke_llm(greeting_prompt, PATIENT_SYSTEM_MESSAGE, game_id)
    else:
        # 获取病人回复
        content = invoke_llm(prompt, PATIENT_SYSTEM_MESSAGE, game_id)

    # 确保内容不为空
    if not content.strip():
        content = "医生，我能再详细说明一下我的症状吗？"

    # 检查是否需要询问身体 - 使用更严格的格式匹配
    # 匹配[询问身体:xxx]格式，包括可能的空格和换行
    inquiry_match = re.search(r'\s*\[\s*询问身体\s*:\s*(.*?)\]\s*', content)

    # 初始消息不应该直接询问身体
    if len(messages) <= 1 and inquiry_match:
        # 如果是初始消息却包含询问身体，去掉询问部分
        content = re.sub(r'\s*\[\s*询问身体\s*:\s*.*?\]\s*', '', content)
        # 匹配旧格式[询问身体]
        content = re.sub(r'\s*\[\s*询问身体\s*\]\s*:?\s*', '', content)
        content = content.strip()
        new_message = {"sender": "patient", "content": content}
        return {
            "messages": messages + [new_message],
            "current_sender": "system",
            "diagnosis": diagnosis,
            "game_over": False
        }
    elif inquiry_match and inquiry_match.group(1).strip():  # 确保询问内容不为空
        # 当检测到询问身体时，只处理询问身体的部分，不生成对医生的回复
        # 提取询问内容
        inquiry_content = inquiry_match.group(1).strip()

        # 创建只包含询问身体内容的消息
        inquiry_message = {"sender": "patient", "content": f"[询问身体:{inquiry_content}]"}

        # 直接进入body节点，不生成对医生的回复
        return {
            "messages": messages + [inquiry_message],
            "current_sender": "body",
            "diagnosis": diagnosis,
            "game_over": False
        }
    else:
        # 不询问身体，直接进入系统检查
        new_message = {"sender": "patient", "content": content}
        return {
            "messages": messages + [new_message],
            "current_sender": "system",
            "diagnosis": diagnosis,
            "game_over": False
        }

def get_initial_symptoms(diagnosis: str, game_id=None) -> str:
    """获取初始症状信息，用于游戏开始时"""
    # 使用缓存避免重复调用
    if "initial_symptoms_cache" not in globals():
        globals()["initial_symptoms_cache"] = {}

    # 生成缓存键
    cache_key = f"{diagnosis}_{game_id}" if game_id else diagnosis

    # 检查缓存中是否已有结果
    if cache_key in globals()["initial_symptoms_cache"]:
        print(f"使用缓存的初始症状: {cache_key}")
        return globals()["initial_symptoms_cache"][cache_key]

    # 构建提示
    prompt = f"""
你代表病人的身体感官系统。病人得了{diagnosis}，但病人不知道自己的疾病名称。
请提供与{diagnosis}相关的初始症状描述，使用简洁的要点形式。
这些症状将作为病人的基础感受，帮助病人在游戏开始时能够描述自己的不适。
请确保症状描述：
1. 典型且明显，能够引导医生进行诊断
2. 不要直接透露疾病名称
3. 使用简洁的要点形式,输出尽量少
"""

    # 获取身体回复
    content = invoke_llm(prompt, BODY_SYSTEM_MESSAGE + f"\n当前病名是：{diagnosis}。请描述初始症状。", game_id)

    # 确保内容不为空
    if not content.strip():
        content = f"- 与{diagnosis}相关的典型症状\n- 具体表现为常见的不适感"

    # 保存到缓存
    globals()["initial_symptoms_cache"][cache_key] = content

    return content

def body_node(state: GameState, game_id=None) -> Dict:
    """身体节点，生成身体感官响应"""
    import re
    messages = state["messages"]
    diagnosis = state.get("diagnosis", "")

    # 获取病人的询问 - 使用严格的格式匹配
    patient_message = messages[-1]["content"]

    # 提取方括号内的内容，使用更严格的正则表达式
    # 匹配[询问身体:xxx]格式，包括可能的空格和换行
    inquiry_match = re.search(r'\s*\[\s*询问身体\s*:\s*(.*?)\]\s*', patient_message)

    if inquiry_match and inquiry_match.group(1).strip():
        patient_query = inquiry_match.group(1).strip()
    else:
        # 尝试匹配旧格式[询问身体]
        old_format_match = re.search(r'\s*\[\s*询问身体\s*\]\s*:?\s*(.*)', patient_message)
        if old_format_match and old_format_match.group(1).strip():
            patient_query = old_format_match.group(1).strip()
        else:
            # 如果都没匹配到，使用默认查询
            patient_query = "我的症状是什么？"

    # 构建提示
    formatted_messages = "\n".join([f"{msg['sender']}: {msg['content']}" for msg in messages])
    prompt = body_prompt.format(
        messages=formatted_messages,
        diagnosis=diagnosis
    )

    # 获取身体回复
    content = invoke_llm(prompt, BODY_SYSTEM_MESSAGE + f"\n当前病名是：{diagnosis}。针对'{patient_query}'请描述相关的身体感受。", game_id)

    # 确保内容不为空
    if not content.strip():
        content = f"- 与{diagnosis}相关的典型症状\n- 具体表现为常见的不适感"

    # 更新状态
    new_message = {"sender": "body", "content": content}

    return {
        "messages": messages + [new_message],
        "current_sender": "patient",
        "diagnosis": diagnosis,
        "game_over": False
    }

def system_node(state: GameState, game_id=None) -> Dict:
    """系统节点，负责检查消息格式和游戏状态"""
    messages = state["messages"]
    diagnosis = state["diagnosis"]

    # 如果没有消息，返回当前状态
    if not messages:
        return state

    # 首先清理所有病人消息中的询问身体内容
    import re
    for i, msg in enumerate(messages):
        if msg["sender"] == "patient":
            content = msg["content"]
            # 使用更严格的正则表达式清理询问身体格式
            # 匹配[询问身体:xxx]格式，包括可能的空格和换行
            cleaned_content = re.sub(r'\s*\[\s*询问身体\s*:\s*.*?\]\s*', '', content)
            # 匹配旧格式[询问身体]
            cleaned_content = re.sub(r'\s*\[\s*询问身体\s*\]\s*:?\s*', '', cleaned_content)
            # 去除可能的多余空格
            cleaned_content = cleaned_content.strip()

            # 只在内容有变化时更新
            if cleaned_content != content:
                messages[i]["content"] = cleaned_content

    # 获取最新的消息
    current_message = messages[-1]

    # 检查是否是空白消息，如果是则移除
    if current_message["sender"] == "patient" and not current_message["content"].strip():
        # 如果最后一条消息是空白的，移除它
        messages = messages[:-1]
        if not messages:
            return state
        current_message = messages[-1]

    # 检查是否是医生消息，以及是否可能包含诊断
    diagnosis_result = None
    if current_message["sender"] == "doctor":
        # 根据配置决定是否使用关键词判断或直接使用LLM判断
        should_check_diagnosis = True

        if GAME_CONFIG["use_keyword_diagnosis_check"]:
            # 使用关键词判断是否包含诊断相关词语
            message_text = current_message["content"].lower()
            should_check_diagnosis = (diagnosis.lower() in message_text) or any(term in message_text for term in ["诊断", "判断", "认为", "确定", "可能是", "应该是", "我觉得是", "你有", "你患了"])

        # 如果需要检查诊断（关键词判断为真或配置为不使用关键词判断）
        if should_check_diagnosis:
            # 构建特殊提示来检查诊断是否正确
            diagnosis_prompt = f"""
医生的消息: "{current_message['content']}"
正确的诊断: "{diagnosis}"

医生是否正确诊断出了疾病？请分析医生的回复是否明确指出了正确的疾病名称。
只有当医生明确指出正确疾病名称时才算正确，如果医生提到了错误的疾病，一定是不正确的。
请输出"诊断正确: 是/否"。
"""
            diagnosis_result = invoke_llm(diagnosis_prompt, "你是医学诊断评估专家，判断医生的诊断是否与标准诊断匹配。", game_id)

            # 解析诊断结果 - 使用更鲁棒的方法
            # 1. 首先尝试精确匹配标准格式
            is_correct_diagnosis = "诊断正确: 是" in diagnosis_result

            # 2. 如果没有精确匹配，尝试更宽松的匹配
            if not is_correct_diagnosis:
                import re
                # 匹配"诊断正确"或"正确诊断"等相关表述后跟着肯定词
                correct_patterns = [
                    r'诊断正确\s*[:：]?\s*(是|正确|对|没错|确实|肯定)',
                    r'正确诊断\s*[:：]?\s*(是|正确|对|没错|确实|肯定)',
                    r'诊断(是|正确|对|没错|确实|肯定)(正确|对|没错)',
                    r'医生(正确|准确)地?诊断',
                    r'医生的诊断是正确的',
                    r'诊断结果(正确|准确|符合)',
                    r'(正确|准确)地?判断出了?疾病'
                ]

                # 匹配否定表述
                incorrect_patterns = [
                    r'诊断正确\s*[:：]?\s*(否|不正确|不对|错误|不准确)',
                    r'诊断不正确',
                    r'诊断错误',
                    r'没有正确诊断',
                    r'医生没有(正确|准确)诊断',
                    r'医生的诊断(不正确|不准确|有误|错误)'
                ]

                # 先检查是否有明确的否定表述
                has_negative = any(re.search(pattern, diagnosis_result, re.IGNORECASE) for pattern in incorrect_patterns)

                # 如果没有否定表述，再检查是否有肯定表述
                if not has_negative:
                    is_correct_diagnosis = any(re.search(pattern, diagnosis_result, re.IGNORECASE) for pattern in correct_patterns)
            if is_correct_diagnosis:
                return {
                    "messages": messages + [{"sender": "system", "content": f"恭喜！你正确诊断出了病人的疾病：{diagnosis}。"}],
                    "current_sender": "system",
                    "diagnosis": diagnosis,
                    "game_over": True,
                    "system_notes": diagnosis_result  # 保存系统的思考过程
                }

    # 对于医生消息，直接返回
    if current_message["sender"] == "doctor":
        # 直接轮到病人回复
        return {
            "messages": messages,
            "current_sender": "patient",
            "diagnosis": diagnosis,
            "game_over": False,
            "system_notes": "医生消息已接收"  # 更新系统笔记
        }

    # 只对病人消息进行格式检查
    if current_message["sender"] == "patient":
        # 检查是否为空消息
        if not current_message["content"].strip():
            # 如果消息为空，提供默认内容
            default_content = "医生，我能否再详细描述一下我的症状？"
            fixed_message = {"sender": "patient", "content": default_content}

            return {
                "messages": messages[:-1] + [fixed_message],  # 替换空消息
                "current_sender": "doctor",
                "diagnosis": diagnosis,
                "game_over": False,
                "system_notes": "空白消息已替换为默认内容"
            }

        # 根据配置决定是否进行LLM检查
        if GAME_CONFIG["check_patient_response"]:
            # 构建提示
            formatted_messages = "\n".join([f"{msg['sender']}: {msg['content']}" for msg in messages[:-1]])
            prompt = system_prompt.format(
                messages=formatted_messages,
                current_message=current_message["content"],
                sender=current_message["sender"],
                diagnosis=diagnosis
            )

            # 获取系统判断
            system_response = invoke_llm(prompt, SYSTEM_REFEREE_MESSAGE + f"\n正确的诊断是：{diagnosis}", game_id)

            # 解析系统回复 - 使用更鲁棒的方法
            # 1. 首先尝试精确匹配标准格式
            is_reasonable = "符合要求: 是" in system_response

            # 2. 如果没有精确匹配，尝试更宽松的匹配
            if not is_reasonable:
                import re
                # 匹配"符合要求"或"符合规则"或"合理"等相关表述后跟着肯定词
                reasonable_patterns = [
                    r'符合要求\s*[:：]?\s*(是|正确|合理|可以|没问题|通过)',
                    r'符合规则\s*[:：]?\s*(是|正确|合理|可以|没问题|通过)',
                    r'合理性\s*[:：]?\s*(是|正确|合理|可以|没问题|通过)',
                    r'(合理|正确|恰当|适当)\s*[:：]?\s*(是|正确|合理|可以|没问题|通过)',
                    r'回复(合理|正确|恰当|适当)',
                    r'没有问题',
                    r'可以接受'
                ]

                # 匹配否定表述
                unreasonable_patterns = [
                    r'符合要求\s*[:：]?\s*(否|不正确|不合理|不可以|有问题|不通过)',
                    r'不符合要求',
                    r'不合理',
                    r'有问题',
                    r'不恰当',
                    r'不适当'
                ]

                # 先检查是否有明确的否定表述
                has_negative = any(re.search(pattern, system_response, re.IGNORECASE) for pattern in unreasonable_patterns)

                # 如果没有否定表述，再检查是否有肯定表述
                if not has_negative:
                    is_reasonable = any(re.search(pattern, system_response, re.IGNORECASE) for pattern in reasonable_patterns)

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
5. 回复简短直接，不超过1句话
6. 确保回复有实际内容，不能为空
"""
                # 生成修正后的病人回复
                fixed_content = invoke_llm(fix_prompt, PATIENT_SYSTEM_MESSAGE + "\n请确保生成合理的病人回复，避免之前的问题。", game_id)

                # 确保内容不为空
                if not fixed_content.strip():
                    fixed_content = "医生，我想再详细说明一下我的症状，我确实感到不舒服，但很难用专业术语描述。"

                # 再次清理询问身体内容和特殊格式
                # 匹配[询问身体:xxx]格式，包括可能的空格和换行
                fixed_content = re.sub(r'\s*\[\s*询问身体\s*:\s*.*?\]\s*', '', fixed_content)
                # 匹配旧格式[询问身体]
                fixed_content = re.sub(r'\s*\[\s*询问身体\s*\]\s*:?\s*', '', fixed_content)
                # 去除可能的多余空格
                fixed_content = fixed_content.strip()

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
        else:
            # 不进行LLM检查，直接轮到医生回复
            return {
                "messages": messages,
                "current_sender": "doctor",
                "diagnosis": diagnosis,
                "game_over": False,
                "system_notes": "跳过病人消息格式检查（已禁用）"
            }

    # 其他情况，直接返回当前状态
    return state