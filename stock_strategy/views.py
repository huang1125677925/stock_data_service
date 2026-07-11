from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.core.cache import cache
import json
import pandas as pd
from datetime import datetime, timedelta
import hashlib
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from .services import rps_service, StockScreeningService
from stock_strategy.data_tasks.dc_board_rps import compute_board_rps
from stock_strategy.data_tasks.dc_board_member_rps import compute_dc_board_member_rps
from stock_strategy.data_tasks.major_index_rps import compute_major_index_rps
from stock_strategy.data_tasks.stock_rps import compute_stock_rps
from .models import IndexRPS, StockSelectionRecord
from .industry_turnover_strategy import industry_turnover_strategy
from common.response import success_response, error_response, drf_success_response, drf_error_response
from stock_strategy.data_tasks.stock_tagging_tasks import stock_tagging_service
from .industry_ma_breadth_strategy import industry_ma_breadth_strategy
from .industry_scale_breadth_strategy import industry_scale_breadth_strategy
from .industry_actual_output_strategy import industry_actual_output_strategy
from .auction_selection_strategy import auction_selection_strategy_service
from .limit_board_service import limit_board_data_service
from .value_stock_strategy import value_stock_strategy_service
from .swing_analysis_strategy import swing_analysis_service
from industry_stock_data.models import IndustrySector, IndustrySectorDaily, IndustrySectorFundFlow
from .index_analysis.services import get_macd_xgb_recent_growth_dates
from stock_strategy.serializers import SuccessResponseMacdXgbGrowthDatesSerializer, SuccessResponseActualRiseRatio5DSerializer
from etfapp.serializers import ErrorResponseSerializer


def _get_required_trade_date(request):
    trade_date = request.GET.get('trade_date')
    if not trade_date or len(trade_date) != 8 or not trade_date.isdigit():
        raise ValueError('trade_date 为必填参数，格式为 YYYYMMDD')
    return trade_date


def _get_positive_int_param(request, name, default, max_value=None):
    value = int(request.GET.get(name, default))
    if value <= 0:
        raise ValueError(f'{name} 必须大于 0')
    if max_value is not None:
        value = min(value, max_value)
    return value


