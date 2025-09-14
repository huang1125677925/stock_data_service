#!/usr/bin/env python3
"""
用户权限装饰器
"""

from functools import wraps
from django.http import JsonResponse
from common.response import error_response
from .services import TokenService, UserService


def admin_required(view_func):
    """
    管理员权限装饰器，用于验证用户是否为管理员
    """
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        # 验证用户是否为管理员
        if not hasattr(request, 'user') or not request.user.is_admin:
            return JsonResponse(error_response('权限不足', code=403))
        return view_func(self, request, *args, **kwargs)
    return wrapper


def jwt_login_required(view_func):
    """
    JWT登录验证装饰器，用于验证用户是否已登录
    适用于API视图函数，支持Bearer Token认证
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 获取认证头
        auth_header = request.headers.get('Authorization', '')
        
        # 如果没有认证头或格式不正确，返回错误
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse(error_response('未认证', code=401))
        
        # 获取令牌
        token = auth_header.split(' ')[1]
        
        # 验证令牌
        token_service = TokenService()
        is_valid, _, user = token_service.validate_token(token)
        
        if not is_valid or not user:
            return JsonResponse(error_response('无效的令牌或用户不存在', code=401))
        
        # 将用户对象添加到请求中
        request.user = user
        request.token = token
        
        return view_func(request, *args, **kwargs)
    return wrapper