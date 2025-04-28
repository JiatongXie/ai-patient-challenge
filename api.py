from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import re

from game_engine import (
    patient_node,
    body_node,
    system_node,
    invoke_llm,
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

# 自动保存对话函数
def auto_save_conversation(game_id):
    """自动保存对话历史到服务器"""
    if game_id not in active_games:
        return None
    
    state = active_games[game_id]
    logs = api_logs.get(game_id, [])
    
    # 创建保存目录
    os.makedirs("conversations", exist_ok=True)
    
    # 生成文件名 (使用game_id确保同一对话使用同一文件)
    filename = f"conversations/conversation_{game_id}.txt"
    
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
                # 清理询问身体内容
                new_msg["content"] = re.sub(r'\[询问身体:.*?\]', '', new_msg["content"]).strip()
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
    # 可选的疾病列表
    diseases = [
        "流感", "肺炎", "胃溃疡", "偏头痛", "扁桃体炎", 
        "高血压", "糖尿病", "关节炎", "哮喘", "过敏性鼻炎"
    ]
    
    import random
    diagnosis = random.choice(diseases)
    
    # 生成游戏ID
    game_id = str(uuid.uuid4())
    
    # 创建初始状态
    initial_state = {
        "messages": [{"sender": "system", "content": "游戏开始，病人即将进入诊室。"}],
        "current_sender": "patient",
        "diagnosis": diagnosis,
        "game_over": False
    }
    
    # 存储游戏状态
    active_games[game_id] = initial_state
    api_logs[game_id] = []
    
    # 生成病人的初始消息
    patient_state = patient_node(initial_state)
    
    # 确保初始消息不包含询问身体内容
    for i, msg in enumerate(patient_state["messages"]):
        if msg["sender"] == "patient":
            # 清理可能的询问身体内容
            cleaned_content = re.sub(r'\[询问身体:.*?\]', '', msg["content"]).strip()
            if not cleaned_content:
                cleaned_content = "医生您好，我最近感觉身体不舒服，来看看是怎么回事。"
            patient_state["messages"][i]["content"] = cleaned_content
    
    # 进行系统检查
    system_checked_state = system_node(patient_state)
    
    # 更新游戏状态
    active_games[game_id] = {
        "messages": system_checked_state["messages"],
        "current_sender": "doctor",  # 轮到医生
        "diagnosis": diagnosis,
        "game_over": False
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
    
    return jsonify(response)

@app.route('/api/send_message', methods=['POST'])
def send_message():
    """发送消息"""
    data = request.json
    game_id = data.get('game_id')
    message = data.get('message')
    
    if not game_id or not message or game_id not in active_games:
        return jsonify({"error": "Invalid request"}), 400
    
    # 获取当前游戏状态
    current_state = active_games[game_id]
    
    # 如果游戏已结束，返回错误
    if current_state.get("game_over", False):
        return jsonify({"error": "Game already over"}), 400
    
    # 如果不是医生的回合，返回错误
    if current_state.get("current_sender") != "doctor":
        return jsonify({"error": "Not doctor's turn"}), 400
    
    # 添加医生消息
    doctor_state = {
        "messages": current_state["messages"] + [{"sender": "doctor", "content": message}],
        "current_sender": "system",
        "diagnosis": current_state.get("diagnosis"),
        "game_over": current_state.get("game_over", False)
    }
    
    # 系统检查消息
    system_state = system_node(doctor_state)
    
    # 检查游戏是否结束
    if system_state.get("game_over", False):
        active_games[game_id] = system_state
        
        # 自动保存对话
        auto_save_conversation(game_id)
        
        # 返回游戏结束信息
        return jsonify({
            "messages": [msg for msg in system_state["messages"] if msg["sender"] != "body"],
            "current_sender": "system",
            "game_over": True,
            "diagnosis": system_state.get("diagnosis")
        })
    
    # 如果不是病人回合，直接返回系统状态
    if system_state.get("current_sender") != "patient":
        active_games[game_id] = system_state
        return jsonify({
            "messages": [msg for msg in system_state["messages"] if msg["sender"] != "body"],
            "current_sender": system_state.get("current_sender"),
            "game_over": False
        })
    
    # 病人回合 - 生成病人回复
    patient_state = patient_node(system_state)
    
    # 检查患者是否询问身体
    if patient_state.get("current_sender") == "body":
        last_patient_msg = None
        
        # 查找最后一条患者消息
        for msg in reversed(patient_state["messages"]):
            if msg["sender"] == "patient":
                last_patient_msg = msg
                break
        
        if last_patient_msg:
            # 提取询问身体的内容（使用严格的格式匹配）
            inquiry_match = re.search(r'\[询问身体:(.*?)\]', last_patient_msg["content"])
            if inquiry_match and inquiry_match.group(1).strip():
                api_logs[game_id].append(f"患者询问身体: {inquiry_match.group(1).strip()}")
            else:
                # 兼容旧格式，但确保不会记录普通消息
                old_format = last_patient_msg["content"].replace("[询问身体]:", "").strip()
                if "[询问身体]" in last_patient_msg["content"]:
                    api_logs[game_id].append(f"患者询问身体: {old_format}")
            
            # 调用身体节点
            body_state = body_node(patient_state)
            
            # 找到身体回复消息
            body_msg = None
            for msg in reversed(body_state["messages"]):
                if msg["sender"] == "body":
                    body_msg = msg
                    break
            
            if body_msg and body_msg["content"].strip():
                api_logs[game_id].append(f"身体感知响应:\n{body_msg['content']}")
                
                # 使用更新后的patient_node处理body回复
                final_patient_state = patient_node(body_state)
                
                # 找到基于身体感知生成的患者回复
                new_patient_msg = None
                for msg in reversed(final_patient_state["messages"]):
                    if msg["sender"] == "patient" and msg not in body_state["messages"]:
                        new_patient_msg = msg
                        break
                
                if new_patient_msg and new_patient_msg["content"].strip():
                    api_logs[game_id].append(f"患者基于身体感知的回复: {new_patient_msg['content']}")
                
                # 系统验证最终的病人消息
                final_state = system_node(final_patient_state)
                
                # 更新游戏状态
                active_games[game_id] = final_state
                
                # 自动保存对话
                auto_save_conversation(game_id)
                
                # 过滤所有空白消息
                messages_to_return = []
                for msg in final_state["messages"]:
                    if msg["sender"] != "body" and (not msg["sender"] == "patient" or msg["content"].strip()):
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
    final_state = system_node(patient_state)
    
    # 更新游戏状态
    active_games[game_id] = final_state
    
    # 自动保存对话
    auto_save_conversation(game_id)
    
    # 过滤所有空白消息和身体消息
    messages_to_return = []
    for msg in final_state["messages"]:
        if msg["sender"] != "body" and (not msg["sender"] == "patient" or msg["content"].strip()):
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
    
    return jsonify({
        "messages": [msg for msg in state["messages"] if msg["sender"] != "body"],
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001) 