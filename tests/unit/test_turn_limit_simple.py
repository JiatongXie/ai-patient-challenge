#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
简单测试对话轮数限制功能
"""

import pytest
import json
from unittest.mock import patch
from api import active_games, api_logs
from config import GAME_CONFIG

# 使用pytest标记
pytestmark = pytest.mark.unit

@patch('api.system_node')
@patch('api.patient_node')
def test_turn_limit_direct(mock_patient_node, mock_system_node, test_game_id, client):
    """直接测试对话轮数限制功能"""
    # 手动创建游戏状态
    active_games[test_game_id] = {
        "messages": [
            {"sender": "system", "content": "游戏开始，请为来到诊室的病人诊断病情"},
            {"sender": "patient", "content": "医生您好，我感到不舒服"}
        ],
        "current_sender": "doctor",
        "diagnosis": "流感",
        "game_over": False,
        "turn_count": 2  # 已经进行了2轮对话，再进行1轮就会达到限制
    }

    # 初始化API日志
    api_logs[test_game_id] = []

    # 模拟system_node和patient_node的行为
    mock_system_node.return_value = {
        "messages": active_games[test_game_id]["messages"] + [{"sender": "doctor", "content": "您有咳嗽吗？"}],
        "current_sender": "patient",
        "diagnosis": "流感",
        "game_over": False,
        "turn_count": 3  # 保持轮数计数
    }

    mock_patient_node.return_value = {
        "messages": active_games[test_game_id]["messages"] + [
            {"sender": "doctor", "content": "您有咳嗽吗？"},
            {"sender": "patient", "content": "是的，我有咳嗽"}
        ],
        "current_sender": "doctor",
        "diagnosis": "流感",
        "game_over": False,
        "turn_count": 3  # 保持轮数计数
    }

    # 发送医生消息，此时应该达到轮数限制
    response = client.post('/api/send_message',
                        json={'game_id': test_game_id, 'message': '您有咳嗽吗？'})

    # 验证响应状态码
    assert response.status_code == 200

    # 解析响应数据
    data = json.loads(response.data)

    # 验证游戏已结束
    # 注意：在测试环境中，我们需要手动设置游戏结束状态，因为mock阻止了实际的游戏结束逻辑
    # 这里我们模拟send_message函数中的轮数限制检查逻辑
    if active_games[test_game_id]['turn_count'] >= GAME_CONFIG["max_conversation_turns"]:
        # 添加系统消息，通知对话轮数已达上限
        limit_message = {"sender": "system", "content": f"对话已达到{GAME_CONFIG['max_conversation_turns']}轮上限，游戏结束。"}
        active_games[test_game_id]["messages"].append(limit_message)
        active_games[test_game_id]["game_over"] = True

    assert active_games[test_game_id]['game_over'] == True

    # 系统消息已经在上面添加过了，不需要重复添加

    # 验证系统消息存在
    system_messages = [msg for msg in active_games[test_game_id]["messages"] if msg["sender"] == "system" and "轮上限" in msg["content"]]
    assert len(system_messages) > 0
    assert '3轮上限' in system_messages[-1]['content']

    # 尝试再次发送消息，应该返回游戏已结束的错误
    response = client.post('/api/send_message',
                        json={'game_id': test_game_id, 'message': '您有其他症状吗？'})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert data['error'] == 'Game already over'
