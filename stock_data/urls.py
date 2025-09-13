from django.urls import path
from . import views

app_name = 'stock_data'

urlpatterns = [
    path('realtime/', views.get_realtime_stocks, name='realtime_stocks'),
    path('filter/', views.filter_stocks, name='filter_stocks'),
    path('stock/detail/<str:code>/', views.get_stock_detail, name='stock_detail'),
    path('market-summary/', views.get_market_summary, name='market_summary'),
    path('hot-stocks/', views.get_hot_stocks, name='hot_stocks'),
    path('low-turnover-stocks/', views.get_low_turnover_stocks, name='low_turnover_stocks'),
    path('stock/type/<str:code>/', views.get_stock_type, name='stock_type'),
    path('stock/stock-value-em/<str:code>/', views.get_stock_value_em, name='stock_value_em'),
    path('stock/fund-flow/<str:code>/', views.get_stock_individual_fund_flow, name='stock_individual_fund_flow'),
    path('stock/history/<str:code>/', views.get_stock_history, name='stock_history'),
    path('stock/account/statistics/', views.get_stock_account_statistics, name='stock_account_statistics'),
    path('stock/market-activity/', views.get_stock_market_activity, name='stock_market_activity'),
    path('stock/types/batch/', views.get_stock_types_batch, name='stock_types_batch'),
    path('industries/', views.get_industries, name='industries'),
]