#!/bin/bash

# 股票数据服务Linux部署脚本
set -e

echo "===== 股票数据服务Linux部署脚本 ====="
echo "此脚本将帮助您在Linux服务器上部署股票数据服务"

# 获取当前目录作为项目根目录
PROJECT_DIR=$(pwd)
echo "项目目录: $PROJECT_DIR"

# 创建日志目录
echo "创建日志目录..."
mkdir -p $PROJECT_DIR/logs

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "创建.env文件..."
    cp .env.example .env
    echo "请编辑.env文件，配置数据库连接信息和其他设置"
    echo "编辑完成后，请重新运行此脚本"
    exit 0
fi

# 执行数据库迁移
echo "执行数据库迁移..."
python manage.py migrate

# 收集静态文件
echo "收集静态文件..."
python manage.py collectstatic --noinput

# 配置定时任务
echo "配置定时任务..."
python manage.py crontab remove  # 先移除已有的定时任务
python manage.py crontab add

# 显示定时任务
echo "已配置的定时任务:"
python manage.py crontab show

echo "===== 部署完成 ====="
echo "您可以使用以下命令启动服务:"
echo "开发环境: ./start.sh"
echo "生产环境: 请参考 docs/linux_deployment.md 配置Gunicorn和Supervisor"