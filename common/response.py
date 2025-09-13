#!/usr/bin/env python3
"""
Django响应工具函数
统一API响应格式
"""

from django.http import JsonResponse
from datetime import datetime
from rest_framework.response import Response
from rest_framework import status

def success_response(data=None, message='success', **kwargs):
    """
    成功响应格式
    
    Args:
        data: 响应数据
        message: 成功消息
        **kwargs: 其他字段
    
    Returns:
        标准格式的JSON响应
    """
    response_data = {
        'code': 200,
        'message': message,
        'timestamp': datetime.now().isoformat(),
        'data': data or {}
    }
    
    # 添加其他字段
    response_data.update(kwargs)
    
    return JsonResponse(response_data)

def error_response(message='error', code=500, **kwargs):
    """
    错误响应格式
    
    Args:
        message: 错误消息
        code: 错误代码
        **kwargs: 其他字段
    
    Returns:
        标准格式的JSON响应
    """
    response_data = {
        'code': code,
        'message': message,
        'timestamp': datetime.now().isoformat(),
        'data': None
    }
    
    # 添加其他字段
    response_data.update(kwargs)
    
    return JsonResponse(response_data, status=code)

def validation_error(errors):
    """
    验证错误响应
    
    Args:
        errors: 验证错误信息
    
    Returns:
        验证错误JSON响应
    """
    return error_response('参数验证失败', 400, errors=errors)

def not_found_error(message='资源未找到'):
    """
    404错误响应
    
    Args:
        message: 错误消息
    
    Returns:
        404错误JSON响应
    """
    return error_response(message, 404)

def unauthorized_error(message='未授权访问'):
    """
    401错误响应
    
    Args:
        message: 错误消息
    
    Returns:
        401错误JSON响应
    """
    return error_response(message, 401)

def forbidden_error(message='权限不足'):
    """
    403错误响应
    
    Args:
        message: 错误消息
    
    Returns:
        403错误JSON响应
    """
    return error_response(message, 403)

def server_error(message='服务器内部错误'):
    """
    500错误响应
    
    Args:
        message: 错误消息
    
    Returns:
        500错误JSON响应
    """
    return error_response(message, 500)

# DRF版本的响应函数
def drf_success_response(data=None, message='success', **kwargs):
    """
    DRF成功响应格式
    
    Args:
        data: 响应数据
        message: 成功消息
        **kwargs: 其他字段
    
    Returns:
        DRF Response对象
    """
    response_data = {
        'code': 200,
        'message': message,
        'timestamp': datetime.now().isoformat(),
        'data': data or {}
    }
    
    # 添加其他字段
    response_data.update(kwargs)
    
    return Response(response_data, status=status.HTTP_200_OK)

def drf_error_response(message='error', code=500, **kwargs):
    """
    DRF错误响应格式
    
    Args:
        message: 错误消息
        code: 错误代码
        **kwargs: 其他字段
    
    Returns:
        DRF Response对象
    """
    response_data = {
        'code': code,
        'message': message,
        'timestamp': datetime.now().isoformat(),
        'data': None
    }
    
    # 添加其他字段
    response_data.update(kwargs)
    
    return Response(response_data, status=code)