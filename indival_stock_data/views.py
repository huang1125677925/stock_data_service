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
from rest_framework.permissions import AllowAny
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .services import individual_stock_service, stock_tag_service
from common.validators import validate_stock_symbol
from common.response import success_response, error_response
from .models import IndividualStock, StrategyResult, BalanceSheet, IncomeStatement, CashFlowStatement, StockTag
from .serializers import (
    IndividualStockSerializer, StrategyResultSerializer, BalanceSheetSerializer, 
    IncomeStatementSerializer, CashFlowStatementSerializer, StockTagSerializer, StockTagQuerySerializer,
    SuccessResponseConceptListSerializer, ErrorResponseSerializer,
    SuccessResponseStockCorrelationSerializer, SuccessResponseStockVolatilityListSerializer,
)
from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiTypes
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class StockListView(APIView):
    """
    获取股票列表
    """
    def get(self, request):
        """
        功能：获取股票列表，支持关键词搜索、行业筛选与分页，提高查询性能。
        参数：
        - request(HttpRequest): 请求对象，查询参数包括：
          - page(int, 可选): 页码，默认1
          - page_size(int, 可选): 每页数量，默认20
          - keyword(str, 可选): 关键词，按股票名称或代码模糊匹配
          - industry(str, 可选): 行业名称，按行业精确匹配
          - dc_concept(str, 可选): 东财概念，按概念模糊匹配
          - stock_names(list[str] 或 逗号分隔字符串, 可选): 股票名列表，按名称精确筛选，支持JSON数组或逗号分隔
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
            industry = request.query_params.get('industry', None)
            dc_concept = request.query_params.get('dc_concept', None)
            stock_names_param = request.query_params.get('stock_names', None)
            codes_param = request.query_params.get('codes', None)

            # 解析股票名列表参数，支持JSON数组或逗号分隔的字符串
            names_list = []
            if stock_names_param:
                try:
                    param_str = stock_names_param.strip()
                    if param_str.startswith('['):
                        # JSON 数组格式
                        parsed = json.loads(param_str)
                        if not isinstance(parsed, list):
                            return error_response('stock_names参数格式错误，应为数组', 400)
                        names_list = [s.strip() for s in parsed if isinstance(s, str) and s.strip()]
                    else:
                        # 逗号分隔字符串格式
                        names_list = [s.strip() for s in param_str.split(',') if s.strip()]
                except Exception:
                    return error_response('stock_names参数格式错误，应为JSON数组或逗号分隔字符串', 400)
            
            codes_list = []
            if codes_param:
                codes_list = [c.strip() for c in codes_param.split(',') if c and c.strip()]

            # 使用数据库层面的过滤与分页，避免一次性加载全部数据
            queryset = IndividualStock.objects.all().order_by('code')
            if keyword:
                queryset = queryset.filter(Q(name__icontains=keyword) | Q(code__icontains=keyword))
            if industry:
                queryset = queryset.filter(industry__icontains=industry)
            if dc_concept:
                queryset = queryset.filter(dc_concept__icontains=dc_concept)
            if names_list:
                queryset = queryset.filter(name__in=names_list)
            if codes_list:
                queryset = queryset.filter(code__in=codes_list)

            if queryset.count() == 0:
                return error_response("没有搜索到相关股票", 404)

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


class DcConceptListView(APIView):
    """
    东财概念列表API视图
    功能：根据个股数据中的 dc_concept 字段提取概念列表，进行去重与排序后返回。
    参数：无（无需任何查询参数）
    返回值：统一响应结构 success_response
      - code (int): 状态码，成功为 200
      - message (str): 提示信息
      - timestamp (str): ISO 时间戳
      - data (list[str]): 概念名称列表
    事件：无
    """

    @extend_schema(
        summary="东财概念列表",
        description="从个股数据的 dc_concept 字段提取概念，去重并排序后返回。无需任何参数，统一响应结构。",
        tags=["individual_stock"],
        responses={
            200: SuccessResponseConceptListSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            # 提取所有非空的概念字符串
            concept_strings = (
                IndividualStock.objects
                .exclude(dc_concept__isnull=True)
                .exclude(dc_concept__exact='')
                .values_list('dc_concept', flat=True)
            )

            # 分割、去重并排序
            concepts = set()
            for cs in concept_strings:
                parts = [p.strip() for p in str(cs).split(',') if p and p.strip()]
                concepts.update(parts)

            concepts_list = sorted(concepts)

            # 直接返回概念列表数据（无需任何查询参数）
            return success_response(concepts_list)
        except Exception as e:
            logger.error(f"获取东财概念列表失败: {str(e)}")
            return error_response(f'获取东财概念列表失败: {str(e)}', 500)


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
        """
        功能：获取指定股票的历史行情数据，支持日频和周频。
        参数：
        - request(HttpRequest): 请求对象，查询参数包括：
          - start_date(str, 可选): 开始日期，格式：YYYYMMDD，默认30天前
          - end_date(str, 可选): 结束日期，格式：YYYYMMDD，默认今天
          - adjust(str, 可选): 复权类型，""为不复权，"qfq"前复权，"hfq"后复权
          - frequency(str, 可选): 数据频率，"daily"(默认) 或 "weekly"（周频）
        - stock_code(str): 股票代码
        返回值：
        - JsonResponse: 使用success_response返回历史数据列表；参数错误或服务异常使用error_response返回错误信息。
        事件：
        - 当股票代码无效或参数格式错误时，记录日志并返回错误响应；当查询无数据时返回空列表。
        """
        try:
            if not validate_stock_symbol(stock_code):
                return error_response(f"无效的股票代码: {stock_code}", 400)
            
            # 获取查询参数
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            adjust = request.query_params.get('adjust', "")
            frequency = request.query_params.get('frequency', 'daily')
            
            # 获取历史数据
            history = individual_stock_service.get_stock_history(stock_code, start_date, end_date, adjust, frequency)
            
            
            return success_response(history)
        except ValueError as e:
            logger.error(f"参数格式错误: {str(e)}")
            return error_response(f'参数格式错误: {str(e)}', 400)
        except Exception as e:
            logger.error(f"获取股票历史行情数据失败: {str(e)}")
            return error_response(f'获取股票历史行情数据失败: {str(e)}', 500)


class StockDailyCorrelationView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="股票收盘价相关性矩阵",
        description=(
            "输入股票代码列表与时间范围，计算收盘价曲线的Pearson相关性，两两组合生成相关性矩阵。"
        ),
        tags=["individual_stock"],
        responses={
            200: SuccessResponseStockCorrelationSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            codes_str = request.query_params.get('stock_codes')
            if not codes_str:
                return error_response('参数缺失：stock_codes 必填（逗号分隔）', 400)
            codes = [c.strip() for c in codes_str.split(',') if c.strip()]
            seen = set()
            ordered_codes = []
            for c in codes:
                if c not in seen:
                    ordered_codes.append(c)
                    seen.add(c)
            if len(ordered_codes) < 2:
                return error_response('至少提供两个不同的股票代码以计算相关性', 400)

            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')

            def normalize_date(s):
                if not s:
                    return None
                return s.replace('-', '')

            sd_str = normalize_date(start_date)
            ed_str = normalize_date(end_date)

            bulk = individual_stock_service.get_stocks_history_bulk(ordered_codes, sd_str, ed_str, "daily")
            series_list = []
            for code in ordered_codes:
                dailies = bulk.get(code, [])
                if not dailies:
                    series_list.append(pd.Series(dtype=float, name=code))
                    continue
                dates = [datetime.strptime(d['date'], '%Y-%m-%d').date() for d in dailies if d.get('date')]
                closes = [float(d['close_price']) for d in dailies if d.get('close_price') is not None]
                if not dates or not closes or len(dates) != len(closes):
                    series_list.append(pd.Series(dtype=float, name=code))
                    continue
                s = pd.Series(data=closes, index=dates, name=code)
                series_list.append(s)

            if not series_list:
                return error_response('查询范围内无任何日线数据', 404)

            df = pd.concat(series_list, axis=1)
            corr_df = df.corr(method='pearson', min_periods=2)

            labels = list(corr_df.columns)
            matrix = []
            for row_values in corr_df.values.tolist():
                row = []
                for v in row_values:
                    if v is None or (isinstance(v, float) and np.isnan(v)):
                        row.append(None)
                    else:
                        row.append(round(float(v), 4))
                matrix.append(row)

            payload = {
                'labels': labels,
                'matrix': matrix,
                'start_date': start_date,
                'end_date': end_date,
            }
            return success_response(payload)
        except Exception as e:
            logger.error(f"股票收盘价相关性计算失败: {str(e)}")
            return error_response(f'股票收盘价相关性计算失败: {str(e)}', 500)


class StockDailyVolatilityView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="股票区间波动度统计",
        description=(
            "对股票列表在区间内的收盘价曲线进行统计：最高/最低、最大下跌/上涨、"
            "最新价在区间的百分位、方差、均值、趋势与网格交易适配。时间范围需≥1年。"
        ),
        tags=["individual_stock"],
        responses={
            200: SuccessResponseStockVolatilityListSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            codes_str = request.query_params.get('stock_codes')
            if not codes_str:
                return error_response('参数缺失：stock_codes 必填（逗号分隔）', 400)
            codes = [c.strip() for c in codes_str.split(',') if c.strip()]
            seen = set()
            ordered_codes = []
            for c in codes:
                if c not in seen:
                    ordered_codes.append(c)
                    seen.add(c)
            if len(ordered_codes) == 0:
                return error_response('未提供有效的股票代码', 400)

            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            sample_n_str = request.query_params.get('sample_n')
            sample_n = None
            if sample_n_str:
                try:
                    sample_n = int(sample_n_str)
                except ValueError:
                    return error_response('参数错误：sample_n 必须为整数', 400)
                if sample_n is not None and sample_n < 10:
                    return error_response('参数错误：sample_n 需≥10', 400)

            def parse_date(s):
                if not s:
                    return None
                return datetime.strptime(s, '%Y-%m-%d').date()

            sd = parse_date(start_date)
            ed = parse_date(end_date)
            today = datetime.now().date()
            if ed is None:
                ed = today
            if sd is None:
                sd = ed - timedelta(days=365)

            if (ed - sd).days < 365:
                return error_response('时间范围至少需覆盖1年', 400)

            sd_str = sd.strftime('%Y%m%d')
            ed_str = ed.strftime('%Y%m%d')

            bulk = individual_stock_service.get_stocks_history_bulk(ordered_codes, sd_str, ed_str, "daily")
            items = []
            skipped = 0
            for code in ordered_codes:
                dailies = bulk.get(code, [])
                if not dailies or len(dailies) < 2:
                    skipped += 1
                    continue
                dates = [datetime.strptime(d['date'], '%Y-%m-%d').date() for d in dailies if d.get('date')]
                closes = [float(d['close_price']) for d in dailies if d.get('close_price') is not None]
                if len(closes) < 2 or len(dates) != len(closes):
                    skipped += 1
                    continue
                closes_np = np.array(closes, dtype=float)

                highest_idx = int(np.argmax(closes_np))
                lowest_idx = int(np.argmin(closes_np))
                highest_val = float(closes_np[highest_idx])
                lowest_val = float(closes_np[lowest_idx])
                highest_date = dates[highest_idx].strftime('%Y-%m-%d')
                lowest_date = dates[lowest_idx].strftime('%Y-%m-%d')

                running_max = -np.inf
                mdd = 0.0
                mdd_start = 0
                mdd_end = 0
                peak_idx = 0
                for i, price in enumerate(closes_np):
                    if price > running_max:
                        running_max = price
                        peak_idx = i
                    dd = price / running_max - 1.0
                    if dd < mdd:
                        mdd = dd
                        mdd_start = peak_idx
                        mdd_end = i
                mdd_days = mdd_end - mdd_start if mdd_end >= mdd_start else 0

                running_min = np.inf
                max_rise = 0.0
                rise_start = 0
                rise_end = 0
                trough_idx = 0
                for i, price in enumerate(closes_np):
                    if price < running_min:
                        running_min = price
                        trough_idx = i
                    rise = price / running_min - 1.0
                    if rise > max_rise:
                        max_rise = rise
                        rise_start = trough_idx
                        rise_end = i
                rise_days = rise_end - rise_start if rise_end >= rise_start else 0

                latest_price = float(closes_np[-1])
                latest_date = dates[-1].strftime('%Y-%m-%d')
                denom = highest_val - lowest_val
                if denom > 0:
                    percentile = round((latest_price - lowest_val) / denom * 100.0, 2)
                else:
                    percentile = 100.0

                mean_val = float(np.mean(closes_np))
                var_val = float(np.var(closes_np, ddof=1))
                std_val = float(np.std(closes_np, ddof=1))

                idx = np.arange(len(closes_np), dtype=float)
                use_sample = False
                if sample_n and len(closes_np) > sample_n:
                    step = max(1, len(closes_np) // sample_n)
                    closes_fit = closes_np[::step]
                    idx_fit = idx[::step]
                    use_sample = True
                else:
                    closes_fit = closes_np
                    idx_fit = idx
                slope, intercept = np.polyfit(idx_fit, closes_fit, 1)
                pred = slope * idx_fit + intercept
                ss_res = float(np.sum((closes_fit - pred) ** 2))
                ss_tot = float(np.sum((closes_fit - np.mean(closes_fit)) ** 2))
                r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
                slope_scaled = slope / mean_val if mean_val != 0 else 0.0

                trend = 'range'
                if r2 >= 0.5 and abs(slope_scaled) >= 0.0005:
                    trend = 'up' if slope_scaled > 0 else 'down'

                range_ratio = (highest_val - lowest_val) / mean_val if mean_val > 0 else 0.0
                grid_ok = trend == 'range' and 0.05 <= range_ratio <= 0.5

                item = {
                    'stock_code': code,
                    'start_date': sd.strftime('%Y-%m-%d'),
                    'end_date': ed.strftime('%Y-%m-%d'),
                    'highest_value': round(highest_val, 4),
                    'highest_date': highest_date,
                    'lowest_value': round(lowest_val, 4),
                    'lowest_date': lowest_date,
                    'max_drawdown_pct': round(mdd * 100.0, 2),
                    'mdd_start_date': dates[mdd_start].strftime('%Y-%m-%d'),
                    'mdd_end_date': dates[mdd_end].strftime('%Y-%m-%d'),
                    'mdd_days': int(mdd_days),
                    'max_rise_pct': round(max_rise * 100.0, 2),
                    'rise_start_date': dates[rise_start].strftime('%Y-%m-%d'),
                    'rise_end_date': dates[rise_end].strftime('%Y-%m-%d'),
                    'rise_days': int(rise_days),
                    'latest_price': round(latest_price, 4),
                    'latest_date': latest_date,
                    'percentile_between_min_max': float(percentile),
                    'mean': round(mean_val, 4),
                    'variance': round(var_val, 6),
                    'stddev': round(std_val, 4),
                    'trend': trend,
                    'grid_applicable': bool(grid_ok),
                    'sample_used': bool(use_sample),
                    'sample_n': int(sample_n) if sample_n else None,
                }
                items.append(item)

            payload = {
                'items': items,
                'total': len(items),
                'start_date': sd.strftime('%Y-%m-%d'),
                'end_date': ed.strftime('%Y-%m-%d'),
                'skipped': skipped,
            }
            return success_response(payload)
        except Exception as e:
            logger.error(f"股票区间波动度计算失败: {str(e)}")
            return error_response(f'股票区间波动度计算失败: {str(e)}', 500)

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


class BalanceSheetView(APIView):
    """
    资产负债表API视图
    功能：提供资产负债表数据的查询接口
    参数：
    - request: HTTP请求对象
    返回值：
    - JsonResponse: 调用success_response返回数据；失败时调用error_response返回错误信息
    事件：
    - 当查询参数错误时，记录日志并返回错误响应
    """
    
    def get(self, request, stock_code=None):
        """
        获取资产负债表数据
        
        路径参数:
        - stock_code: 股票代码（可选）
        
        查询参数:
        - date: 报告期，格式YYYYMMDD（可选）
        - page: 页码，默认1
        - page_size: 每页数量，默认20
        """
        try:
            # 获取查询参数
            date = request.query_params.get('date')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # 构建查询条件
            queryset = BalanceSheet.objects.select_related('stock').all()
            
            if stock_code:
                if not validate_stock_symbol(stock_code):
                    return error_response("无效的股票代码格式", 400)
                queryset = queryset.filter(stock__code=stock_code)
            
            if date:
                queryset = queryset.filter(date=date)
            
            # 按日期倒序排列
            queryset = queryset.order_by('-report_date', 'stock__code')
            
            # 分页处理
            paginator = Paginator(queryset, page_size)
            if page > paginator.num_pages and paginator.num_pages > 0:
                return error_response("页码超出范围", 400)
            
            page_data = paginator.get_page(page)
            
            # 序列化数据
            serializer = BalanceSheetSerializer(page_data.object_list, many=True)
            
            return success_response({
                'total': paginator.count,
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'data': serializer.data
            }, "成功获取资产负债表数据")
            
        except ValueError as e:
            logger.error(f"参数格式错误: {str(e)}")
            return error_response(f"参数格式错误: {str(e)}", 400)
        except Exception as e:
            logger.error(f"获取资产负债表数据失败: {str(e)}")
            return error_response(f"获取资产负债表数据失败: {str(e)}", 500)


class IncomeStatementView(APIView):
    """
    利润表API视图
    功能：提供利润表数据的查询接口
    参数：
    - request: HTTP请求对象
    返回值：
    - JsonResponse: 调用success_response返回数据；失败时调用error_response返回错误信息
    事件：
    - 当查询参数错误时，记录日志并返回错误响应
    """
    
    def get(self, request, stock_code=None):
        """
        获取利润表数据
        
        路径参数:
        - stock_code: 股票代码（可选）
        
        查询参数:
        - date: 报告期，格式YYYYMMDD（可选）
        - page: 页码，默认1
        - page_size: 每页数量，默认20
        """
        try:
            # 获取查询参数
            date = request.query_params.get('date')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # 构建查询条件
            queryset = IncomeStatement.objects.select_related('stock').all()
            
            if stock_code:
                if not validate_stock_symbol(stock_code):
                    return error_response("无效的股票代码格式", 400)
                queryset = queryset.filter(stock__code=stock_code)
            
            if date:
                queryset = queryset.filter(date=date)
            
            # 按日期倒序排列
            queryset = queryset.order_by('-report_date', 'stock__code')
            
            # 分页处理
            paginator = Paginator(queryset, page_size)
            if page > paginator.num_pages and paginator.num_pages > 0:
                return error_response("页码超出范围", 400)
            
            page_data = paginator.get_page(page)
            
            # 序列化数据
            serializer = IncomeStatementSerializer(page_data.object_list, many=True)
            
            return success_response({
                'total': paginator.count,
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'data': serializer.data
            }, "成功获取利润表数据")
            
        except ValueError as e:
            logger.error(f"参数格式错误: {str(e)}")
            return error_response(f"参数格式错误: {str(e)}", 400)
        except Exception as e:
            logger.error(f"获取利润表数据失败: {str(e)}")
            return error_response(f"获取利润表数据失败: {str(e)}", 500)


class CashFlowStatementView(APIView):
    """
    现金流量表API视图
    功能：提供现金流量表数据的查询接口
    参数：
    - request: HTTP请求对象
    返回值：
    - JsonResponse: 调用success_response返回数据；失败时调用error_response返回错误信息
    事件：
    - 当查询参数错误时，记录日志并返回错误响应
    """
    
    def get(self, request, stock_code=None):
        """
        获取现金流量表数据
        
        路径参数:
        - stock_code: 股票代码（可选）
        
        查询参数:
        - date: 报告期，格式YYYYMMDD（可选）
        - page: 页码，默认1
        - page_size: 每页数量，默认20
        """
        try:
            # 获取查询参数
            date = request.query_params.get('date')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # 构建查询条件
            queryset = CashFlowStatement.objects.select_related('stock').all()
            
            if stock_code:
                if not validate_stock_symbol(stock_code):
                    return error_response("无效的股票代码格式", 400)
                queryset = queryset.filter(stock__code=stock_code)
            
            if date:
                queryset = queryset.filter(date=date)
            
            # 按日期倒序排列
            queryset = queryset.order_by('-report_date', 'stock__code')
            
            # 分页处理
            paginator = Paginator(queryset, page_size)
            if page > paginator.num_pages and paginator.num_pages > 0:
                return error_response("页码超出范围", 400)
            
            page_data = paginator.get_page(page)
            
            # 序列化数据
            serializer = CashFlowStatementSerializer(page_data.object_list, many=True)
            
            return success_response({
                'total': paginator.count,
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'data': serializer.data
            }, "成功获取现金流量表数据")
            
        except ValueError as e:
            logger.error(f"参数格式错误: {str(e)}")
            return error_response(f"参数格式错误: {str(e)}", 400)
        except Exception as e:
            logger.error(f"获取现金流量表数据失败: {str(e)}")
            return error_response(f"获取现金流量表数据失败: {str(e)}", 500)


class StockTagView(APIView):
    """
    股票标记API视图
    提供股票标记的增删改查功能
    支持多种标记因子的单选和多选查询
    """
    
    def get(self, request, tag_id=None):
        """
        功能：获取股票标记，支持单个标记查询和批量查询
        参数：
        - request(HttpRequest): 请求对象
        - tag_id(int, 可选): 标记ID，如果提供则获取单个标记
        返回值：
        - JsonResponse: 调用success_response返回数据；失败时调用error_response返回错误信息
        事件：
        - 当标记不存在时，记录日志并返回错误响应
        """
        try:
            if tag_id:
                # 获取单个标记
                stock_tag = stock_tag_service.get_stock_tag(tag_id)
                if not stock_tag:
                    return error_response(f"股票标记{tag_id}不存在", 404)
                
                serializer = StockTagSerializer(stock_tag)
                return success_response(serializer.data)
            else:
                # 批量查询标记
                query_serializer = StockTagQuerySerializer(data=request.query_params)
                if not query_serializer.is_valid():
                    return error_response(f"查询参数错误: {query_serializer.errors}", 400)
                
                # 执行查询
                result = stock_tag_service.query_stock_tags(**query_serializer.validated_data)
                
                # 序列化结果
                serializer = StockTagSerializer(result['results'], many=True)
                
                return success_response({
                    'total': result['total'],
                    'page': result['page'],
                    'page_size': result['page_size'],
                    'total_pages': result['total_pages'],
                    'has_next': result['has_next'],
                    'has_previous': result['has_previous'],
                    'data': serializer.data
                })
                
        except Exception as e:
            logger.error(f"获取股票标记失败: {str(e)}")
            return error_response(f"获取股票标记失败: {str(e)}", 500)
    
    def post(self, request):
        """
        功能：创建股票标记
        参数：
        - request(HttpRequest): 请求对象，包含标记数据
        返回值：
        - JsonResponse: 调用success_response返回创建的标记数据；失败时调用error_response返回错误信息
        事件：
        - 当数据验证失败时，记录日志并返回错误响应
        """
        try:
            serializer = StockTagSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response(f"数据验证失败: {serializer.errors}", 400)
            
            # 获取股票代码
            stock_code = request.data.get('stock_code')
            if not stock_code:
                return error_response("缺少股票代码", 400)
            
            # 创建标记
            stock_tag = stock_tag_service.create_stock_tag(stock_code, serializer.validated_data)
            
            # 返回创建的标记
            result_serializer = StockTagSerializer(stock_tag)
            return success_response(result_serializer.data, status_code=201)
            
        except ValueError as e:
            logger.error(f"创建股票标记失败: {str(e)}")
            return error_response(str(e), 400)
        except Exception as e:
            logger.error(f"创建股票标记失败: {str(e)}")
            return error_response(f"创建股票标记失败: {str(e)}", 500)
    
    def put(self, request, tag_id):
        """
        功能：更新股票标记
        参数：
        - request(HttpRequest): 请求对象，包含更新的标记数据
        - tag_id(int): 标记ID
        返回值：
        - JsonResponse: 调用success_response返回更新后的标记数据；失败时调用error_response返回错误信息
        事件：
        - 当标记不存在时，记录日志并返回错误响应
        """
        try:
            serializer = StockTagSerializer(data=request.data, partial=True)
            if not serializer.is_valid():
                return error_response(f"数据验证失败: {serializer.errors}", 400)
            
            # 更新标记
            stock_tag = stock_tag_service.update_stock_tag(tag_id, serializer.validated_data)
            
            # 返回更新后的标记
            result_serializer = StockTagSerializer(stock_tag)
            return success_response(result_serializer.data)
            
        except ValueError as e:
            logger.error(f"更新股票标记失败: {str(e)}")
            return error_response(str(e), 404)
        except Exception as e:
            logger.error(f"更新股票标记失败: {str(e)}")
            return error_response(f"更新股票标记失败: {str(e)}", 500)
    
    def delete(self, request, tag_id):
        """
        功能：删除股票标记
        参数：
        - request(HttpRequest): 请求对象
        - tag_id(int): 标记ID
        返回值：
        - JsonResponse: 调用success_response返回删除成功信息；失败时调用error_response返回错误信息
        事件：
        - 当标记不存在时，记录日志并返回错误响应
        """
        try:
            stock_tag_service.delete_stock_tag(tag_id)
            return success_response({"message": "删除成功"})
            
        except ValueError as e:
            logger.error(f"删除股票标记失败: {str(e)}")
            return error_response(str(e), 404)
        except Exception as e:
            logger.error(f"删除股票标记失败: {str(e)}")
            return error_response(f"删除股票标记失败: {str(e)}", 500)


class StockTagChoicesView(APIView):
    """
    股票标记选择项API视图
    提供所有标记因子的选择项
    """
    
    def get(self, request):
        """
        功能：获取所有标记因子的选择项
        参数：
        - request(HttpRequest): 请求对象
        返回值：
        - JsonResponse: 调用success_response返回选择项数据；失败时调用error_response返回错误信息
        事件：
        - 当获取选择项失败时，记录日志并返回错误响应
        """
        try:
            choices = stock_tag_service.get_tag_choices()
            return success_response(choices)
            
        except Exception as e:
            logger.error(f"获取标记因子选择项失败: {str(e)}")
            return error_response(f"获取标记因子选择项失败: {str(e)}", 500)


class StockTagByStockView(APIView):
    """
    按股票查询标记API视图
    获取指定股票的所有标记
    """
    
    def get(self, request, stock_code):
        """
        功能：获取指定股票的所有标记
        参数：
        - request(HttpRequest): 请求对象，查询参数包括：
          - start_date(str, 可选): 开始日期，格式：YYYY-MM-DD
          - end_date(str, 可选): 结束日期，格式：YYYY-MM-DD
        - stock_code(str): 股票代码
        返回值：
        - JsonResponse: 调用success_response返回标记数据；失败时调用error_response返回错误信息
        事件：
        - 当股票代码无效时，记录日志并返回错误响应
        """
        try:
            if not validate_stock_symbol(stock_code):
                return error_response(f"无效的股票代码: {stock_code}", 400)
            
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            # 获取股票标记
            stock_tags = stock_tag_service.get_stock_tags_by_stock(stock_code, start_date, end_date)
            
            # 序列化结果
            serializer = StockTagSerializer(stock_tags, many=True)
            
            return success_response({
                'stock_code': stock_code,
                'total': len(stock_tags),
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"获取股票{stock_code}标记失败: {str(e)}")
            return error_response(f"获取股票{stock_code}标记失败: {str(e)}", 500)
