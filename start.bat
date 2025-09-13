@echo off
REM 股票数据服务启动脚本 (Windows版)

REM 设置环境变量
set PYTHONPATH=%cd%

REM 检查虚拟环境
if exist venv (
    echo 激活虚拟环境...
    call venv\Scripts\activate
)

REM 检查依赖
echo 检查依赖...
pip install -r requirements.txt

REM 执行数据库迁移
echo 执行数据库迁移...
python manage.py migrate

REM 启动服务
echo 启动股票数据服务...
python manage.py runserver 0.0.0.0:8000