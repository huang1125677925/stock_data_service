#!/usr/bin/env python3
"""
用户权限装饰器

鉴权已关闭。装饰器保留为兼容历史引用，但不再拦截请求。
"""

from functools import wraps


def admin_required(view_func):
    """
    管理员权限装饰器，用于验证用户是否为管理员
    """
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        return view_func(self, request, *args, **kwargs)
    return wrapper


def jwt_login_required(view_func):
    """
    JWT登录验证装饰器，用于验证用户是否已登录
    适用于API视图函数，支持Bearer Token认证
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper
