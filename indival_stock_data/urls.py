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
    
    # 策略选股结果管理接口
    # 获取策略结果列表或创建新的策略结果
    path('strategy-results/', views.StrategyResultView.as_view(), name='strategy_result_list'),
    # 获取、更新或删除单个策略结果
    path('strategy-results/<int:result_id>/', views.StrategyResultView.as_view(), name='strategy_result_detail'),
    
    # 业绩快报接口
    # 获取业绩快报数据（通过查询参数指定报告期或股票代码）
    path('performance-reports/', views.PerformanceReportView.as_view(), name='performance_report_list'),
    # 获取指定股票的业绩快报数据
    path('stocks/<str:stock_code>/performance-reports/', views.StockPerformanceReportView.as_view(), name='stock_performance_reports'),
]