#!/usr/bin/env python3
"""
定时任务数据模型
"""

import json
from datetime import datetime
from django.db import models
from django.utils import timezone


class ScheduledTask(models.Model):
    """
    定时任务模型
    存储定时任务的配置和执行状态
    """
    name = models.CharField('任务名称', max_length=100, unique=True)
    description = models.TextField('任务描述', blank=True, null=True)
    task_function = models.CharField('任务函数', max_length=255, 
                                   help_text='格式: module.submodule.function')
    cron_expression = models.CharField('Cron表达式', max_length=100,
                                     help_text='格式: 分 时 日 月 周')
    parameters = models.JSONField('参数', default=dict, blank=True, null=True,
                                help_text='JSON格式的参数')
    is_active = models.BooleanField('是否激活', default=True)
    last_run = models.DateTimeField('上次运行时间', blank=True, null=True)
    next_run = models.DateTimeField('下次运行时间', blank=True, null=True)
    last_result = models.TextField('上次运行结果', blank=True, null=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        app_label = 'scheduled_tasks'
        verbose_name = '定时任务'
        verbose_name_plural = '定时任务'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_parameters(self):
        """
        获取任务参数
        """
        if not self.parameters:
            return {}
        return self.parameters
    
    def update_last_run(self, result=None):
        """
        更新上次运行时间和结果
        """
        self.last_run = timezone.now()
        if result is not None:
            if isinstance(result, (dict, list)):
                self.last_result = json.dumps(result, ensure_ascii=False)
            else:
                self.last_result = str(result)
        self.save(update_fields=['last_run', 'last_result'])
    
    def update_next_run(self, next_run_time):
        """
        更新下次运行时间
        """
        self.next_run = next_run_time
        self.save(update_fields=['next_run'])


class TaskLog(models.Model):
    """
    任务执行日志
    记录每次任务执行的详细信息
    """
    task = models.ForeignKey(ScheduledTask, on_delete=models.CASCADE, 
                           verbose_name='关联任务', related_name='logs')
    start_time = models.DateTimeField('开始时间', auto_now_add=True)
    end_time = models.DateTimeField('结束时间', blank=True, null=True)
    status = models.CharField('执行状态', max_length=20, 
                            choices=[
                                ('success', '成功'),
                                ('failed', '失败'),
                                ('running', '执行中'),
                            ],
                            default='running')
    result = models.TextField('执行结果', blank=True, null=True)
    error_message = models.TextField('错误信息', blank=True, null=True)
    
    class Meta:
        app_label = 'scheduled_tasks'
        verbose_name = '任务日志'
        verbose_name_plural = '任务日志'
        ordering = ['-start_time']
    
    def __str__(self):
        return f"{self.task.name} - {self.start_time}"
    
    def complete(self, status, result=None, error=None):
        """
        完成任务执行
        """
        self.end_time = timezone.now()
        self.status = status
        
        if result is not None:
            if isinstance(result, (dict, list)):
                self.result = json.dumps(result, ensure_ascii=False)
            else:
                self.result = str(result)
                
        if error is not None:
            self.error_message = str(error)
            
        self.save()