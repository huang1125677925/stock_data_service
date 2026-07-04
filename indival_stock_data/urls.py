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
    # 获取股票历史行情数据
    # 查询参数：start_date(YYYYMMDD, 可选)、end_date(YYYYMMDD, 可选)、adjust("", qfq, hfq, 可选)、frequency(daily|weekly, 可选，默认daily)
    path('stocks/<str:stock_code>/history/', views.StockHistoryView.as_view(), name='stock_history'),
]
