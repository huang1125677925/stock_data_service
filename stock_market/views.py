from datetime import datetime

from django.shortcuts import render
from django.db import models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator
from .services import get_sse_daily_overview, get_rise_fall_ratio_data
from .models import IndexBasicData, StockMarketFundFlow
import logging
from common.response import success_response, error_response
from common.tushare_proxy import call_tushare

logger = logging.getLogger(__name__)


def _normalize_market_flow_date(date_str):
    """
    规范化大盘资金流查询日期格式。

    参数:
        date_str (str | None): 原始日期字符串，支持 YYYY-MM-DD 或 YYYYMMDD，为空时直接返回 None。

    返回值:
        str | None: 转换后的 YYYYMMDD 格式日期；若传入为空则返回 None。

    异常情况:
        ValueError: 当日期格式既不是 YYYY-MM-DD 也不是 YYYYMMDD 时抛出异常。
    """
    if not date_str:
        return None

    cleaned_date = date_str.strip()
    if not cleaned_date:
        return None

    for fmt in ('%Y-%m-%d', '%Y%m%d'):
        try:
            return datetime.strptime(cleaned_date, fmt).strftime('%Y%m%d')
        except ValueError:
            continue

    raise ValueError('日期格式错误，请使用YYYY-MM-DD或YYYYMMDD格式')


def _to_float(value):
    """
    将 Decimal、int 等数值转换为 float，便于接口序列化。

    参数:
        value (Any): 待转换的数值对象。

    返回值:
        float | None: 转换后的浮点数；当值为空时返回 None。

    异常情况:
        ValueError: 当传入值无法转换为 float 时抛出异常。
        TypeError: 当传入值类型不支持转换时抛出异常。
    """
    if value is None or value == '':
        return None
    return float(value)


def _build_market_flow_change_summary(records):
    """
    生成大盘资金流区间变化摘要。

    参数:
        records (list[dict]): 已按交易日升序排列的大盘资金流记录列表。

    返回值:
        dict: 包含区间首尾日期、主力净流入变化、上证/深证收盘价变化与涨跌幅表现的摘要信息。

    异常情况:
        无。若记录为空则返回空摘要结构。
    """
    if not records:
        return {
            'start_date': None,
            'end_date': None,
            'record_count': 0,
            'net_amount_change': None,
            'shanghai_close_change': None,
            'shenzhen_close_change': None,
            'shanghai_change_rate_span': None,
            'shenzhen_change_rate_span': None,
        }

    first_record = records[0]
    last_record = records[-1]

    def _diff(field_name):
        start_value = first_record.get(field_name)
        end_value = last_record.get(field_name)
        if start_value is None or end_value is None:
            return None
        return round(end_value - start_value, 4)

    return {
        'start_date': first_record.get('trade_date'),
        'end_date': last_record.get('trade_date'),
        'record_count': len(records),
        'net_amount_change': _diff('net_amount'),
        'shanghai_close_change': _diff('close_sh'),
        'shenzhen_close_change': _diff('close_sz'),
        'shanghai_change_rate_span': _diff('pct_change_sh'),
        'shenzhen_change_rate_span': _diff('pct_change_sz'),
    }

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


