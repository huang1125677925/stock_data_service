#!/usr/bin/env python3
"""
定时任务应用配置
"""

from django.apps import AppConfig


class ScheduledTasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scheduled_tasks'
    verbose_name = '定时任务'
