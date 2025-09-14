from django.urls import path
from . import views

app_name = 'stock_strategy'

urlpatterns = [
    path('index-rps/', views.get_index_rps, name='index_rps'),
    path('historical-rps/', views.get_historical_rps, name='historical_rps'),
    path('industry-turnover-percentile/', views.get_industry_turnover_percentile, name='industry_turnover_percentile'),
]