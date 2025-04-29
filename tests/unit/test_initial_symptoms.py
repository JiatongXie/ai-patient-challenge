#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试初始症状功能的脚本
"""

import pytest
from game_engine import get_initial_symptoms, patient_node

# 使用pytest标记
pytestmark = pytest.mark.unit

@pytest.mark.parametrize("disease", ["流感", "肺炎", "胃溃疡", "偏头痛", "扁桃体炎"])
def test_initial_symptoms(disease):
    """测试初始症状功能"""
    # 获取初始症状
    symptoms = get_initial_symptoms(disease)

    # 验证症状不为空
    assert symptoms
    assert len(symptoms) > 0

    # 创建初始状态
    initial_state = {
        "messages": [{"sender": "system", "content": "游戏开始，病人即将进入诊室。"}],
        "current_sender": "patient",
        "diagnosis": disease,
        "game_over": False
    }

    # 生成病人的初始消息
    patient_state = patient_node(initial_state)

    # 验证病人消息
    patient_messages = [msg for msg in patient_state["messages"] if msg["sender"] == "patient"]
    assert len(patient_messages) > 0

    # 验证病人消息不为空
    assert patient_messages[-1]["content"]
    assert len(patient_messages[-1]["content"]) > 0
