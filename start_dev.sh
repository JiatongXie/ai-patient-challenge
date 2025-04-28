#!/bin/bash

# 启动后端
echo "启动Flask后端..."
python api.py &
BACKEND_PID=$!

# 等待后端启动
sleep 2

# 启动前端
echo "启动Vite前端..."
cd frontend && npm run start

# Ctrl+C 会杀死脚本，添加trap确保关闭后端进程
trap "kill $BACKEND_PID; exit" INT TERM EXIT 