from django.urls import path
from .views import SSEDailyOverviewView

urlpatterns = [
    path('sse-daily-overview/', SSEDailyOverviewView.as_view(), name='sse-daily-overview'),
]