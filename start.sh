#!/bin/bash

# 股票数据服务启动脚本

# 设置环境变量
export PYTHONPATH=$(pwd)

# 检查虚拟环境
if [ -d "venv" ]; then
    echo "激活虚拟环境..."
    source venv/bin/activate
fi

# 检查依赖
echo "检查依赖..."
pip install -r requirements.txt

# 执行数据库迁移
echo "执行数据库迁移..."
python manage.py migrate

# 启动服务
echo "启动股票数据服务..."
python manage.py runserver 0.0.0.0:8000