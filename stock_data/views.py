from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging
import pandas as pd
import akshare as ak
from datetime import datetime
from .services import stock_service, industry_sector_service
from common.response import success_response, error_response
from common.validators import validate_pagination_params, validate_stock_symbol

# 行业板块相关验证函数
def validate_sector_code(code):
    """验证行业板块代码"""
    if not code or not isinstance(code, str):
        return False
    return True

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["GET"])
def get_realtime_stocks(request):
    """
    获取上证A股实时行情数据
    
    Query Parameters:
        limit (int): 返回股票数量限制，默认返回全部
        offset (int): 偏移量，默认0
    
    Returns:
        {
            "code": 200,
            "message": "success",
            "timestamp": "2024-01-01T12:00:00",
            "data": {
                "total": 500,
                "stocks": [...],
                "query_time": "2024-01-01T12:00:00"
            }
        }
    """
    try:
        # 获取查询参数
        limit = int(request.GET.get('limit')) if request.GET.get('limit') else None
        offset = int(request.GET.get('offset', 0))
        
        # 验证分页参数
        limit, offset = validate_pagination_params(limit, offset)
        
        # 获取实时数据
        stocks = stock_service.get_realtime_stocks()
        if stocks is None:
            return error_response('获取上证A股数据失败', 500)
        
        # 应用分页
        total = len(stocks)
        if limit:
            stocks = stocks[offset:offset + limit]
        else:
            stocks = stocks[offset:]
        
        return success_response({
            'total': total,
            'stocks': stocks,
            'query_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取上证A股实时行情失败: {str(e)}")
        return error_response(f'获取上证A股实时行情失败: {str(e)}', 500)

@csrf_exempt
@require_http_methods(["GET"])
def filter_stocks(request):
    """
    根据条件筛选上证A股股票
    
    Query Parameters:
        min_price (float): 最低价格，默认0
        max_price (float): 最高价格，默认1000
        min_turnover_rate (float): 最低换手率(%)
        max_turnover_rate (float): 最高换手率(%)
        min_market_cap (float): 最低流通市值(亿元)
        max_market_cap (float): 最高流通市值(亿元)
        sort_by (str): 排序字段
        ascending (bool): 是否升序，默认true
    
    Returns:
        {
            "code": 200,
            "message": "success",
            "data": {
                "total": 50,
                "stocks": [...],
                "filters": {...}
            }
        }
    """
    try:
        # 获取筛选参数
        filters = {
            'min_price': float(request.GET.get('min_price', 0)),
            'max_price': float(request.GET.get('max_price', 1000)),
            'min_turnover_rate': float(request.GET.get('min_turnover_rate', 0)),
            'max_turnover_rate': float(request.GET.get('max_turnover_rate', 100)),
            'min_market_cap': float(request.GET.get('min_market_cap', 0)),
            'max_market_cap': float(request.GET.get('max_market_cap', 100000)),
            'sort_by': request.GET.get('sort_by', 'turnover_rate'),
            'ascending': request.GET.get('ascending', 'true').lower() != 'false'
        }
        
        # 筛选股票
        filtered_stocks = stock_service.filter_stocks(**filters)
        if filtered_stocks is None:
            return error_response('筛选股票数据失败', 500)
        
        return success_response({
            'total': len(filtered_stocks),
            'stocks': filtered_stocks,
            'filters': filters
        })
        
    except ValueError as e:
        logger.error(f"参数格式错误: {str(e)}")
        return error_response(f'参数格式错误: {str(e)}', 400)
    except Exception as e:
        logger.error(f"筛选股票失败: {str(e)}")
        return error_response(f'筛选股票失败: {str(e)}', 500)

@csrf_exempt
@require_http_methods(["GET"])
def get_stock_detail(request, code):
    """
    获取单只股票详细信息
    
    Args:
        code (str): 股票代码
    
    Returns:
        {
            "code": 200,
            "message": "success",
            "data": {...}
        }
    """
    try:
        # 验证股票代码
        if not validate_stock_symbol(code):
            return error_response('无效的股票代码格式', 400)
        
        # 获取股票详情
        stock_detail = stock_service.get_stock_detail(code)
        if stock_detail is None:
            return error_response('股票不存在或获取失败', 404)
        
        return success_response(stock_detail)
        
    except Exception as e:
        logger.error(f"获取股票详情失败: {str(e)}")
        return error_response(f'获取股票详情失败: {str(e)}', 500)

@csrf_exempt
@require_http_methods(["GET"])
def get_market_summary(request):
    """
    获取上证A股市场概况
    
    Returns:
        {
            "code": 200,
            "message": "success",
            "data": {
                "total_stocks": 1000,
                "rising_stocks": 600,
                "falling_stocks": 300,
                "unchanged_stocks": 100
            }
        }
    """
    try:
        summary = stock_service.get_market_summary()
        if summary is None:
            return error_response('获取市场概况失败', 500)
        
        return success_response(summary)
        
    except Exception as e:
        logger.error(f"获取市场概况失败: {str(e)}")
        return error_response(f'获取市场概况失败: {str(e)}', 500)

@csrf_exempt
@require_http_methods(["GET"])
def get_hot_stocks(request):
    """
    获取热门股票（基于换手率排序）
    
    Query Parameters:
        count (int): 返回股票数量，默认10
    
    Returns:
        {
            "code": 200,
            "message": "success",
            "data": {
                "count": 10,
                "stocks": [...]
            }
        }
    """
    try:
        count = min(int(request.GET.get('count', 10)), 100)
        
        # 从服务层获取热门股票
        hot_stocks = stock_service.get_hot_stocks(count)
        if hot_stocks is None:
            return error_response('获取热门股票失败', 500)
        
        return success_response({
            'count': len(hot_stocks),
            'stocks': hot_stocks
        })
        
    except Exception as e:
        logger.error(f"获取热门股票失败: {str(e)}")
        return error_response(f'获取热门股票失败: {str(e)}', 500)

@csrf_exempt
@require_http_methods(["GET"])
def get_low_turnover_stocks(request):
    """
    获取低换手率优质股票
    
    基于筛选逻辑：换手率在1%到5%之间，价格在10-60之间，流通市值大于100亿
    
    Query Parameters:
        count (int): 返回股票数量，默认20
    
    Returns:
        {
            "code": 200,
            "message": "success",
            "data": {
                "count": 20,
                "stocks": [...],
                "criteria": {...}
            }
        }
    """
    try:
        count = min(int(request.GET.get('count', 20)), 100)
        
        # 从服务层获取低换手率股票
        low_turnover_stocks = stock_service.get_low_turnover_stocks(count)
        if low_turnover_stocks is None:
            return error_response('获取低换手率股票失败', 500)
        
        criteria = {
            'price_range': '10-60',
            'turnover_range': '1%-5%',
            'min_market_cap': '100亿元',
            'sort_by': 'turnover_rate_asc'
        }
        
        return success_response({
            'count': len(low_turnover_stocks),
            'stocks': low_turnover_stocks,
            'criteria': criteria
        })
        
    except Exception as e:
        logger.error(f"获取低换手率股票失败: {str(e)}")
        return error_response(f'获取低换手率股票失败: {str(e)}', 500)

@csrf_exempt
@require_http_methods(["GET"])
def get_stock_type(request, code):
    """
    获取指定股票的类型信息

    Args:
        code (str): 股票代码

    Returns:
        {
            "code": 200,
            "message": "success",
            "data": {...}
        }
    """
    try:
        # 验证股票代码
        if not validate_stock_symbol(code):
            return error_response('无效的股票代码格式', 400)
        
        # 从服务层获取股票类型信息
        type_info = stock_service.get_stock_type_info(code)
        if type_info is None:
            return error_response(f'无法获取股票{code}的类型信息', 404)
        
        return success_response(type_info)
        
    except Exception as e:
        logger.error(f"获取股票类型信息失败: {str(e)}")
        return error_response(str(e), 500)


@csrf_exempt
@require_http_methods(["GET"])
def get_industry_sectors(request):
    """
    获取所有行业板块列表
    
    Query Parameters:
        limit (int): 返回行业板块数量限制，默认返回全部
        offset (int): 偏移量，默认0
    
    Returns:
        {
            "code": 200,
            "message": "success",
            "timestamp": "2024-01-01T12:00:00",
            "data": {
                "total": 100,
                "sectors": [...],
                "query_time": "2024-01-01T12:00:00"
            }
        }
    """
    try:
        # 获取查询参数
        limit = int(request.GET.get('limit')) if request.GET.get('limit') else None
        offset = int(request.GET.get('offset', 0))
        
        # 验证分页参数
        limit, offset = validate_pagination_params(limit, offset)
        
        # 获取行业板块列表
        sectors = industry_sector_service.get_industry_sectors()
        if sectors is None:
            return error_response('获取行业板块列表失败', 500)
        
        # 应用分页
        total = len(sectors)
        if limit:
            sectors = sectors[offset:offset + limit]
        else:
            sectors = sectors[offset:]
        
        return success_response({
            'total': total,
            'sectors': sectors,
            'query_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取行业板块列表失败: {str(e)}")
        return error_response(f'获取行业板块列表失败: {str(e)}', 500)


@csrf_exempt
@require_http_methods(["GET"])
def get_industry_sector_daily(request, code):
    """
    获取行业板块日频数据
    
    Path Parameters:
        code (str): 行业板块代码
    
    Query Parameters:
        start_date (str): 开始日期，格式：YYYYMMDD
        end_date (str): 结束日期，格式：YYYYMMDD
    
    Returns:
        {
            "code": 200,
            "message": "success",
            "timestamp": "2024-01-01T12:00:00",
            "data": {
                "sector_code": "BK0001",
                "sector_name": "农业",
                "daily_data": [...],
                "query_time": "2024-01-01T12:00:00"
            }
        }
    """
    try:
        # 验证行业板块代码
        if not validate_sector_code(code):
            return error_response('无效的行业板块代码', 400)
        
        # 获取查询参数
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # 获取行业板块日频数据
        daily_data = industry_sector_service.get_industry_sector_daily(code, start_date, end_date)
        if daily_data is None:
            return error_response(f'获取行业板块 {code} 日频数据失败', 500)
        
        # 获取行业板块信息
        from .models import IndustrySector
        sector = IndustrySector.objects.filter(code=code).first()
        sector_name = sector.name if sector else '未知'
        
        return success_response({
            'sector_code': code,
            'sector_name': sector_name,
            'daily_data': daily_data,
            'query_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取行业板块 {code} 日频数据失败: {str(e)}")
        return error_response(f'获取行业板块日频数据失败: {str(e)}', 500)


@csrf_exempt
@require_http_methods(["GET"])
def get_industry_sector_realtime(request, code):
    """
    获取行业板块实时行情
    
    Path Parameters:
        code (str): 行业板块代码
    
    Returns:
        {
            "code": 200,
            "message": "success",
            "timestamp": "2024-01-01T12:00:00",
            "data": {
                "sector_code": "BK0001",
                "sector_name": "农业",
                "latest_price": 1234.56,
                "change_percent": 1.23,
                ...
            }
        }
    """
    try:
        # 验证行业板块代码
        if not validate_sector_code(code):
            return error_response('无效的行业板块代码', 400)
        
        # 获取行业板块实时行情
        realtime_data = industry_sector_service.get_industry_sector_realtime(code)
        if realtime_data is None:
            return error_response(f'获取行业板块 {code} 实时行情失败', 500)
        
        return success_response(realtime_data)
        
    except Exception as e:
        logger.error(f"获取行业板块 {code} 实时行情失败: {str(e)}")
        return error_response(f'获取行业板块实时行情失败: {str(e)}', 500)


@csrf_exempt
@require_http_methods(["GET"])
def get_industry_sector_constituents(request, code):
    """
    获取行业板块成分股
    
    Path Parameters:
        code (str): 行业板块代码
    
    Returns:
        {
            "code": 200,
            "message": "success",
            "timestamp": "2024-01-01T12:00:00",
            "data": {
                "sector_code": "BK0001",
                "sector_name": "农业",
                "constituents": [...],
                "total": 50,
                "query_time": "2024-01-01T12:00:00"
            }
        }
    """
    try:
        # 验证行业板块代码
        if not validate_sector_code(code):
            return error_response('无效的行业板块代码', 400)
        
        # 获取行业板块成分股
        constituents = industry_sector_service.get_industry_sector_constituents(code)
        if constituents is None:
            return error_response(f'获取行业板块 {code} 成分股失败', 500)
        
        # 获取行业板块信息
        from .models import IndustrySector
        sector = IndustrySector.objects.filter(code=code).first()
        sector_name = sector.name if sector else '未知'
        
        return success_response({
            'sector_code': code,
            'sector_name': sector_name,
            'constituents': constituents,
            'total': len(constituents),
            'query_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取行业板块 {code} 成分股失败: {str(e)}")
        return error_response(f'获取行业板块成分股失败: {str(e)}', 500)

@csrf_exempt
@require_http_methods(["GET"])
def get_stock_value_em(request, code):
    """
    获取指定股票的估值分析信息

    Args:
        code (str): 股票代码

    Returns:
        {
            "code": 200,
            "message": "success",
            "data": {...}
        }
    """
    try:
        # 验证股票代码
        if not validate_stock_symbol(code):
            return error_response('无效的股票代码格式', 400)
        
        # 从服务层获取股票估值信息
        value_info = stock_service.get_stock_value_em(code)
        if value_info is None:
            # 如果服务层没有数据，直接从akshare获取
            info = ak.stock_value_em(symbol=code)
            if info is None or info.empty:
                return error_response(f'无法获取股票{code}的估值分析信息', 404)
            
            # 转换日期格式
            info['date'] = pd.to_datetime(info['数据日期']).dt.strftime('%Y-%m-%d')
            # 转换为JSON字符串
            value_info = json.loads(info.to_json(orient="records", force_ascii=False))
            
            # 保存到服务层
            stock_service.save_stock_value_em(code, value_info)
        
        return success_response(value_info)
        
    except Exception as e:
        logger.error(f"获取股票估值分析信息失败: {str(e)}")
        return error_response(str(e), 500)

@csrf_exempt
@require_http_methods(["GET"])
def get_stock_individual_fund_flow(request, code):
    """
    获取指定股票的资金流向  

    Args:
        code (str): 股票代码

    Returns:
        {
            "code": 200,
            "message": "success",
            "data": {...}
        }
    """
    try:
        # 验证股票代码
        if not validate_stock_symbol(code):
            return error_response('无效的股票代码格式', 400)
        
        # 从服务层获取股票资金流向信息
        fund_flow = stock_service.get_stock_individual_fund_flow(code)
        if fund_flow is None:
            # 如果服务层没有数据，直接从akshare获取
            info = ak.stock_individual_fund_flow(stock=code)
            if info is None or info.empty:
                return error_response(f'无法获取股票{code}的资金流向信息', 404)
            
            # 转换日期格式
            info['date'] = pd.to_datetime(info['日期']).dt.strftime('%Y-%m-%d')
            # 转换为JSON字符串
            fund_flow = json.loads(info.to_json(orient="records", force_ascii=False))
            
            # 保存到服务层
            stock_service.save_stock_individual_fund_flow(code, fund_flow)
        
        return success_response(fund_flow)
        
    except Exception as e:
        logger.error(f"获取股票资金流向信息失败: {str(e)}")
        return error_response(str(e), 500)

@csrf_exempt
@require_http_methods(["GET"])
def get_stock_history(request, code):
    """
    获取指定股票的历史数据

    Args:
        code (str): 股票代码

    Query Parameters:
        start_date (str): 开始日期，格式YYYYMMDD，默认20200101
        end_date (str): 结束日期，格式YYYYMMDD，默认当前日期

    Returns:
        {
            "code": 200,
            "message": "success",
            "data": [...]
        }
    """
    try:
        # 验证股票代码
        if not validate_stock_symbol(code):
            return error_response('无效的股票代码格式', 400)
        
        # 获取查询参数
        start_date = request.GET.get('start_date', '20200101')
        end_date = request.GET.get('end_date', datetime.now().strftime('%Y%m%d'))
        
        # 从服务层获取股票历史数据
        history_data = stock_service.get_stock_history(code, start_date, end_date)
        if history_data is None:
            # 如果服务层没有数据，直接从akshare获取
            try:
                info = ak.index_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date
                )
                if info is None or info.empty:
                    return error_response(f'无法获取股票{code}的历史数据', 404)
                
                # 转换日期格式
                info['date'] = pd.to_datetime(info['日期']).dt.strftime('%Y-%m-%d')
                # 转换为JSON字符串
                history_data = json.loads(info.to_json(orient="records", force_ascii=False))
                
                # 保存到服务层
                stock_service.save_stock_history(code, history_data, start_date, end_date)
            except Exception as e:
                logger.error(f"从akshare获取股票历史数据失败: {str(e)}")
                return error_response(f'无法获取股票{code}的历史数据: {str(e)}', 404)
        
        return success_response(history_data)
        
    except Exception as e:
        logger.error(f"获取股票历史数据失败: {str(e)}")
        return error_response(str(e), 500)

@csrf_exempt
@require_http_methods(["GET"])
def get_stock_account_statistics(request):
    """
    获取股票账户统计月度数据
    
    描述: 东方财富网-数据中心-特色数据-股票账户统计
    
    Returns:
        {
            "code": 200,
            "message": "success",
            "data": [...]
        }
    """
    try:
        # 从服务层获取股票账户统计数据
        account_stats = stock_service.get_stock_account_statistics()
        if account_stats is None:
            # 如果服务层没有数据，直接从akshare获取
            try:
                stats = ak.stock_account_statistics_em()
                if stats is None or stats.empty:
                    return error_response('无法获取股票账户统计数据', 404)
                
                # 转换日期格式
                stats['date'] = pd.to_datetime(stats['数据日期']).dt.strftime('%Y-%m')
                # 转换为JSON字符串
                account_stats = json.loads(stats.to_json(orient="records", force_ascii=False))
                
                # 保存到服务层
                stock_service.save_stock_account_statistics(account_stats)
            except Exception as e:
                logger.error(f"从akshare获取股票账户统计数据失败: {str(e)}")
                return error_response(f'无法获取股票账户统计数据: {str(e)}', 404)
        
        return success_response(account_stats)
        
    except Exception as e:
        logger.error(f"获取股票账户统计数据失败: {str(e)}")
        return error_response(str(e), 500)

@csrf_exempt
@require_http_methods(["GET"])
def get_stock_market_activity(request):
    """
    获取股票市场活跃度数据
    
    Returns:
        {
            "code": 200,
            "message": "success",
            "data": [...]
        }
    """
    try:
        # 从服务层获取股票市场活跃度数据
        activity_data = stock_service.get_stock_market_activity()
        if activity_data is None:
            # 如果服务层没有数据，直接从akshare获取
            try:
                data = ak.stock_market_activity_legu()
                if data is None or data.empty:
                    return error_response('无法获取股票市场活跃度数据', 404)
                
                # 转换日期格式
                data['date'] = pd.to_datetime(data['数据日期']).dt.strftime('%Y-%m')
                # 转换为JSON字符串
                activity_data = json.loads(data.to_json(orient="records", force_ascii=False))
                
                # 保存到服务层
                stock_service.save_stock_market_activity(activity_data)
            except Exception as e:
                logger.error(f"从akshare获取股票市场活跃度数据失败: {str(e)}")
                return error_response(f'无法获取股票市场活跃度数据: {str(e)}', 404)
        
        return success_response(activity_data)
        
    except Exception as e:
        logger.error(f"获取股票市场活跃度数据失败: {str(e)}")
        return error_response(str(e), 500)

@csrf_exempt
@require_http_methods(["POST"])
def get_stock_types_batch(request):
    """
    批量获取股票类型信息

    POST Body:
        {
            "codes": ["600000", "600001", ...]
        }

    Returns:
        {
            "code": 200,
            "message": "success",
            "data": {
                "total": 3,
                "types": [...]
            }
        }
    """
    try:
        data = json.loads(request.body)
        if not data or 'codes' not in data:
            return error_response('请提供股票代码列表', 400)
        
        codes = data['codes']
        if not isinstance(codes, list):
            return error_response('codes必须是列表格式', 400)
        
        # 从服务层批量获取股票类型信息
        type_info_list = stock_service.get_stock_types_batch(codes)
        if type_info_list is None:
            return error_response('获取股票类型信息失败', 500)
        
        return success_response({
            'total': len(type_info_list),
            'types': type_info_list
        })
        
    except json.JSONDecodeError:
        return error_response('无效的JSON格式', 400)
    except Exception as e:
        logger.error(f"批量获取股票类型信息失败: {str(e)}")
        return error_response(str(e), 500)

@csrf_exempt
@require_http_methods(["GET"])
def get_industries(request):
    """
    获取所有上证A股行业分类

    Returns:
        {
            "code": 200,
            "message": "success",
            "data": {
                "total": 50,
                "industries": [...]
            }
        }
    """
    try:
        # 从服务层获取行业分类数据
        industries = stock_service.get_all_industries()
        if industries is None:
            return error_response('获取行业分类失败', 500)
        
        return success_response({
            'total': len(industries),
            'industries': industries
        })
        
    except Exception as e:
        logger.error(f"获取行业分类失败: {str(e)}")
        return error_response(str(e), 500)