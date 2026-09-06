#!/usr/bin/env python3
"""
站点统计URL配置
"""

from django.urls import path
from .views import SiteVisitView

urlpatterns = [
    path('', SiteVisitView.as_view(), name='site_visit'),
]
