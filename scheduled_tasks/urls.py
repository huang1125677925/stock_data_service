#!/usr/bin/env python3
"""
scheduled_tasks URL 配置
目前未暴露任何HTTP接口，仅用于占位以避免 include 导入错误。
后续如需提供任务管理API，可在此处添加 URL 路由。
"""
from django.urls import path

from .views import DcDailyProxyView, DcIndexProxyView
from .views import LimitStepProxyView

app_name = 'scheduled_tasks'

urlpatterns = [
    path('dc-daily/', DcDailyProxyView.as_view(), name='dc-daily-proxy'),
    path('dc-index/', DcIndexProxyView.as_view(), name='dc-index-proxy'),
    path('limit-step/', LimitStepProxyView.as_view(), name='limit-step-proxy'),
]
