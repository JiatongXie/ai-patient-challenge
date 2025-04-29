#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试配置文件
包含测试的共享夹具和配置
"""

import pytest
import os
import sys
import uuid
from unittest.mock import patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import app, active_games, recent_requests, api_logs
from config import GAME_CONFIG

@pytest.fixture
def client():
    """创建测试客户端"""
    app.testing = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def clean_state():
    """清理测试状态"""
    # 保存原始配置
    original_max_turns = GAME_CONFIG["max_conversation_turns"]
    
    # 清空活跃游戏字典和请求缓存
    active_games.clear()
    recent_requests.clear()
    
    yield
    
    # 恢复原始配置
    GAME_CONFIG["max_conversation_turns"] = original_max_turns
    
    # 清空活跃游戏字典和请求缓存
    active_games.clear()
    recent_requests.clear()

@pytest.fixture
def test_game_id():
    """生成测试游戏ID"""
    return str(uuid.uuid4())

@pytest.fixture
def test_game_state(test_game_id):
    """创建测试游戏状态"""
    # 设置较小的对话轮数限制，方便测试
    GAME_CONFIG["max_conversation_turns"] = 3
    
    # 创建游戏状态
    active_games[test_game_id] = {
        "messages": [
            {"sender": "system", "content": "游戏开始，请为来到诊室的病人诊断病情"},
            {"sender": "patient", "content": "医生您好，我感到不舒服"}
        ],
        "current_sender": "doctor",
        "diagnosis": "流感",
        "game_over": False,
        "turn_count": 0
    }
    
    # 初始化API日志
    api_logs[test_game_id] = []
    
    return test_game_id
