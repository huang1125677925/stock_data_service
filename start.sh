#!/bin/bash

# 股票数据服务启动脚本
#!/bin/bash
cd /root/django/stock_data_service || exit 1

# 仅杀死当前用户的 runserver 进程（避免误杀）
pkill -f "runserver 0.0.0.0:8001" || true

# 使用虚拟环境的 Python 直接启动（无需 nohup）
. venv/bin/activate
exec python manage.py runserver 0.0.0.0:8001