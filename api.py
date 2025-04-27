from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

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
CORS(app)  # 允许跨域请求

# 存储游戏状态的字典
active_games = {}

# 存储API日志
api_logs = {}

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
    
    # 更新游戏状态
    active_games[game_id] = {
        "messages": patient_state["messages"],
        "current_sender": "doctor",  # 轮到医生
        "diagnosis": diagnosis,
        "game_over": False
    }
    
    # 返回游戏信息和初始消息
    response = {
        "game_id": game_id,
        "messages": [msg for msg in patient_state["messages"] if msg["sender"] != "body"],
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
    
    # 病人回合
    patient_state = patient_node(system_state)
    
    # 如果病人要询问身体
    if patient_state.get("current_sender") == "body":
        # 调用身体节点
        body_state = body_node(patient_state)
        
        # 记录身体感知内容
        for msg in body_state["messages"]:
            if msg["sender"] == "body":
                api_logs[game_id].append(f"身体感知响应:\n{msg['content']}")
        
        # 使用更新后的patient_node处理body回复
        patient_state = patient_node(body_state)
    
    # 系统验证病人消息
    final_state = system_node(patient_state)
    
    # 更新游戏状态
    active_games[game_id] = final_state
    
    # 返回更新后的消息
    return jsonify({
        "messages": [msg for msg in final_state["messages"] if msg["sender"] != "body"],
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
    """保存对话历史"""
    if game_id not in active_games:
        return jsonify({"error": "Game not found"}), 404
    
    state = active_games[game_id]
    logs = api_logs.get(game_id, [])
    
    # 创建保存目录
    os.makedirs("conversations", exist_ok=True)
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"conversations/conversation_{timestamp}.txt"
    
    # 写入文件
    with open(filename, "w", encoding="utf-8") as f:
        # 写入标题
        f.write("="*70 + "\n")
        f.write(" "*20 + "AI问诊小游戏记录\n")
        f.write("="*70 + "\n\n")
        
        # 写入对话历史
        f.write("## 对话内容\n")
        f.write("-"*70 + "\n\n")
        for msg in state["messages"]:
            # 只显示医生、病人和最终的系统消息，跳过身体消息
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
    
    return jsonify({
        "filename": filename,
        "message": "对话已保存"
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
    app.run(debug=True, port=5000) 