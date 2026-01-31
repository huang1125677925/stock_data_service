from django.urls import path

from .views import (
    IndexMemberAllProxyView, 
    IndexClassifyProxyView, 
    SwDailyProxyView, 
    SwValuationAnalysisView,
    IndexBasicProxyView,
    IndexDailyProxyView,
    IndexWeightProxyView,
    IndexDailybasicProxyView,
    IndexValuationSummaryProxyView,
)

app_name = "index_data"

urlpatterns = [
    path("sw-industry-members/", IndexMemberAllProxyView.as_view(), name="sw-industry-members"),
    path("sw-index-classify/", IndexClassifyProxyView.as_view(), name="sw-index-classify"),
    path("sw-daily/", SwDailyProxyView.as_view(), name="sw-daily"),
    path("sw-valuation-analysis/", SwValuationAnalysisView.as_view(), name="sw-valuation-analysis"),
    path("index-basic/", IndexBasicProxyView.as_view(), name="index-basic"),
    path("index-daily/", IndexDailyProxyView.as_view(), name="index-daily"),
    path("index-weight/", IndexWeightProxyView.as_view(), name="index-weight"),
    path("index-dailybasic/", IndexDailybasicProxyView.as_view(), name="index-dailybasic"),
    path("index-valuation-summary/", IndexValuationSummaryProxyView.as_view(), name="index-valuation-summary"),
]
