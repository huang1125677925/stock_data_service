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
from scheduled_tasks.stock_data_query_tasks.stock_tagging_tasks import stock_tagging_service
from .industry_ma_breadth_strategy import industry_ma_breadth_strategy
from .industry_scale_breadth_strategy import industry_scale_breadth_strategy
from .industry_actual_output_strategy import industry_actual_output_strategy

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
        start_date (str): 开始日期，格式YYYY-MM-DD
        end_date (str): 结束日期，格式YYYY-MM-DD
        periods (str): 时间周期，多个周期用逗号分隔，如 "5,20,60"
        limit (int): 返回记录数限制，默认100
    
    Returns:
        JSON响应
    """
    try:
        # 获取查询参数
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        periods_str = request.GET.get('periods', '5,20,60')
        limit = int(request.GET.get('limit', 100))
        
        # 解析周期参数
        try:
            periods = [int(p.strip()) for p in periods_str.split(',') if p.strip()]
            if not periods:
                periods = [5, 20, 60]  # 默认周期
        except ValueError:
            return error_response('周期参数格式错误，应为逗号分隔的整数', 400)
        
        # 获取历史RPS数据
        queryset = IndexRPS.objects.all()
        
        # 应用日期过滤
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        # 应用周期过滤
        queryset = queryset.filter(period__in=periods)
        
        # 排序和限制
        queryset = queryset.order_by('-date', 'period')[:limit]
        
        # 转换为字典格式
        data = []
        for rps in queryset:
            data.append({
                'date': rps.date.strftime('%Y-%m-%d'),
                'period': rps.period,
                'rps_value': rps.rps_value,
                'created_at': rps.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        result = {
            'historical_rps': data,
            'periods': periods,
            'total_count': len(data),
            'filters': {
                'start_date': start_date,
                'end_date': end_date,
                'limit': limit
            }
        }
        
        return success_response(result, f'成功获取{len(data)}条历史RPS数据')
        
    except Exception as e:
        return error_response(f'获取历史RPS数据失败: {str(e)}', 500)

@csrf_exempt
@require_http_methods(["GET"])
def get_industry_turnover_percentile(request):
    """
    获取行业换手率百分位数据
    
    Query Parameters:
        date (str): 查询日期，格式YYYY-MM-DD，默认为最新日期
        percentile (float): 百分位数，0-100之间，默认80
    
    Returns:
        JSON响应
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
    
    功能：根据窗口大小和成交量倍数筛选符合条件的股票，支持自动标记功能
    参数：
    - window_size: 分析窗口大小（交易日数量），默认60
    - volume_multiplier: 成交量放大倍数，默认1.5
    - stock_codes: 指定股票代码列表，可选（通过逗号分隔的字符串传递）
    - limit: 返回结果数量限制，默认50
    - auto_tag: 是否自动标记筛选结果到数据库，默认false
    
    返回值：
    - 成功时返回筛选结果和统计信息
    - 失败时返回错误信息
    
    事件：
    - 参数验证失败时记录错误日志
    - 筛选过程中出现异常时记录错误日志
    - 自动标记时记录标记结果
    """
    try:
        # 获取GET参数
        window_size = int(request.GET.get('window_size', 60))
        volume_multiplier = float(request.GET.get('volume_multiplier', 1.5))
        stock_codes_str = request.GET.get('stock_codes', None)
        limit = int(request.GET.get('limit', 50))
        auto_tag = request.GET.get('auto_tag', 'false').lower() == 'true'
        
        # 处理股票代码列表
        stock_codes = None
        if stock_codes_str:
            stock_codes = [code.strip() for code in stock_codes_str.split(',') if code.strip()]
        
        # 生成缓存键（不包含auto_tag参数，因为标记不影响筛选结果）
        cache_key_data = f"screen_stocks_{window_size}_{volume_multiplier}_{stock_codes_str or 'all'}_{limit}"
        cache_key = hashlib.md5(cache_key_data.encode()).hexdigest()
        
        # 尝试从缓存获取结果
        cached_result = cache.get(cache_key)
        if cached_result and not auto_tag:  # 如果需要标记，则不使用缓存
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
            response_data = result['data']
            response_message = result['message']
            
            # 如果启用自动标记功能
            if auto_tag:
                tagging_result = stock_tagging_service.execute_previous_high_breakout_tagging(
                    window_size=window_size,
                    volume_multiplier=volume_multiplier,
                    stock_codes=stock_codes,
                    limit=limit
                )
                
                # 将标记结果添加到响应数据中
                response_data['tagging_result'] = tagging_result
                if tagging_result['success']:
                    response_message += f"，已自动标记 {tagging_result['data']['success_count']} 只股票"
                else:
                    response_message += f"，标记失败: {tagging_result['message']}"
            
            # 将结果缓存（仅在不标记时缓存）
            if not auto_tag:
                cache.set(cache_key, result['data'], 3600 * 24)
            
            return success_response(response_data, response_message)
        else:
            return error_response(result['message'], 500)
            
    except (ValueError, TypeError) as e:
        return error_response(f'参数格式错误: {str(e)}', 400)
    except Exception as e:
        return error_response(f'股票筛选失败: {str(e)}', 500)


@csrf_exempt
@require_http_methods(["POST"])
def execute_stock_tagging_task(request):
    """
    执行股票标记任务
    
    功能：直接执行前高突破策略的股票标记任务
    参数：
    - window_size: 分析窗口大小（交易日数量），默认60
    - volume_multiplier: 成交量放大倍数，默认1.5
    - stock_codes: 指定股票代码列表，可选（JSON数组格式）
    - limit: 处理结果数量限制，默认50
    
    返回值：
    - 成功时返回标记统计信息
    - 失败时返回错误信息
    
    事件：
    - 任务执行过程中记录详细日志
    """
    try:
        # 解析请求体
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = {}
        
        # 获取参数
        window_size = int(data.get('window_size', 60))
        volume_multiplier = float(data.get('volume_multiplier', 1.5))
        stock_codes = data.get('stock_codes', None)
        limit = int(data.get('limit', 50))
        
        # 验证stock_codes格式
        if stock_codes is not None and not isinstance(stock_codes, list):
            return error_response('stock_codes参数必须是数组格式', 400)
        
        # 执行标记任务
        result = stock_tagging_service.execute_previous_high_breakout_tagging(
            window_size=window_size,
            volume_multiplier=volume_multiplier,
            stock_codes=stock_codes,
            limit=limit
        )
        
        if result['success']:
            return success_response(result['data'], result['message'])
        else:
            return error_response(result['message'], 500)
            
    except json.JSONDecodeError:
        return error_response('请求体JSON格式错误', 400)
    except (ValueError, TypeError) as e:
        return error_response(f'参数格式错误: {str(e)}', 400)
    except Exception as e:
        return error_response(f'执行标记任务失败: {str(e)}', 500)


@csrf_exempt
@require_http_methods(["GET"])
def get_stock_analysis_detail(request, stock_code):
    """
    获取股票分析详情
    
    功能：获取指定股票的详细分析数据
    参数：
    - stock_code: 股票代码（URL路径参数）
    - window_size: 分析窗口大小，默认60
    
    返回值：
    - 成功时返回股票分析详情
    - 失败时返回错误信息
    
    事件：
    - 分析过程中记录日志
    """
    try:
        # 获取查询参数
        window_size = int(request.GET.get('window_size', 60))
        
        # 创建服务实例
        screening_service = StockScreeningService()
        
        # 获取股票分析详情
        result = screening_service.get_stock_analysis_detail(stock_code, window_size)
        
        if result['success']:
            return success_response(result['data'], result['message'])
        else:
            return error_response(result['message'], 404 if 'not found' in result['message'].lower() else 500)
            
    except (ValueError, TypeError) as e:
        return error_response(f'参数格式错误: {str(e)}', 400)
    except Exception as e:
        return error_response(f'获取股票分析详情失败: {str(e)}', 500)

@csrf_exempt
@require_http_methods(["GET"])
def get_industry_ma_breadth(request):
    """
    行业MA20市场宽度指标查询接口
    
    功能：计算并返回指定日期范围内，每个行业中“收盘价高于MA20”的股票占比（市场宽度）。
    参数（Query Parameters）：
    - start_date(str): 开始日期，格式YYYY-MM-DD，默认过去90天
    - end_date(str): 结束日期，格式YYYY-MM-DD，默认当天
    - ma_window(int): 移动平均窗口大小（交易日），默认20
    - sector_codes(str): 行业板块代码列表（逗号分隔），可选；若为空则计算所有板块
    返回值：
    - 成功：返回包含各行业每日宽度数据的JSON（total, data, query_time, 参数回显）
    - 失败：返回错误信息JSON
    事件：
    - 参数解析与校验
    - 计算过程中异常捕获
    - 统一响应封装success_response/error_response
    """
    try:
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        ma_window = int(request.GET.get('ma_window', 20))
        sector_codes_str = request.GET.get('sector_codes', None)
        sector_codes = None
        if sector_codes_str:
            sector_codes = [code.strip() for code in sector_codes_str.split(',') if code.strip()]
        # 计算行业MA市场宽度
        result = industry_ma_breadth_strategy.get_industry_ma_breadth(
            start_date=start_date,
            end_date=end_date,
            ma_window=ma_window,
            sector_codes=sector_codes
        )
        if result is None:
            return error_response('获取行业MA市场宽度数据失败', 500)
        return success_response({
            'total': len(result),
            'data': result,
            'start_date': start_date,
            'end_date': end_date,
            'ma_window': ma_window,
            'sector_codes': sector_codes,
            'query_time': datetime.now().isoformat()
        })
    except ValueError:
        return error_response('参数格式错误：ma_window应为整数', 400)
    except Exception as e:
        return error_response(f'获取行业MA市场宽度数据失败: {str(e)}', 500)

@csrf_exempt
@require_http_methods(["GET"])
def get_industry_scale_breadth(request):
    """
    行业规模宽度指标查询接口
    
    功能：计算并返回每个行业的规模宽度指标 = (行业总市值 / 市场总市值) × (行业公司数量 / 市场总公司数量)
    参数（Query Parameters）：
    - sector_codes(str): 行业板块代码列表（逗号分隔），可选；为空则计算所有板块
    返回值：
    - 成功：返回包含各行业规模宽度数据的JSON（total, data, query_time, 参数回显）
    - 失败：返回错误信息JSON
    事件：
    - 参数解析与校验
    - 计算过程中异常捕获
    - 统一响应封装success_response/error_response
    """
    try:
        sector_codes_str = request.GET.get('sector_codes', None)
        sector_codes = None
        if sector_codes_str:
            sector_codes = [code.strip() for code in sector_codes_str.split(',') if code.strip()]
        # 计算行业规模宽度
        result = industry_scale_breadth_strategy.get_industry_scale_breadth(
            sector_codes=sector_codes
        )
        if result is None:
            return error_response('获取行业规模宽度数据失败', 500)
        return success_response({
            'total': len(result),
            'data': result,
            'sector_codes': sector_codes,
            'query_time': datetime.now().isoformat()
        })
    except Exception as e:
        return error_response(f'获取行业规模宽度数据失败: {str(e)}', 500)

@csrf_exempt
@require_http_methods(["GET"])
def get_industry_actual_output(request):
    """
    行业实际产出规模估算接口
    
    功能：按公式 估算产出 ≈ 前N企业营业总收入之和 / 行业集中度（CRn）
    参数（Query Parameters）：
    - sector_codes(str): 行业板块代码列表（逗号分隔），可选；为空则计算所有板块
    - top_n(int): 前N企业数量，默认3
    - report_date(str): 报告期，格式YYYYMMDD，可选；为空时使用最新业绩快报
    返回值：
    - 成功：返回包含各行业实际产出估算数据的JSON（total, data, query_time, 参数回显）
    - 失败：返回错误信息JSON
    事件：
    - 参数解析与校验
    - 计算过程中异常捕获
    - 统一响应封装success_response/error_response
    """
    try:
        sector_codes_str = request.GET.get('sector_codes', None)
        sector_codes = None
        if sector_codes_str:
            sector_codes = [code.strip() for code in sector_codes_str.split(',') if code.strip()]

        top_n_str = request.GET.get('top_n', '3')
        try:
            top_n = int(top_n_str)
        except ValueError:
            return error_response('参数格式错误：top_n应为整数', 400)
        report_date = request.GET.get('report_date', None)
        if report_date is not None:
            # 简单格式校验：长度为8且全为数字
            if not (len(report_date) == 8 and report_date.isdigit()):
                return error_response('参数格式错误：report_date应为YYYYMMDD', 400)

        result = industry_actual_output_strategy.get_industry_actual_output(
            sector_codes=sector_codes,
            top_n=top_n,
            report_date=report_date
        )
        if result is None:
            return error_response('获取行业实际产出规模估算数据失败', 500)
        return success_response({
            'total': len(result),
            'data': result,
            'sector_codes': sector_codes,
            'top_n': top_n,
            'report_date': report_date,
            'query_time': datetime.now().isoformat()
        })
    except Exception as e:
        return error_response(f'获取行业实际产出规模估算数据失败: {str(e)}', 500)
