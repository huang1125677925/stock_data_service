#!/usr/bin/env python3
"""
定时任务应用配置
"""

from django.apps import AppConfig


class ScheduledTasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scheduled_tasks'
    verbose_name = '定时任务'
    
    def ready(self):
        """
        应用启动时执行的初始化操作
        在这里导入信号处理器或启动定时任务
        """
        # 导入信号处理器
        import scheduled_tasks.signals
        
        # 启动定时任务（如果需要）
        from scheduled_tasks.services import start_scheduled_tasks
        start_scheduled_tasks()