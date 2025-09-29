#!/usr/bin/env python3
"""
量化策略URL配置
"""

from django.urls import path
from . import views
from .get_raw_indicator_data import get_raw_indicator_data

app_name = 'quantitative_strategy'

urlpatterns = [
    # 策略相关接口
    path('strategies/', views.get_strategies, name='get_strategies'),
    
    # 回测任务相关接口
    path('backtest/create/', views.create_backtest, name='create_backtest'),
    path('backtest/<str:task_id>/run/', views.run_backtest, name='run_backtest'),
    path('backtest/<str:task_id>/status/', views.get_task_status, name='get_task_status'),
    path('backtest/<str:task_id>/result/', views.get_backtest_result, name='get_backtest_result'),
    path('backtest/<str:task_id>/chart/', views.get_backtest_chart, name='get_backtest_chart'),
    path('backtest/<str:task_id>/observer/', views.get_observer_data, name='get_observer_data'),
    path('backtest/<str:task_id>/raw-indicator/', get_raw_indicator_data, name='get_raw_indicator_data'),
    
    # 历史记录接口
    path('backtest/history/', views.get_backtest_history, name='get_backtest_history'),
]