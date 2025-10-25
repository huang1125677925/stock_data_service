from django.urls import path
from . import views

urlpatterns = [
    path('index-rps/', views.get_index_rps, name='get_index_rps'),
    path('historical-rps/', views.get_historical_rps, name='get_historical_rps'),
    path('industry-turnover-percentile/', views.get_industry_turnover_percentile, name='get_industry_turnover_percentile'),
    path('screen-stocks/', views.screen_stocks_by_previous_high, name='screen_stocks_by_previous_high'),
    path('execute-tagging-task/', views.execute_stock_tagging_task, name='execute_stock_tagging_task'),
    path('stock-analysis/<str:stock_code>/', views.get_stock_analysis_detail, name='get_stock_analysis_detail'),
    path('industry-ma-breadth/', views.get_industry_ma_breadth, name='get_industry_ma_breadth'),
    path('industry-scale-breadth/', views.get_industry_scale_breadth, name='get_industry_scale_breadth'),
    path('industry-actual-output/', views.get_industry_actual_output, name='get_industry_actual_output'),
    path('industry-fund-flow-correlation/', views.get_industry_fund_flow_correlation, name='get_industry_fund_flow_correlation'),
]