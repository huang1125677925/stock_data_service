#!/usr/bin/env python3
"""
预定义的定时任务函数
可以在这里添加通用的定时任务
"""
import os
import sys
from pathlib import Path
import django
# 设置Django环境
sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_data_service.settings')
django.setup()

import logging
from django.utils import timezone

logger = logging.getLogger(__name__)

def example_task():
    """
    示例任务
    用于测试定时任务系统
    """
    current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f"示例任务执行于: {current_time}")
    return {"status": "success", "time": current_time}

def cleanup_old_logs(days=30):
    """
    清理旧的任务日志
    
    Args:
        days: 保留的天数，默认30天
    """
    from .models import TaskLog
    
    # 计算截止日期
    cutoff_date = timezone.now() - timezone.timedelta(days=days)
    
    # 删除旧日志
    deleted_count, _ = TaskLog.objects.filter(start_time__lt=cutoff_date).delete()
    
    logger.info(f"已清理 {deleted_count} 条旧日志记录")
    return {"deleted_count": deleted_count}

def check_task_status():
    """
    检查所有任务的状态
    查找可能失败或长时间未运行的任务
    """
    from .models import ScheduledTask
    
    # 获取所有激活的任务
    active_tasks = ScheduledTask.objects.filter(is_active=True)
    
    # 检查状态
