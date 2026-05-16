#!/usr/bin/env python3
"""
scheduled_tasks URL 配置
目前未暴露任何HTTP接口，仅用于占位以避免 include 导入错误。
后续如需提供任务管理API，可在此处添加 URL 路由。
"""
from django.urls import path

from .views import GitInfoView
from .views import DcDailyProxyView, DcIndexProxyView
from .views import (
    AhComparisonProxyView,
    BrokerRecommendProxyView,
    CcassHoldDetailProxyView,
    CcassHoldProxyView,
    LimitStepProxyView,
    HmDetailProxyView,
    HkHoldProxyView,
    StockHsgtProxyView,
    HsgtTop10ProxyView,
    IrmQaShProxyView,
    IrmQaSzProxyView,
    CyqPerfProxyView,
    MybookDirectoryView,
    MybookMarkdownFilesView,
    MybookMarkdownContentView,
)

app_name = 'scheduled_tasks'

urlpatterns = [
    path('dc-daily/', DcDailyProxyView.as_view(), name='dc-daily-proxy'),
    path('dc-index/', DcIndexProxyView.as_view(), name='dc-index-proxy'),
    path('ah-comparison/', AhComparisonProxyView.as_view(), name='ah-comparison-proxy'),
    path('broker-recommend/', BrokerRecommendProxyView.as_view(), name='broker-recommend-proxy'),
    path('ccass-hold-detail/', CcassHoldDetailProxyView.as_view(), name='ccass-hold-detail-proxy'),
    path('ccass-hold/', CcassHoldProxyView.as_view(), name='ccass-hold-proxy'),
    path('limit-step/', LimitStepProxyView.as_view(), name='limit-step-proxy'),
    path('hm-detail/', HmDetailProxyView.as_view(), name='hm-detail-proxy'),
    # 新增九个直通代理接口
    path('hk-hold/', HkHoldProxyView.as_view(), name='hk-hold-proxy'),
    path('stock-hsgt/', StockHsgtProxyView.as_view(), name='stock-hsgt-proxy'),
    path('hsgt-top10/', HsgtTop10ProxyView.as_view(), name='hsgt-top10-proxy'),
    path('irm-qa-sh/', IrmQaShProxyView.as_view(), name='irm-qa-sh-proxy'),
    path('irm-qa-sz/', IrmQaSzProxyView.as_view(), name='irm-qa-sz-proxy'),
    path('cyq-perf/', CyqPerfProxyView.as_view(), name='cyq-perf-proxy'),
    path('mybook/directory/', MybookDirectoryView.as_view(), name='mybook-directory'),
    path('mybook/markdown-files/', MybookMarkdownFilesView.as_view(), name='mybook-markdown-files'),
    path('mybook/markdown-content/', MybookMarkdownContentView.as_view(), name='mybook-markdown-content'),
    path('git-info/', GitInfoView.as_view(), name='git-info'),
]
