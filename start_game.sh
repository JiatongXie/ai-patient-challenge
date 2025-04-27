#!/bin/bash

# 检查是否存在.env文件
if [ ! -f ".env" ]; then
    echo "未找到.env文件，正在创建示例文件..."
    cat > .env << EOL
# OpenAI API配置
ARK_API_KEY=your_api_key_here
API_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
MODEL_ID=ep-20250221232531-6qwkh
EOL
    echo ".env文件已创建，请编辑文件填入您的API密钥"
    exit 1
fi

# 检查是否存在虚拟环境
if [ ! -d ".venv" ]; then
    echo "正在创建虚拟环境..."
    uv venv
fi

# 安装依赖
echo "正在安装依赖..."
uv pip install -r requirements.txt

# 激活虚拟环境并运行游戏
source .venv/bin/activate
python doctor_game.py

# 退出虚拟环境
deactivate 