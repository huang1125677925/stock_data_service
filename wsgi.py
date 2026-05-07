#!/usr/bin/env python3
"""
WSGI配置文件
用于生产环境部署Django应用
"""

import os
import sys
from django.core.wsgi import get_wsgi_application

# 添加项目路径到Python路径
project_path = os.path.dirname(os.path.abspath(__file__))
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# 设置Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_data_service.settings')

# 获取WSGI应用
application = get_wsgi_application()

# 用于Gunicorn等WSGI服务器
if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)