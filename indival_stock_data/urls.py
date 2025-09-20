#!/usr/bin/env python3
"""
个股数据URL配置
"""

from django.urls import path
from . import views

app_name = 'individual_stock'

urlpatterns = [
    # 获取股票列表
    path('stocks/', views.StockListView.as_view(), name='stock_list'),
    # 获取所有股票实时行情
    path('stocks/realtime/', views.StockRealtimeView.as_view(), name='stock_realtime_all'),
    # 获取单只股票实时行情
    path('stocks/<str:stock_code>/realtime/', views.StockRealtimeView.as_view(), name='stock_realtime'),
    # 获取股票历史行情数据
    path('stocks/<str:stock_code>/history/', views.StockHistoryView.as_view(), name='stock_history'),
    # 获取股票详细信息
    path('stocks/<str:stock_code>/info/', views.StockInfoView.as_view(), name='stock_info'),
]