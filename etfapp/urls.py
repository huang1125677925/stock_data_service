from django.urls import path
from . import views

urlpatterns = [
    # ETF 基本信息查询
    path('basic/', views.EtfBasicListView.as_view(), name='etf_basic_list'),
    # ETF 日线行情查询
    path('daily/', views.EtfDailyListView.as_view(), name='etf_daily_list'),
    # ETF 最近一个交易日所有ETF行情查询
    path('daily/latest/', views.EtfLatestDailyAllView.as_view(), name='etf_daily_latest_all'),
]