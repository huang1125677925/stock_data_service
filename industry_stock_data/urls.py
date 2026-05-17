from django.urls import path
from . import views

app_name = 'industry_stock_data'

urlpatterns = [
    path('realtime/', views.get_realtime_stocks, name='realtime_stocks'),
    path('filter/', views.filter_stocks, name='filter_stocks'),
    path('stock/detail/<str:code>/', views.get_stock_detail, name='stock_detail'),
    path('market-summary/', views.get_market_summary, name='market_summary'),
    path('hot-stocks/', views.get_hot_stocks, name='hot_stocks'),
    path('low-turnover-stocks/', views.get_low_turnover_stocks, name='low_turnover_stocks'),
    path('stock/type/<str:code>/', views.get_stock_type, name='stock_type'),
    path('stock/stock-value-em/<str:code>/', views.get_stock_value_em, name='stock_value_em'),
    path('dividend-yield/', views.get_stock_dividend_yield, name='stock_dividend_yield'),
    path('stock/fund-flow/<str:code>/', views.get_stock_individual_fund_flow, name='stock_individual_fund_flow'),
    path('stock/history/<str:code>/', views.get_stock_history, name='stock_history'),
    path('stock/account/statistics/', views.get_stock_account_statistics, name='stock_account_statistics'),
    path('stock/market-activity/', views.get_stock_market_activity, name='stock_market_activity'),
    path('stock/types/batch/', views.get_stock_types_batch, name='stock_types_batch'),
    path('industries/', views.get_industries, name='industries'),
    
    # 行业板块相关API
    path('industry-sectors/', views.get_industry_sectors, name='industry_sectors'),
    path('industry-sector/daily/<str:code>/', views.get_industry_sector_daily, name='industry_sector_daily'),
    path('industry-sector/realtime/<str:code>/', views.get_industry_sector_realtime, name='industry_sector_realtime'),
    path('industry-sector/constituents/<str:code>/', views.get_industry_sector_constituents, name='industry_sector_constituents'),
    
    # 业绩快报相关API
    path('industry/performance-reports/', views.get_industry_performance_reports, name='industry_performance_reports'),
    
    # 行业热力图数据API
    path('industry/heatmap-data/', views.get_industry_heatmap_data, name='industry_heatmap_data'),
    
    # 行业统计数据API
    path('industry/statistics/', views.get_industry_statistics, name='industry_statistics'),
    path('industry/ranking/', views.get_industry_ranking, name='industry_ranking'),
    path('industry/comparison/', views.get_industry_comparison, name='industry_comparison'),
    
    # 行业资金流向相关API
    path('industry/fund-flow/data/', views.get_industry_fund_flow_data, name='industry_fund_flow_data'),
    path('industry/fund-flow/ranking/', views.get_industry_fund_flow_ranking, name='industry_fund_flow_ranking'),
    path('industry/fund-flow/summary/', views.get_industry_fund_flow_summary, name='industry_fund_flow_summary'),
    path('fund-flow/ranking/', views.get_fund_flow_ranking, name='fund_flow_ranking'),
]
