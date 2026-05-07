#!/usr/bin/env python3
"""
定时任务信号处理模块
用于处理与定时任务相关的Django信号
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import ScheduledTask
from .services import register_task, unregister_task


@receiver(post_save, sender=ScheduledTask)
def handle_task_save(sender, instance, created, **kwargs):
    """
    当定时任务被创建或更新时触发
    
    Args:
        sender: 发送信号的模型类
        instance: 被保存的实例
        created: 是否是新创建的实例
    """
    if instance.is_active:
        # 如果任务是激活状态，注册到系统
        register_task(instance)
    else:
        # 如果任务是非激活状态，从系统中取消注册
        unregister_task(instance)


@receiver(post_delete, sender=ScheduledTask)
def handle_task_delete(sender, instance, **kwargs):
    """
    当定时任务被删除时触发
    
    Args:
        sender: 发送信号的模型类
        instance: 被删除的实例
    """
    # 从系统中取消注册任务
    unregister_task(instance)