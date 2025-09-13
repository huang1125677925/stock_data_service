#!/usr/bin/env python3
"""
定时任务服务层
提供定时任务的注册、执行和管理功能
"""

import logging
import importlib
import traceback
from datetime import datetime
from django.conf import settings
from django.utils import timezone
# from django_crontab.crontab import Crontab  # 动态注册不受支持，移除运行时依赖

logger = logging.getLogger(__name__)

# 全局定时任务管理器（django-crontab 不支持运行时动态添加，这里不再实例化）
# crontab = Crontab()

def start_scheduled_tasks():
    """
    启动所有激活的定时任务
    在应用启动时调用
    """
    logger.info("正在启动定时任务系统...")
    
    # 延迟导入，避免循环引用
    from .models import ScheduledTask
    
    # 注册所有激活的任务
    active_tasks = ScheduledTask.objects.filter(is_active=True)
    for task in active_tasks:
        register_task(task)
    
    logger.info(f"成功启动 {active_tasks.count()} 个定时任务")

def register_task(task):
    """
    注册单个定时任务到系统
    
    Args:
        task: ScheduledTask实例
    """
    # 先取消注册，避免重复
    unregister_task(task)
    
    # django-crontab 不支持在运行时动态添加任务，
    # 这里仅记录，不做持久化修改，避免触发 post_save 递归。
    logger.info(f"任务 '{task.name}' 已注册（仅记录）")

def unregister_task(task):
    """
    从系统中取消注册定时任务
    
    Args:
        task: ScheduledTask实例
    """
    # 运行时不进行实际的 crontab 移除操作，仅记录日志
    logger.info(f"任务 '{task.name}' 已取消注册（仅记录）")

def execute_task(task_id):
    """
    执行指定的定时任务
    
    Args:
        task_id: 任务ID
    """
    # 延迟导入，避免循环引用
    from .models import ScheduledTask, TaskLog
    
    try:
        # 获取任务
        task = ScheduledTask.objects.get(id=task_id)
        
        # 创建执行日志
        log_entry = TaskLog.objects.create(task=task)
        
        logger.info(f"开始执行任务: {task.name}")
        
        # 动态导入并执行函数
        result = None
        try:
            # 解析函数路径
            module_path, function_name = task.task_function.rsplit('.', 1)
            module = importlib.import_module(module_path)
            function = getattr(module, function_name)
            
            # 执行函数
            parameters = task.get_parameters()
            result = function(**parameters) if parameters else function()
            
            # 更新任务状态
            task.update_last_run(result)
            
            # 这里不再计算下次运行时间（django-crontab 无对应 API），保持为 None 或由外部管理
            # task.update_next_run(None)
            
            # 更新日志状态为成功
            log_entry.complete('success', result=result)
            
            logger.info(f"任务 '{task.name}' 执行成功")
            return result
            
        except Exception as e:
            error_msg = f"执行任务 '{task.name}' 时出错: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            
            # 更新任务状态
            task.update_last_run(f"错误: {str(e)}")
            
            # 更新日志状态为失败
            log_entry.complete('failed', error=error_msg)
            
            # 重新抛出异常
            raise
            
    except ScheduledTask.DoesNotExist:
        logger.error(f"任务ID {task_id} 不存在")

def get_available_task_functions():
    """
    获取系统中所有可用的任务函数
    用于前端选择任务函数
    
    Returns:
        list: 可用任务函数列表
    """
    # 这里可以实现动态扫描项目中的函数
    # 简化起见，先返回一些预定义的函数
    return [
        'stock_data.services.update_stock_data',
        'stock_strategy.services.calculate_strategy_signals',
        'cctv_news.services.fetch_latest_news',
    ]

def run_task_now(task_id):
    """
    立即执行指定的定时任务
    
    Args:
        task_id: 任务ID
    
    Returns:
        dict: 执行结果
    """
    from .models import ScheduledTask
    
    try:
        task = ScheduledTask.objects.get(id=task_id)
        result = execute_task(task_id)
        return {
            'success': True,
            'message': f"任务 '{task.name}' 执行成功",
            'result': result
        }
    except ScheduledTask.DoesNotExist:
        return {
            'success': False,
            'message': f"任务ID {task_id} 不存在"
        }
    except Exception as e:
        return {
            'success': False,
            'message': f"执行失败: {str(e)}"
        }