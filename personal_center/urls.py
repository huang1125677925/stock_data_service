from django.urls import path
from .views import HoldingsView, HoldingDetailView

app_name = 'personal_center'

urlpatterns = [
    # 个人中心页面

    # 持有/关注股票API
    path('holdings/', HoldingsView.as_view(), name='holdings'),
    path('holdings/<int:holding_id>/', HoldingDetailView.as_view(), name='holding_detail'),
]