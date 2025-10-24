#!/usr/bin/env python3
"""
个人中心视图
包括：
- 个人持有/关注股票的列表、新增、删除API
- 个人中心页面（Vue）
"""

import logging
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from django.db import IntegrityError
from common.response import success_response, error_response
from indival_stock_data.models import IndividualStock
from .models import Holding
from common.validators import validate_stock_symbol
from django.contrib.auth.models import AnonymousUser
from user_management.decorators import jwt_login_required

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class HoldingsView(APIView):
    """
    持有/关注股票API视图
    功能：提供当前登录用户的持有或关注股票的查询与新增
    参数：
    - GET: 无（从请求令牌识别用户）
    - POST: {
        stock_code(str): 股票代码，必填
        relation_type(str): 关系类型，可选，默认 WATCHED，可选值：HELD/WATCHED
      }
    返回值：
    - 成功：{ list: [...], pagination: {...} } 或新增后的记录信息
    事件：
    - 参数格式错误、股票不存在、重复添加时返回错误
    """
    authentication_classes = []

    @method_decorator(jwt_login_required)
    def get(self, request):
        try:
            user = request.user
            if user is None or isinstance(user, AnonymousUser) or not getattr(user, 'id', None):
                return error_response('未认证', 401)
            holdings = Holding.objects.select_related('stock').filter(user_id=user.id).order_by('-created_at')
            data = [
                {
                    'id': h.id,
                    'stock_code': h.stock.code,
                    'stock_name': h.stock.name,
                    'industry': h.industry,
                    'relation_type': h.relation_type,
                    'created_at': h.created_at.isoformat()
                } for h in holdings
            ]
            return success_response({'list': data, 'total': len(data)}, '查询成功')
        except Exception as e:
            logger.error(f"查询持有/关注股票失败: {str(e)}")
            return error_response(f"查询失败: {str(e)}", 500)

    @method_decorator(jwt_login_required)
    def post(self, request):
        try:
            user = getattr(request, 'user', None)
            if user is None or isinstance(user, AnonymousUser) or not getattr(user, 'id', None):
                return error_response('未认证', 401)
            stock_code = request.data.get('stock_code')
            relation_type = (request.data.get('relation_type') or 'WATCHED').upper()
            if not stock_code:
                return error_response('stock_code不能为空', 400)
            if relation_type not in ('HELD', 'WATCHED'):
                return error_response('relation_type必须为HELD或WATCHED', 400)
            if not validate_stock_symbol(stock_code):
                return error_response('无效的股票代码格式', 400)
            try:
                stock = IndividualStock.objects.get(code=stock_code)
            except IndividualStock.DoesNotExist:
                return error_response('股票不存在', 404)
            holding = Holding(user=user, stock=stock, relation_type=relation_type)
            try:
                holding.save()
            except IntegrityError:
                return error_response('该记录已存在', 400)
            return success_response({
                'id': holding.id,
                'stock_code': stock.code,
                'stock_name': stock.name,
                'industry': holding.industry,
                'relation_type': holding.relation_type,
                'created_at': holding.created_at.isoformat()
            }, '新增成功')
        except Exception as e:
            logger.error(f"新增持有/关注股票失败: {str(e)}")
            return error_response(f"新增失败: {str(e)}", 500)

@method_decorator(csrf_exempt, name='dispatch')
class HoldingDetailView(APIView):
    """
    持有/关注股票详情API视图
    功能：删除当前用户的指定持有/关注记录
    参数：
    - DELETE: 路径参数 holding_id(int)
    返回值：
    - 成功：删除成功消息
    事件：
    - 当记录不存在或不属于当前用户时返回错误
    """
    authentication_classes = []

    @method_decorator(jwt_login_required)
    def delete(self, request, holding_id):
        try:
            user = getattr(request, 'user', None)
            if user is None or isinstance(user, AnonymousUser) or not getattr(user, 'id', None):
                return error_response('未认证', 401)
            try:
                holding = Holding.objects.select_related('stock').get(id=holding_id, user_id=user.id)
            except Holding.DoesNotExist:
                return error_response('记录不存在', 404)
            holding.delete()
            return success_response(message='删除成功')
        except Exception as e:
            logger.error(f"删除持有/关注记录失败: {str(e)}")
            return error_response(f"删除失败: {str(e)}", 500)