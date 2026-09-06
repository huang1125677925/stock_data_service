#!/usr/bin/env python3
"""
用户认证中间件

鉴权已关闭。保留这个类是为了兼容历史配置引用；即使被误加回
MIDDLEWARE，也不会再拦截请求。
"""

from django.utils.deprecation import MiddlewareMixin


class AuthenticationMiddleware(MiddlewareMixin):
    """
    兼容用中间件，不再验证用户令牌。
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
    
    def process_request(self, request):
        return None
