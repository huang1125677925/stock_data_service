from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.core.cache import cache
import json
import pandas as pd
from datetime import datetime
import hashlib
from .services import rps_service, StockScreeningService
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


@csrf_exempt
@require_http_methods(["GET"])
def screen_stocks_by_previous_high(request):
    """
    使用前高突破策略筛选股票
    
    功能：根据窗口大小和成交量倍数筛选符合条件的股票
    参数：
    - window_size: 分析窗口大小（交易日数量），默认60
    - volume_multiplier: 成交量放大倍数，默认1.5
    - stock_codes: 指定股票代码列表，可选（通过逗号分隔的字符串传递）
    - limit: 返回结果数量限制，默认50
    
    返回值：
    - 成功时返回筛选结果和统计信息
    - 失败时返回错误信息
    
    事件：
    - 参数验证失败时记录错误日志
    - 筛选过程中出现异常时记录错误日志
    """
    try:
        # 获取GET参数
        window_size = int(request.GET.get('window_size', 60))
        volume_multiplier = float(request.GET.get('volume_multiplier', 1.5))
        stock_codes_str = request.GET.get('stock_codes', None)
        limit = int(request.GET.get('limit', 50))
        
        # 处理股票代码列表
        stock_codes = None
        if stock_codes_str:
            stock_codes = [code.strip() for code in stock_codes_str.split(',') if code.strip()]
        
        # 生成缓存键
        cache_key_data = f"screen_stocks_{window_size}_{volume_multiplier}_{stock_codes_str or 'all'}_{limit}"
        cache_key = hashlib.md5(cache_key_data.encode()).hexdigest()
        
        # 尝试从缓存获取结果
        cached_result = cache.get(cache_key)
        if cached_result:
            return success_response(cached_result, "股票筛选成功（缓存数据）")
        
        # 创建服务实例
        screening_service = StockScreeningService()
        
        # 验证参数
        validation_result = screening_service.validate_parameters(window_size, volume_multiplier)
        if not validation_result['valid']:
            return error_response(f"参数验证失败: {', '.join(validation_result['errors'])}", 400)
        
        # 执行筛选
        result = screening_service.screen_stocks_by_previous_high(
            window_size=window_size,
            volume_multiplier=volume_multiplier,
            stock_codes=stock_codes,
            limit=limit
        )
        
        if result['success']:
            # 将结果缓存15分钟
            cache.set(cache_key, result['data'], 3600 * 24)
            return success_response(result['data'], result['message'])
        else:
            return error_response(result['message'], 500)
            
    except (ValueError, TypeError) as e:
        return error_response(f'参数格式错误: {str(e)}', 400)
    except Exception as e:
        return error_response(f'股票筛选失败: {str(e)}', 500)


@csrf_exempt
@require_http_methods(["GET"])
def get_stock_analysis_detail(request, stock_code):
    """
    获取单只股票的详细分析结果
    
    功能：分析指定股票是否符合前高突破策略条件
    参数：
    - stock_code: 股票代码（URL路径参数）
    - window_size: 分析窗口大小，默认20
    - volume_multiplier: 成交量放大倍数，默认1.5
    
    返回值：
    - 成功时返回股票详细分析结果和交易数据
    - 失败时返回错误信息
    
    事件：
    - 股票不存在时返回404错误
    - 股票不符合条件时返回相应提示
    """
    try:
        # 获取查询参数
        window_size = int(request.GET.get('window_size', 20))
        volume_multiplier = float(request.GET.get('volume_multiplier', 1.5))
        
        # 创建服务实例
        screening_service = StockScreeningService()
        
        # 验证参数
        validation_result = screening_service.validate_parameters(window_size, volume_multiplier)
        if not validation_result['valid']:
            return error_response(f"参数验证失败: {', '.join(validation_result['errors'])}", 400)
        
        # 获取分析详情
        result = screening_service.get_stock_analysis_detail(
            stock_code=stock_code,
            window_size=window_size,
            volume_multiplier=volume_multiplier
        )
        
        if result['success']:
            return success_response(result['data'], result['message'])
        else:
            status_code = 404 if '不存在' in result['message'] else 400
            return error_response(result['message'], status_code)
            
    except ValueError as e:
        return error_response(f'参数格式错误: {str(e)}', 400)
    except Exception as e:
        return error_response(f'获取股票分析详情失败: {str(e)}', 500)
