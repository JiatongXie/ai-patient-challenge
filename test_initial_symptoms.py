#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试初始症状功能的脚本
"""

from game_engine import get_initial_symptoms, patient_node, body_node, system_node

def test_initial_symptoms():
    """测试初始症状功能"""
    print("="*70)
    print("测试初始症状功能")
    print("="*70)
    
    # 测试几种疾病
    diseases = ["流感", "肺炎", "胃溃疡", "偏头痛", "扁桃体炎"]
    
    for disease in diseases:
        print(f"\n测试疾病: {disease}")
        print("-"*50)
        
        # 获取初始症状
        symptoms = get_initial_symptoms(disease)
        print(f"初始症状:\n{symptoms}")
        
        # 创建初始状态
        initial_state = {
            "messages": [{"sender": "system", "content": "游戏开始，病人即将进入诊室。"}],
            "current_sender": "patient",
            "diagnosis": disease,
            "game_over": False
        }
        
        # 生成病人的初始消息
        patient_state = patient_node(initial_state)
        
        # 打印病人消息
        for msg in patient_state["messages"]:
            if msg["sender"] == "patient":
                print(f"\n病人初始消息: {msg['content']}")
        
        print("-"*50)

if __name__ == "__main__":
    test_initial_symptoms()
