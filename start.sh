#!/bin/bash

# 股票数据服务启动脚本
PROJECT_DIR=/root/django/stock_data_service
cd "$PROJECT_DIR" || exit 1

# 仅杀死当前用户的 uvicorn 进程（避免误杀）
pkill -f "uvicorn stock_data_service.asgi:application" || true

# 使用虚拟环境的 Python 直接启动（无需 nohup）
. venv/bin/activate

# 加载项目根目录下的 .env，并自动导出其中的环境变量
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    . "$PROJECT_DIR/.env"
    set +a
else
    echo "Error: $PROJECT_DIR/.env not found"
    exit 1
fi

exec uvicorn stock_data_service.asgi:application \
    --host 0.0.0.0 \
    --port 8001 \
    --workers 1 \
    --loop asyncio
