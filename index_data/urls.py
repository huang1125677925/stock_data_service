from django.urls import path

from .views import IndexMemberAllProxyView, IndexClassifyProxyView, SwDailyProxyView, SwValuationAnalysisView

app_name = "index_data"

urlpatterns = [
    path("sw-industry-members/", IndexMemberAllProxyView.as_view(), name="sw-industry-members"),
    path("sw-index-classify/", IndexClassifyProxyView.as_view(), name="sw-index-classify"),
    path("sw-daily/", SwDailyProxyView.as_view(), name="sw-daily"),
    path("sw-valuation-analysis/", SwValuationAnalysisView.as_view(), name="sw-valuation-analysis"),
]
