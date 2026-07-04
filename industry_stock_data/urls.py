from django.urls import path
from . import views

app_name = 'industry_stock_data'

urlpatterns = [
    # 行业板块相关API
    path('industry-sectors/', views.get_industry_sectors, name='industry_sectors'),

    # 行业资金流向相关API
    path('industry/fund-flow/data/', views.get_industry_fund_flow_data, name='industry_fund_flow_data'),
]
