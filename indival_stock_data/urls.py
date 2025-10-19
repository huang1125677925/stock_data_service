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
    
    # 财务报表接口
    # 资产负债表接口
    path('balance-sheets/', views.BalanceSheetView.as_view(), name='balance_sheet_list'),
    path('stocks/<str:stock_code>/balance-sheets/', views.BalanceSheetView.as_view(), name='stock_balance_sheets'),
    
    # 利润表接口
    path('income-statements/', views.IncomeStatementView.as_view(), name='income_statement_list'),
    path('stocks/<str:stock_code>/income-statements/', views.IncomeStatementView.as_view(), name='stock_income_statements'),
    
    # 现金流量表接口
    path('cash-flow-statements/', views.CashFlowStatementView.as_view(), name='cash_flow_statement_list'),
    path('stocks/<str:stock_code>/cash-flow-statements/', views.CashFlowStatementView.as_view(), name='stock_cash_flow_statements'),
    
    # 股票标记接口
    # 获取股票标记列表或创建新的股票标记
    path('stock-tags/', views.StockTagView.as_view(), name='stock_tag_list'),
    # 获取、更新或删除单个股票标记
    path('stock-tags/<int:tag_id>/', views.StockTagView.as_view(), name='stock_tag_detail'),
    # 获取标记因子选择项
    path('stock-tags/choices/', views.StockTagChoicesView.as_view(), name='stock_tag_choices'),
    # 获取指定股票的所有标记
    path('stocks/<str:stock_code>/tags/', views.StockTagByStockView.as_view(), name='stock_tags_by_stock'),
]