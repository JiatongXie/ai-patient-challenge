"""
游戏配置文件
包含游戏的各种配置选项
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(override=True)

# 游戏基本配置
GAME_CONFIG = {
    # 是否使用LLM检查患者回复的合理性
    "check_patient_response": os.getenv("CHECK_PATIENT_RESPONSE", "false").lower() == "true",
    
    # 可选的疾病列表
    "diseases": [
        "流感", "肺炎", "胃溃疡", "偏头痛", "扁桃体炎",
        "高血压", "糖尿病", "关节炎", "哮喘", "过敏性鼻炎"
    ],
    
    # API相关配置
    "api": {
        "base_url": os.getenv("API_BASE_URL"),
        "api_key": os.getenv("API_KEY"),
        "model_id": os.getenv("MODEL_ID"),
    }
}
