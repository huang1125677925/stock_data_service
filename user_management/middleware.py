#!/usr/bin/env python3
"""
用户认证中间件
"""

from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve
from django.http import JsonResponse
from .services import TokenService, UserService
from common.response import error_response


class AuthenticationMiddleware(MiddlewareMixin):
    """
    用户认证中间件，用于验证用户令牌
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # 不需要认证的路径
        self.exempt_urls = [
            'user_register',
            'user_login',
            'validate_invitation_code',
        ]
        # 不需要认证的路径前缀
        self.exempt_path_prefixes = [
            '/admin/',
            '/django/api/user/register/',
            '/django/api/user/login/',
            '/django/api/user/invitation/validate/',
            '/django/api/user/reset-password/',
            '/django/api/individual_stock/strategy-results/',
            # '/django/api/stock/industry/performance-reports/',
            # '/django/api/stock/industry/heatmap-data/',
            '/django/api/market/',
            '/django/api/stock/industry/statistics/',
            '/django/api/stock/industry/ranking/',
            '/django/api/stock/industry/comparison/',
        ]
    
    def process_request(self, request):
        """
        处理请求，验证用户令牌
        """
        # 检查路径前缀
        for prefix in self.exempt_path_prefixes:
            if request.path.startswith(prefix):
                return None
                
        # 获取当前路径名称
        path_name = resolve(request.path_info).url_name
        
        # 如果是不需要认证的路径，直接放行
        if path_name in self.exempt_urls:
            return None
        
        # 获取认证头
        auth_header = request.headers.get('Authorization', '')
        
        # 如果没有认证头或格式不正确，返回错误
        if not auth_header or not auth_header.startswith('Bearer '):
            return error_response('未认证', code=401)
        
        # 获取令牌
        token = auth_header.split(' ')[1]
        
        # 验证令牌
        token_service = TokenService()
        is_valid, _, user = token_service.validate_token(token)
        
        if not is_valid:
            return error_response('无效的令牌', code=401)
        
        # 将用户对象添加到请求中
        request.user = user
        
        if not user:
            return error_response('用户不存在', code=401)
        
        # 将用户信息添加到请求中
        request.user = user
        request.token = token
        
        return None