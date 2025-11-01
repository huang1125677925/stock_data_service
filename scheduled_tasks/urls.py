#!/usr/bin/env python3
"""
scheduled_tasks URL 配置
目前未暴露任何HTTP接口，仅用于占位以避免 include 导入错误。
后续如需提供任务管理API，可在此处添加 URL 路由。
"""
from django.urls import path

from .views import IndexBasicProxyView, IndexDailyProxyView, IndexWeightProxyView

app_name = 'scheduled_tasks'

urlpatterns = [
    path('index-basic/', IndexBasicProxyView.as_view(), name='index-basic-proxy'),
    path('index-daily/', IndexDailyProxyView.as_view(), name='index-daily-proxy'),
    path('index-weight/', IndexWeightProxyView.as_view(), name='index-weight-proxy'),
]