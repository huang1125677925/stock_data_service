import logging
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from common.response import success_response, error_response
from .serializers import (
    EtfBasicSerializer,
    EtfDailySerializer,
    SuccessResponseEtfBasicListSerializer,
    SuccessResponseEtfDailyListSerializer,
    SuccessResponseEtfCorrelationSerializer,
    SuccessResponseEtfVolatilityListSerializer,
    ErrorResponseSerializer,
)
from .services import etf_service
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class EtfBasicListView(APIView):
    """
    ETF 基本信息查询接口（类视图）
    功能：查询ETF的基础信息，支持多条件筛选与分页。
    参数（Query）：
    - ts_code(str, 可选)：TS代码
    - index_code(str, 可选)：跟踪指数代码
    - exchange(str, 可选)：交易所
    - list_status(str, 可选)：上市状态（L/D/P）
    - mgr_name(str, 可选)：管理人名称（模糊匹配）
    - etf_type(str, 可选)：ETF类型（INDEX/BOND/CURRENCY/COMMODITY/SECTOR/THEME/CROSS_BORDER/OTHER）
    - name(str, 可选)：名称模糊匹配
    - page(int, 可选)：页码，默认1
    - page_size(int, 可选)：每页数量，默认20，最大100
    返回值：调用 success_response 返回分页数据；错误时调用 error_response。
    事件：当页码参数格式错误或超出范围时记录日志并返回错误响应。
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="ETF 基本信息查询",
        description=(
            "查询ETF的基础信息，支持多条件筛选与分页。\n"
            "参数（Query）：ts_code, index_code, exchange, list_status, mgr_name, etf_type, name, page, page_size。\n"
            "统一响应结构（success_response），data 为分页后的 items 列表及分页元信息。"
        ),
        tags=["etf"],
        responses={
            200: SuccessResponseEtfBasicListSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            filters = {
                'ts_code': request.query_params.get('ts_code'),
                'index_code': request.query_params.get('index_code'),
                'exchange': request.query_params.get('exchange'),
                'list_status': request.query_params.get('list_status'),
                'mgr_name': request.query_params.get('mgr_name'),
                'etf_type': request.query_params.get('etf_type'),
                'name': request.query_params.get('name'),
            }

            page = int(request.query_params.get('page', 1))
            page_size = max(1, min(int(request.query_params.get('page_size', 20)), 100))

            basics = etf_service.query_basic(filters)
            paginator = Paginator(basics, page_size)
            if paginator.count == 0:
                return error_response("没有搜索到相关ETF", 404)
            try:
                current_page = paginator.page(page)
            except (PageNotAnInteger, EmptyPage):
                logger.warning(f"ETF 基本信息页码超出范围: {page}")
                return error_response("页码超出范围", 400)

            serializer = EtfBasicSerializer(current_page.object_list, many=True)
            logger.info(f"ETF 基本信息总数 {paginator.count}，返回第 {page} 页 / 共 {paginator.num_pages} 页")

            return success_response({
                'total': paginator.count,
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'data': serializer.data,
            })
        except ValueError as e:
            logger.error(f"参数格式错误: {str(e)}")
            return error_response(f'参数格式错误: {str(e)}', 400)
        except Exception as e:
            logger.error(f"ETF 基本信息查询失败: {str(e)}")
            return error_response(f'ETF基本信息查询失败: {str(e)}', 500)


class EtfDailyListView(APIView):
    """
    ETF 日线行情查询接口（类视图）
    功能：按 ts_code 与日期范围查询 ETF 日线行情。
    参数（Query）：
    - ts_code(str, 必填)：TS代码
    - start_date(str, 可选)：开始日期，格式YYYY-MM-DD
    - end_date(str, 可选)：结束日期，格式YYYY-MM-DD
    返回值：调用 success_response 返回列表数据；错误时调用 error_response。
    事件：无
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="ETF 日线行情查询",
        description=(
            "按 ts_code 与日期范围查询 ETF 日线行情。\n"
            "参数（Query）：ts_code（必填），start_date（可选，YYYY-MM-DD），end_date（可选，YYYY-MM-DD）。\n"
            "统一响应结构（success_response），data 为行情列表。"
        ),
        tags=["etf"],
        responses={
            200: SuccessResponseEtfDailyListSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            ts_code = request.query_params.get('ts_code')
            if not ts_code:
                return error_response('参数缺失：ts_code 必填', 400)

            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')

            dailies = etf_service.query_daily(ts_code, start_date, end_date)
            serializer = EtfDailySerializer(dailies, many=True)
            return success_response(serializer.data)
        except Exception as e:
            logger.error(f"ETF 日线行情查询失败: {str(e)}")
            return error_response(f'ETF日线行情查询失败: {str(e)}', 500)


class EtfLatestDailyAllView(APIView):
    """
    ETF 最近一个交易日所有ETF日线行情查询接口（类视图）
    功能：首先获取数据库中最近一个交易日的日期，然后根据该日期读取所有ETF的日线交易数据并返回。
    参数（Query）：无
    返回值：调用 success_response 返回列表数据（data为 EtfDailySerializer[]）；错误时调用 error_response。
    事件：无
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="ETF 最近交易日所有ETF日线行情",
        description=(
            "获取数据库中最新的交易日日期，并返回该日期下所有ETF的日线行情列表。\n"
            "统一响应结构（success_response），data 为行情列表。"
        ),
        tags=["etf"],
        responses={
            200: SuccessResponseEtfDailyListSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            dailies = etf_service.query_daily_latest_all()
            if not dailies:
                return error_response('数据库中无ETF日线数据', 404)

            latest_date = dailies[0].trade_date
            serializer = EtfDailySerializer(dailies, many=True)
            # 按统一规范返回，并附加 trade_date 与总数元信息
            return success_response(
                serializer.data,
                trade_date=latest_date.strftime('%Y-%m-%d'),
                total=len(dailies),
            )
        except Exception as e:
            logger.error(f"ETF 最近交易日所有ETF行情查询失败: {str(e)}")
            return error_response(f'ETF最近交易日行情查询失败: {str(e)}', 500)


class EtfDailyCorrelationView(APIView):
    """
    ETF 列表日线收盘价相关性计算接口（类视图）
    功能：根据给定的ETF代码列表与时间范围，计算收盘价曲线的两两相关性，返回用于热力图展示的相关性矩阵。
    参数（Query）：
    - ts_codes(str, 必填)：ETF代码列表，逗号分隔
    - start_date(str, 可选)：开始日期，格式YYYY-MM-DD
    - end_date(str, 可选)：结束日期，格式YYYY-MM-DD
    返回值：调用 success_response 返回包含 labels 与 matrix 的载荷；错误时调用 error_response。
    事件：无
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="ETF 收盘价相关性矩阵",
        description=(
            "输入ETF代码列表与时间范围，计算收盘价曲线的Pearson相关性，两两组合生成相关性矩阵，用于热力图展示。\n"
            "参数（Query）：ts_codes（必填，逗号分隔），start_date（可选，YYYY-MM-DD），end_date（可选，YYYY-MM-DD）。\n"
            "统一响应结构（success_response），data包含labels与matrix。"
        ),
        tags=["etf"],
        responses={
            200: SuccessResponseEtfCorrelationSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            ts_codes_str = request.query_params.get('ts_codes')
            if not ts_codes_str:
                return error_response('参数缺失：ts_codes 必填（逗号分隔）', 400)
            ts_codes = [c.strip() for c in ts_codes_str.split(',') if c.strip()]
            # 去重保持顺序
            seen = set()
            ordered_codes = []
            for c in ts_codes:
                if c not in seen:
                    ordered_codes.append(c)
                    seen.add(c)
            if len(ordered_codes) < 2:
                return error_response('至少提供两个不同的ETF代码以计算相关性', 400)

            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')

            # 构建以交易日为索引、ETF代码为列的收盘价DataFrame
            series_list = []
            for code in ordered_codes:
                dailies = etf_service.query_daily(code, start_date, end_date)
                if not dailies:
                    # 无数据也加入空列，相关性将为null
                    series = pd.Series(dtype=float, name=code)
                    series_list.append(series)
                    continue
                dates = [d.trade_date for d in dailies]
                closes = [float(d.close) for d in dailies]
                s = pd.Series(data=closes, index=dates, name=code)
                series_list.append(s)

            if not series_list:
                return error_response('查询范围内无任何日线数据', 404)

            df = pd.concat(series_list, axis=1)
            # 计算Pearson相关系数矩阵（按列）
            corr_df = df.corr(method='pearson', min_periods=2)

            labels = list(corr_df.columns)
            # 将NaN转换为None，并进行适度四舍五入
            matrix = []
            for row_values in corr_df.values.tolist():
                row = []
                for v in row_values:
                    if v is None:
                        row.append(None)
                    else:
                        try:
                            # pandas会返回float或nan
                            if pd.isna(v):
                                row.append(None)
                            else:
                                row.append(round(float(v), 4))
                        except Exception:
                            row.append(None)
                matrix.append(row)

            payload = {
                'labels': labels,
                'matrix': matrix,
                'start_date': start_date,
                'end_date': end_date,
            }
            return success_response(payload)
        except Exception as e:
            logger.error(f"ETF 收盘价相关性计算失败: {str(e)}")
            return error_response(f'ETF收盘价相关性计算失败: {str(e)}', 500)


class EtfDailyVolatilityView(APIView):
    """
    ETF 列表区间波动度计算接口（类视图）
    功能：针对给定ETF列表与时间范围，计算收盘价曲线的波动度统计，
    包含最高/最低、最大下跌/上涨、最新价区间百分位、方差、均值、趋势与网格适配等。
    参数（Query）：
    - ts_codes(str, 必填)：ETF代码列表，逗号分隔
    - start_date(str, 可选)：开始日期，YYYY-MM-DD
    - end_date(str, 可选)：结束日期，YYYY-MM-DD
    - sample_n(int, 可选)：抽样点数量，用于趋势判定（>=10）
    返回值：统一 success_response，data.items 为ETF指标列表；错误时 error_response。
    事件：无
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="ETF 区间波动度统计",
        description=(
            "对ETF列表在区间内的收盘价曲线进行统计：最高/最低、最大下跌/上涨、"
            "最新价在区间的百分位、方差、均值、趋势（涨/跌/震荡）与网格交易适配。"
            "最小时间范围需≥1年；可选抽样 sample_n 参与趋势判定。"
        ),
        tags=["etf"],
        responses={
            200: SuccessResponseEtfVolatilityListSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            ts_codes_str = request.query_params.get('ts_codes')
            if not ts_codes_str:
                return error_response('参数缺失：ts_codes 必填（逗号分隔）', 400)
            ts_codes = [c.strip() for c in ts_codes_str.split(',') if c.strip()]
            seen = set()
            ordered_codes = []
            for c in ts_codes:
                if c not in seen:
                    ordered_codes.append(c)
                    seen.add(c)
            if len(ordered_codes) == 0:
                return error_response('未提供有效的ETF代码', 400)

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

            items = []
            skipped = 0
            for code in ordered_codes:
                dailies = etf_service.query_daily(code, sd.strftime('%Y-%m-%d'), ed.strftime('%Y-%m-%d'))
                if not dailies or len(dailies) < 2:
                    skipped += 1
                    continue

                dates = [d.trade_date for d in dailies]
                closes = np.array([float(d.close) for d in dailies], dtype=float)

                highest_idx = int(np.argmax(closes))
                lowest_idx = int(np.argmin(closes))
                highest_val = float(closes[highest_idx])
                lowest_val = float(closes[lowest_idx])
                highest_date = dates[highest_idx].strftime('%Y-%m-%d')
                lowest_date = dates[lowest_idx].strftime('%Y-%m-%d')

                # 最大下跌（MDD）
                running_max = -np.inf
                mdd = 0.0
                mdd_start = 0
                mdd_end = 0
                peak_idx = 0
                for i, price in enumerate(closes):
                    if price > running_max:
                        running_max = price
                        peak_idx = i
                    dd = price / running_max - 1.0
                    if dd < mdd:
                        mdd = dd
                        mdd_start = peak_idx
                        mdd_end = i
                mdd_days = mdd_end - mdd_start if mdd_end >= mdd_start else 0

                # 最大上涨
                running_min = np.inf
                max_rise = 0.0
                rise_start = 0
                rise_end = 0
                trough_idx = 0
                for i, price in enumerate(closes):
                    if price < running_min:
                        running_min = price
                        trough_idx = i
                    rise = price / running_min - 1.0
                    if rise > max_rise:
                        max_rise = rise
                        rise_start = trough_idx
                        rise_end = i
                rise_days = rise_end - rise_start if rise_end >= rise_start else 0

                latest_price = float(closes[-1])
                latest_date = dates[-1].strftime('%Y-%m-%d')
                denom = highest_val - lowest_val
                if denom > 0:
                    percentile = round(
                        (latest_price - lowest_val) / denom * 100.0, 2
                    )
                else:
                    percentile = 100.0

                mean_val = float(np.mean(closes))
                var_val = float(np.var(closes, ddof=1))
                std_val = float(np.std(closes, ddof=1))

                # 趋势判定（可抽样）
                idx = np.arange(len(closes), dtype=float)
                use_sample = False
                if sample_n and len(closes) > sample_n:
                    step = max(1, len(closes) // sample_n)
                    closes_fit = closes[::step]
                    idx_fit = idx[::step]
                    use_sample = True
                else:
                    closes_fit = closes
                    idx_fit = idx
                # 线性拟合
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
                    'ts_code': code,
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
            logger.error(f"ETF 区间波动度计算失败: {str(e)}")
            return error_response(f'ETF区间波动度计算失败: {str(e)}', 500)
