#!/usr/bin/env python3
"""
个股数据API视图
提供个股数据的REST API接口
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.http import JsonResponse
from django.core.paginator import Paginator
from .services import individual_stock_service
from common.validators import validate_stock_symbol
from common.response import success_response, error_response
from .models import IndividualStock, StrategyResult
from .serializers import IndividualStockSerializer, StrategyResultSerializer

logger = logging.getLogger(__name__)


class StockListView(APIView):
    """
    获取股票列表
    """
    def get(self, request):
        try:
            # 获取分页参数
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            keyword = request.query_params.get('keyword', None)

            # 从数据库获取股票列表
            # 方案一：使用 values() 方法直接获取字典格式数据，避免 ORM 对象转换开销
            stock_list = []
            stocks_query = IndividualStock.objects.all()
            if stocks_query.exists():
                # 方案二：使用 Django REST Framework 序列化器（取消下面注释即可启用）
                serializer = IndividualStockSerializer(stocks_query, many=True)
                stock_list = serializer.data
                
                logger.info(f"从数据库获取{len(stock_list)}只股票信息")

            if not stock_list:
                return error_response("获取股票列表失败", 404)

            if keyword:
                stock_list = [stock for stock in stock_list if keyword.lower() in stock['name'].lower() or keyword.lower() in stock['code'].lower()]

            # 分页处理
            paginator = Paginator(stock_list, page_size)
            current_page = paginator.page(page)
            
            return success_response({
                "total": paginator.count,
                "page": page,
                "page_size": page_size,
                "total_pages": paginator.num_pages,
                "data": list(current_page.object_list)
            })
        except ValueError as e:
            logger.error(f"参数格式错误: {str(e)}")
            return error_response(f'参数格式错误: {str(e)}', 400)
        except Exception as e:
            logger.error(f"获取股票列表失败: {str(e)}")
            return error_response(f'获取股票列表失败: {str(e)}', 500)


class StockRealtimeView(APIView):
    """
    获取股票实时行情
    """
    def get(self, request, stock_code=None):
        try:
            # 如果提供了股票代码，则获取单只股票的实时行情
            if stock_code:
                if not validate_stock_symbol(stock_code):
                    return error_response(f"无效的股票代码: {stock_code}", 400)
                
                realtime = individual_stock_service.get_stock_realtime(stock_code)
                
                if not realtime:
                    return error_response(f"获取股票{stock_code}实时行情失败", 404)
                
                return success_response(realtime)
            
            # 否则获取所有股票的实时行情
            # 获取分页参数
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # 获取所有股票的实时行情
            realtime_list = individual_stock_service.get_stock_realtime()
            
            if not realtime_list:
                return error_response("获取股票实时行情失败", 404)
            
            # 分页处理
            paginator = Paginator(realtime_list, page_size)
            current_page = paginator.page(page)
            
            return success_response({
                "total": paginator.count,
                "page": page,
                "page_size": page_size,
                "total_pages": paginator.num_pages,
                "data": list(current_page.object_list)
            })
        except ValueError as e:
            logger.error(f"参数格式错误: {str(e)}")
            return error_response(f'参数格式错误: {str(e)}', 400)
        except Exception as e:
            logger.error(f"获取股票实时行情失败: {str(e)}")
            return error_response(f'获取股票实时行情失败: {str(e)}', 500)


class StockHistoryView(APIView):
    """
    获取股票历史行情数据
    """
    def get(self, request, stock_code):
        try:
            if not validate_stock_symbol(stock_code):
                return error_response(f"无效的股票代码: {stock_code}", 400)
            
            # 获取查询参数
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            adjust = request.query_params.get('adjust', "")
            
            # 获取历史数据
            history = individual_stock_service.get_stock_history(stock_code, start_date, end_date, adjust)
            
            
            return success_response(history)
        except ValueError as e:
            logger.error(f"参数格式错误: {str(e)}")
            return error_response(f'参数格式错误: {str(e)}', 400)
        except Exception as e:
            logger.error(f"获取股票历史行情数据失败: {str(e)}")
            return error_response(f'获取股票历史行情数据失败: {str(e)}', 500)


class StockInfoView(APIView):
    """
    获取股票详细信息
    """
    def get(self, request, stock_code):
        try:
            if not validate_stock_symbol(stock_code):
                return error_response(f"无效的股票代码: {stock_code}", 400)
            
            # 获取股票详细信息
            info = individual_stock_service.get_stock_info(stock_code)
            
            return success_response(info)
        except ValueError as e:
            logger.error(f"参数格式错误: {str(e)}")
            return error_response(f'参数格式错误: {str(e)}', 400)
        except Exception as e:
            logger.error(f"获取股票详细信息失败: {str(e)}")
            return error_response(f'获取股票详细信息失败: {str(e)}', 500)


class StrategyResultView(APIView):
    """
    策略选股结果管理接口
    提供策略结果的增删改查功能
    """
    
    def get(self, request, result_id=None):
        """
        获取策略结果
        - 如果提供result_id，返回单个策略结果
        - 如果不提供result_id，返回策略结果列表（支持分页和筛选）
        """
        try:
            if result_id:
                # 获取单个策略结果
                try:
                    strategy_result = StrategyResult.objects.get(id=result_id)
                    serializer = StrategyResultSerializer(strategy_result)
                    return success_response(serializer.data)
                except StrategyResult.DoesNotExist:
                    return error_response("策略结果不存在", 404)
            else:
                # 获取策略结果列表
                page = int(request.query_params.get('page', 1))
                page_size = int(request.query_params.get('page_size', 20))
                strategy_name = request.query_params.get('strategy_name', None)
                
                # 构建查询条件
                queryset = StrategyResult.objects.all()
                if strategy_name:
                    queryset = queryset.filter(strategy_name__icontains=strategy_name)
                
                # 分页处理
                paginator = Paginator(queryset, page_size)
                current_page = paginator.get_page(page)
                
                # 序列化数据
                serializer = StrategyResultSerializer(current_page.object_list, many=True)
                
                return success_response({
                    'total': paginator.count,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': paginator.num_pages,
                    'results': serializer.data
                })
                
        except ValueError as e:
            logger.error(f"参数格式错误: {str(e)}")
            return error_response(f'参数格式错误: {str(e)}', 400)
        except Exception as e:
            logger.error(f"获取策略结果失败: {str(e)}")
            return error_response(f'获取策略结果失败: {str(e)}', 500)
    
    
    def post(self, request):
        """
        创建新的策略结果
        """
        try:
            serializer = StrategyResultSerializer(data=request.data)
            if serializer.is_valid():
                strategy_result = serializer.save()
                return success_response(
                    StrategyResultSerializer(strategy_result).data,
                    "策略结果创建成功"
                )
            else:
                return error_response(f"数据验证失败: {serializer.errors}", 400)
                
        except Exception as e:
            logger.error(f"创建策略结果失败: {str(e)}")
            return error_response(f'创建策略结果失败: {str(e)}', 500)
    
    def put(self, request, result_id):
        """
        更新策略结果
        """
        try:
            try:
                strategy_result = StrategyResult.objects.get(id=result_id)
            except StrategyResult.DoesNotExist:
                return error_response("策略结果不存在", 404)
            
            serializer = StrategyResultSerializer(strategy_result, data=request.data)
            if serializer.is_valid():
                updated_result = serializer.save()
                return success_response(
                    StrategyResultSerializer(updated_result).data,
                    "策略结果更新成功"
                )
            else:
                return error_response(f"数据验证失败: {serializer.errors}", 400)
                
        except Exception as e:
            logger.error(f"更新策略结果失败: {str(e)}")
            return error_response(f'更新策略结果失败: {str(e)}', 500)
    
    def patch(self, request, result_id):
        """
        部分更新策略结果
        """
        try:
            try:
                strategy_result = StrategyResult.objects.get(id=result_id)
            except StrategyResult.DoesNotExist:
                return error_response("策略结果不存在", 404)
            
            serializer = StrategyResultSerializer(strategy_result, data=request.data, partial=True)
            if serializer.is_valid():
                updated_result = serializer.save()
                return success_response(
                    StrategyResultSerializer(updated_result).data,
                    "策略结果更新成功"
                )
            else:
                return error_response(f"数据验证失败: {serializer.errors}", 400)
                
        except Exception as e:
            logger.error(f"更新策略结果失败: {str(e)}")
            return error_response(f'更新策略结果失败: {str(e)}', 500)
    
    def delete(self, request, result_id):
        """
        删除策略结果
        """
        try:
            try:
                strategy_result = StrategyResult.objects.get(id=result_id)
            except StrategyResult.DoesNotExist:
                return error_response("策略结果不存在", 404)
            
            strategy_name = strategy_result.strategy_name
            strategy_result.delete()
            
            return success_response(
                {"deleted_id": result_id, "strategy_name": strategy_name},
                "策略结果删除成功"
            )
            
        except Exception as e:
            logger.error(f"删除策略结果失败: {str(e)}")
            return error_response(f'删除策略结果失败: {str(e)}', 500)

