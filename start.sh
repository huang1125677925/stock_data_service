#!/bin/bash

# 股票数据服务启动脚本
cd /root/django/stock_data_service || exit 1

# 仅杀死当前用户的 uvicorn 进程（避免误杀）
pkill -f "uvicorn stock_data_service.asgi:application" || true

# 使用虚拟环境的 Python 直接启动（无需 nohup）
. venv/bin/activate
export TUSHARE_TOKEN=119db86ff3fd948e85905f8c506e1012d33fe18bf4b726e99f33ab09
export GITHUB_TOKEN=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
# 启用 MCP server.shell.run（在 MCP 所在进程继承此环境变量）
export SERVER_SHELL_TOOL_ENABLED=true
exec uvicorn stock_data_service.asgi:application \
    --host 0.0.0.0 \
    --port 8001 \
    --workers 1 \
    --loop asyncio
