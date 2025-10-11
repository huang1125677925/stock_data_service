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
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .services import individual_stock_service
from common.validators import validate_stock_symbol
from common.response import success_response, error_response
from .models import IndividualStock, StrategyResult
from .serializers import IndividualStockSerializer, StrategyResultSerializer
from django.db.models import Q

logger = logging.getLogger(__name__)


class StockListView(APIView):
    """
    获取股票列表
    """
    def get(self, request):
        """
        功能：获取股票列表，支持关键词搜索与分页，提高查询性能。
        参数：
        - request(HttpRequest): 请求对象，查询参数包括：
          - page(int, 可选): 页码，默认1
          - page_size(int, 可选): 每页数量，默认20
          - keyword(str, 可选): 关键词，按股票名称或代码模糊匹配
        返回值：
        - JsonResponse: 调用success_response返回数据；失败时调用error_response返回错误信息。
        事件：
        - 当页码格式错误或超出范围时，记录日志并返回错误响应。
        """
        try:
            # 获取分页参数
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            keyword = request.query_params.get('keyword', None)

            # 使用数据库层面的过滤与分页，避免一次性加载全部数据
            queryset = IndividualStock.objects.all().order_by('code')
            if keyword:
                queryset = queryset.filter(Q(name__icontains=keyword) | Q(code__icontains=keyword))

            # 分页处理（数据库分页）
            paginator = Paginator(queryset, page_size)
            if paginator.count == 0:
                return error_response("获取股票列表失败", 404)
            try:
                current_page = paginator.page(page)
            except (PageNotAnInteger, EmptyPage):
                logger.warning(f"页码超出范围: {page}")
                return error_response("页码超出范围", 400)

            # 仅序列化当前页的数据，减少序列化开销
            serializer = IndividualStockSerializer(current_page.object_list, many=True)
            logger.info(f"从数据库获取{paginator.count}只股票信息，当前返回第{page}页，共{paginator.num_pages}页")

            return success_response({
                "total": paginator.count,
                "page": page,
                "page_size": page_size,
                "total_pages": paginator.num_pages,
                "data": serializer.data
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


class PerformanceReportView(APIView):
    """
    业绩快报API视图
    提供业绩快报数据的查询接口
    """
    
    def get(self, request):
        """
        获取业绩快报数据
        
        查询参数:
        - date: 报告期，格式YYYYMMDD，如20200331（必需）
        - stock_code: 股票代码（可选，用于查询特定股票）
        - page: 页码，默认1
        - page_size: 每页数量，默认20
        """
        try:
            # 获取查询参数
            date = request.query_params.get('date')
            stock_code = request.query_params.get('stock_code')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # 如果指定了股票代码，获取该股票的所有业绩快报
            if stock_code:
                if not validate_stock_symbol(stock_code):
                    return error_response("无效的股票代码格式", 400)
                
                data = individual_stock_service.get_stock_performance_reports(stock_code)
                if data is None:
                    return error_response("获取股票业绩快报数据失败", 500)
                
                # 分页处理
                paginator = Paginator(data, page_size)
                if page > paginator.num_pages:
                    return error_response("页码超出范围", 400)
                
                page_data = paginator.get_page(page)
                
                return success_response(
                    {
                        'reports': list(page_data),
                        'pagination': {
                            'current_page': page,
                            'total_pages': paginator.num_pages,
                            'total_count': paginator.count,
                            'page_size': page_size,
                            'has_next': page_data.has_next(),
                            'has_previous': page_data.has_previous()
                        }
                    },
                    f"成功获取股票{stock_code}的业绩快报数据"
                )
            
            # 如果指定了报告期，获取该期的所有业绩快报
            elif date:
                data = individual_stock_service.get_performance_report(date)
                if data is None:
                    return error_response("获取业绩快报数据失败", 500)
                
                # 分页处理
                paginator = Paginator(data, page_size)
                if page > paginator.num_pages:
                    return error_response("页码超出范围", 400)
                
                page_data = paginator.get_page(page)
                
                return success_response(
                    {
                        'reports': list(page_data),
                        'pagination': {
                            'current_page': page,
                            'total_pages': paginator.num_pages,
                            'total_count': paginator.count,
                            'page_size': page_size,
                            'has_next': page_data.has_next(),
                            'has_previous': page_data.has_previous()
                        }
                    },
                    f"成功获取{date}期业绩快报数据"
                )
            
            else:
                return error_response("请提供date（报告期）或stock_code（股票代码）参数", 400)
                
        except ValueError as e:
            return error_response(f"参数格式错误: {str(e)}", 400)
        except Exception as e:
            logger.error(f"获取业绩快报数据失败: {str(e)}")
            return error_response(f"获取业绩快报数据失败: {str(e)}", 500)


class StockPerformanceReportView(APIView):
    """
    单个股票业绩快报API视图
    提供特定股票的业绩快报数据查询
    """
    
    def get(self, request, stock_code):
        """
        获取指定股票的业绩快报数据
        
        路径参数:
        - stock_code: 股票代码
        
        查询参数:
        - page: 页码，默认1
        - page_size: 每页数量，默认20
        """
        try:
            # 验证股票代码
            if not validate_stock_symbol(stock_code):
                return error_response("无效的股票代码格式", 400)
            
            # 获取分页参数
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # 获取数据
            data = individual_stock_service.get_stock_performance_reports(stock_code)
            if data is None:
                return error_response("获取股票业绩快报数据失败", 500)
            
            # 分页处理
            paginator = Paginator(data, page_size)
            if page > paginator.num_pages and paginator.num_pages > 0:
                return error_response("页码超出范围", 400)
            
            page_data = paginator.get_page(page)
            
            return success_response(
                {
                    'stock_code': stock_code,
                    'reports': list(page_data),
                    'pagination': {
                        'current_page': page,
                        'total_pages': paginator.num_pages,
                        'total_count': paginator.count,
                        'page_size': page_size,
                        'has_next': page_data.has_next(),
                        'has_previous': page_data.has_previous()
                    }
                },
                f"成功获取股票{stock_code}的业绩快报数据"
            )
            
        except ValueError as e:
            return error_response(f"参数格式错误: {str(e)}", 400)
        except Exception as e:
            logger.error(f"获取股票业绩快报数据失败: {str(e)}")
            return error_response(f"获取股票业绩快报数据失败: {str(e)}", 500)

