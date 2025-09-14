#!/bin/bash

# 股票数据服务启动脚本
ps -ef | grep manage.py | awk '{print $2}' | xargs kill -s 15
source ./venv/bin/activate
nohup python manage.py runserver 0.0.0.0:8001 > custom.log 2>&1 &