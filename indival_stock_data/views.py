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
            
            # 获取股票列表
            stocks = individual_stock_service.get_stock_list()
            
            if not stocks:
                return Response({"message": "获取股票列表失败"}, status=status.HTTP_404_NOT_FOUND)
            
            # 分页处理
            paginator = Paginator(stocks, page_size)
            current_page = paginator.page(page)
            
            return Response({
                "total": paginator.count,
                "page": page,
                "page_size": page_size,
                "total_pages": paginator.num_pages,
                "data": list(current_page.object_list)
            })
        except Exception as e:
            logger.error(f"获取股票列表失败: {str(e)}")
            return Response({"message": f"获取股票列表失败: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StockRealtimeView(APIView):
    """
    获取股票实时行情
    """
    def get(self, request, stock_code=None):
        try:
            # 如果提供了股票代码，则获取单只股票的实时行情
            if stock_code:
                if not validate_stock_symbol(stock_code):
                    return Response({"message": f"无效的股票代码: {stock_code}"}, status=status.HTTP_400_BAD_REQUEST)
                
                realtime = individual_stock_service.get_stock_realtime(stock_code)
                
                if not realtime:
                    return Response({"message": f"获取股票{stock_code}实时行情失败"}, status=status.HTTP_404_NOT_FOUND)
                
                return Response(realtime)
            
            # 否则获取所有股票的实时行情
            # 获取分页参数
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # 获取所有股票的实时行情
            realtime_list = individual_stock_service.get_stock_realtime()
            
            if not realtime_list:
                return Response({"message": "获取股票实时行情失败"}, status=status.HTTP_404_NOT_FOUND)
            
            # 分页处理
            paginator = Paginator(realtime_list, page_size)
            current_page = paginator.page(page)
            
            return Response({
                "total": paginator.count,
                "page": page,
                "page_size": page_size,
                "total_pages": paginator.num_pages,
                "data": list(current_page.object_list)
            })
        except Exception as e:
            logger.error(f"获取股票实时行情失败: {str(e)}")
            return Response({"message": f"获取股票实时行情失败: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StockHistoryView(APIView):
    """
    获取股票历史行情数据
    """
    def get(self, request, stock_code):
        try:
            if not validate_stock_symbol(stock_code):
                return Response({"message": f"无效的股票代码: {stock_code}"}, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取查询参数
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            adjust = request.query_params.get('adjust', "")
            
            # 获取历史数据
            history = individual_stock_service.get_stock_history(stock_code, start_date, end_date, adjust)
            
            if not history:
                return Response({"message": f"获取股票{stock_code}历史行情数据失败"}, status=status.HTTP_404_NOT_FOUND)
            
            return Response(history)
        except Exception as e:
            logger.error(f"获取股票历史行情数据失败: {str(e)}")
            return Response({"message": f"获取股票历史行情数据失败: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StockInfoView(APIView):
    """
    获取股票详细信息
    """
    def get(self, request, stock_code):
        try:
            if not validate_stock_symbol(stock_code):
                return Response({"message": f"无效的股票代码: {stock_code}"}, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取股票详细信息
            info = individual_stock_service.get_stock_info(stock_code)
            
            if not info:
                return Response({"message": f"获取股票{stock_code}详细信息失败"}, status=status.HTTP_404_NOT_FOUND)
            
            return Response(info)
        except Exception as e:
            logger.error(f"获取股票详细信息失败: {str(e)}")
            return Response({"message": f"获取股票详细信息失败: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def update_stock_data(request):
    """
    手动更新股票数据
    """
    try:
        # 获取请求参数
        stock_code = request.data.get('stock_code')
        update_type = request.data.get('update_type', 'all')  # all, realtime, history
        days = int(request.data.get('days', 30))
        
        result = {}
        
        # 根据更新类型执行不同的更新操作
        if update_type == 'all' or update_type == 'realtime':
            # 更新实时行情
            if stock_code:
                realtime = individual_stock_service.get_stock_realtime(stock_code)
                result['realtime'] = "success" if realtime else "failed"
            else:
                updated, created, failed = individual_stock_service.update_all_stocks()
                result['realtime'] = {
                    "updated": updated,
                    "created": created,
                    "failed": failed
                }
        
        if update_type == 'all' or update_type == 'history':
            # 更新历史数据
            updated_stocks, updated_history = individual_stock_service.update_stock_history(stock_code, days)
            result['history'] = {
                "updated_stocks": updated_stocks,
                "updated_history": updated_history
            }
        
        return Response({
            "message": "股票数据更新成功",
            "result": result
        })
    except Exception as e:
        logger.error(f"更新股票数据失败: {str(e)}")
        return Response({"message": f"更新股票数据失败: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
