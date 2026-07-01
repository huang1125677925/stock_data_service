from django.urls import path
from .views import SSEDailyOverviewView, IndexBasicDataView, IndexHighLowStatisticsView, RiseFallRatioView, StockMarketFundFlowView, StockMarketFundFlowTrendView, IndexInfoView

urlpatterns = [
    path('sse-daily-overview/', SSEDailyOverviewView.as_view(), name='sse-daily-overview'),
    path('index-basic-data/', IndexBasicDataView.as_view(), name='index-basic-data'),
    path('index-info/', IndexInfoView.as_view(), name='index-info'),
    path('index-high-low-statistics/', IndexHighLowStatisticsView.as_view(), name='index-high-low-statistics'),
    path('rise-fall-ratio/', RiseFallRatioView.as_view(), name='rise-fall-ratio'),
    path('fund-flow/', StockMarketFundFlowView.as_view(), name='stock-market-fund-flow'),
    path('fund-flow/trend/', StockMarketFundFlowTrendView.as_view(), name='stock-market-fund-flow-trend'),
]
