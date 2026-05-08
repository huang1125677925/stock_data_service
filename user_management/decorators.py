#!/usr/bin/env python3
"""
用户权限装饰器
"""

from functools import wraps
from django.http import JsonResponse
from common.response import error_response
from .services import UserService


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
    原 JWT 装饰器：项目已关闭强制鉴权，此处仅解析可选 Bearer 并注入 request.user
    （无令牌时使用系统访客用户，便于 ORM 外键仍指向有效 User）。
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        request.user = UserService.resolve_request_user(request)
        return view_func(request, *args, **kwargs)
    return wrapper