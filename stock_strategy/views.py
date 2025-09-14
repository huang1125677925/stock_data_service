from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import pandas as pd
from datetime import datetime
from .services import rps_service
from .models import IndexRPS
from .industry_turnover_strategy import industry_turnover_strategy
from common.response import success_response, error_response

@csrf_exempt
@require_http_methods(["GET"])
def get_index_rps(request):
    """
    获取指数RPS强度排名数据
    
    Query Parameters:
        periods (str): 时间周期，多个周期用逗号分隔，如 "5,20,60"
        save (bool): 是否保存到数据库，默认False
    
    Returns:
        JSON响应
    """
    try:
        # 获取查询参数
        periods_str = request.GET.get('periods', '5,20,60')
        save = request.GET.get('save', 'false').lower() == 'true'
        
        # 解析周期参数
        try:
            periods = [int(p.strip()) for p in periods_str.split(',') if p.strip()]
            if not periods:
                periods = [5, 20, 60]  # 默认周期
        except ValueError:
            return error_response('周期参数格式错误，应为逗号分隔的整数', 400)
        
        # 获取RPS数据
        df, errors = rps_service.get_rps_data(periods)
        
        if df is None:
            return error_response(f'获取RPS数据失败: {", ".join(errors)}', 500)
        
        # 保存数据到数据库
        saved_count = 0
        if save:
            saved_count = rps_service.save_rps_data(df, periods)
        
        # 转换DataFrame为JSON可序列化格式
        result = df.fillna('').to_dict('records')
        
        return success_response({
            'total': len(result),
            'data': result,
            'periods': periods,
            'saved_count': saved_count,
            'errors': errors,
            'query_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        return error_response(f'获取指数RPS强度排名失败: {str(e)}', 500)

@csrf_exempt
@require_http_methods(["GET"])
def get_historical_rps(request):
    """
    获取历史RPS数据
    
    Query Parameters:
        period (int): 时间周期，默认20
        limit (int): 返回数量限制，默认100
        offset (int): 偏移量，默认0
    
    Returns:
        JSON响应
    """
    try:
        # 获取查询参数
        period = int(request.GET.get('period', 20))
        limit = int(request.GET.get('limit', 100))
        offset = int(request.GET.get('offset', 0))
        
        # 查询数据库
        queryset = IndexRPS.objects.filter(period=period)
        
        # 获取总数
        total = queryset.count()
        
        # 应用分页
        items = queryset[offset:offset+limit]
        
        # 转换为字典列表
        result = [item.to_dict() for item in items]
        
        return success_response({
            'total': total,
            'data': result,
            'period': period,
            'query_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        return error_response(f'获取历史RPS数据失败: {str(e)}', 500)

@csrf_exempt
@require_http_methods(["GET"])
def get_industry_turnover_percentile(request):
    """
    获取行业成交额占比分位数数据
    
    Query Parameters:
        start_date (str): 开始日期，格式为YYYY-MM-DD，默认为7天前
        end_date (str): 结束日期，格式为YYYY-MM-DD，默认为当天
        use_cache (bool): 是否使用缓存，默认为True
    
    Returns:
        JSON响应，包含每个行业在指定日期范围内的成交额占比分位数数据
    """
    try:
        # 获取查询参数
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        use_cache = request.GET.get('use_cache', 'true').lower() == 'true'
        
        # 获取行业成交额占比分位数数据
        result = industry_turnover_strategy.get_industry_turnover_percentile(
            start_date=start_date,
            end_date=end_date
        )
        
        if result is None:
            return error_response('获取行业成交额占比分位数数据失败', 500)
        
        return success_response({
            'total': len(result),
            'data': result,
            'start_date': start_date,
            'end_date': end_date,
            'query_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        return error_response(f'获取行业成交额占比分位数数据失败: {str(e)}', 500)
