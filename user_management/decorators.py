#!/usr/bin/env python3
"""
用户权限装饰器
"""

from functools import wraps
from django.http import JsonResponse
from common.response import error_response


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