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
        import scheduled_tasks.signals  # noqa: F401

        # 在独立线程中执行 DB 查询，避免 ASGI 启动时触发
        # SynchronousOnlyOperation（ready() 在 ASGI 下处于 async 上下文）
        import threading
        from scheduled_tasks.services import start_scheduled_tasks

        t = threading.Thread(target=start_scheduled_tasks, daemon=True)
        t.start()