def _get_required_date_range(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if not start_date or len(start_date) != 8 or not start_date.isdigit():
        raise ValueError('start_date 为必填参数，格式为 YYYYMMDD')
    if not end_date or len(end_date) != 8 or not end_date.isdigit():
        raise ValueError('end_date 为必填参数，格式为 YYYYMMDD')
    return start_date, end_date


def _get_float_param(request, name, default):
    raw_value = request.GET.get(name, default)
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        raise ValueError(f'{name} 参数格式错误，应为数字')


@csrf_exempt
@require_http_methods(["GET"])
def get_value_stock_candidates(request):
    """
    价值股筛选接口
    功能：从 Tushare 最新财报数据筛选营收正增长、净利润靠前的股票。

    Query Parameters:
        report_period: 财报期，格式 YYYYMMDD；不传时自动向前查找最新可用季度
        min_revenue_growth: 最低营收同比增长率，默认 0
        min_net_profit: 最低净利润，单位元，默认 0
        limit: 返回数量，默认 50，最大 2000
        lookback_periods: 自动查找最新财报时最多回看季度数，默认 8，最大 16
    """
    try:
        report_period = request.GET.get('report_period')
        if report_period and (len(report_period) != 8 or not report_period.isdigit()):
            return error_response('report_period 参数格式错误，应为 YYYYMMDD', 400)

        min_revenue_growth = _get_float_param(request, 'min_revenue_growth', 0)
        min_net_profit = _get_float_param(request, 'min_net_profit', 0)
        limit = _get_positive_int_param(request, 'limit', 50, max_value=2000)
        lookback_periods = _get_positive_int_param(request, 'lookback_periods', 8, max_value=16)

        result = value_stock_strategy_service.screen_value_stocks(
            report_period=report_period,
            min_revenue_growth=min_revenue_growth,
            min_net_profit=min_net_profit,
            limit=limit,
            lookback_periods=lookback_periods,
        )
        return success_response(result)
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(f'价值股筛选失败: {str(e)}', 500)


@csrf_exempt
@require_http_methods(["GET"])
def get_value_stock_revenue_history(request):
    """
    高营收增长股票营收历史接口
    功能：根据 ts_codes 获取过去若干财报期的营业收入和净利润数据。

    Query Parameters:
        ts_codes: Tushare 股票代码，多个用逗号分隔，如 600519.SH,000333.SZ
        periods: 财报期数量，默认 8，最大 16
    """
    try:
        ts_codes_param = request.GET.get('ts_codes')
        if not ts_codes_param:
            return error_response('ts_codes 为必填参数，多个代码用逗号分隔', 400)

        ts_codes = [code.strip() for code in ts_codes_param.split(',') if code.strip()]
        invalid_codes = [
            code for code in ts_codes
            if len(code) != 9 or code[6] != '.' or code[-2:].upper() not in {'SH', 'SZ', 'BJ'}
        ]
        if invalid_codes:
            return error_response(f'ts_codes 参数包含无效代码: {",".join(invalid_codes)}', 400)

        periods = _get_positive_int_param(request, 'periods', 8, max_value=16)
        result = value_stock_strategy_service.get_revenue_history(
            ts_codes=ts_codes,
            periods=periods,
        )
        return success_response(result)
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(f'获取营收历史失败: {str(e)}', 500)


@csrf_exempt
@require_http_methods(["GET"])
def get_swing_analysis(request):
    """
    波段分析接口
    功能：从 Tushare 获取股票或 ETF 行情，返回波段交易所需的趋势、位置、波动、量能和支撑压力数据。

    Query Parameters:
        target_type: 标的类型，stock 或 etf
        code: 股票代码或 ETF ts_code。股票可传 600519 或 600519.SH；ETF 传 510300.SH
        start_date: 开始日期，YYYYMMDD 或 YYYY-MM-DD，默认最近约 240 天
        end_date: 结束日期，YYYYMMDD 或 YYYY-MM-DD，默认今天
        adjust: 股票复权类型，可选 qfq/hfq；ETF 忽略该参数
    """
    try:
        result = swing_analysis_service.analyze(
            target_type=request.GET.get('target_type', 'stock'),
            code=request.GET.get('code') or request.GET.get('ts_code') or request.GET.get('stock_code'),
            start_date=request.GET.get('start_date'),
            end_date=request.GET.get('end_date'),
            adjust=request.GET.get('adjust', ''),
        )
        return success_response(result)
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(f'波段分析失败: {str(e)}', 500)


@csrf_exempt
@require_http_methods(["GET"])
def get_swing_channel_candidates(request):
    """
    上升通道靠近下轨波段选股接口
    功能：筛选股票或 ETF 中通道线朝上，且当前价格接近下通道线的波段候选标的。

    Query Parameters:
        target_type: 标的类型，stock 或 etf，默认 etf
        codes: 可选，逗号分隔指定扫描代码；为空时使用 Tushare 候选池
        start_date/end_date: 行情区间，YYYYMMDD 或 YYYY-MM-DD
        channel_window: 通道计算窗口，默认 60，范围 20-180
        max_distance_pct: 当前价距离下轨最大百分比，默认 3
        max_channel_position_pct: 当前价在通道内最大位置百分比，默认 35
        min_slope_pct: 下轨最小日斜率百分比，默认 0
        universe_limit: 候选池扫描数量，默认 100，最大 2000
        limit: 返回数量，默认 50，最大 500
        adjust: 股票复权类型 qfq/hfq；ETF 忽略
    """
    try:
        result = swing_analysis_service.screen_up_channel_near_lower(
            target_type=request.GET.get('target_type', 'etf'),
            codes=request.GET.get('codes'),
            start_date=request.GET.get('start_date'),
            end_date=request.GET.get('end_date'),
            adjust=request.GET.get('adjust', ''),
            channel_window=_get_positive_int_param(request, 'channel_window', 60, max_value=180),
            max_distance_pct=_get_float_param(request, 'max_distance_pct', 3.0),
            max_channel_position_pct=_get_float_param(request, 'max_channel_position_pct', 35.0),
            min_slope_pct=_get_float_param(request, 'min_slope_pct', 0.0),
            universe_limit=_get_positive_int_param(request, 'universe_limit', 100, max_value=2000),
            limit=_get_positive_int_param(request, 'limit', 50, max_value=500),
        )
        return success_response(result)
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(f'上升通道波段筛选失败: {str(e)}', 500)

@csrf_exempt
@require_http_methods(["GET"])
def get_index_rps(request):
    """
    获取指数/板块RPS强度排名数据（基于 Tushare 东方财富板块接口）
    
    Query Parameters:
        periods (str): 回看交易日周期，多个周期用逗号分隔，如 "5,20,60"
        idx_type (str): 板块类型：概念板块、行业板块、地域板块（默认：概念板块）
        level (str): 东财行业层级，仅 idx_type=行业板块 时生效
        trade_date (str): 截止交易日（YYYYMMDD），为空时自动使用最新交易日
        token (str): Tushare Token（覆盖环境变量）

    默认附加字段:
        pct_change (float): 截止交易日当天涨跌幅
        RPS_today (float): 按当天涨跌幅计算的横向 RPS
    
    Returns:
        JSON响应
    """
    try:
        # 获取查询参数
        periods_str = request.GET.get('periods', '5,20,60')
        idx_type = request.GET.get('idx_type', '概念板块')
        level = request.GET.get('level')
        trade_date = request.GET.get('trade_date')
        token = request.GET.get('token')
        allowed_levels = {'东财一级行业', '东财二级行业', '东财三级行业'}
        effective_level = level if idx_type == '行业板块' else None
        if effective_level and effective_level not in allowed_levels:
            return error_response('level参数错误，仅支持：东财一级行业、东财二级行业、东财三级行业', 400)
        
        # 解析周期参数
        try:
            periods = [int(p.strip()) for p in periods_str.split(',') if p.strip()]
            if not periods:
                periods = [5, 20, 60]  # 默认周期
        except ValueError:
            return error_response('周期参数格式错误，应为逗号分隔的整数', 400)
        
        # 使用 scheduled_tasks 的 Tushare 服务实时获取数据并计算RPS，
        # 默认附带当天涨跌幅及其 RPS。
        df, errors = compute_board_rps(
            periods=periods,
            idx_type=idx_type,
            trade_date=trade_date,
            level=effective_level,
            token=token,
        )
        
        if df is None:
            return error_response(f'获取RPS数据失败: {", ".join(errors)}', 500)
        
        # 转换DataFrame为JSON可序列化格式
        result = df.fillna('').to_dict('records')
        
        return success_response({
            'total': len(result),
            'data': result,
            'periods': periods,
            'idx_type': idx_type,
            'level': effective_level,
            'trade_date': trade_date,
            'errors': errors,
            'query_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        return error_response(f'获取指数RPS强度排名失败: {str(e)}', 500)


@csrf_exempt
@require_http_methods(["GET"])
def get_stock_rps(request):
    """
    获取股票多周期 RPS 强度排名数据。

    Query Parameters:
        periods (str): 回看交易日周期，多个周期用逗号分隔，如 "5,20,60"。
        trade_date (str): 截止交易日（YYYYMMDD），为空时自动使用最近可用交易日。
        exchange (str): 交易所筛选，可选，如 SSE、SZSE、BSE。
        market (str): 市场类型筛选，可选，如 主板、创业板、科创板、北交所。
        industry_mapping (str): 行业映射方式，可选，默认 default。
            - default: 使用 stock_basic 的 industry 字段（默认，无对应东财板块代码）
            - dc_concept: 东财概念板块
            - dc_region: 东财地域板块
            - dc_l1: 东财一级行业板块
            - dc_l2: 东财二级行业板块
            - dc_l3: 东财三级行业板块
        token (str): Tushare Token（覆盖环境变量）。

    每条股票记录包含 industry（行业名）与 industry_code（东财板块代码，仅 dc_* 映射有值）；
    dc_* 映射额外返回 industries、industry_codes 多对多列表。

    Returns:
        JSON响应，包含股票列表、周期参数、目标日期、错误信息和查询时间。

    Raises:
        无。异常会统一包装为 error_response。
    """
    try:
        periods_str = request.GET.get('periods', '5,20,60')
        trade_date = request.GET.get('trade_date')
        exchange = request.GET.get('exchange')
        market = request.GET.get('market')
        industry_mapping = request.GET.get('industry_mapping', 'default')
        token = request.GET.get('token')

        try:
            periods = [int(p.strip()) for p in periods_str.split(',') if p.strip()]
            if not periods:
                periods = [5, 20, 60]
        except ValueError:
            return error_response('周期参数格式错误，应为逗号分隔的整数', 400)

        df, errors = compute_stock_rps(
            periods=periods,
            trade_date=trade_date,
            token=token,
            exchange=exchange,
            market=market,
            industry_mapping=industry_mapping,
        )
        if df is None:
            error_message = ', '.join(errors) if errors else '未获取到股票 RPS 数据'
            return error_response(f'获取股票RPS排名失败: {error_message}', 500)

        result = df.fillna('').to_dict('records')
        return success_response({
            'total': len(result),
            'data': result,
            'periods': periods,
            'trade_date': df.attrs.get('trade_date', trade_date),
            'exchange': exchange,
            'market': market,
            'industry_mapping': industry_mapping,
            'errors': errors,
            'query_time': datetime.now().isoformat(),
        })

    except Exception as e:
        return error_response(f'获取股票RPS排名失败: {str(e)}', 500)


@csrf_exempt
@require_http_methods(["GET"])
def get_major_index_rps(request):
    """
    获取国内+国际大盘指数的多周期 RPS 强度排名数据。

    Query Parameters:
        periods (str): 回看交易日周期，多个周期用逗号分隔，如 "5,20,60,120,250"。
        trade_date (str): 目标截止日期（YYYYMMDD），为空时默认使用当前系统日期。
        token (str): Tushare Token（覆盖环境变量）。

    Returns:
        JSON响应，包含指数列表、周期参数、目标日期、错误信息和查询时间。

    Raises:
        无。异常会统一包装为 error_response。
    """
    try:
        periods_str = request.GET.get('periods', '5,20,60,120,250')
        trade_date = request.GET.get('trade_date')
        token = request.GET.get('token')

        try:
            periods = [int(p.strip()) for p in periods_str.split(',') if p.strip()]
            if not periods:
                periods = [5, 20, 60, 120, 250]
        except ValueError:
            return error_response('周期参数格式错误，应为逗号分隔的整数', 400)

        df, errors = compute_major_index_rps(
            periods=periods,
            trade_date=trade_date,
            token=token,
        )
        if df is None:
            error_message = ', '.join(errors) if errors else '未获取到大盘指数 RPS 数据'
            return error_response(f'获取国内国际大盘指数RPS排名失败: {error_message}', 500)

        result = df.fillna('').to_dict('records')
        return success_response(
            {
                'total': len(result),
                'data': result,
                'periods': periods,
                'trade_date': df.attrs.get('trade_date', trade_date),
                'errors': errors,
                'query_time': datetime.now().isoformat(),
            }
        )

    except Exception as e:
        return error_response(f'获取国内国际大盘指数RPS排名失败: {str(e)}', 500)


@csrf_exempt
@require_http_methods(["GET"])
def get_dc_board_member_rps(request):
    """
    获取指定东财板块成分股的 RPS 强度排名数据。

    Query Parameters:
        periods (str): 回看交易日周期，多个周期用逗号分隔，如 "5,20,60"。
        ts_code (str): 东财板块代码，默认 BK1462.DC。
        trade_date (str): 截止交易日（YYYYMMDD），为空时自动使用最新交易日。
        token (str): Tushare Token（覆盖环境变量）。

    Returns:
        JSON响应，包含板块信息、成分股数量、成分股 RPS 排名结果及告警信息。

    Raises:
        无。异常会统一包装为 error_response。
    """
    try:
        periods_str = request.GET.get('periods', '5,20,60')
        board_ts_code = request.GET.get('ts_code', 'BK1462.DC')
        trade_date = request.GET.get('trade_date')
        token = request.GET.get('token')

        try:
            periods = [int(p.strip()) for p in periods_str.split(',') if p.strip()]
            if not periods:
                periods = [5, 20, 60]
        except ValueError:
            return error_response('周期参数格式错误，应为逗号分隔的整数', 400)

        df, meta, errors = compute_dc_board_member_rps(
            periods=periods,
            board_ts_code=board_ts_code,
            trade_date=trade_date,
            token=token,
        )
        if df is None:
            error_message = ', '.join(errors) if errors else '未获取到板块成分股 RPS 数据'
            return error_response(f'获取板块成分股RPS排名失败: {error_message}', 500)

        result = df.fillna('').to_dict('records')
        return success_response({
            'total': len(result),
            'data': result,
            'periods': periods,
            'board_ts_code': meta.get('board_ts_code'),
            'board_name': meta.get('board_name'),
            'trade_date': meta.get('trade_date'),
            'member_count': meta.get('member_count'),
            'errors': errors,
            'query_time': datetime.now().isoformat(),
        })

    except Exception as e:
        return error_response(f'获取板块成分股RPS排名失败: {str(e)}', 500)


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
    板块成交额百分位查询接口

    功能：
    - 基于东方财富板块日频行情 `dc_daily`，返回目标板块的成交额、占总额百分比与成交额百分位。

    参数（Query Parameters）：
    - start_date(str): 开始日期，格式 YYYY-MM-DD，默认过去 90 天
    - end_date(str): 结束日期，格式 YYYY-MM-DD，默认当天
    - idx_type(str): 东方财富板块类型，支持：行业板块、概念板块、地域板块；默认行业板块
    - level(str): 东财行业层级，仅 idx_type=行业板块 时生效，支持：东财一级行业、东财二级行业、东财三级行业

    返回值：
    - 成功：返回包含板块成交额、占总额比例、成交额百分位的 JSON 数据
    - 失败：返回错误信息 JSON

    事件：
    - 参数解析与校验
    - 调用成交额百分位策略
    - 统一响应封装 success_response/error_response
    """
    try:
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        idx_type = request.GET.get('idx_type', '行业板块')
        level = request.GET.get('level')
        allowed_levels = {'东财一级行业', '东财二级行业', '东财三级行业'}
        effective_level = level if idx_type == '行业板块' else None
        if effective_level and effective_level not in allowed_levels:
            return error_response('level参数错误，仅支持：东财一级行业、东财二级行业、东财三级行业', 400)

        result = industry_turnover_strategy.get_industry_turnover_percentile(
            start_date=start_date,
            end_date=end_date,
            idx_type=idx_type,
            level=effective_level,
        )
        if result is None:
            return error_response('获取板块成交额百分位数据失败', 500)

        actual_end_date = result[-1]['date'] if result else None
        return success_response({
            'total': len(result),
            'data': result,
            'start_date': start_date,
            'end_date': end_date,
            'actual_end_date': actual_end_date,
            'idx_type': idx_type,
            'level': effective_level,
            'query_time': datetime.now().isoformat()
        })
    except ValueError as e:
        return error_response(f'参数错误: {str(e)}', 400)
    except Exception as e:
        return error_response(f'获取板块成交额百分位数据失败: {str(e)}', 500)

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
    - idx_type(str): 东方财富板块类型，支持：行业板块、概念板块、地域板块；默认行业板块
    - level(str): 东财行业层级，仅 idx_type=行业板块 时生效，支持：东财一级行业、东财二级行业、东财三级行业
    - sector_code(str): 东财板块代码，例如 BK1462.DC；传入时进入单行业模式，
      仅计算该板块并按成分股逐只拉取因子数据（请求次数与时间跨度无关），此时忽略 idx_type/level
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
        idx_type = request.GET.get('idx_type', '行业板块')
        level = request.GET.get('level')
        sector_code = (request.GET.get('sector_code') or '').strip() or None
        allowed_levels = {'东财一级行业', '东财二级行业', '东财三级行业'}
        # 单行业模式下由板块代码唯一确定行业，忽略 idx_type/level
        effective_level = None if sector_code else (level if idx_type == '行业板块' else None)
        if not sector_code and effective_level and effective_level not in allowed_levels:
            return error_response('level参数错误，仅支持：东财一级行业、东财二级行业、东财三级行业', 400)
        # 计算行业MA市场宽度
        result = industry_ma_breadth_strategy.get_industry_ma_breadth(
            start_date=start_date,
            end_date=end_date,
            ma_window=ma_window,
            idx_type=idx_type,
            level=effective_level,
            sector_code=sector_code,
        )
        if result is None:
            return error_response('获取行业MA市场宽度数据失败', 500)
        return success_response({
            'total': len(result),
            'data': result,
            'start_date': start_date,
            'end_date': end_date,
            'ma_window': ma_window,
            'idx_type': idx_type,
            'level': effective_level,
            'sector_code': sector_code,
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
        resolved_sector_codes = sector_codes or [
            item.get('sector_code')
            for item in result
            if item.get('sector_code')
        ]
        return success_response({
            'total': len(result),
            'data': result,
            'sector_codes': resolved_sector_codes,
            'top_n': top_n,
            'report_date': report_date,
            'query_time': datetime.now().isoformat()
        })
    except Exception as e:
        return error_response(f'获取行业实际产出规模估算数据失败: {str(e)}', 500)


@csrf_exempt
@require_http_methods(["GET"])
def get_industry_fund_flow_correlation(request):
    """
    功能：获取指定行业在日期范围内的涨跌幅/换手率/振幅与净流入数据的二维坐标点列表，并按净流入排序
    参数：
    - sector_code (str): 行业板块代码，必填
    - start_date (str): 开始日期，格式YYYY-MM-DD，必填
    - end_date (str): 结束日期，格式YYYY-MM-DD，必填
    - x_axis (str): 选择x轴字段，支持 'change_percent'、'turnover_rate'、'amplitude'，默认 'change_percent'
    - y_axis (str): 选择y轴净流入类型，支持 'main'、'super_large'、'large'、'medium'、'small'、'all'，默认 'main'
      对应金额字段：main_net_inflow_amount、super_large_net_inflow_amount、large_net_inflow_amount、medium_net_inflow_amount、small_net_inflow_amount；'all'为四类金额之和
    - sort_order (str): 排序方向，'desc' 或 'asc'，默认 'desc'（按y值排序）
    返回值：
    - 成功：返回包含坐标点列表、筛选信息和统计信息的标准响应
    - 失败：返回错误信息
    事件：
    - 参数验证失败时返回400错误
    - 查询过程中异常记录日志并返回500错误
    """
    try:
        # 获取参数
        sector_code = request.GET.get('sector_code')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        x_axis = request.GET.get('x_axis', 'change_percent')
        y_axis = request.GET.get('y_axis', 'main')
        sort_order = request.GET.get('sort_order', 'desc').lower()

        # 参数校验
        if not sector_code:
            return error_response('缺少参数: sector_code', 400)
        if not start_date or not end_date:
            return error_response('缺少参数: start_date 或 end_date', 400)

        x_axis_map = {
            'change_percent': 'change_percent',
            'turnover_rate': 'turnover_rate',
            'amplitude': 'amplitude'
        }
        if x_axis not in x_axis_map:
            return error_response('x_axis 参数不合法，应为 change_percent/turnover_rate/amplitude', 400)

        y_axis_options = {
            'main': 'main_net_inflow_amount',
            'super_large': 'super_large_net_inflow_amount',
            'large': 'large_net_inflow_amount',
            'medium': 'medium_net_inflow_amount',
            'small': 'small_net_inflow_amount',
            'all': 'all'
        }
        if y_axis not in y_axis_options:
            return error_response('y_axis 参数不合法，应为 main/super_large/large/medium/small/all', 400)

        # 行业板块校验
        try:
            sector = IndustrySector.objects.get(code=sector_code)
        except IndustrySector.DoesNotExist:
            return error_response(f'行业板块不存在: {sector_code}', 404)

        # 查询日频与资金流数据（数据库）
        daily_qs = IndustrySectorDaily.objects.filter(
            sector=sector, date__gte=start_date, date__lte=end_date
        ).values('date', x_axis_map[x_axis])

        fund_flow_qs = IndustrySectorFundFlow.objects.filter(
            sector=sector, date__gte=start_date, date__lte=end_date
        ).values('date', 'main_net_inflow_amount', 'super_large_net_inflow_amount', 'large_net_inflow_amount', 'medium_net_inflow_amount', 'small_net_inflow_amount')

        # 构建日期映射
        daily_map = {item['date']: item[x_axis_map[x_axis]] for item in daily_qs}

        points = []
        for item in fund_flow_qs:
            d = item['date']
            if d in daily_map:
                x_val = daily_map[d]
                # 计算净流入Y值
                if y_axis == 'all':
                    y_val = (item.get('super_large_net_inflow_amount') or 0) + \
                            (item.get('large_net_inflow_amount') or 0) + \
                            (item.get('medium_net_inflow_amount') or 0) + \
                            (item.get('small_net_inflow_amount') or 0)
                    y_label = 'all_net_inflow_amount'
                else:
                    y_field = y_axis_options[y_axis]
                    y_val = item.get(y_field) or 0
                    y_label = y_field

                # 转为可序列化数值
                x_value = float(x_val) if x_val is not None else None
                y_value = float(y_val) if y_val is not None else 0.0

                points.append({
                    'date': d.strftime('%Y-%m-%d'),
                    'x': x_value,
                    'y': y_value
                })

        # 排序（按y值）
        reverse = sort_order != 'asc'
        points.sort(key=lambda p: p['y'], reverse=reverse)

        response_data = {
            'sector_code': sector.code,
            'sector_name': sector.name,
            'filters': {
                'start_date': start_date,
                'end_date': end_date,
                'x_axis': x_axis,
                'y_axis': y_axis,
                'sort_order': sort_order
            },
            'total': len(points),
            'points': points,
            'x_label': x_axis,
            'y_label': 'all_net_inflow_amount' if y_axis == 'all' else y_axis_options[y_axis]
        }

        return success_response(response_data, '获取行业资金流相关坐标点成功')

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'获取行业资金流相关坐标点失败: {str(e)}')
        return error_response(f'获取行业资金流相关坐标点失败: {str(e)}', 500)


@csrf_exempt
@require_http_methods(["GET"])
def get_auction_selection_result(request):
    """
    获取 9 点 25 竞价选股策略结果

    功能：
    - 基于前一交易日涨停池与目标交易日集合竞价数据，筛选竞价候选股并输出评分拆解。

    参数：
    - trade_date: 目标交易日，格式 YYYYMMDD，默认最近交易日
    - top_n: 返回的首选池数量，默认 3
    - token: 可选，覆盖环境变量中的 Tushare Token
    - auction_max_retries: 集合竞价数据重试次数，默认 12
    - auction_base_wait: 集合竞价数据基础等待秒数，默认 5
    - prev_limit_max_retries: 昨日涨停数据重试次数，默认 3
    - prev_limit_base_wait: 昨日涨停数据基础等待秒数，默认 3

    返回值：
    - 成功时返回市场情绪、候选池、TOP池、评分拆解和查询参数
    - 失败时返回统一错误响应

    事件：
    - 参数格式错误时返回 400 业务码
    - 数据获取或策略执行失败时返回 500 业务码
    """
    try:
        trade_date = request.GET.get('trade_date')
        top_n = int(request.GET.get('top_n', 3))
        token = request.GET.get('token')
        auction_max_retries = int(request.GET.get('auction_max_retries', 12))
        auction_base_wait = int(request.GET.get('auction_base_wait', 5))
        prev_limit_max_retries = int(request.GET.get('prev_limit_max_retries', 3))
        prev_limit_base_wait = int(request.GET.get('prev_limit_base_wait', 3))

        result = auction_selection_strategy_service.get_strategy_result(
            trade_date=trade_date,
            top_n=top_n,
            token=token,
            auction_max_retries=auction_max_retries,
            auction_base_wait=auction_base_wait,
            prev_limit_max_retries=prev_limit_max_retries,
            prev_limit_base_wait=prev_limit_base_wait,
        )
        return success_response(result, '获取 9 点 25 竞价选股结果成功')
    except ValueError as e:
        return error_response(f'参数格式错误: {str(e)}', 400)
    except RuntimeError as e:
        return error_response(str(e), 500)
    except Exception as e:
        return error_response(f'获取 9 点 25 竞价选股结果失败: {str(e)}', 500)


@csrf_exempt
@require_http_methods(["GET"])
def get_limit_board_trend_analysis(request):
    """
    获取涨停打板趋势分析。

    按时间区间分析情绪变化、题材变化、涨停股生命周期变化。
    """
    try:
        start_date, end_date = _get_required_date_range(request)
        token = request.GET.get('token')
        top_n = _get_positive_int_param(request, 'top_n', 20, 100)
        result = limit_board_data_service.get_trend_analysis(
            start_date=start_date,
            end_date=end_date,
            token=token,
            top_n=top_n,
        )
        return success_response(result, '获取涨停打板趋势分析成功')
    except ValueError as e:
        return error_response(f'参数格式错误: {str(e)}', 400)
    except RuntimeError as e:
        return error_response(str(e), 500)
    except Exception as e:
        return error_response(f'获取涨停打板趋势分析失败: {str(e)}', 500)


@csrf_exempt
@require_http_methods(["GET"])
def get_limit_board_industry_trend_strength(request):
    """
    涨停趋势强度行业分析接口

    功能：
    - 以 Tushare `limit_list_ths(limit_type=涨停池)` 区间数据为基础，按 `industry_mapping` 指定的
      映射方式获取每只涨停股所属行业，按交易日为 key 返回整体、行业、个股三个维度的涨停数据。
    - 剔除 ST/退市类股票，以及无法归类到具体行业（未知行业）的个股，不计入统计范围。

    参数：
    - start_date (str): 开始日期，必填，格式 `YYYYMMDD`。
    - end_date (str): 结束日期，必填，格式 `YYYYMMDD`。
    - token (str，可选): Tushare Token，传入后覆盖环境变量。
    - industry_mapping (str，可选): 行业映射方式，默认 `default`。可选值：
      `default`（limit_list_d 行业字段，按日动态）、`dc_concept`（东财概念板块）、
      `dc_region`（东财地域板块）、`dc_l1`/`dc_l2`/`dc_l3`（东财一/二/三级行业板块），
      后 5 种基于本地东方财富板块成分快照。

    返回值：
    - 成功：以交易日为 key 返回三个维度数据——整体（当日涨停总数与行业数量）、
      行业（当日各行业涨停数量，及 T字板/一字板/换手板 涨停状态统计）、
      个股（各行业内涨停股列表，含 `limit_list_ths` 全部字段）。
      统计范围剔除 ST/退市股与未知行业股。
    - 失败：返回统一错误响应。

    异常：
    - ValueError: 参数格式不正确时转为 400 响应。
    - RuntimeError: 底层数据源调用失败时转为 500 响应。

    事件：
    - 解析并校验日期区间参数。
    - 调用涨停打板组合服务执行行业维度趋势强度聚合。
    - 使用 `success_response` / `error_response` 统一封装响应。
    """
    try:
        start_date, end_date = _get_required_date_range(request)
        token = request.GET.get('token')
        industry_mapping = request.GET.get('industry_mapping')
        result = limit_board_data_service.get_industry_trend_strength(
            start_date=start_date,
            end_date=end_date,
            token=token,
            industry_mapping=industry_mapping,
        )
        return success_response(result, '获取行业涨停趋势强度分析成功')
    except ValueError as e:
        return error_response(f'参数格式错误: {str(e)}', 400)
    except RuntimeError as e:
        return error_response(str(e), 500)
    except Exception as e:
        return error_response(f'获取行业涨停趋势强度分析失败: {str(e)}', 500)

class IndexMacdXgbGrowthDatesView(APIView):
    """
    指数MACD XGBoost最近上涨日预测视图
    功能：
    - 加载已保存的MACD XGBoost模型并进行预测。
    - 返回最近指定天数内预测为“上涨”的交易日期列表。
    参数：
    - stock_code(str, 路径参数): 指数TS代码，如 '000001.SH'
    - days(int, 查询参数，可选): 最近交易日数量，默认30
    - token(str, 查询参数，可选): Tushare Token（覆盖环境变量）
    返回值：
    - 统一响应：code、message、timestamp、data
      其中 data = { ts_code, list: [YYYYMMDD...], count, params }
    事件：
    - 解析参数 → 服务预测 → 返回统一响应
    """

    @extend_schema(
        summary="指数MACD XGBoost最近上涨日预测",
        description=(
            "获取指定指数最近30天预测上涨的交易日期列表（基于已保存的MACD XGBoost模型）。\n"
            "参数（Path）：stock_code（必填，指数TS代码），例如 000001.SH。\n"
            "参数（Query）：days（可选，默认30），token（可选，覆盖环境变量）。\n"
            "统一响应结构（success_response），data 包含 ts_code、list、count、params。"
        ),
        tags=["index-analysis"],
        responses={
            200: SuccessResponseMacdXgbGrowthDatesSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request, stock_code: str):
        try:
            days = int(request.GET.get('days', 30))
            token = request.GET.get('token')

            result = get_macd_xgb_recent_growth_dates(ts_code=stock_code, days=days, token=token)
            if not result.get('success'):
                return drf_error_response(result.get('message', '获取预测结果失败'), 500)

            return drf_success_response(result.get('data'), result.get('message', 'success'))
        except ValueError:
            return drf_error_response('days参数格式错误，应为整数', 400)
        except Exception as e:
            return drf_error_response(f'获取预测上涨日期失败: {str(e)}', 500)


class ActualRiseRatio5DView(APIView):
    """
    组件：5日实际上涨比例查询视图（ActualRiseRatio5DView）

    功能：
    - 基于 StockSelectionRecord 模型，按代码与可选过滤条件查询记录，并返回 5 日实际上涨比例等信息。

    参数：
    - stock_code (str, 路径参数): 股票或指数代码，例如 `000001` 或 `000001.SH`。
    - start_date (str, 查询参数，可选): 开始日期，格式 `YYYY-MM-DD`。
    - end_date (str, 查询参数，可选): 结束日期，格式 `YYYY-MM-DD`。
    - prediction_type (str, 查询参数，可选): 过滤预测类型，如 `MACD_XGBoost`。

    返回值：
    - 统一响应（drf_success_response / drf_error_response）：
      data = [
        {
          'market': str,
          'code': str,
          'name': str,
          'trade_date': 'YYYY-MM-DD',
          'predict_rise_prob': float,
          'confidence': float,
          'actual_rise_ratio_5d': float | null,
          'prediction_type': str,
          'created_at': 'YYYY-MM-DDTHH:mm:ss',
        }, ...
      ]

    事件：
    - 解析查询参数 → 构建并执行数据库查询 → 整理返回数据结构。
    """

    @extend_schema(
        summary="查询5日实际上涨比例",
        description=(
            "按代码查询选股记录中的5日实际上涨比例，支持日期区间与预测类型过滤。\n"
            "参数（Path）：stock_code。\n"
            "参数（Query）：start_date, end_date, prediction_type。\n"
            "注意：end_date 将被强制设为当前日期减3个交易日（不计周末），忽略传入的 end_date，以保证数据截止为最近交易日。\n"
            "统一响应结构（success_response 样式，DRF封装为 drf_success_response）。"
        ),
        tags=["individual-analysis"],
        responses={
            200: SuccessResponseActualRiseRatio5DSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            start_date = request.GET.get('start_date')
            # 强制将 end_date 设置为当前日期减3个交易日（不计周末），忽略传入参数
            # 组件说明：
            # 功能：规范查询截止日为最近的交易日，避免包含非交易日导致查询结果偏差。
            # 参数：忽略 request.GET['end_date']。
            # 返回值：不变，仍为统一 success_response/data 列表结构。
            # 事件：无特别事件，仅内部日期处理。
            end_date = request.GET.get('end_date')
            # days_to_subtract = 4
            # current_date = datetime.now().date()
            # trading_days_count = 0
            # temp_date = current_date
            # while trading_days_count < days_to_subtract:
            #     temp_date = temp_date - timedelta(days=1)
            #     # 周一=0 ... 周五=5（周六=5? 实际weekday: 周一=0, 周日=6）
            #     if temp_date.weekday() < 5:  # 仅计工作日为交易日
            #         trading_days_count += 1
            # end_date = temp_date.strftime('%Y%m%d')
            prediction_type = request.GET.get('prediction_type')

            qs = StockSelectionRecord.objects.filter()
            if prediction_type:
                qs = qs.filter(prediction_type=prediction_type)
            if start_date:
                qs = qs.filter(trade_date__gte=start_date)
            if end_date:
                qs = qs.filter(trade_date__lte=end_date)
            qs = qs.order_by('trade_date')

            if not qs.exists():
                return drf_error_response('无选股记录', 404)

            data = []
            for r in qs:
                data.append(r.to_dict())

            return drf_success_response(data, '查询5日实际上涨比例成功')
        except Exception as e:
            return drf_error_response(f'查询5日实际上涨比例失败: {str(e)}', 500)
