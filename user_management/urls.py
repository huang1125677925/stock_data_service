#!/usr/bin/env python3
"""
用户管理应用URL配置
"""

from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from . import views

urlpatterns = [
    # 用户注册、登录、登出
    path('register/', views.RegisterView.as_view(), name='user_register'),
    path('login/', views.LoginView.as_view(), name='user_login'),
    path('logout/', views.LogoutView.as_view(), name='user_logout'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='reset_password'),
    
    # 用户信息
    path('info/', views.UserInfoView.as_view(), name='user_info'),
    
    # 邀请码
    path('invitation/', views.InvitationCodeView.as_view(), name='invitation_code'),
    path('invitation/validate/', views.ValidateInvitationCodeView.as_view(), name='validate_invitation_code'),
]