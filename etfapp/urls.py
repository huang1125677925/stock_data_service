from django.urls import path
from . import views

urlpatterns = [
    # ETF 基本信息查询
    path('basic/', views.EtfBasicListView.as_view(), name='etf_basic_list'),
    # ETF 日线行情查询
    path('daily/', views.EtfDailyListView.as_view(), name='etf_daily_list'),
    # ETF 最近一个交易日所有ETF行情查询
    path(
        'daily/latest/',
        views.EtfLatestDailyAllView.as_view(),
        name='etf_daily_latest_all',
    ),
    # ETF 收盘价相关性矩阵
    path(
        'daily/correlation/',
        views.EtfDailyCorrelationView.as_view(),
        name='etf_daily_correlation',
    ),
    # ETF 区间波动度统计
    path(
        'daily/volatility/',
        views.EtfDailyVolatilityView.as_view(),
        name='etf_daily_volatility',
    ),
    # 指数估值信息查询
    path(
        'index/valuation/',
        views.IndexValuationView.as_view(),
        name='index_valuation',
    ),
    path(
        'index/valuation/income/',
        views.IndexValuationIncomeView.as_view(),
        name='index_valuation_income',
    ),
    path(
        'index/valuation/range/',
        views.IndexValuationRangeView.as_view(),
        name='index_valuation_range',
    ),
]
