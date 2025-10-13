from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import models
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

@csrf_exempt
@require_http_methods(["GET"])
def get_industry_performance_reports(request):
    """
    获取行业业绩快报汇聚数据
    功能：根据行业和报告类型筛选业绩快报数据，按报告期和行业汇聚各类指标。
    参数：
    - industry (str, optional): 行业名称，不指定则获取所有行业
    - report_type (str, optional): 报告类型，支持 'annual'(年报)、'semi_annual'(中报)、'quarterly'(季报)
    - start_date (str, optional): 开始日期，格式YYYYMMDD
    - end_date (str, optional): 结束日期，格式YYYYMMDD
    返回值：
    {
        "code": 200,
        "message": "success", 
        "timestamp": "2024-01-01T12:00:00",
        "data": {
            "total_records": 50,
            "aggregated_reports": [...],
            "query_params": {...}
        }
    }
    事件：无（视图函数不直接触发事件）
    """
    try:
        # 导入模型
        from indival_stock_data.models import PerformanceReport, IndividualStock
        from django.db.models import Sum, Count, Avg
        
        # 获取查询参数
        industry = request.GET.get('industry')
        report_type = request.GET.get('report_type')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
            
        # 构建查询条件
        queryset = PerformanceReport.objects.select_related('stock')
        
        # 按行业筛选
        if industry:
            queryset = queryset.filter(industry__icontains=industry)
            
        # 按报告类型筛选（根据报告期判断）
        if report_type:
            if report_type == 'annual':
                # 年报：报告期以1231结尾
                queryset = queryset.filter(report_date__endswith='1231')
            elif report_type == 'semi_annual':
                # 中报：报告期以0630结尾
                queryset = queryset.filter(report_date__endswith='0630')
            elif report_type == 'q1':
                # 一季报：报告期以0331结尾
                queryset = queryset.filter(report_date__endswith='0331')
            elif report_type == 'q3':
                # 三季报：报告期以0930结尾
                queryset = queryset.filter(report_date__endswith='0930')
            elif report_type == 'quarterly':
                # 季报：报告期以0331或0930结尾（保持向后兼容）
                queryset = queryset.filter(
                    models.Q(report_date__endswith='0331') | 
                    models.Q(report_date__endswith='0930')
                )
                
        # 按日期范围筛选
        if start_date:
            queryset = queryset.filter(report_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(report_date__lte=end_date)
            
        # 按报告期和行业分组汇聚数据
        aggregated_data = queryset.values('report_date', 'industry').annotate(
            # 汇聚财务指标
            total_operating_revenue=Sum('operating_revenue'),
            total_net_profit=Sum('net_profit'),
            avg_earnings_per_share=Avg('earnings_per_share'),
            avg_operating_revenue_growth_rate=Avg('operating_revenue_growth_rate'),
            avg_net_profit_growth_rate=Avg('net_profit_growth_rate'),
            avg_roe=Avg('roe'),
            avg_gross_profit_margin=Avg('gross_profit_margin'),
            avg_net_assets_per_share=Avg('net_assets_per_share'),
            avg_operating_cash_flow_per_share=Avg('operating_cash_flow_per_share'),
            # 统计信息
            company_count=Count('stock', distinct=True)
        ).order_by('report_date', 'industry')
        
        # 转换为列表格式
        reports_list = []
        for item in aggregated_data:
            report_dict = {
                'report_date': item['report_date'],
                'industry': item['industry'],
                'company_count': item['company_count'],
                'total_operating_revenue': float(item['total_operating_revenue']) if item['total_operating_revenue'] else 0,
                'total_net_profit': float(item['total_net_profit']) if item['total_net_profit'] else 0,
                'avg_earnings_per_share': round(float(item['avg_earnings_per_share']), 4) if item['avg_earnings_per_share'] else 0,
                'avg_operating_revenue_growth_rate': round(float(item['avg_operating_revenue_growth_rate']), 2) if item['avg_operating_revenue_growth_rate'] else 0,
                'avg_net_profit_growth_rate': round(float(item['avg_net_profit_growth_rate']), 2) if item['avg_net_profit_growth_rate'] else 0,
                'avg_roe': round(float(item['avg_roe']), 4) if item['avg_roe'] else 0,
                'avg_gross_profit_margin': round(float(item['avg_gross_profit_margin']), 4) if item['avg_gross_profit_margin'] else 0,
                'avg_net_assets_per_share': round(float(item['avg_net_assets_per_share']), 4) if item['avg_net_assets_per_share'] else 0,
                'avg_operating_cash_flow_per_share': round(float(item['avg_operating_cash_flow_per_share']), 4) if item['avg_operating_cash_flow_per_share'] else 0,
            }
            reports_list.append(report_dict)
            
        # 构建响应数据
        data = {
            'total_records': len(reports_list),
            'aggregated_reports': reports_list,
            'query_params': {
                'industry': industry,
                'report_type': report_type,
                'start_date': start_date,
                'end_date': end_date
            }
        }
        
        return success_response(data)
        
    except ValueError as e:
        logger.error(f"参数错误: {str(e)}")
        return error_response(f"参数错误: {str(e)}", 400)
    except Exception as e:
        logger.error(f"获取行业业绩快报数据失败: {str(e)}")
        return error_response(f"获取数据失败: {str(e)}", 500)


@csrf_exempt
@require_http_methods(["GET"])
def get_industry_heatmap_data(request):
    """
    获取行业热力图数据接口
    功能：使用行业业绩数据的“报告期+行业”汇聚结果，返回适合前端热力图渲染的行业数据。
    规则：
    - 比率类指标（如 ROE、毛利率、营收/利润增速）直接使用当期行业均值作为热力图值；
    - 非比率类指标（如营业收入、净利润、每股收益、每股净资产、每股经营现金流）按行业在时间序列中计算同比（相邻上一期）增速，返回该增速作为热力图值。
    参数：
    - metric_type (str, required): 指标类型，支持：
      * 比率类：'roe'、'gross_profit_margin'、'operating_revenue_growth_rate'、'net_profit_growth_rate'
      * 非比率类：'operating_revenue'、'net_profit'、'earnings_per_share'、'net_assets_per_share'、'operating_cash_flow_per_share'
    - report_type (str, required): 报告类型：'annual'(年报, 1231)、'semi_annual'(中报, 0630)、'q1'(一季报, 0331)、'q3'(三季报, 0930)
    返回值：
    {
        "code": 200,
        "message": "success",
        "timestamp": "2024-01-01T12:00:00",
        "data": {
            "metric_type": "roe",
            "metric_name": "净资产收益率(%)",
            "report_type": "annual",
            "periods": [
                {"report_date": "20231231", "heatmap_data": [{"industry": "银行", "value": 12.5, "company_count": 42, "rank": 1}], "statistics": {"total_industries": 30, "max_value": 25.8, "min_value": -5.2, "avg_value": 8.6}},
                {"report_date": "20221231", "heatmap_data": [...], "statistics": {...}}
            ],
            "report_date": "20231231",
            "heatmap_data": [{"industry": "银行", "value": 12.5, "company_count": 42, "rank": 1}],
            "statistics": {"total_industries": 30, "max_value": 25.8, "min_value": -5.2, "avg_value": 8.6}
        }
    }
    事件：无（视图函数不直接触发事件）
    """
    from indival_stock_data.models import PerformanceReport, IndividualStock
    from django.db.models import Sum, Count, Avg
    
    # 获取查询参数
    industry = request.GET.get('industry')
    report_type = request.GET.get('report_type')
        
    # 构建查询条件
    queryset = PerformanceReport.objects.select_related('stock')
    
    # 按行业筛选
    if industry:
        queryset = queryset.filter(industry__icontains=industry)
        
    # 按报告类型筛选（根据报告期判断）
    if report_type:
        if report_type == 'annual':
            # 年报：报告期以1231结尾
            queryset = queryset.filter(report_date__endswith='1231')
        elif report_type == 'semi_annual':
            # 中报：报告期以0630结尾
            queryset = queryset.filter(report_date__endswith='0630')
        elif report_type == 'q1':
            # 一季报：报告期以0331结尾
            queryset = queryset.filter(report_date__endswith='0331')
        elif report_type == 'q3':
            # 三季报：报告期以0930结尾
            queryset = queryset.filter(report_date__endswith='0930')
        elif report_type == 'quarterly':
            # 季报：报告期以0331或0930结尾（保持向后兼容）
            queryset = queryset.filter(
                models.Q(report_date__endswith='0331') | 
                models.Q(report_date__endswith='0930')
            )
        
    # 按报告期和行业分组汇聚数据
    aggregated_data = queryset.values('report_date', 'industry').annotate(
        # 汇聚财务指标
        total_operating_revenue=Sum('operating_revenue'),
        total_net_profit=Sum('net_profit'),
        avg_earnings_per_share=Avg('earnings_per_share'),
        avg_operating_revenue_growth_rate=Avg('operating_revenue_growth_rate'),
        avg_net_profit_growth_rate=Avg('net_profit_growth_rate'),
        avg_roe=Avg('roe'),
        avg_gross_profit_margin=Avg('gross_profit_margin'),
        avg_net_assets_per_share=Avg('net_assets_per_share'),
        avg_operating_cash_flow_per_share=Avg('operating_cash_flow_per_share'),
        # 统计信息
        company_count=Count('stock', distinct=True)
    ).order_by('report_date', 'industry')
    
    # 转换为列表格式
    reports_list = []
    for item in aggregated_data:
        report_dict = {
            'report_date': item['report_date'],
            'industry': item['industry'],
            'company_count': item['company_count'],
            'total_operating_revenue': float(item['total_operating_revenue']) if item['total_operating_revenue'] else 0,
            'total_net_profit': float(item['total_net_profit']) if item['total_net_profit'] else 0,
            'avg_earnings_per_share': round(float(item['avg_earnings_per_share']), 4) if item['avg_earnings_per_share'] else 0,
            'avg_operating_revenue_growth_rate': round(float(item['avg_operating_revenue_growth_rate']), 2) if item['avg_operating_revenue_growth_rate'] else 0,
            'avg_net_profit_growth_rate': round(float(item['avg_net_profit_growth_rate']), 2) if item['avg_net_profit_growth_rate'] else 0,
            'avg_roe': round(float(item['avg_roe']), 4) if item['avg_roe'] else 0,
            'avg_gross_profit_margin': round(float(item['avg_gross_profit_margin']), 4) if item['avg_gross_profit_margin'] else 0,
            'avg_net_assets_per_share': round(float(item['avg_net_assets_per_share']), 4) if item['avg_net_assets_per_share'] else 0,
            'avg_operating_cash_flow_per_share': round(float(item['avg_operating_cash_flow_per_share']), 4) if item['avg_operating_cash_flow_per_share'] else 0,
        }
        reports_list.append(report_dict)
    
    # 构建热力图数据格式
    heatmap_data = convert_to_heatmap_format(reports_list)
    
    return success_response(heatmap_data)


def convert_to_heatmap_format(reports_data):
    """
    将行业业绩数据转换为热力图格式
    
    参数:
        reports_data: 行业业绩数据列表
        
    返回:
        符合热力图要求的数据格式
    """
    # 直接使用原始数据中的行业名称
    industry_names = list(set([item['industry'] for item in reports_data]))
    industry_code_mapping = {}
    for i, industry in enumerate(industry_names):
        industry_code_mapping[industry] = f'801{str(i+1).zfill(3)}.SI'
    
    # 获取所有唯一的报告日期
    unique_dates = sorted(list(set([item['report_date'] for item in reports_data])))
    
    # 获取所有唯一的行业
    unique_industries = list(set([item['industry'] for item in reports_data]))
    
    # 构建行业代码名称映射
    sw_code_names = []
    for industry in unique_industries:
        index_code = industry_code_mapping.get(industry, f'801{str(len(sw_code_names) + 1).zfill(3)}.SI')
        sw_code_names.append({
            'indexCode': index_code,
            'indexName': industry
        })
    
    # 构建拥堵度数据
    congestions = {}
    for industry in unique_industries:
        index_code = industry_code_mapping.get(industry, f'801{str(unique_industries.index(industry) + 1).zfill(3)}.SI')
        industry_data = []
        
        for date in unique_dates:
            # 查找该行业在该日期的数据
            industry_report = next((item for item in reports_data 
                                  if item['industry'] == industry and item['report_date'] == date), None)
            
            if industry_report:
                # 使用原始数据中的指标计算热力图值
                # 使用原始数据中的指标计算热力图值
                industry_data.append({
                    'avg_operating_revenue_growth_rate': round(float(industry_report['avg_operating_revenue_growth_rate'] or 0), 2),
                    'avg_net_profit_growth_rate': round(float(industry_report['avg_net_profit_growth_rate'] or 0), 2),
                    'total_operating_revenue': float(industry_report['total_operating_revenue'] or 0),
                    'total_net_profit': float(industry_report['total_net_profit'] or 0),
                    'avg_earnings_per_share': round(float(industry_report['avg_earnings_per_share'] or 0), 4),
                    'avg_roe': round(float(industry_report['avg_roe'] or 0), 4),
                    'avg_gross_profit_margin': round(float(industry_report['avg_gross_profit_margin'] or 0), 4),
                    'avg_net_assets_per_share': round(float(industry_report['avg_net_assets_per_share'] or 0), 4),
                    'avg_operating_cash_flow_per_share': round(float(industry_report['avg_operating_cash_flow_per_share'] or 0), 4)
                })
            else:
                # 如果没有数据，使用默认值
                industry_data.append({
                    'avg_operating_revenue_growth_rate': 0,
                    'avg_net_profit_growth_rate': 0,
                    'total_operating_revenue': 0,
                    'total_net_profit': 0,
                    'avg_earnings_per_share': 0,
                    'avg_roe': 0,
                    'avg_gross_profit_margin': 0,
                    'avg_net_assets_per_share': 0,
                    'avg_operating_cash_flow_per_share': 0
                })
        
        congestions[index_code] = industry_data
    
    # 格式化日期（将YYYYMMDD转换为YYYY-MM-DD）
    formatted_dates = []
    for date in unique_dates:
        if len(date) == 8:
            formatted_dates.append(f"{date[:4]}-{date[4:6]}-{date[6:8]}")
        else:
            formatted_dates.append(date)
    
    return {
        'dates': formatted_dates,
        'swCodeNames': sw_code_names,
        'congestions': congestions
    }


@csrf_exempt
@require_http_methods(["GET"])
def get_industry_statistics(request):
    """
    获取行业统计数据
    
    Query Parameters:
        industry (str): 行业名称，可选，不传则返回所有行业统计
    
    Returns:
        {
            "code": 200,
            "message": "success",
            "timestamp": "2024-01-01T12:00:00",
            "data": {
                "industries": [...] | "industry": {...},
                "total_industries": 50,
                "timestamp": "2024-01-01T12:00:00"
            }
        }
    """
    try:
        # 获取查询参数
        industry_name = request.GET.get('industry')
        
        # 导入服务
        from .services import industry_stats_service
        
        # 获取行业统计数据
        result = industry_stats_service.get_industry_statistics(industry_name)
        
        if result is None:
            return error_response(
                message=f"未找到行业统计数据: {industry_name or '全部行业'}",
                code=404
            )
        
        return success_response(
            data=result,
            message="获取行业统计数据成功"
        )
        
    except Exception as e:
        logger.error(f"获取行业统计数据失败: {str(e)}")
        return error_response(
            message=f"获取行业统计数据失败: {str(e)}",
            code=500
        )


@csrf_exempt
@require_http_methods(["GET"])
def get_industry_ranking(request):
    """
    获取行业排名数据
    
    Query Parameters:
        sort_by (str): 排序字段，默认为total_market_cap_sum
        order (str): 排序方向，asc或desc，默认desc
        limit (int): 返回数量限制，默认20
    
    Returns:
        {
            "code": 200,
            "message": "success",
            "timestamp": "2024-01-01T12:00:00",
            "data": [
                {
                    "industry": "电子",
                    "rank": 1,
                    "stock_count": 100,
                    "total_market_cap_sum": 1000000000,
                    ...
                }
            ]
        }
    """
    try:
        # 获取查询参数
        sort_by = request.GET.get('sort_by', 'total_market_cap_sum')
        order = request.GET.get('order', 'desc')
        limit = int(request.GET.get('limit', 20))
        
        # 验证参数
        if limit <= 0 or limit > 100:
            return error_response(
                message="limit参数必须在1-100之间",
                code=400
            )
        
        if order not in ['asc', 'desc']:
            return error_response(
                message="order参数必须是asc或desc",
                code=400
            )
        
        # 导入服务
        from .services import industry_stats_service
        
        # 获取行业排名数据
        result = industry_stats_service.get_industry_ranking(sort_by, order, limit)
        
        if result is None:
            return error_response(
                message="未找到行业排名数据",
                code=404
            )
        
        return success_response(
            data=result,
            message="获取行业排名数据成功"
        )
        
    except ValueError as e:
        return error_response(
            message=f"参数错误: {str(e)}",
            code=400
        )
    except Exception as e:
        logger.error(f"获取行业排名数据失败: {str(e)}")
        return error_response(
            message=f"获取行业排名数据失败: {str(e)}",
            code=500
        )


@csrf_exempt
@require_http_methods(["POST"])
def get_industry_comparison(request):
    """
    获取多个行业对比数据
    
    Request Body:
        {
            "industries": ["电子", "医药生物", "计算机"]
        }
    
    Returns:
        {
            "code": 200,
            "message": "success",
            "timestamp": "2024-01-01T12:00:00",
            "data": {
                "industries": [...],
                "comparison_count": 3,
                "timestamp": "2024-01-01T12:00:00"
            }
        }
    """
    try:
        # 解析请求体
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            return error_response(
                message="请求头Content-Type必须为application/json",
                code=400
            )
        
        # 获取行业列表
        industries = data.get('industries', [])
        
        # 验证参数
        if not industries or not isinstance(industries, list):
            return error_response(
                message="industries参数必须是非空数组",
                code=400
            )
        
        if len(industries) < 2:
            return error_response(
                message="行业对比需要至少2个行业",
                code=400
            )
        
        if len(industries) > 10:
            return error_response(
                message="最多支持对比10个行业",
                code=400
            )
        
        # 验证行业名称
        for industry in industries:
            if not isinstance(industry, str) or not industry.strip():
                return error_response(
                    message="行业名称必须是非空字符串",
                    code=400
                )
        
        # 导入服务
        from .services import industry_stats_service
        
        # 获取行业对比数据
        result = industry_stats_service.get_industry_comparison(industries)
        
        if result is None:
            return error_response(
                message="未找到有效的行业对比数据",
                code=404
            )
        
        return success_response(
            data=result,
            message="获取行业对比数据成功"
        )
        
    except json.JSONDecodeError:
        return error_response(
            message="请求体JSON格式错误",
            code=400
        )
    except Exception as e:
        logger.error(f"获取行业对比数据失败: {str(e)}")
        return error_response(
            message=f"获取行业对比数据失败: {str(e)}",
            code=500
        )
        
    

        