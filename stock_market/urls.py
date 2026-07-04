from django.urls import path
from .views import StockMarketFundFlowTrendView

urlpatterns = [
    path('fund-flow/trend/', StockMarketFundFlowTrendView.as_view(), name='stock-market-fund-flow-trend'),
]