class StockMarketFundFlowView(APIView):
    """
    大盘资金流数据查询接口
    
    功能：提供大盘资金流数据的查询操作（仅从数据库查询）
    支持的操作：
        - GET: 查询大盘资金流数据（支持分页、日期范围查询）
    参数：
        - start_date: 开始日期，格式：YYYY-MM-DD
        - end_date: 结束日期，格式：YYYY-MM-DD
        - page: 页码，默认为1
        - page_size: 每页数量，默认为20，最大100
        - order_by: 排序字段，默认按日期倒序
    返回值：包含资金流数据和分页信息的JSON响应
    事件：数据库查询操作
    """
    
    def get(self, request):
        """
        查询大盘资金流数据
        
        参数:
            start_date (str, optional): 开始日期，格式：YYYY-MM-DD
            end_date (str, optional): 结束日期，格式：YYYY-MM-DD
            page (int, optional): 页码，默认为1
            page_size (int, optional): 每页数量，默认为20，最大100
            order_by (str, optional): 排序字段，可选值：date, -date（默认）
        
        返回:
            包含资金流数据列表和分页信息的响应
        """
        try:
            # 获取查询参数
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 20)), 100)
            order_by = request.query_params.get('order_by', '-date')
            
            # 验证参数
            if page <= 0:
                return error_response('页码必须大于0', 400)
            if page_size <= 0:
                return error_response('每页数量必须大于0', 400)
            
            # 构建查询集
            queryset = StockMarketFundFlow.objects.all()
            
            # 日期范围过滤
            if start_date:
                try:
                    queryset = queryset.filter(date__gte=start_date)
                except ValueError:
                    return error_response('开始日期格式错误，请使用YYYY-MM-DD格式', 400)
            
            if end_date:
                try:
                    queryset = queryset.filter(date__lte=end_date)
                except ValueError:
                    return error_response('结束日期格式错误，请使用YYYY-MM-DD格式', 400)
            
            # 排序
            if order_by in ['date', 'created_at', '-created_at']:
                queryset = queryset.order_by(order_by)
            else:
                queryset = queryset.order_by('date')  # 默认按日期倒序
            
            # 分页处理
            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)
            
            # 序列化数据
            data = []
            for item in page_obj:
                data.append({
                    'id': item.id,
                    'date': item.date.isoformat(),
                    'main_net_inflow_amount': float(item.main_net_inflow_amount) if item.main_net_inflow_amount else None,
                    'small_net_inflow_amount': float(item.small_net_inflow_amount) if item.small_net_inflow_amount else None,
                    'medium_net_inflow_amount': float(item.medium_net_inflow_amount) if item.medium_net_inflow_amount else None,
                    'large_net_inflow_amount': float(item.large_net_inflow_amount) if item.large_net_inflow_amount else None,
                    'super_large_net_inflow_amount': float(item.super_large_net_inflow_amount) if item.super_large_net_inflow_amount else None,
                    'main_net_inflow_ratio': float(item.main_net_inflow_ratio) if item.main_net_inflow_ratio else None,
                    'small_net_inflow_ratio': float(item.small_net_inflow_ratio) if item.small_net_inflow_ratio else None,
                    'medium_net_inflow_ratio': float(item.medium_net_inflow_ratio) if item.medium_net_inflow_ratio else None,
                    'large_net_inflow_ratio': float(item.large_net_inflow_ratio) if item.large_net_inflow_ratio else None,
                    'super_large_net_inflow_ratio': float(item.super_large_net_inflow_ratio) if item.super_large_net_inflow_ratio else None,
                    'shanghai_close_price': float(item.shanghai_close_price) if item.shanghai_close_price else None,
                    'shanghai_change_rate': float(item.shanghai_change_rate) if item.shanghai_change_rate else None,
                    'shenzhen_close_price': float(item.shenzhen_close_price) if item.shenzhen_close_price else None,
                    'shenzhen_change_rate': float(item.shenzhen_change_rate) if item.shenzhen_change_rate else None,
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
            
            return success_response(result, '查询大盘资金流数据成功')
            
        except ValueError as e:
            logger.error(f"参数格式错误: {str(e)}")
            return error_response(f'参数格式错误: {str(e)}', 400)
        except Exception as e:
            logger.error(f"查询大盘资金流数据失败: {str(e)}")
            return error_response(f'查询大盘资金流数据失败: {str(e)}', 500)


class StockMarketFundFlowTrendView(APIView):
    """
    大盘资金流趋势查询接口。

    功能：基于 Tushare `moneyflow_mkt_dc` 接口查询指定日期范围内的大盘资金流趋势数据，
    供前端展示区间内的资金变化、上证/深证涨跌幅以及收盘价变化。
    参数：
        - trade_date: 单个交易日，支持 YYYY-MM-DD 或 YYYYMMDD 格式
        - start_date: 开始日期，支持 YYYY-MM-DD 或 YYYYMMDD 格式
        - end_date: 结束日期，支持 YYYY-MM-DD 或 YYYYMMDD 格式
    返回值：包含接口标识、记录数量、趋势明细、区间变化摘要和查询条件的 JSON 响应
    事件：调用 Tushare 大盘资金流向接口并返回前端可视化所需结构
    """

    def get(self, request):
        """
        查询大盘资金流趋势数据。

        参数:
            request (Request): Django REST Framework 请求对象。支持 trade_date、start_date、end_date 查询参数。

        返回值:
            Response: 使用 `success_response` 或 `error_response` 包装的 JSON 响应。

        异常情况:
            ValueError: 当日期格式错误或开始日期晚于结束日期时返回参数错误响应。
            Exception: 当调用 Tushare 失败或数据处理异常时返回失败响应。
        """
        try:
            trade_date = _normalize_market_flow_date(request.query_params.get('trade_date'))
            start_date = _normalize_market_flow_date(request.query_params.get('start_date'))
            end_date = _normalize_market_flow_date(request.query_params.get('end_date'))

            if start_date and end_date and start_date > end_date:
                return error_response('开始日期不能晚于结束日期', 400)

            if trade_date and (start_date or end_date):
                return error_response('trade_date 与 start_date/end_date 不能同时传入', 400)

            if not trade_date and not start_date and not end_date:
                return error_response('请至少传入 trade_date 或 start_date/end_date 之一', 400)

            params = {
                key: value
                for key, value in {
                    'trade_date': trade_date,
                    'start_date': start_date,
                    'end_date': end_date,
                }.items()
                if value
            }
            fields = (
                'trade_date,close_sh,pct_change_sh,close_sz,pct_change_sz,'
                'net_amount,net_amount_rate,buy_elg_amount,buy_elg_amount_rate,'
                'buy_lg_amount,buy_lg_amount_rate,buy_md_amount,buy_md_amount_rate,'
                'buy_sm_amount,buy_sm_amount_rate'
            )

            tushare_result = call_tushare(
                interface='moneyflow_mkt_dc',
                params=params,
                fields=fields,
                use_query=False,
            )
            if tushare_result.get('code') != 200:
                error_message = tushare_result.get('message') or '调用大盘资金流向接口失败'
                logger.error(f"调用 Tushare 大盘资金流向接口失败: {tushare_result}")
                return error_response(error_message, tushare_result.get('code', 500))

            raw_records = tushare_result.get('data', {}).get('records', [])
            sorted_records = sorted(raw_records, key=lambda item: item.get('trade_date', ''))

            records = []
            baseline_net_amount = None
            baseline_close_sh = None
            baseline_close_sz = None

            for item in sorted_records:
                net_amount = _to_float(item.get('net_amount'))
                close_sh = _to_float(item.get('close_sh'))
                close_sz = _to_float(item.get('close_sz'))

                if baseline_net_amount is None and net_amount is not None:
                    baseline_net_amount = net_amount
                if baseline_close_sh is None and close_sh is not None:
                    baseline_close_sh = close_sh
                if baseline_close_sz is None and close_sz is not None:
                    baseline_close_sz = close_sz

                records.append({
                    'trade_date': item.get('trade_date'),
                    'close_sh': close_sh,
                    'pct_change_sh': _to_float(item.get('pct_change_sh')),
                    'close_sz': close_sz,
                    'pct_change_sz': _to_float(item.get('pct_change_sz')),
                    'net_amount': net_amount,
                    'net_amount_rate': _to_float(item.get('net_amount_rate')),
                    'buy_elg_amount': _to_float(item.get('buy_elg_amount')),
                    'buy_elg_amount_rate': _to_float(item.get('buy_elg_amount_rate')),
                    'buy_lg_amount': _to_float(item.get('buy_lg_amount')),
                    'buy_lg_amount_rate': _to_float(item.get('buy_lg_amount_rate')),
                    'buy_md_amount': _to_float(item.get('buy_md_amount')),
                    'buy_md_amount_rate': _to_float(item.get('buy_md_amount_rate')),
                    'buy_sm_amount': _to_float(item.get('buy_sm_amount')),
                    'buy_sm_amount_rate': _to_float(item.get('buy_sm_amount_rate')),
                    'net_amount_change': round(net_amount - baseline_net_amount, 4)
                    if net_amount is not None and baseline_net_amount is not None else None,
                    'close_sh_change': round(close_sh - baseline_close_sh, 4)
                    if close_sh is not None and baseline_close_sh is not None else None,
                    'close_sz_change': round(close_sz - baseline_close_sz, 4)
                    if close_sz is not None and baseline_close_sz is not None else None,
                })

            result = {
                'interface': 'moneyflow_mkt_dc',
                'count': len(records),
                'records': records,
                'summary': _build_market_flow_change_summary(records),
                'query': {
                    'trade_date': trade_date,
                    'start_date': start_date,
                    'end_date': end_date,
                }
            }
            return success_response(result, '查询大盘资金流趋势数据成功')

        except ValueError as e:
            logger.error(f"参数格式错误: {str(e)}")
            return error_response(f'参数格式错误: {str(e)}', 400)
        except Exception as e:
            logger.error(f"查询大盘资金流趋势数据失败: {str(e)}")
            return error_response(f'查询大盘资金流趋势数据失败: {str(e)}', 500)


class IndexInfoView(APIView):
    """
    指数信息查询接口（仅从数据库读取）

    功能：提供指数基础信息的查询（code/name），支持按代码精确匹配或关键词搜索。
    参数：
        - code: 指数代码（精确匹配）
        - search: 关键词，模糊匹配代码或名称
        - limit: 返回数量上限，默认100，最大1000
    返回：
        - list: 指数记录列表（id, code, name）
        - count: 返回记录数量
    """

    def get(self, request):
        try:
            code = request.query_params.get('code', '').strip()
            search = request.query_params.get('search', '').strip()
            limit = int(request.query_params.get('limit', 100))
            limit = max(1, min(limit, 1000))

            qs = IndexBasicData.objects.all()
            if code:
                qs = qs.filter(code=code)
            elif search:
                qs = qs.filter(models.Q(code__icontains=search) | models.Q(name__icontains=search))

            records = []
            for item in qs[:limit]:
                records.append({
                    'id': item.id,
                    'code': item.code,
                    'name': item.name,
                })

            return success_response({'count': len(records), 'list': records}, '查询指数信息成功')

        except ValueError as e:
            logger.error(f"参数格式错误: {str(e)}")
            return error_response(f'参数格式错误: {str(e)}', 400)
        except Exception as e:
            logger.error(f"查询指数信息失败: {str(e)}")
            return error_response(f'查询指数信息失败: {str(e)}', 500)
