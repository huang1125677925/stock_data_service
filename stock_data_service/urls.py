"""stock_data_service URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from datetime import datetime

def health_check(request):
    """健康检查接口"""
    return JsonResponse({
        'status': 'healthy',
        'message': '股票数据服务运行正常',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })

def index(request):
    """根路径接口"""
    return JsonResponse({
        'message': '欢迎使用股票数据服务API',
        'version': '1.0.0',
        'endpoints': {
            'health': '/health',
            'stock_data': '/api/stock/',
            'cctv_news': '/api/news/',
            'stock_strategy': '/api/strategy/',
            'user_management': '/api/user/',
            'scheduled_tasks': '/api/tasks/',
            'forum': '/api/forum/'
        },
        'timestamp': datetime.now().isoformat()
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    path('health/', health_check, name='health_check'),
    path('django/api/stock/', include('stock_data.urls')),
    path('django/api/individual_stock/', include('indival_stock_data.urls')),
    path('django/api/news/', include('cctv_news.urls')),
    path('django/api/strategy/', include('stock_strategy.urls')),
    path('django/api/user/', include('user_management.urls')),
    path('django/api/tasks/', include('scheduled_tasks.urls')),
    path('django/api/forum/', include('forum.urls')),
]