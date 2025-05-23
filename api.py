from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import re

from config import GAME_CONFIG
from game_engine import (
    patient_node,
    body_node,
    system_node,
    invoke_llm,
    save_api_log,
    PATIENT_SYSTEM_MESSAGE,
    BODY_SYSTEM_MESSAGE,
    SYSTEM_REFEREE_MESSAGE
)

app = Flask(__name__)
# 配置CORS，允许所有请求
CORS(app, resources={r"/*": {"origins": "*", "supports_credentials": True, "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]}})

# 存储游戏状态的字典
active_games = {}

# 存储API日志
api_logs = {}

# 存储最近的请求，用于去重
recent_requests = {}

# 存储疾病统计数据的字典 {疾病名称: {"attempts": 尝试次数, "correct": 正确次数}}
disease_stats = {}

# 加载疾病统计数据
def load_disease_stats():
    """从文件加载疾病统计数据"""
    global disease_stats
    stats_file = "disease_stats.json"

    if os.path.exists(stats_file):
        try:
            with open(stats_file, "r", encoding="utf-8") as f:
                disease_stats = json.load(f)
            print(f"已加载疾病统计数据: {len(disease_stats)}个疾病")
        except Exception as e:
            print(f"加载疾病统计数据失败: {e}")
            disease_stats = {}

    # 确保所有配置中的疾病都有统计数据
    for disease in GAME_CONFIG["diseases"]:
        if disease not in disease_stats:
            disease_stats[disease] = {"attempts": 0, "correct": 0}

# 保存疾病统计数据
def save_disease_stats():
    """将疾病统计数据保存到文件"""
    stats_file = "disease_stats.json"
    try:
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(disease_stats, f, ensure_ascii=False, indent=2)
        print("疾病统计数据已保存")
    except Exception as e:
        print(f"保存疾病统计数据失败: {e}")

# 更新疾病统计数据
def update_disease_stats(disease, is_correct):
    """更新疾病统计数据

    Args:
        disease: 疾病名称
        is_correct: 是否正确诊断
    """
    global disease_stats

    if disease not in disease_stats:
        disease_stats[disease] = {"attempts": 0, "correct": 0}

    disease_stats[disease]["attempts"] += 1
    if is_correct:
        disease_stats[disease]["correct"] += 1

    # 保存更新后的统计数据
    save_disease_stats()

# 初始化时加载统计数据
load_disease_stats()

# 自动保存对话函数
def auto_save_conversation(game_id):
    """自动保存对话历史到服务器"""
    if game_id not in active_games:
        return None

    state = active_games[game_id]
    logs = api_logs.get(game_id, [])

    # 创建保存目录
    os.makedirs("conversations", exist_ok=True)

    # 存储游戏会话对话文件名的全局字典
    if "game_conversation_files" not in globals():
        globals()["game_conversation_files"] = {}

    # 确定文件名
    if game_id in globals()["game_conversation_files"]:
        # 使用已存在的对话文件
        filename = globals()["game_conversation_files"][game_id]
    else:
        # 查找是否已经存在该游戏ID的对话文件
        import glob
        existing_files = glob.glob(f"conversations/conversation_*_{game_id}.txt")

        if existing_files:
            # 如果找到现有文件，使用第一个找到的文件
            filename = existing_files[0]
        else:
            # 生成新的文件名 (使用时间戳+game_id确保按时间排序且不会重名)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"conversations/conversation_{timestamp}_{game_id}.txt"

        # 保存到全局字典中
        globals()["game_conversation_files"][game_id] = filename

    # 写入文件
    with open(filename, "w", encoding="utf-8") as f:
        # 写入标题
        f.write("="*70 + "\n")
        f.write(" "*20 + "AI问诊小游戏记录\n")
        f.write("="*70 + "\n\n")

        # 写入对话历史
        f.write("## 对话内容\n")
        f.write("-"*70 + "\n\n")

        # 清理病人消息中可能的询问身体内容
        messages_to_save = []
        for msg in state["messages"]:
            if msg["sender"] == "patient":
                # 复制消息以避免修改原始状态
                new_msg = msg.copy()
                # 清理询问身体内容，使用更严格的正则表达式
                # 匹配[询问身体:xxx]或[询问身体：xxx]格式，包括可能的空格和换行，同时支持中英文冒号
                new_msg["content"] = re.sub(r'\s*\[\s*询问身体\s*[：:]\s*.*?\]\s*', '', new_msg["content"])
                # 匹配旧格式[询问身体]
                new_msg["content"] = re.sub(r'\s*\[\s*询问身体\s*\]\s*[：:]?\s*', '', new_msg["content"])
                # 去除可能的多余空格
                new_msg["content"] = new_msg["content"].strip()
                messages_to_save.append(new_msg)
            elif msg["sender"] != "body":  # 排除身体消息
                messages_to_save.append(msg)

        # 写入清理后的消息
        for msg in messages_to_save:
            # 只显示医生、病人和最终的系统消息
            if msg["sender"] in ["doctor", "patient"] or (msg["sender"] == "system" and "恭喜" in msg["content"]):
                sender = msg["sender"].upper()
                if sender == "PATIENT":
                    sender = "👤 病人"
                elif sender == "DOCTOR":
                    sender = "👨‍⚕️ 医生"
                elif sender == "SYSTEM":
                    sender = "🎮 系统"

                f.write(f"{sender}：{msg['content']}\n\n")

        # 写入游戏日志
        if logs:
            f.write("\n\n## 游戏日志\n")
            f.write("-"*70 + "\n\n")
            for log in logs:
                f.write(log + "\n\n")

        # 写入时间戳
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"\n最后更新时间: {timestamp}\n")

    return filename

@app.route('/api/new_game', methods=['POST'])
def new_game():
    """创建一个新游戏"""
    import time
    import hashlib

    # 生成请求ID（基于客户端IP和时间戳）
    client_ip = request.remote_addr
    timestamp = int(time.time())
    request_id = hashlib.md5(f"{client_ip}:{timestamp // 2}".encode()).hexdigest()  # 每2秒内的请求视为相同请求

    # 检查是否是重复请求
    if request_id in recent_requests:
        print(f"检测到重复的new_game请求，返回缓存的响应: {request_id}")
        return jsonify(recent_requests[request_id])

    # 使用配置文件中的疾病列表
    import random
    diagnosis = random.choice(GAME_CONFIG["diseases"])

    # 生成游戏ID
    game_id = str(uuid.uuid4())

    # 创建初始状态
    initial_state = {
        "messages": [{"sender": "system", "content": "游戏开始，请为来到诊室的病人诊断病情"}],
        "current_sender": "patient",
        "diagnosis": diagnosis,
        "game_over": False,
        "turn_count": 0  # 初始化对话轮数计数
    }

    # 存储游戏状态
    active_games[game_id] = initial_state
    api_logs[game_id] = []

    # 记录游戏开始和诊断信息
    api_logs[game_id].append(f"游戏开始，诊断为: {diagnosis}")

    # 生成病人的初始消息 - patient_node内部会自动调用get_initial_symptoms
    patient_state = patient_node(initial_state, game_id)

    # 确保初始消息不包含询问身体内容
    for i, msg in enumerate(patient_state["messages"]):
        if msg["sender"] == "patient":
            # 清理可能的询问身体内容，使用更严格的正则表达式
            # 匹配[询问身体:xxx]或[询问身体：xxx]格式，包括可能的空格和换行，同时支持中英文冒号
            cleaned_content = re.sub(r'\s*\[\s*询问身体\s*[：:]\s*.*?\]\s*', '', msg["content"])
            # 匹配旧格式[询问身体]
            cleaned_content = re.sub(r'\s*\[\s*询问身体\s*\]\s*[：:]?\s*', '', cleaned_content)
            # 去除可能的多余空格
            cleaned_content = cleaned_content.strip()

            if not cleaned_content:
                cleaned_content = "医生您好，我最近感觉身体不舒服，来看看是怎么回事。"
            patient_state["messages"][i]["content"] = cleaned_content

    # 进行系统检查
    system_checked_state = system_node(patient_state, game_id)

    # 更新游戏状态
    active_games[game_id] = {
        "messages": system_checked_state["messages"],
        "current_sender": "doctor",  # 轮到医生
        "diagnosis": diagnosis,
        "game_over": False,
        "turn_count": 0  # 初始化对话轮数计数
    }

    # 自动保存对话
    auto_save_conversation(game_id)

    # 返回游戏信息和初始消息
    response = {
        "game_id": game_id,
        "messages": [msg for msg in system_checked_state["messages"] if msg["sender"] != "body"],
        "current_sender": "doctor",
        "game_over": False
    }

    # 缓存响应，防止重复请求
    recent_requests[request_id] = response

    # 清理旧的请求缓存（只保留最近的100个请求）
    if len(recent_requests) > 100:
        # 删除最旧的请求
        oldest_key = next(iter(recent_requests))
        del recent_requests[oldest_key]

    print(f"创建新游戏成功，请求ID: {request_id}, 游戏ID: {game_id}")
    return jsonify(response)

@app.route('/api/get_config', methods=['GET'])
def get_config():
    """获取游戏配置信息"""
    # 返回前端需要的配置信息
    return jsonify({
        "max_input_length": GAME_CONFIG["max_input_length"],
        "max_conversation_turns": GAME_CONFIG["max_conversation_turns"]
    })

@app.route('/api/send_message', methods=['POST'])
def send_message():
    """发送消息"""
    data = request.json
    game_id = data.get('game_id')
    message = data.get('message')

    if not game_id or not message or game_id not in active_games:
        return jsonify({"error": "Invalid request"}), 400

    # 检查消息长度是否超过限制
    max_length = GAME_CONFIG["max_input_length"]
    if len(message) > max_length:
        return jsonify({"error": f"消息长度超过限制（最大{max_length}字）"}), 400

    # 获取当前游戏状态
    current_state = active_games[game_id]

    # 如果游戏已结束，返回错误
    if current_state.get("game_over", False):
        return jsonify({"error": "Game already over"}), 400

    # 如果不是医生的回合，返回错误
    if current_state.get("current_sender") != "doctor":
        return jsonify({"error": "Not doctor's turn"}), 400

    # 获取当前对话轮数
    current_turn_count = current_state.get("turn_count", 0)

    # 检查是否达到对话轮数限制
    max_turns = GAME_CONFIG["max_conversation_turns"]
    if current_turn_count >= max_turns:
        # 添加系统消息，通知对话轮数已达上限
        limit_message = {"sender": "system", "content": f"对话已达到{max_turns}轮上限，游戏结束。"}
        active_games[game_id]["messages"].append(limit_message)
        active_games[game_id]["game_over"] = True

        # 自动保存对话
        auto_save_conversation(game_id)

        return jsonify({
            "messages": [msg for msg in active_games[game_id]["messages"] if msg["sender"] != "body"],
            "current_sender": "system",
            "game_over": True,
            "diagnosis": current_state.get("diagnosis")
        })

    # 增加对话轮数计数
    new_turn_count = current_turn_count + 1

    # 添加医生消息
    doctor_state = {
        "messages": current_state["messages"] + [{"sender": "doctor", "content": message}],
        "current_sender": "system",
        "diagnosis": current_state.get("diagnosis"),
        "game_over": current_state.get("game_over", False),
        "turn_count": new_turn_count  # 更新对话轮数
    }

    # 系统检查消息
    system_state = system_node(doctor_state, game_id)

    # 检查游戏是否结束
    if system_state.get("game_over", False):
        # 保留对话轮数计数
        system_state["turn_count"] = new_turn_count
        active_games[game_id] = system_state

        # 自动保存对话
        auto_save_conversation(game_id)

        # 更新疾病统计数据
        diagnosis = system_state.get("diagnosis")
        if diagnosis:
            # 检查是否是正确诊断（通过查找系统消息中的"恭喜"字样）
            is_correct = False
            for msg in system_state["messages"]:
                if msg["sender"] == "system" and "恭喜" in msg["content"]:
                    is_correct = True
                    break

            # 更新统计数据
            update_disease_stats(diagnosis, is_correct)

        # 返回游戏结束信息
        return jsonify({
            "messages": [msg for msg in system_state["messages"] if msg["sender"] != "body"],
            "current_sender": "system",
            "game_over": True,
            "diagnosis": diagnosis
        })

    # 如果不是病人回合，直接返回系统状态
    if system_state.get("current_sender") != "patient":
        # 保留对话轮数计数
        system_state["turn_count"] = new_turn_count
        active_games[game_id] = system_state
        return jsonify({
            "messages": [msg for msg in system_state["messages"] if msg["sender"] != "body"],
            "current_sender": system_state.get("current_sender"),
            "game_over": False
        })

    # 病人回合 - 生成病人回复
    # 保留对话轮数计数
    system_state["turn_count"] = new_turn_count
    patient_state = patient_node(system_state, game_id)

    # 检查患者是否询问身体
    if patient_state.get("current_sender") == "body":
        last_patient_msg = None

        # 查找最后一条患者消息
        for msg in reversed(patient_state["messages"]):
            if msg["sender"] == "patient":
                last_patient_msg = msg
                break

        if last_patient_msg:
            # 提取询问身体的内容（使用更严格的格式匹配）
            # 匹配[询问身体:xxx]或[询问身体：xxx]格式，包括可能的空格和换行，同时支持中英文冒号
            inquiry_match = re.search(r'\s*\[\s*询问身体\s*[：:]\s*(.*?)\]\s*', last_patient_msg["content"])
            if inquiry_match and inquiry_match.group(1).strip():
                inquiry_content = inquiry_match.group(1).strip()
                api_logs[game_id].append(f"患者询问身体: {inquiry_content}")
            else:
                # 尝试匹配旧格式[询问身体]
                old_format_match = re.search(r'\s*\[\s*询问身体\s*\]\s*[：:]?\s*(.*)', last_patient_msg["content"])
                if old_format_match and old_format_match.group(1).strip():
                    inquiry_content = old_format_match.group(1).strip()
                    api_logs[game_id].append(f"患者询问身体: {inquiry_content}")

            # 调用身体节点
            body_state = body_node(patient_state, game_id)

            # 找到身体回复消息
            body_msg = None
            for msg in reversed(body_state["messages"]):
                if msg["sender"] == "body":
                    body_msg = msg
                    break

            if body_msg and body_msg["content"].strip():
                api_logs[game_id].append(f"身体感知响应:\n{body_msg['content']}")

                # 使用更新后的patient_node处理body回复
                final_patient_state = patient_node(body_state, game_id)

                # 找到基于身体感知生成的患者回复
                new_patient_msg = None
                for msg in reversed(final_patient_state["messages"]):
                    if msg["sender"] == "patient" and msg not in body_state["messages"]:
                        new_patient_msg = msg
                        break

                if new_patient_msg and new_patient_msg["content"].strip():
                    # 确保回复中不包含询问身体的内容
                    clean_content = re.sub(r'\s*\[\s*询问身体\s*[：:]\s*.*?\]\s*', '', new_patient_msg["content"])
                    clean_content = re.sub(r'\s*\[\s*询问身体\s*\]\s*[：:]?\s*', '', clean_content)
                    clean_content = clean_content.strip()

                    # 如果清理后内容为空，提供默认回复
                    if not clean_content:
                        clean_content = "医生，我感觉症状确实比较明显，您能给我一些建议吗？"
                        new_patient_msg["content"] = clean_content

                    api_logs[game_id].append(f"患者基于身体感知的回复: {clean_content}")

                # 系统验证最终的病人消息
                final_state = system_node(final_patient_state, game_id)

                # 检查是否需要再次验证病人回复
                # 如果system_node返回的current_sender是system，说明需要再次验证
                retry_count = 0
                max_retries = 3  # 设置最大重试次数，防止无限循环

                while final_state.get("current_sender") == "system" and retry_count < max_retries:
                    # 记录重试信息
                    api_logs[game_id].append(f"重新验证基于身体感知的病人回复 (第{retry_count+1}次)")

                    # 再次调用system_node进行验证
                    final_state = system_node(final_state, game_id)
                    retry_count += 1

                # 如果经过多次重试后仍然是system状态，强制设为doctor以避免卡住
                if final_state.get("current_sender") == "system":
                    api_logs[game_id].append("警告：多次重试后基于身体感知的回复仍未通过验证，强制设置为医生回合")
                    final_state["current_sender"] = "doctor"

                # 确保保留对话轮数计数
                if "turn_count" not in final_state and "turn_count" in doctor_state:
                    final_state["turn_count"] = doctor_state["turn_count"]
                # 更新游戏状态
                active_games[game_id] = final_state

                # 自动保存对话
                auto_save_conversation(game_id)

                # 过滤所有空白消息和清理患者消息中的询问身体内容
                messages_to_return = []
                for msg in final_state["messages"]:
                    if msg["sender"] != "body" and (not msg["sender"] == "patient" or msg["content"].strip()):
                        # 如果是患者消息，确保彻底清理询问身体内容
                        if msg["sender"] == "patient":
                            # 复制消息以避免修改原始状态
                            new_msg = msg.copy()
                            # 清理询问身体内容，使用更严格的正则表达式
                            # 匹配[询问身体:xxx]或[询问身体：xxx]格式，包括可能的空格和换行，同时支持中英文冒号
                            new_msg["content"] = re.sub(r'\s*\[\s*询问身体\s*[：:]\s*.*?\]\s*', '', new_msg["content"])
                            # 匹配旧格式[询问身体]
                            new_msg["content"] = re.sub(r'\s*\[\s*询问身体\s*\]\s*[：:]?\s*', '', new_msg["content"])
                            # 去除可能的多余空格
                            new_msg["content"] = new_msg["content"].strip()
                            messages_to_return.append(new_msg)
                        else:
                            messages_to_return.append(msg)

                # 返回更新后的消息
                return jsonify({
                    "messages": messages_to_return,
                    "current_sender": final_state.get("current_sender"),
                    "game_over": final_state.get("game_over", False)
                })
            else:
                # 如果身体消息为空，回退到普通患者回复
                patient_state["current_sender"] = "system"
        else:
            # 如果找不到患者消息，回退到普通处理
            patient_state["current_sender"] = "system"

    # 如果没有询问身体或询问身体过程有问题，走普通流程
    final_state = system_node(patient_state, game_id)

    # 检查是否需要再次验证病人回复
    # 如果system_node返回的current_sender是system，说明需要再次验证
    retry_count = 0
    max_retries = 3  # 设置最大重试次数，防止无限循环

    while final_state.get("current_sender") == "system" and retry_count < max_retries:
        # 记录重试信息
        api_logs[game_id].append(f"重新验证病人回复 (第{retry_count+1}次)")

        # 再次调用system_node进行验证
        final_state = system_node(final_state, game_id)
        retry_count += 1

    # 如果经过多次重试后仍然是system状态，强制设为doctor以避免卡住
    if final_state.get("current_sender") == "system":
        api_logs[game_id].append("警告：多次重试后仍未通过验证，强制设置为医生回合")
        final_state["current_sender"] = "doctor"

    # 确保保留对话轮数计数
    if "turn_count" not in final_state and "turn_count" in doctor_state:
        final_state["turn_count"] = doctor_state["turn_count"]
    # 更新游戏状态
    active_games[game_id] = final_state

    # 自动保存对话
    auto_save_conversation(game_id)

    # 过滤所有空白消息和身体消息，并清理患者消息中的询问身体内容
    messages_to_return = []
    for msg in final_state["messages"]:
        if msg["sender"] != "body" and (not msg["sender"] == "patient" or msg["content"].strip()):
            # 如果是患者消息，确保彻底清理询问身体内容
            if msg["sender"] == "patient":
                # 复制消息以避免修改原始状态
                new_msg = msg.copy()
                # 清理询问身体内容，使用更严格的正则表达式
                # 匹配[询问身体:xxx]或[询问身体：xxx]格式，包括可能的空格和换行，同时支持中英文冒号
                new_msg["content"] = re.sub(r'\s*\[\s*询问身体\s*[：:]\s*.*?\]\s*', '', new_msg["content"])
                # 匹配旧格式[询问身体]
                new_msg["content"] = re.sub(r'\s*\[\s*询问身体\s*\]\s*[：:]?\s*', '', new_msg["content"])
                # 去除可能的多余空格
                new_msg["content"] = new_msg["content"].strip()
                messages_to_return.append(new_msg)
            else:
                messages_to_return.append(msg)

    # 返回更新后的消息
    return jsonify({
        "messages": messages_to_return,
        "current_sender": final_state.get("current_sender"),
        "game_over": final_state.get("game_over", False)
    })

@app.route('/api/game_status/<game_id>', methods=['GET'])
def game_status(game_id):
    """获取游戏状态"""
    if game_id not in active_games:
        return jsonify({"error": "Game not found"}), 404

    state = active_games[game_id]

    # 过滤所有身体消息，并清理患者消息中的询问身体内容
    messages_to_return = []
    for msg in state["messages"]:
        if msg["sender"] != "body":
            # 如果是患者消息，确保彻底清理询问身体内容
            if msg["sender"] == "patient":
                # 复制消息以避免修改原始状态
                new_msg = msg.copy()
                # 清理询问身体内容，使用更严格的正则表达式
                # 匹配[询问身体:xxx]格式，包括可能的空格和换行
                new_msg["content"] = re.sub(r'\s*\[\s*询问身体\s*:\s*.*?\]\s*', '', new_msg["content"])
                # 匹配旧格式[询问身体]
                new_msg["content"] = re.sub(r'\s*\[\s*询问身体\s*\]\s*:?\s*', '', new_msg["content"])
                # 去除可能的多余空格
                new_msg["content"] = new_msg["content"].strip()
                messages_to_return.append(new_msg)
            else:
                messages_to_return.append(msg)

    return jsonify({
        "messages": messages_to_return,
        "current_sender": state.get("current_sender"),
        "game_over": state.get("game_over", False),
        "diagnosis": state.get("diagnosis") if state.get("game_over", False) else None
    })

@app.route('/api/logs/<game_id>', methods=['GET'])
def get_logs(game_id):
    """获取游戏日志"""
    if game_id not in active_games:
        return jsonify({"error": "Game not found"}), 404

    logs = api_logs.get(game_id, [])

    return jsonify({
        "logs": logs
    })

@app.route('/api/save_conversation/<game_id>', methods=['POST'])
def save_conversation(game_id):
    """保存对话历史并返回下载链接"""
    if game_id not in active_games:
        return jsonify({"error": "Game not found"}), 404

    # 使用自动保存函数保存文件
    filename = auto_save_conversation(game_id)

    if not filename:
        return jsonify({"error": "保存失败"}), 500

    # 创建文件内容字符串用于前端下载
    with open(filename, "r", encoding="utf-8") as f:
        conversation_text = f.read()

    return jsonify({
        "filename": filename,
        "message": "对话已保存",
        "conversation_text": conversation_text
    })

@app.route('/api/active_games', methods=['GET'])
def get_active_games():
    """获取所有活跃游戏"""
    games = []
    for game_id, state in active_games.items():
        games.append({
            "game_id": game_id,
            "message_count": len(state["messages"]),
            "game_over": state.get("game_over", False),
            "last_message": state["messages"][-1]["content"] if state["messages"] else ""
        })

    return jsonify({
        "games": games
    })

@app.route('/api/disease_stats', methods=['GET'])
def get_all_disease_stats():
    """获取所有疾病的统计数据"""
    return jsonify({
        "stats": disease_stats
    })

@app.route('/api/disease_stats/<disease>', methods=['GET'])
def get_disease_stats(disease):
    """获取特定疾病的统计数据"""
    if disease not in disease_stats:
        return jsonify({"error": "Disease not found"}), 404

    stats = disease_stats[disease]
    attempts = stats["attempts"]
    correct = stats["correct"]

    # 计算正确率
    correct_rate = (correct / attempts * 100) if attempts > 0 else 0

    return jsonify({
        "disease": disease,
        "attempts": attempts,
        "correct": correct,
        "correct_rate": round(correct_rate, 2)  # 保留两位小数
    })

@app.route('/api/current_game_stats/<game_id>', methods=['GET'])
def get_current_game_stats(game_id):
    """获取当前游戏的疾病统计数据（不显示疾病名称）"""
    if game_id not in active_games:
        return jsonify({"error": "Game not found"}), 404

    # 获取当前游戏的疾病
    current_disease = active_games[game_id].get("diagnosis")
    if not current_disease or current_disease not in disease_stats:
        return jsonify({"error": "No statistics available"}), 404

    stats = disease_stats[current_disease]
    attempts = stats["attempts"]
    correct = stats["correct"]

    # 计算正确率
    correct_rate = (correct / attempts * 100) if attempts > 0 else 0

    return jsonify({
        "attempts": attempts,
        "correct": correct,
        "correct_rate": round(correct_rate, 2)  # 保留两位小数
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)