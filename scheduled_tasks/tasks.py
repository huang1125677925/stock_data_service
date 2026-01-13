#!/usr/bin/env python3
"""
预定义的定时任务函数
可以在这里添加通用的定时任务
"""
import sys
import os
from pathlib import Path
from tracemalloc import start
import django
# 设置Django环境
sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_data_service.settings')
django.setup()

import logging
from datetime import datetime
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


def fetch_cctv_news():
    """
    获取CCTV新闻联播内容
    每天晚上8:30执行
    """
    import sys
    import os
    from pathlib import Path
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info("开始执行CCTV新闻联播爬取任务")
    
    try:
        # 导入new_spide模块
        current_dir = Path(__file__).resolve().parent
        sys.path.insert(0, str(current_dir))
        
        # 导入main函数
        from cctv_spider_requests import main
        
        # 执行main函数
        main()
        
        logger.info("CCTV新闻联播爬取任务执行完成")
        return {"status": "success", "message": "新闻联播内容获取成功"}
    except Exception as e:
        logger.error(f"CCTV新闻联播爬取任务执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}

def analyze_cctv_news():
    """
    分析CCTV新闻联播内容并保存AI分析结果
    每天晚上10:00执行
    """
    import sys
    import os
    from pathlib import Path
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info("开始执行CCTV新闻联播分析任务")
    
    try:
        # 导入analyse_news模块
        current_dir = Path(__file__).resolve().parent
        sys.path.insert(0, str(current_dir))
        
        # 导入analyze_and_save_latest_news函数
        from analyse_news import analyze_and_save_latest_news
        
        # 执行分析函数
        analyze_and_save_latest_news()
        
        logger.info("CCTV新闻联播分析任务执行完成")
        return {"status": "success", "message": "新闻联播内容分析成功"}
    except Exception as e:
        logger.error(f"CCTV新闻联播分析任务执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    # analyze_cctv_news()
    fetch_cctv_news()