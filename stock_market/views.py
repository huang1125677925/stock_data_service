from django.shortcuts import render
from django.db import models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator
from .services import get_sse_daily_overview, get_rise_fall_ratio_data
from .models import IndexBasicData
import logging
from common.response import success_response, error_response

logger = logging.getLogger(__name__)

class SSEDailyOverviewView(APIView):
    """
    获取上海证券交易所每日概况数据的API视图
    """
    def get(self, request):
        """
        获取上证每日概况数据
        
        参数:
            date (str, optional): 日期，格式为YYYYMMDD，默认为最近一个交易日
        """
        try:
            date = request.query_params.get('date')
            result = get_sse_daily_overview(date)
            return success_response(result)
        except ValueError as e:
            logger.error(f"参数格式错误: {str(e)}")
            return error_response(f'参数格式错误: {str(e)}', 400)
        except Exception as e:
            logger.error(f"获取上证每日概况数据失败: {str(e)}")
            return error_response(f'获取上证每日概况数据失败: {str(e)}', 500)


class IndexBasicDataView(APIView):
    """
    指数基础数据查询接口
    
    功能：提供指数基础数据的增删改查操作
    支持的操作：
        - GET: 查询指数列表（支持分页、搜索）
        - POST: 创建新的指数记录
        - PUT: 更新指数信息
        - DELETE: 删除指数记录
    """
    
    def get(self, request):
        """
        查询指数基础数据列表
        
        参数:
            page (int, optional): 页码，默认为1
            page_size (int, optional): 每页数量，默认为20，最大100
            search (str, optional): 搜索关键词，支持按代码或名称搜索
            code (str, optional): 精确匹配指数代码
        
        返回:
            包含指数列表和分页信息的响应
        """
        try:
            # 获取查询参数
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 20)), 100)
            search = request.query_params.get('search', '').strip()
            code = request.query_params.get('code', '').strip()
            
            # 构建查询集
            queryset = IndexBasicData.objects.all()
            
            # 精确匹配代码
            if code:
                queryset = queryset.filter(code=code)
            # 模糊搜索
            elif search:
                queryset = queryset.filter(
                    models.Q(code__icontains=search) | 
                    models.Q(name__icontains=search)
                )
            
            # 分页处理
            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)
            
            # 序列化数据
            data = []
            for item in page_obj:
                data.append({
                    'id': item.id,
                    'code': item.code,
                    'name': item.name,
                    'created_at': item.created_at.isoformat(),
                    'updated_at': item.updated_at.isoformat()
                })
            
            # 构建响应数据
            result = {
                'list': data,
                'pagination': {
                    'current_page': page_obj.number,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count,
                    'page_size': page_size,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous()
                }
            }
            
            return success_response(result, '查询成功')
            
        except ValueError as e:
            logger.error(f"参数格式错误: {str(e)}")
            return error_response(f'参数格式错误: {str(e)}', 400)
        except Exception as e:
            logger.error(f"查询指数基础数据失败: {str(e)}")
            return error_response(f'查询指数基础数据失败: {str(e)}', 500)
    
    def post(self, request):
        """
        创建新的指数记录
        
        参数:
            code (str): 指数代码，必填
            name (str): 指数名称，必填
        
        返回:
            创建成功的指数信息
        """
        try:
            data = request.data
            code = data.get('code', '').strip()
            name = data.get('name', '').strip()
            
            # 参数验证
            if not code:
                return error_response('指数代码不能为空', 400)
            if not name:
                return error_response('指数名称不能为空', 400)
            
            # 检查代码是否已存在
            if IndexBasicData.objects.filter(code=code).exists():
                return error_response(f'指数代码 {code} 已存在', 400)
            
            # 创建记录
            index_data = IndexBasicData.objects.create(
                code=code,
                name=name
            )
            
            result = {
                'id': index_data.id,
                'code': index_data.code,
                'name': index_data.name,
                'created_at': index_data.created_at.isoformat(),
                'updated_at': index_data.updated_at.isoformat()
            }
            
            return success_response(result, '创建成功')
            
        except Exception as e:
            logger.error(f"创建指数基础数据失败: {str(e)}")
            return error_response(f'创建指数基础数据失败: {str(e)}', 500)
    
    def put(self, request):
        """
        更新指数信息
        
        参数:
            id (int): 指数ID，必填
            code (str, optional): 新的指数代码
            name (str, optional): 新的指数名称
        
        返回:
            更新后的指数信息
        """
        try:
            data = request.data
            index_id = data.get('id')
            
            if not index_id:
                return error_response('指数ID不能为空', 400)
            
            # 查找记录
            try:
                index_data = IndexBasicData.objects.get(id=index_id)
            except IndexBasicData.DoesNotExist:
                return error_response('指数记录不存在', 404)
            
            # 更新字段
            code = data.get('code', '').strip()
            name = data.get('name', '').strip()
            
            if code and code != index_data.code:
                # 检查新代码是否已存在
                if IndexBasicData.objects.filter(code=code).exclude(id=index_id).exists():
                    return error_response(f'指数代码 {code} 已存在', 400)
                index_data.code = code
            
            if name:
                index_data.name = name
            
            index_data.save()
            
            result = {
                'id': index_data.id,
                'code': index_data.code,
                'name': index_data.name,
                'created_at': index_data.created_at.isoformat(),
                'updated_at': index_data.updated_at.isoformat()
            }
            
            return success_response(result, '更新成功')
            
        except Exception as e:
            logger.error(f"更新指数基础数据失败: {str(e)}")
            return error_response(f'更新指数基础数据失败: {str(e)}', 500)
    
    def delete(self, request):
        """
        删除指数记录
        
        参数:
            id (int): 指数ID，必填
        
        返回:
            删除结果
        """
        try:
            data = request.data
            index_id = data.get('id')
            
            if not index_id:
                return error_response('指数ID不能为空', 400)
            
            # 查找并删除记录
            try:
                index_data = IndexBasicData.objects.get(id=index_id)
                index_data.delete()
                return success_response(None, '删除成功')
            except IndexBasicData.DoesNotExist:
                return error_response('指数记录不存在', 404)
            
        except Exception as e:
            logger.error(f"删除指数基础数据失败: {str(e)}")
            return error_response(f'删除指数基础数据失败: {str(e)}', 500)


