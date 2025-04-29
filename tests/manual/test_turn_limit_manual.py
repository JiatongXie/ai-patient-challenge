#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
手动测试对话轮数限制功能的脚本
"""

import pytest
import requests
import json
import time
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(override=True)

# 设置API基础URL
BASE_URL = "http://localhost:5001"

# 使用pytest标记
pytestmark = pytest.mark.manual

def test_conversation_turn_limit():
    """测试对话轮数限制功能"""
    print("="*70)
    print("测试对话轮数限制功能")
    print("="*70)

    # 设置较小的对话轮数限制，方便测试
    os.environ["MAX_CONVERSATION_TURNS"] = "5"
    print(f"设置对话轮数限制为: {os.environ['MAX_CONVERSATION_TURNS']}")

    # 创建新游戏
    print("\n创建新游戏...")
    response = requests.post(f"{BASE_URL}/api/new_game")
    if response.status_code != 200:
        print(f"创建游戏失败: {response.text}")
        return

    game_data = response.json()
    game_id = game_data["game_id"]
    print(f"游戏ID: {game_id}")

    # 打印初始消息
    for msg in game_data["messages"]:
        print(f"{msg['sender']}: {msg['content']}")

    # 医生的问题列表
    doctor_questions = [
        "您好，请问您有什么不舒服的地方？",
        "您的症状持续多久了？",
        "您有发烧吗？",
        "您有头痛或者肌肉酸痛吗？",
        "您最近有接触过感冒的人吗？",
        "您平时有什么慢性病史吗？",
        "您有服用过什么药物吗？",
        "您的症状会在什么时候加重？",
        "您的饮食和睡眠情况如何？",
        "根据您的症状，我认为您可能患有流感。"
    ]

    # 模拟对话，直到达到轮数限制或问题用完
    turn_count = 0
    for question in doctor_questions:
        turn_count += 1
        print(f"\n第{turn_count}轮对话:")
        print(f"医生: {question}")

        # 发送医生消息
        response = requests.post(
            f"{BASE_URL}/api/send_message",
            json={"game_id": game_id, "message": question}
        )

        # 检查响应
        if response.status_code != 200:
            print(f"发送消息失败: {response.text}")
            error_data = response.json()
            if "error" in error_data and error_data["error"] == "Game already over":
                print("游戏已结束，可能是因为达到了对话轮数限制")
            break

        # 获取响应数据
        response_data = response.json()

        # 打印新消息
        new_messages = response_data["messages"][len(game_data["messages"]):]
        for msg in new_messages:
            print(f"{msg['sender']}: {msg['content']}")

        # 更新消息历史
        game_data["messages"] = response_data["messages"]

        # 检查游戏是否结束
        if response_data.get("game_over", False):
            print("\n游戏已结束!")
            if "diagnosis" in response_data and response_data["diagnosis"]:
                print(f"诊断结果: {response_data['diagnosis']}")

            # 检查是否是因为轮数限制而结束
            last_system_msg = next((msg for msg in reversed(response_data["messages"])
                                   if msg["sender"] == "system"), None)
            if last_system_msg and "轮上限" in last_system_msg["content"]:
                print(f"游戏因达到对话轮数限制而结束: {last_system_msg['content']}")
            break

        # 暂停一下，避免请求过快
        time.sleep(1)

    print("\n测试完成!")

if __name__ == "__main__":
    test_conversation_turn_limit()