class IndexHighLowStatisticsView(APIView):
    """
    指数涨跌统计数据API视图
    
    功能：提供指数涨跌统计数据的查询接口（仅从数据库查询）
    支持的操作：
        - GET: 查询指数涨跌统计数据
    参数：
        - index_code: 指数代码（all/sz50/hs300/zz500）
        - start_date: 开始日期
        - end_date: 结束日期
        - limit: 返回记录数量限制
    返回值：包含涨跌统计数据的JSON响应
    事件：数据查询操作
    """
    
    def get(self, request):
        """
        查询指数涨跌统计数据（仅从数据库查询）
        
        参数:
            index_code (str, optional): 指数代码，可选值：'all', 'sz50', 'hs300', 'zz500'
            start_date (str, optional): 开始日期，格式：YYYY-MM-DD
            end_date (str, optional): 结束日期，格式：YYYY-MM-DD
            limit (int, optional): 返回记录数量限制，默认30
        """
        try:
            index_code = request.query_params.get('index_code')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            limit = int(request.query_params.get('limit', 30))
            
            # 从数据库查询数据
            result = get_rise_fall_ratio_data(
                index_code=index_code,
                start_date=start_date,
                end_date=end_date,
                limit=limit
            )
            return success_response(result, '查询指数涨跌统计数据成功')
                
        except ValueError as e:
            logger.error(f"参数格式错误: {str(e)}")
            return error_response(f'参数格式错误: {str(e)}', 400)
        except Exception as e:
            logger.error(f"查询涨跌统计数据失败: {str(e)}")
            return error_response(f'查询涨跌统计数据失败: {str(e)}', 500)


class RiseFallRatioView(APIView):
    """
    涨跌比数据查询API视图
    
    功能：查询指数的涨跌比历史数据
    参数：
        - index_code: 指数代码（可选）
        - start_date: 开始日期（可选）
        - end_date: 结束日期（可选）
        - limit: 返回记录数限制
    返回值：涨跌比数据列表
    事件：数据库查询操作
    """
    
    def get(self, request):
        """
        查询涨跌比数据
        
        参数:
            index_code (str, optional): 指数代码，不指定则查询所有
            start_date (str, optional): 开始日期，格式YYYY-MM-DD
            end_date (str, optional): 结束日期，格式YYYY-MM-DD
            limit (int, optional): 返回记录数限制，默认30条
        """
        try:
            index_code = request.query_params.get('index_code')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            limit = int(request.query_params.get('limit', 500))
            
            # 验证limit参数
            if limit <= 0 or limit > 1000:
                return error_response('limit参数必须在1-1000之间', 400)
            
            result = get_rise_fall_ratio_data(
                index_code=index_code,
                start_date=start_date,
                end_date=end_date,
                limit=limit
            )
            
            return success_response({
                'count': len(result),
                'results': result
            }, '查询涨跌比数据成功')
            
        except ValueError as e:
            logger.error(f"参数格式错误: {str(e)}")
            return error_response(f'参数格式错误: {str(e)}', 400)
        except Exception as e:
            logger.error(f"查询涨跌比数据失败: {str(e)}")
            return error_response(f'查询涨跌比数据失败: {str(e)}', 500)
