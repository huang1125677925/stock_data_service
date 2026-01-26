import logging
import calendar
import math
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from common.response import success_response, error_response
from common.tushare_proxy import call_tushare
from .serializers import (
    EtfBasicSerializer,
    EtfDailySerializer,
    SuccessResponseEtfBasicListSerializer,
    SuccessResponseEtfDailyListSerializer,
    SuccessResponseEtfCorrelationSerializer,
    SuccessResponseEtfVolatilityListSerializer,
    SuccessResponseIndexValuationSerializer,
    SuccessResponseIndexValuationRangeSerializer,
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
            # 1. 构造 Tushare 查询参数
            ts_params = {}
            # 直接映射的参数
            if request.query_params.get('ts_code'):
                ts_params['ts_code'] = request.query_params.get('ts_code')
            if request.query_params.get('index_code'):
                ts_params['index_code'] = request.query_params.get('index_code')
            if request.query_params.get('exchange'):
                ts_params['exchange'] = request.query_params.get('exchange')
            if request.query_params.get('list_status'):
                ts_params['list_status'] = request.query_params.get('list_status')
            # 参数名映射 mgr_name -> mgr
            if request.query_params.get('mgr_name'):
                ts_params['mgr'] = request.query_params.get('mgr_name')

            # 2. 调用 Tushare 接口
            # 字段列表参考文档和 Serializer 需求，尽量获取全量字段
            fields = "ts_code,csname,extname,cname,index_code,index_name,setup_date,list_date,delist_date,list_status,exchange,mgr_name,custod_name,mgt_fee,etf_type"
            
            resp = call_tushare("etf_basic", params=ts_params, fields=fields, use_query=False)
            if resp.get("code") != 200:
                return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))
            
            items = resp.get("data", {}).get("records", [])

            # 3. 内存过滤 (Tushare 接口不支持的参数)
            etf_type_filter = request.query_params.get('etf_type')
            name_filter = request.query_params.get('name')

            if etf_type_filter:
                items = [x for x in items if x.get('etf_type') == etf_type_filter]
            
            if name_filter:
                # 模糊匹配中文简称、扩位简称或全称
                items = [x for x in items if (name_filter in x.get('csname', '')) or (name_filter in x.get('extname', '')) or (name_filter in x.get('cname', ''))]

            # 4. 数据清洗 (日期格式转换 YYYYMMDD -> YYYY-MM-DD, 处理 NaN)
            from index_data.views import replace_nan # 复用 NaN 处理逻辑

            def format_date(date_str):
                if date_str and len(date_str) == 8:
                    return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                return date_str

            cleaned_items = []
            for item in items:
                # 格式化日期
                for date_field in ['setup_date', 'list_date', 'delist_date']:
                    if item.get(date_field):
                        item[date_field] = format_date(item[date_field])
                
                # 处理 NaN
                cleaned_item = replace_nan(item)
                cleaned_items.append(cleaned_item)

            # 5. 分页
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))

            paginator = Paginator(cleaned_items, page_size)
            if paginator.count == 0:
                if page == 1:
                     return error_response("没有搜索到相关ETF", 404)
                else:
                    pass

            try:
                current_page = paginator.page(page)
            except (PageNotAnInteger, EmptyPage):
                logger.warning(f"ETF 基本信息页码超出范围: {page}")
                return error_response("页码超出范围", 400)

            # 6. 序列化
            # 由于 items 已经是字典列表，且字段已清洗，直接传给 Serializer
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
            logger.error(f"查询ETF基本信息失败: {str(e)}")
            return error_response(f"查询ETF基本信息失败: {str(e)}", 500)


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


class IndexValuationView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="指数估值信息查询",
        description=(
            "输入指数代码，获取指数成分与权重（index_weight），再结合成分股每日指标（daily_basic），"
            "按权重聚合计算指数层面的估值指标（如PE/PB/PS/股息率等）。"
        ),
        tags=["etf"],
        parameters=[
            OpenApiParameter(
                name="index_code",
                description="指数代码（如 399300.SZ）",
                required=True,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="trade_date",
                description="交易日期（YYYYMMDD，可选；用于选择当月权重窗口，默认今天）",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="token",
                description="Tushare Token（可选，覆盖环境变量）",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: SuccessResponseIndexValuationSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            index_code = request.query_params.get("index_code") or request.query_params.get("ts_code")
            if not index_code:
                return error_response("参数缺失：index_code 必填", 400)

            token = request.query_params.get("token")
            trade_date = request.query_params.get("trade_date") or datetime.now().strftime("%Y%m%d")

            try:
                dt = datetime.strptime(trade_date, "%Y%m%d")
            except ValueError:
                return error_response("参数错误：trade_date 格式应为 YYYYMMDD", 400)

            month_last_day = calendar.monthrange(dt.year, dt.month)[1]
            month_start = f"{dt.year}{dt.month:02d}01"
            month_end = f"{dt.year}{dt.month:02d}{month_last_day:02d}"
            logger.info(f"指数估值查询: index_code={index_code}, trade_date={trade_date}, 权重窗口={month_start}-{month_end}")

            weights_resp = call_tushare(
                "index_weight",
                params={"index_code": index_code, "start_date": month_start, "end_date": month_end},
                fields="index_code,con_code,trade_date,weight",
                token=token,
                use_query=False,
            )
            if weights_resp.get("code") != 200:
                return error_response(
                    weights_resp.get("message", "获取指数成分权重失败"),
                    weights_resp.get("code", 500),
                    error=weights_resp.get("error"),
                )

            weight_records = (weights_resp.get("data") or {}).get("records") or []
            if not weight_records:
                fallback_start = (dt - timedelta(days=120)).strftime("%Y%m%d")
                logger.warning(f"指数权重当月为空，回退查询: index_code={index_code}, {fallback_start}-{trade_date}")
                fallback_resp = call_tushare(
                    "index_weight",
                    params={"index_code": index_code, "start_date": fallback_start, "end_date": trade_date},
                    fields="index_code,con_code,trade_date,weight",
                    token=token,
                    use_query=False,
                )
                if fallback_resp.get("code") != 200:
                    return error_response(
                        fallback_resp.get("message", "获取指数成分权重失败"),
                        fallback_resp.get("code", 500),
                        error=fallback_resp.get("error"),
                    )
                weight_records = (fallback_resp.get("data") or {}).get("records") or []

            if not weight_records:
                return error_response("未获取到指数成分与权重数据", 404)

            weight_trade_date = max(
                (r.get("trade_date") for r in weight_records if r.get("trade_date")),
                default=None,
            )
            if not weight_trade_date:
                return error_response("指数成分权重数据缺少 trade_date 字段", 500)

            weights = [r for r in weight_records if r.get("trade_date") == weight_trade_date]
            if not weights:
                return error_response("未找到可用的指数成分权重切片", 404)
            logger.info(f"选定权重日期: {weight_trade_date}, 成分数={len(weights)}")

            def to_float(v):
                if v is None:
                    return None
                if isinstance(v, (int, float)):
                    fv = float(v)
                    if math.isnan(fv) or math.isinf(fv):
                        return None
                    return fv
                s = str(v).strip()
                if s == "" or s.lower() == "nan":
                    return None
                try:
                    fv = float(s)
                    if math.isnan(fv) or math.isinf(fv):
                        return None
                    return fv
                except Exception:
                    return None

            fina_series_cache = {}

            def _get_fina_series(ts_code: str):
                if ts_code in fina_series_cache:
                    return fina_series_cache[ts_code]
                resp = call_tushare(
                    "fina_indicator",
                    params={"ts_code": ts_code},
                    fields="ts_code,end_date,profit_dedt",
                    token=token,
                    use_query=False,
                )
                if resp.get("code") != 200:
                    fina_series_cache[ts_code] = None
                    return None
                recs = (resp.get("data") or {}).get("records") or []
                series = []
                for r in recs:
                    ed = r.get("end_date")
                    pd = to_float(r.get("profit_dedt"))
                    if ed and pd is not None:
                        series.append({"end_date": str(ed), "profit_dedt": pd})
                series.sort(key=lambda x: x["end_date"], reverse=True)
                fina_series_cache[ts_code] = series if series else None
                return fina_series_cache[ts_code]

            def _calc_profit_dedt(ts_code: str, trade_date_str: str):
                series = _get_fina_series(ts_code)
                if not series:
                    return None
                picked = None
                for r in series:
                    if r["end_date"] <= trade_date_str:
                        picked = r
                        break
                if not picked:
                    picked = series[0]
                end_date = picked["end_date"]
                profit_dedt = picked["profit_dedt"]
                ttm_profit_dedt = profit_dedt
                if len(end_date) == 8:
                    mmdd = end_date[4:8]
                    if mmdd != "1231":
                        y = int(end_date[0:4])
                        prev_year_end = f"{y - 1}1231"
                        prev_year_same = f"{y - 1}{mmdd}"
                        m = {r["end_date"]: r["profit_dedt"] for r in series}
                        if prev_year_end in m and prev_year_same in m:
                            ttm_profit_dedt = profit_dedt + m[prev_year_end] - m[prev_year_same]
                return {
                    "end_date": end_date,
                    "profit_dedt": profit_dedt,
                    "profit_dedt_ttm": ttm_profit_dedt,
                }

            weight_sum = 0.0
            for r in weights:
                w = to_float(r.get("weight"))
                if w is not None and w > 0:
                    weight_sum += w
            logger.info(f"权重求和: weight_sum={round(weight_sum, 6)}")
            if weight_sum and (weight_sum < 99 or weight_sum > 101):
                logger.warning(f"权重求和异常: index_code={index_code}, weight_sum={round(weight_sum, 6)}")

            latest_trade_date = weight_trade_date
            try:
                cal_resp = call_tushare(
                    "trade_cal",
                    params={
                        "is_open": 1,
                        "start_date": weight_trade_date,
                        "end_date": datetime.now().strftime("%Y%m%d"),
                    },
                    fields="cal_date,is_open",
                    token=token,
                    use_query=False,
                )
                if cal_resp.get("code") == 200:
                    cal_records = (cal_resp.get("data") or {}).get("records") or []
                    open_dates = [r.get("cal_date") for r in cal_records if str(r.get("is_open")) in ("1", "True", "true", "1.0")]
                    if open_dates:
                        latest_trade_date = max(open_dates)
            except Exception as e:
                logger.warning(f"交易日历查询失败，使用权重日期: {weight_trade_date}, err={e}")
            logger.info(f"每日指标使用交易日: {latest_trade_date}")

            daily_resp = call_tushare(
                "daily_basic",
                params={"trade_date": latest_trade_date},
                fields="ts_code,trade_date,turnover_rate,volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,dv_ttm,total_mv,circ_mv",
                token=token,
                use_query=False,
            )
            if daily_resp.get("code") != 200:
                return error_response(
                    daily_resp.get("message", "获取成分股每日指标失败"),
                    daily_resp.get("code", 500),
                    error=daily_resp.get("error"),
                )

            daily_records = (daily_resp.get("data") or {}).get("records") or []
            if not daily_records:
                return error_response("未获取到成分股每日指标数据", 404)
            logger.info(f"成分股每日指标记录数: {len(daily_records)}")

            daily_map = {}
            for r in daily_records:
                ts_code = r.get("ts_code")
                if ts_code:
                    daily_map[ts_code] = r

            ratio_keys = [
                "pe",
                "pe_ttm",
                "pb",
                "ps",
                "ps_ttm",
                "dv_ratio",
                "dv_ttm",
                "turnover_rate",
                "volume_ratio",
            ]
            sum_keys = ["total_mv", "circ_mv"]
            numerators = {k: 0.0 for k in ratio_keys}
            denoms = {k: 0.0 for k in ratio_keys}
            sums = {k: 0.0 for k in sum_keys}
            sums_count = {k: 0 for k in sum_keys}
            pe_harm_num = 0.0
            pe_harm_den = 0.0
            pe_ttm_harm_num = 0.0
            pe_ttm_harm_den = 0.0
            pb_harm_num = 0.0
            pb_harm_den = 0.0
            ps_harm_num = 0.0
            ps_harm_den = 0.0
            ps_ttm_harm_num = 0.0
            ps_ttm_harm_den = 0.0
            dv_ratio_mv_sum = 0.0
            dv_ttm_mv_sum = 0.0
            mv_sum_for_div = 0.0
            mv_total = 0.0
            mv_pe = 0.0
            mv_pe_ttm = 0.0
            mv_pb = 0.0
            mv_ps = 0.0
            mv_ps_ttm = 0.0

            details = []

            matched = 0
            missing_daily_basic = 0
            pe_need_fill_cnt = 0
            pe_ttm_need_fill_cnt = 0
            pe_fill_ok_cnt = 0
            pe_ttm_fill_ok_cnt = 0
            pe_fill_fail_no_profit_cnt = 0
            pe_ttm_fill_fail_no_profit_cnt = 0
            pe_fill_fail_profit_none_cnt = 0
            pe_ttm_fill_fail_profit_none_cnt = 0
            pe_fill_fail_profit_zero_cnt = 0
            pe_ttm_fill_fail_profit_zero_cnt = 0
            pe_fill_neg_profit_cnt = 0
            pe_ttm_fill_neg_profit_cnt = 0
            pe_fill_fail_cap_nonpos_cnt = 0
            pe_ttm_fill_fail_cap_nonpos_cnt = 0
            pe_impute_sample = []

            for wr in weights:
                con_code = wr.get("con_code")
                w = to_float(wr.get("weight"))
                if not con_code or w is None or w <= 0:
                    continue

                stock = daily_map.get(con_code)
                if not stock:
                    missing_daily_basic += 1
                    continue

                matched += 1
                wf = w / 100.0
                mv_used_val = None
                mv_type = None
                cmv = to_float(stock.get("circ_mv"))
                tmv = to_float(stock.get("total_mv"))
                if tmv is not None and tmv > 0:
                    mv_used_val = tmv
                    mv_type = "total_mv"
                elif cmv is not None and cmv > 0:
                    mv_used_val = cmv
                    mv_type = "circ_mv"

                pe_raw = to_float(stock.get("pe"))
                pe_ttm_raw = to_float(stock.get("pe_ttm"))
                pe_used = pe_raw if (pe_raw is not None and pe_raw > 0) else None
                pe_ttm_used = pe_ttm_raw if (pe_ttm_raw is not None and pe_ttm_raw > 0) else None
                pe_source = "daily_basic" if pe_used is not None else None
                pe_ttm_source = "daily_basic" if pe_ttm_used is not None else None
                profit_info = None
                pe_need_fill = pe_used is None
                pe_ttm_need_fill = pe_ttm_used is None
                if pe_need_fill:
                    pe_need_fill_cnt += 1
                if pe_ttm_need_fill:
                    pe_ttm_need_fill_cnt += 1

                for k in ratio_keys:
                    v = to_float(stock.get(k))
                    if v is None:
                        continue
                    numerators[k] += wf * v
                    denoms[k] += wf
                for k in sum_keys:
                    v = to_float(stock.get(k))
                    if v is None:
                        continue
                    sums[k] += v
                    sums_count[k] += 1
                if mv_used_val is not None and mv_used_val > 0:
                    mv_total += mv_used_val
                    cap_for_pe = tmv if (tmv is not None and tmv > 0) else mv_used_val
                    pe_fill_reason = None
                    pe_ttm_fill_reason = None
                    if (pe_need_fill or pe_ttm_need_fill) and (cap_for_pe is None or cap_for_pe <= 0):
                        if pe_need_fill:
                            pe_fill_fail_cap_nonpos_cnt += 1
                            pe_fill_reason = "cap_nonpos"
                        if pe_ttm_need_fill:
                            pe_ttm_fill_fail_cap_nonpos_cnt += 1
                            pe_ttm_fill_reason = "cap_nonpos"
                    elif (pe_need_fill or pe_ttm_need_fill) and cap_for_pe is not None and cap_for_pe > 0:
                        profit_info = _calc_profit_dedt(con_code, latest_trade_date)
                        if not profit_info:
                            if pe_need_fill:
                                pe_fill_fail_no_profit_cnt += 1
                                pe_fill_reason = "no_profit_info"
                            if pe_ttm_need_fill:
                                pe_ttm_fill_fail_no_profit_cnt += 1
                                pe_ttm_fill_reason = "no_profit_info"
                        else:
                            pd = profit_info.get("profit_dedt")
                            pd_ttm = profit_info.get("profit_dedt_ttm")
                            if pe_need_fill:
                                if pd is None:
                                    pe_fill_fail_profit_none_cnt += 1
                                    pe_fill_reason = "profit_none"
                                elif pd == 0:
                                    pe_fill_fail_profit_zero_cnt += 1
                                    pe_fill_reason = "profit_zero"
                                else:
                                    pe_used = (cap_for_pe * 10000.0) / pd
                                    pe_source = "fina_indicator"
                                    pe_fill_ok_cnt += 1
                                    if pd < 0:
                                        pe_fill_neg_profit_cnt += 1
                                        pe_fill_reason = "profit_negative"
                            if pe_ttm_need_fill:
                                if pd_ttm is None:
                                    pe_ttm_fill_fail_profit_none_cnt += 1
                                    pe_ttm_fill_reason = "profit_ttm_none"
                                elif pd_ttm == 0:
                                    pe_ttm_fill_fail_profit_zero_cnt += 1
                                    pe_ttm_fill_reason = "profit_ttm_zero"
                                else:
                                    pe_ttm_used = (cap_for_pe * 10000.0) / pd_ttm
                                    pe_ttm_source = "fina_indicator"
                                    pe_ttm_fill_ok_cnt += 1
                                    if pd_ttm < 0:
                                        pe_ttm_fill_neg_profit_cnt += 1
                                        pe_ttm_fill_reason = "profit_ttm_negative"

                    if (pe_need_fill or pe_ttm_need_fill) and len(pe_impute_sample) < 20:
                        pe_impute_sample.append({
                            "ts_code": con_code,
                            "trade_date": latest_trade_date,
                            "mv_type": mv_type,
                            "total_mv": tmv,
                            "circ_mv": cmv,
                            "cap_for_pe": cap_for_pe,
                            "profit_end_date": profit_info.get("end_date") if profit_info else None,
                            "profit_dedt": profit_info.get("profit_dedt") if profit_info else None,
                            "profit_dedt_ttm": profit_info.get("profit_dedt_ttm") if profit_info else None,
                            "pe_raw": pe_raw,
                            "pe_ttm_raw": pe_ttm_raw,
                            "pe_need_fill": pe_need_fill,
                            "pe_ttm_need_fill": pe_ttm_need_fill,
                            "pe_calc": pe_used,
                            "pe_ttm_calc": pe_ttm_used,
                            "pe_source": pe_source,
                            "pe_ttm_source": pe_ttm_source,
                            "pe_fill_reason": pe_fill_reason,
                            "pe_ttm_fill_reason": pe_ttm_fill_reason,
                        })

                    if pe_used is not None and pe_used > 0:
                        pe_harm_num += mv_used_val
                        pe_harm_den += mv_used_val / pe_used
                        mv_pe += mv_used_val
                    if pe_ttm_used is not None and pe_ttm_used > 0:
                        pe_ttm_harm_num += mv_used_val
                        pe_ttm_harm_den += mv_used_val / pe_ttm_used
                        mv_pe_ttm += mv_used_val
                    if (pv := to_float(stock.get("pb"))) is not None and pv > 0:
                        pb_harm_num += mv_used_val
                        pb_harm_den += mv_used_val / pv
                        mv_pb += mv_used_val
                    if (pv := to_float(stock.get("ps"))) is not None and pv > 0:
                        ps_harm_num += mv_used_val
                        ps_harm_den += mv_used_val / pv
                        mv_ps += mv_used_val
                    if (pv := to_float(stock.get("ps_ttm"))) is not None and pv > 0:
                        ps_ttm_harm_num += mv_used_val
                        ps_ttm_harm_den += mv_used_val / pv
                        mv_ps_ttm += mv_used_val
                    dv_val = to_float(stock.get("dv_ratio"))
                    if dv_val is not None and dv_val >= 0:
                        dv_ratio_mv_sum += mv_used_val * dv_val
                    dv_ttm_val = to_float(stock.get("dv_ttm"))
                    if dv_ttm_val is not None and dv_ttm_val >= 0:
                        dv_ttm_mv_sum += mv_used_val * dv_ttm_val
                    mv_sum_for_div += mv_used_val

                details.append({
                    "ts_code": con_code,
                    "weight": round(w, 6),
                    "pe": pe_raw,
                    "pe_ttm": pe_ttm_raw,
                    "pe_filled": round(pe_used, 6) if (pe_used is not None and pe_source == "fina_indicator") else None,
                    "pe_ttm_filled": round(pe_ttm_used, 6) if (pe_ttm_used is not None and pe_ttm_source == "fina_indicator") else None,
                    "pe_source": pe_source,
                    "pe_ttm_source": pe_ttm_source,
                    "profit_end_date": profit_info.get("end_date") if profit_info else None,
                    "profit_dedt": round(float(profit_info.get("profit_dedt")), 6) if (profit_info and profit_info.get("profit_dedt") is not None) else None,
                    "profit_dedt_ttm": round(float(profit_info.get("profit_dedt_ttm")), 6) if (profit_info and profit_info.get("profit_dedt_ttm") is not None) else None,
                    "pb": to_float(stock.get("pb")),
                    "ps": to_float(stock.get("ps")),
                    "ps_ttm": to_float(stock.get("ps_ttm")),
                    "dv_ratio": to_float(stock.get("dv_ratio")),
                    "dv_ttm": to_float(stock.get("dv_ttm")),
                    "total_mv": tmv,
                    "circ_mv": cmv,
                    "mv_used": mv_used_val,
                    "mv_type": mv_type,
                })
            logger.info(f"匹配到成分估值: matched={matched}, 缺失每日指标={missing_daily_basic}")
            logger.info(
                "PE补全统计: index_code=%s, trade_date=%s, pe_need_fill=%s, pe_fill_ok=%s, "
                "pe_fail_no_profit=%s, pe_fail_profit_none=%s, pe_fail_profit_zero=%s, pe_neg_profit=%s, "
                "pe_fail_cap_nonpos=%s, "
                "pe_ttm_need_fill=%s, pe_ttm_fill_ok=%s, pe_ttm_fail_no_profit=%s, "
                "pe_ttm_fail_profit_none=%s, pe_ttm_fail_profit_zero=%s, pe_ttm_neg_profit=%s, "
                "pe_ttm_fail_cap_nonpos=%s",
                index_code,
                latest_trade_date,
                pe_need_fill_cnt,
                pe_fill_ok_cnt,
                pe_fill_fail_no_profit_cnt,
                pe_fill_fail_profit_none_cnt,
                pe_fill_fail_profit_zero_cnt,
                pe_fill_neg_profit_cnt,
                pe_fill_fail_cap_nonpos_cnt,
                pe_ttm_need_fill_cnt,
                pe_ttm_fill_ok_cnt,
                pe_ttm_fill_fail_no_profit_cnt,
                pe_ttm_fill_fail_profit_none_cnt,
                pe_ttm_fill_fail_profit_zero_cnt,
                pe_ttm_fill_neg_profit_cnt,
                pe_ttm_fill_fail_cap_nonpos_cnt,
            )
            for s in pe_impute_sample:
                logger.info(
                    "PE补全明细: ts_code=%s, trade_date=%s, mv_type=%s, cap_for_pe=%s(万元), "
                    "profit_end_date=%s, profit_dedt=%s(元), profit_dedt_ttm=%s(元), "
                    "pe_need_fill=%s, pe_raw=%s, pe_source=%s, pe_calc=%s, pe_reason=%s, "
                    "pe_ttm_need_fill=%s, pe_ttm_raw=%s, pe_ttm_source=%s, pe_ttm_calc=%s, pe_ttm_reason=%s",
                    s.get("ts_code"),
                    s.get("trade_date"),
                    s.get("mv_type"),
                    s.get("cap_for_pe"),
                    s.get("profit_end_date"),
                    s.get("profit_dedt"),
                    s.get("profit_dedt_ttm"),
                    s.get("pe_need_fill"),
                    s.get("pe_raw"),
                    s.get("pe_source"),
                    s.get("pe_calc"),
                    s.get("pe_fill_reason"),
                    s.get("pe_ttm_need_fill"),
                    s.get("pe_ttm_raw"),
                    s.get("pe_ttm_source"),
                    s.get("pe_ttm_calc"),
                    s.get("pe_ttm_fill_reason"),
                )
            logger.info(f"谐均分母计数: pe={pe_harm_den:.6f}, pe_ttm={pe_ttm_harm_den:.6f}, pb={pb_harm_den:.6f}, ps={ps_harm_den:.6f}, ps_ttm={ps_ttm_harm_den:.6f}")
            if mv_total > 0:
                logger.info(
                    "估值覆盖率: "
                    f"mv_total={round(mv_total, 6)}, "
                    f"pe={round(mv_pe / mv_total, 6)}, "
                    f"pe_ttm={round(mv_pe_ttm / mv_total, 6)}, "
                    f"pb={round(mv_pb / mv_total, 6)}, "
                    f"ps={round(mv_ps / mv_total, 6)}, "
                    f"ps_ttm={round(mv_ps_ttm / mv_total, 6)}"
                )

            metrics = {}
            for k in ratio_keys:
                if denoms[k] > 0:
                    val = numerators[k] / denoms[k]
                    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                        metrics[k] = None
                    else:
                        metrics[k] = round(float(val), 6)
                else:
                    metrics[k] = None
            for k in sum_keys:
                if sums_count[k] > 0:
                    val = sums[k]
                    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                        metrics[k] = None
                    else:
                        metrics[k] = round(float(val), 6)
                else:
                    metrics[k] = None
            min_cov = 0.8
            pe_cov = (mv_pe / mv_total) if mv_total > 0 else 0.0
            pe_ttm_cov = (mv_pe_ttm / mv_total) if mv_total > 0 else 0.0
            pb_cov = (mv_pb / mv_total) if mv_total > 0 else 0.0
            ps_cov = (mv_ps / mv_total) if mv_total > 0 else 0.0
            ps_ttm_cov = (mv_ps_ttm / mv_total) if mv_total > 0 else 0.0
            if pe_harm_den > 0 and pe_cov >= min_cov:
                metrics["pe"] = round(pe_harm_num / pe_harm_den, 6)
            else:
                metrics["pe"] = None
            if pe_ttm_harm_den > 0 and pe_ttm_cov >= min_cov:
                metrics["pe_ttm"] = round(pe_ttm_harm_num / pe_ttm_harm_den, 6)
            else:
                metrics["pe_ttm"] = None
            if pb_harm_den > 0 and pb_cov >= min_cov:
                metrics["pb"] = round(pb_harm_num / pb_harm_den, 6)
            else:
                metrics["pb"] = None
            if ps_harm_den > 0 and ps_cov >= min_cov:
                metrics["ps"] = round(ps_harm_num / ps_harm_den, 6)
            else:
                metrics["ps"] = None
            if ps_ttm_harm_den > 0 and ps_ttm_cov >= min_cov:
                metrics["ps_ttm"] = round(ps_ttm_harm_num / ps_ttm_harm_den, 6)
            else:
                metrics["ps_ttm"] = None
            if mv_sum_for_div > 0:
                metrics["dv_ratio"] = round(dv_ratio_mv_sum / mv_sum_for_div, 6)
                metrics["dv_ttm"] = round(dv_ttm_mv_sum / mv_sum_for_div, 6)
            else:
                metrics["dv_ratio"] = None
                metrics["dv_ttm"] = None
            if mv_total > 0 and (pe_cov < min_cov or pb_cov < min_cov):
                logger.warning(
                    f"估值覆盖率偏低，返回None以避免误导: index_code={index_code}, date={weight_trade_date}, "
                    f"mv_total={round(mv_total, 6)}, pe_cov={round(pe_cov, 6)}, pb_cov={round(pb_cov, 6)}"
                )
            logger.info(f"指数估值指标计算完成: index_code={index_code}, date={weight_trade_date}, metrics={metrics}")

            idx_basic_resp = call_tushare(
                "index_basic",
                params={"ts_code": index_code},
                fields="ts_code,name,fullname,market,publisher,category",
                token=token,
                use_query=False,
            )
            index_basic = None
            if idx_basic_resp.get("code") == 200:
                records = (idx_basic_resp.get("data") or {}).get("records") or []
                if records:
                    index_basic = records[0]
            logger.info(f"指数基础信息: index_code={index_code}, basic={'有' if index_basic else '无'}")

            payload = {
                "index_code": index_code,
                "trade_date": weight_trade_date,
                "index_basic": index_basic,
                "constituents": {
                    "total": len(weights),
                    "matched": matched,
                    "missing_daily_basic": missing_daily_basic,
                    "weight_sum": round(weight_sum, 6) if weight_sum else None,
                    "mv_covered": round(mv_total, 6) if mv_total else None,
                    "pe_coverage": round(pe_cov, 6) if mv_total else None,
                    "pe_ttm_coverage": round(pe_ttm_cov, 6) if mv_total else None,
                    "pb_coverage": round(pb_cov, 6) if mv_total else None,
                    "ps_coverage": round(ps_cov, 6) if mv_total else None,
                    "ps_ttm_coverage": round(ps_ttm_cov, 6) if mv_total else None,
                },
                "metrics": metrics,
                "details": details,
            }
            return success_response(payload)
        except Exception as e:
            logger.error(f"指数估值信息查询失败: {str(e)}")
            return error_response(f"指数估值信息查询失败: {str(e)}", 500)


class IndexValuationIncomeView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="指数估值信息查询（利润表PE）",
        description=(
            "输入指数代码，获取指数成分与权重（index_weight），再结合成分股每日指标（daily_basic）与利润表（income），"
            "按权重聚合计算指数层面的估值指标，其中PE按市值与利润表净利润的权重汇总计算。"
        ),
        tags=["etf"],
        parameters=[
            OpenApiParameter(
                name="index_code",
                description="指数代码（如 399300.SZ）",
                required=True,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="trade_date",
                description="交易日期（YYYYMMDD，可选；用于选择当月权重窗口，默认今天）",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="token",
                description="Tushare Token（可选，覆盖环境变量）",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: SuccessResponseIndexValuationSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            index_code = request.query_params.get("index_code") or request.query_params.get("ts_code")
            if not index_code:
                return error_response("参数缺失：index_code 必填", 400)

            token = request.query_params.get("token")
            trade_date = request.query_params.get("trade_date") or datetime.now().strftime("%Y%m%d")

            try:
                dt = datetime.strptime(trade_date, "%Y%m%d")
            except ValueError:
                return error_response("参数错误：trade_date 格式应为 YYYYMMDD", 400)

            month_last_day = calendar.monthrange(dt.year, dt.month)[1]
            month_start = f"{dt.year}{dt.month:02d}01"
            month_end = f"{dt.year}{dt.month:02d}{month_last_day:02d}"
            logger.info(f"指数估值查询(利润表PE): index_code={index_code}, trade_date={trade_date}, 权重窗口={month_start}-{month_end}")

            weights_resp = call_tushare(
                "index_weight",
                params={"index_code": index_code, "start_date": month_start, "end_date": month_end},
                fields="index_code,con_code,trade_date,weight",
                token=token,
                use_query=False,
            )
            if weights_resp.get("code") != 200:
                return error_response(
                    weights_resp.get("message", "获取指数成分权重失败"),
                    weights_resp.get("code", 500),
                    error=weights_resp.get("error"),
                )

            weight_records = (weights_resp.get("data") or {}).get("records") or []
            if not weight_records:
                fallback_start = (dt - timedelta(days=120)).strftime("%Y%m%d")
                logger.warning(f"指数权重当月为空，回退查询: index_code={index_code}, {fallback_start}-{trade_date}")
                fallback_resp = call_tushare(
                    "index_weight",
                    params={"index_code": index_code, "start_date": fallback_start, "end_date": trade_date},
                    fields="index_code,con_code,trade_date,weight",
                    token=token,
                    use_query=False,
                )
                if fallback_resp.get("code") != 200:
                    return error_response(
                        fallback_resp.get("message", "获取指数成分权重失败"),
                        fallback_resp.get("code", 500),
                        error=fallback_resp.get("error"),
                    )
                weight_records = (fallback_resp.get("data") or {}).get("records") or []

            if not weight_records:
                return error_response("未获取到指数成分与权重数据", 404)

            weight_trade_date = max(
                (r.get("trade_date") for r in weight_records if r.get("trade_date")),
                default=None,
            )
            if not weight_trade_date:
                return error_response("指数成分权重数据缺少 trade_date 字段", 500)

            weights = [r for r in weight_records if r.get("trade_date") == weight_trade_date]
            if not weights:
                return error_response("未找到可用的指数成分权重切片", 404)
            logger.info(f"选定权重日期: {weight_trade_date}, 成分数={len(weights)}")

            def to_float(v):
                if v is None:
                    return None
                if isinstance(v, (int, float)):
                    fv = float(v)
                    if math.isnan(fv) or math.isinf(fv):
                        return None
                    return fv
                s = str(v).strip()
                if s == "" or s.lower() == "nan":
                    return None
                try:
                    fv = float(s)
                    if math.isnan(fv) or math.isinf(fv):
                        return None
                    return fv
                except Exception:
                    return None

            weight_sum = 0.0
            for r in weights:
                w = to_float(r.get("weight"))
                if w is not None and w > 0:
                    weight_sum += w
            logger.info(f"权重求和: weight_sum={round(weight_sum, 6)}")
            if weight_sum and (weight_sum < 99 or weight_sum > 101):
                logger.warning(f"权重求和异常: index_code={index_code}, weight_sum={round(weight_sum, 6)}")

            latest_trade_date = weight_trade_date
            try:
                cal_resp = call_tushare(
                    "trade_cal",
                    params={
                        "is_open": 1,
                        "start_date": weight_trade_date,
                        "end_date": datetime.now().strftime("%Y%m%d"),
                    },
                    fields="cal_date,is_open",
                    token=token,
                    use_query=False,
                )
                if cal_resp.get("code") == 200:
                    cal_records = (cal_resp.get("data") or {}).get("records") or []
                    open_dates = [r.get("cal_date") for r in cal_records if str(r.get("is_open")) in ("1", "True", "true", "1.0")]
                    if open_dates:
                        latest_trade_date = max(open_dates)
            except Exception as e:
                logger.warning(f"交易日历查询失败，使用权重日期: {weight_trade_date}, err={e}")
            logger.info(f"每日指标使用交易日: {latest_trade_date}")

            daily_resp = call_tushare(
                "daily_basic",
                params={"trade_date": latest_trade_date},
                fields="ts_code,trade_date,turnover_rate,volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,dv_ttm,total_mv,circ_mv",
                token=token,
                use_query=False,
            )
            if daily_resp.get("code") != 200:
                return error_response(
                    daily_resp.get("message", "获取成分股每日指标失败"),
                    daily_resp.get("code", 500),
                    error=daily_resp.get("error"),
                )

            daily_records = (daily_resp.get("data") or {}).get("records") or []
            if not daily_records:
                return error_response("未获取到成分股每日指标数据", 404)
            logger.info(f"成分股每日指标记录数: {len(daily_records)}")

            daily_map = {}
            for r in daily_records:
                ts_code = r.get("ts_code")
                if ts_code:
                    daily_map[ts_code] = r

            income_cache = {}

            def _get_income_series(ts_code: str):
                if ts_code in income_cache:
                    return income_cache[ts_code]
                resp = call_tushare(
                    "income",
                    params={"ts_code": ts_code},
                    fields="ts_code,end_date,n_income_attr_p",
                    token=token,
                    use_query=False,
                )
                if resp.get("code") != 200:
                    income_cache[ts_code] = None
                    return None
                recs = (resp.get("data") or {}).get("records") or []
                series = []
                for r in recs:
                    ed = r.get("end_date")
                    profit = to_float(r.get("n_income_attr_p"))
                    if ed and profit is not None:
                        series.append({"end_date": str(ed), "n_income_attr_p": profit})
                series.sort(key=lambda x: x["end_date"], reverse=True)
                income_cache[ts_code] = series if series else None
                return income_cache[ts_code]

            def _calc_income_ttm(ts_code: str, trade_date_str: str):
                series = _get_income_series(ts_code)
                if not series:
                    return None
                picked = None
                for r in series:
                    if r["end_date"] <= trade_date_str:
                        picked = r
                        break
                if not picked:
                    picked = series[0]
                end_date = picked["end_date"]
                profit = picked["n_income_attr_p"]
                ttm_profit = profit
                if len(end_date) == 8:
                    mmdd = end_date[4:8]
                    if mmdd != "1231":
                        y = int(end_date[0:4])
                        prev_year_end = f"{y - 1}1231"
                        prev_year_same = f"{y - 1}{mmdd}"
                        m = {r["end_date"]: r["n_income_attr_p"] for r in series}
                        if prev_year_end in m and prev_year_same in m:
                            ttm_profit = profit + m[prev_year_end] - m[prev_year_same]
                return {
                    "end_date": end_date,
                    "n_income_attr_p": profit,
                    "n_income_attr_p_ttm": ttm_profit,
                }

            unique_codes = []
            seen_codes = set()
            for wr in weights:
                con_code = wr.get("con_code")
                w = to_float(wr.get("weight"))
                if not con_code or w is None or w <= 0:
                    continue
                if con_code not in seen_codes:
                    unique_codes.append(con_code)
                    seen_codes.add(con_code)

            income_profit_map = {}
            income_missing = 0
            for code in unique_codes:
                info = _calc_income_ttm(code, latest_trade_date)
                income_profit_map[code] = info
                if not info:
                    income_missing += 1

            ratio_keys = [
                "pe_ttm",
                "pb",
                "ps",
                "ps_ttm",
                "dv_ratio",
                "dv_ttm",
                "turnover_rate",
                "volume_ratio",
            ]
            sum_keys = ["total_mv", "circ_mv"]
            numerators = {k: 0.0 for k in ratio_keys}
            denoms = {k: 0.0 for k in ratio_keys}
            sums = {k: 0.0 for k in sum_keys}
            sums_count = {k: 0 for k in sum_keys}
            pe_income_num = 0.0
            pe_income_den = 0.0
            mv_pe_income = 0.0
            pe_ttm_harm_num = 0.0
            pe_ttm_harm_den = 0.0
            pb_harm_num = 0.0
            pb_harm_den = 0.0
            ps_harm_num = 0.0
            ps_harm_den = 0.0
            ps_ttm_harm_num = 0.0
            ps_ttm_harm_den = 0.0
            dv_ratio_mv_sum = 0.0
            dv_ttm_mv_sum = 0.0
            mv_sum_for_div = 0.0
            mv_total = 0.0
            mv_pe_ttm = 0.0
            mv_pb = 0.0
            mv_ps = 0.0
            mv_ps_ttm = 0.0

            details = []

            matched = 0
            missing_daily_basic = 0

            for wr in weights:
                con_code = wr.get("con_code")
                w = to_float(wr.get("weight"))
                if not con_code or w is None or w <= 0:
                    continue

                stock = daily_map.get(con_code)
                if not stock:
                    missing_daily_basic += 1
                    continue

                matched += 1
                wf = w / 100.0
                mv_used_val = None
                mv_type = None
                cmv = to_float(stock.get("circ_mv"))
                tmv = to_float(stock.get("total_mv"))
                if tmv is not None and tmv > 0:
                    mv_used_val = tmv
                    mv_type = "total_mv"
                elif cmv is not None and cmv > 0:
                    mv_used_val = cmv
                    mv_type = "circ_mv"

                for k in ratio_keys:
                    v = to_float(stock.get(k))
                    if v is None:
                        continue
                    numerators[k] += wf * v
                    denoms[k] += wf
                for k in sum_keys:
                    v = to_float(stock.get(k))
                    if v is None:
                        continue
                    sums[k] += v
                    sums_count[k] += 1

                income_info = income_profit_map.get(con_code)
                income_profit_ttm = None
                if income_info:
                    income_profit_ttm = to_float(income_info.get("n_income_attr_p_ttm"))

                if mv_used_val is not None and mv_used_val > 0:
                    mv_total += mv_used_val

                    pe_ttm_used = to_float(stock.get("pe_ttm"))
                    if pe_ttm_used is not None and pe_ttm_used > 0:
                        pe_ttm_harm_num += mv_used_val
                        pe_ttm_harm_den += mv_used_val / pe_ttm_used
                        mv_pe_ttm += mv_used_val
                    if (pv := to_float(stock.get("pb"))) is not None and pv > 0:
                        pb_harm_num += mv_used_val
                        pb_harm_den += mv_used_val / pv
                        mv_pb += mv_used_val
                    if (pv := to_float(stock.get("ps"))) is not None and pv > 0:
                        ps_harm_num += mv_used_val
                        ps_harm_den += mv_used_val / pv
                        mv_ps += mv_used_val
                    if (pv := to_float(stock.get("ps_ttm"))) is not None and pv > 0:
                        ps_ttm_harm_num += mv_used_val
                        ps_ttm_harm_den += mv_used_val / pv
                        mv_ps_ttm += mv_used_val
                    dv_val = to_float(stock.get("dv_ratio"))
                    if dv_val is not None and dv_val >= 0:
                        dv_ratio_mv_sum += mv_used_val * dv_val
                    dv_ttm_val = to_float(stock.get("dv_ttm"))
                    if dv_ttm_val is not None and dv_ttm_val >= 0:
                        dv_ttm_mv_sum += mv_used_val * dv_ttm_val
                    mv_sum_for_div += mv_used_val

                    if income_profit_ttm is not None and income_profit_ttm > 0:
                        pe_income_num += mv_used_val * wf
                        pe_income_den += (income_profit_ttm / 10000.0) * wf
                        mv_pe_income += mv_used_val

                details.append({
                    "ts_code": con_code,
                    "weight": round(w, 6),
                    "profit_end_date": income_info.get("end_date") if income_info else None,
                    "profit_n_income_attr_p": round(float(income_info.get("n_income_attr_p")), 6) if (income_info and income_info.get("n_income_attr_p") is not None) else None,
                    "profit_n_income_attr_p_ttm": round(float(income_info.get("n_income_attr_p_ttm")), 6) if (income_info and income_info.get("n_income_attr_p_ttm") is not None) else None,
                    "pe_ttm": to_float(stock.get("pe_ttm")),
                    "pb": to_float(stock.get("pb")),
                    "ps": to_float(stock.get("ps")),
                    "ps_ttm": to_float(stock.get("ps_ttm")),
                    "dv_ratio": to_float(stock.get("dv_ratio")),
                    "dv_ttm": to_float(stock.get("dv_ttm")),
                    "total_mv": tmv,
                    "circ_mv": cmv,
                    "mv_used": mv_used_val,
                    "mv_type": mv_type,
                })

            logger.info(f"匹配到成分估值: matched={matched}, 缺失每日指标={missing_daily_basic}, 缺失利润表={income_missing}")

            metrics = {}
            for k in ratio_keys:
                if denoms[k] > 0:
                    val = numerators[k] / denoms[k]
                    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                        metrics[k] = None
                    else:
                        metrics[k] = round(float(val), 6)
                else:
                    metrics[k] = None
            for k in sum_keys:
                if sums_count[k] > 0:
                    val = sums[k]
                    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                        metrics[k] = None
                    else:
                        metrics[k] = round(float(val), 6)
                else:
                    metrics[k] = None

            min_cov = 0.8
            pe_cov = (mv_pe_income / mv_total) if mv_total > 0 else 0.0
            pe_ttm_cov = (mv_pe_ttm / mv_total) if mv_total > 0 else 0.0
            pb_cov = (mv_pb / mv_total) if mv_total > 0 else 0.0
            ps_cov = (mv_ps / mv_total) if mv_total > 0 else 0.0
            ps_ttm_cov = (mv_ps_ttm / mv_total) if mv_total > 0 else 0.0

            if pe_income_den > 0 and pe_cov >= min_cov:
                metrics["pe"] = round(pe_income_num / pe_income_den, 6)
            else:
                metrics["pe"] = None
            if pe_ttm_harm_den > 0 and pe_ttm_cov >= min_cov:
                metrics["pe_ttm"] = round(pe_ttm_harm_num / pe_ttm_harm_den, 6)
            else:
                metrics["pe_ttm"] = None
            if pb_harm_den > 0 and pb_cov >= min_cov:
                metrics["pb"] = round(pb_harm_num / pb_harm_den, 6)
            else:
                metrics["pb"] = None
            if ps_harm_den > 0 and ps_cov >= min_cov:
                metrics["ps"] = round(ps_harm_num / ps_harm_den, 6)
            else:
                metrics["ps"] = None
            if ps_ttm_harm_den > 0 and ps_ttm_cov >= min_cov:
                metrics["ps_ttm"] = round(ps_ttm_harm_num / ps_ttm_harm_den, 6)
            else:
                metrics["ps_ttm"] = None
            if mv_sum_for_div > 0:
                metrics["dv_ratio"] = round(dv_ratio_mv_sum / mv_sum_for_div, 6)
                metrics["dv_ttm"] = round(dv_ttm_mv_sum / mv_sum_for_div, 6)
            else:
                metrics["dv_ratio"] = None
                metrics["dv_ttm"] = None

            idx_basic_resp = call_tushare(
                "index_basic",
                params={"ts_code": index_code},
                fields="ts_code,name,fullname,market,publisher,category",
                token=token,
                use_query=False,
            )
            index_basic = None
            if idx_basic_resp.get("code") == 200:
                records = (idx_basic_resp.get("data") or {}).get("records") or []
                if records:
                    index_basic = records[0]

            payload = {
                "index_code": index_code,
                "trade_date": weight_trade_date,
                "index_basic": index_basic,
                "constituents": {
                    "total": len(weights),
                    "matched": matched,
                    "missing_daily_basic": missing_daily_basic,
                    "missing_income": income_missing,
                    "weight_sum": round(weight_sum, 6) if weight_sum else None,
                    "mv_covered": round(mv_total, 6) if mv_total else None,
                    "pe_coverage": round(pe_cov, 6) if mv_total else None,
                    "pe_ttm_coverage": round(pe_ttm_cov, 6) if mv_total else None,
                    "pb_coverage": round(pb_cov, 6) if mv_total else None,
                    "ps_coverage": round(ps_cov, 6) if mv_total else None,
                    "ps_ttm_coverage": round(ps_ttm_cov, 6) if mv_total else None,
                },
                "metrics": metrics,
                "details": details,
            }
            return success_response(payload)
        except Exception as e:
            logger.error(f"指数估值信息查询(利润表PE)失败: {str(e)}")
            return error_response(f"指数估值信息查询失败: {str(e)}", 500)


class IndexValuationRangeView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="指数估值区间查询",
        description=(
            "按指数代码与日期范围，计算每个交易日的指数估值指标。"
        ),
        tags=["etf"],
        parameters=[
            OpenApiParameter(
                name="index_code",
                description="指数代码（如 399300.SZ）",
                required=True,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="start_date",
                description="开始日期（YYYYMMDD）",
                required=True,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="end_date",
                description="结束日期（YYYYMMDD）",
                required=True,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="token",
                description="Tushare Token（可选）",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: SuccessResponseIndexValuationRangeSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            index_code = request.query_params.get("index_code") or request.query_params.get("ts_code")
            start_date = request.query_params.get("start_date")
            end_date = request.query_params.get("end_date")
            token = request.query_params.get("token")
            if not index_code:
                return error_response("参数缺失：index_code 必填", 400)
            if not start_date or not end_date:
                return error_response("参数缺失：start_date 与 end_date 必填", 400)
            try:
                sd = datetime.strptime(start_date, "%Y%m%d")
                ed = datetime.strptime(end_date, "%Y%m%d")
            except ValueError:
                return error_response("参数错误：日期格式应为 YYYYMMDD", 400)
            if ed < sd:
                return error_response("参数错误：end_date 需不早于 start_date", 400)
            logger.info(f"指数估值区间查询: index_code={index_code}, range={start_date}-{end_date}")

            cal_resp = call_tushare(
                "trade_cal",
                params={"is_open": 1, "start_date": start_date, "end_date": end_date},
                fields="cal_date,is_open",
                token=token,
                use_query=False,
            )
            if cal_resp.get("code") != 200:
                return error_response(
                    cal_resp.get("message", "获取交易日历失败"),
                    cal_resp.get("code", 500),
                    error=cal_resp.get("error"),
                )
            cal_records = (cal_resp.get("data") or {}).get("records") or []
            trade_dates = sorted([r.get("cal_date") for r in cal_records if str(r.get("is_open")) in ("1", "True", "true", "1.0")])
            if not trade_dates:
                return error_response("区间内无交易日", 404)
            logger.info(f"区间交易日数量: {len(trade_dates)}")

            weights_resp = call_tushare(
                "index_weight",
                params={"index_code": index_code, "start_date": start_date, "end_date": end_date},
                fields="index_code,con_code,trade_date,weight",
                token=token,
                use_query=False,
            )
            if weights_resp.get("code") != 200:
                return error_response(
                    weights_resp.get("message", "获取指数成分权重失败"),
                    weights_resp.get("code", 500),
                    error=weights_resp.get("error"),
                )
            weight_records = (weights_resp.get("data") or {}).get("records") or []
            if not weight_records:
                fallback_start = (sd - timedelta(days=120)).strftime("%Y%m%d")
                logger.warning(f"区间权重为空，回退查询: index_code={index_code}, {fallback_start}-{end_date}")
                fallback_resp = call_tushare(
                    "index_weight",
                    params={"index_code": index_code, "start_date": fallback_start, "end_date": end_date},
                    fields="index_code,con_code,trade_date,weight",
                    token=token,
                    use_query=False,
                )
                if fallback_resp.get("code") != 200:
                    return error_response(
                        fallback_resp.get("message", "获取指数成分权重失败"),
                        fallback_resp.get("code", 500),
                        error=fallback_resp.get("error"),
                    )
                weight_records = (fallback_resp.get("data") or {}).get("records") or []
            if not weight_records:
                return error_response("未获取到指数成分权重数据", 404)
            weights_by_date = {}
            for r in weight_records:
                d = r.get("trade_date")
                if not d:
                    continue
                weights_by_date.setdefault(d, []).append(r)
            weight_dates_sorted = sorted(weights_by_date.keys())
            logger.info(f"权重快照日期数: {len(weight_dates_sorted)}")

            all_constituents = set()
            for lst in weights_by_date.values():
                for r in lst:
                    if r.get("con_code"):
                        all_constituents.add(r.get("con_code"))
            all_constituents = sorted(list(all_constituents))
            logger.info(f"区间成分总数: {len(all_constituents)}")

            def to_float(v):
                if v is None:
                    return None
                if isinstance(v, (int, float)):
                    fv = float(v)
                    if math.isnan(fv) or math.isinf(fv):
                        return None
                    return fv
                s = str(v).strip()
                if s == "" or s.lower() == "nan":
                    return None
                try:
                    fv = float(s)
                    if math.isnan(fv) or math.isinf(fv):
                        return None
                    return fv
                except Exception:
                    return None

            fina_series_cache = {}

            def _get_fina_series(ts_code: str):
                if ts_code in fina_series_cache:
                    return fina_series_cache[ts_code]
                resp = call_tushare(
                    "fina_indicator",
                    params={"ts_code": ts_code},
                    fields="ts_code,end_date,profit_dedt",
                    token=token,
                    use_query=False,
                )
                if resp.get("code") != 200:
                    fina_series_cache[ts_code] = None
                    return None
                recs = (resp.get("data") or {}).get("records") or []
                series = []
                for r in recs:
                    ed = r.get("end_date")
                    pd = to_float(r.get("profit_dedt"))
                    if ed and pd is not None:
                        series.append({"end_date": str(ed), "profit_dedt": pd})
                series.sort(key=lambda x: x["end_date"], reverse=True)
                fina_series_cache[ts_code] = series if series else None
                return fina_series_cache[ts_code]

            def _calc_profit_dedt(ts_code: str, trade_date_str: str):
                series = _get_fina_series(ts_code)
                if not series:
                    return None
                picked = None
                for r in series:
                    if r["end_date"] <= trade_date_str:
                        picked = r
                        break
                if not picked:
                    picked = series[0]
                end_date = picked["end_date"]
                profit_dedt = picked["profit_dedt"]
                ttm_profit_dedt = profit_dedt
                if len(end_date) == 8:
                    mmdd = end_date[4:8]
                    if mmdd != "1231":
                        y = int(end_date[0:4])
                        prev_year_end = f"{y - 1}1231"
                        prev_year_same = f"{y - 1}{mmdd}"
                        m = {r["end_date"]: r["profit_dedt"] for r in series}
                        if prev_year_end in m and prev_year_same in m:
                            ttm_profit_dedt = (
                                profit_dedt + m[prev_year_end] - m[prev_year_same]
                            )
                return {
                    "end_date": end_date,
                    "profit_dedt": profit_dedt,
                    "profit_dedt_ttm": ttm_profit_dedt,
                }

            stock_series_map = {}
            fields = "ts_code,trade_date,turnover_rate,volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,dv_ttm,total_mv,circ_mv"
            for ts in all_constituents:
                resp = call_tushare(
                    "daily_basic",
                    params={"ts_code": ts, "start_date": start_date, "end_date": end_date},
                    fields=fields,
                    token=token,
                    use_query=False,
                )
                if resp.get("code") != 200:
                    logger.warning(f"成分每日指标获取失败: {ts}, {resp.get('message')}")
                    continue
                recs = (resp.get("data") or {}).get("records") or []
                if not recs:
                    continue
                m = {}
                for r in recs:
                    d = r.get("trade_date")
                    if d:
                        m[d] = r
                stock_series_map[ts] = m
            logger.info(f"成功获取每日指标的成分数: {len(stock_series_map)}")

            def find_weight_date(d):
                from bisect import bisect_right
                pos = bisect_right(weight_dates_sorted, d) - 1
                if pos >= 0:
                    return weight_dates_sorted[pos]
                return None

            items = []
            for d in trade_dates:
                wd = find_weight_date(d)
                if not wd:
                    continue
                slice_weights = weights_by_date.get(wd) or []
                matched = 0
                missing_daily_basic = 0
                weight_sum = 0.0
                for r in slice_weights:
                    w = to_float(r.get("weight"))
                    if w is not None:
                        weight_sum += w
                ratio_keys = [
                    "pe",
                    "pe_ttm",
                    "pb",
                    "ps",
                    "ps_ttm",
                    "dv_ratio",
                    "dv_ttm",
                    "turnover_rate",
                    "volume_ratio",
                ]
                sum_keys = ["total_mv", "circ_mv"]
                numerators = {k: 0.0 for k in ratio_keys}
                denoms = {k: 0.0 for k in ratio_keys}
                sums = {k: 0.0 for k in sum_keys}
                sums_count = {k: 0 for k in sum_keys}
                pe_harm_num = pe_harm_den = 0.0
                pe_ttm_harm_num = pe_ttm_harm_den = 0.0
                pb_harm_num = pb_harm_den = 0.0
                ps_harm_num = ps_harm_den = 0.0
                ps_ttm_harm_num = ps_ttm_harm_den = 0.0
                dv_ratio_mv_sum = dv_ttm_mv_sum = 0.0
                mv_sum_for_div = 0.0
                mv_total = 0.0
                mv_pe = 0.0
                mv_pe_ttm = 0.0
                mv_pb = 0.0
                mv_ps = 0.0
                mv_ps_ttm = 0.0

                for wr in slice_weights:
                    ts = wr.get("con_code")
                    w = to_float(wr.get("weight"))
                    if not ts or w is None or w <= 0:
                        continue
                    rec = (stock_series_map.get(ts) or {}).get(d)
                    if not rec:
                        missing_daily_basic += 1
                        continue
                    matched += 1
                    wf = w / 100.0
                    cmv = to_float(rec.get("circ_mv"))
                    tmv = to_float(rec.get("total_mv"))
                    mv_used = tmv if (tmv is not None and tmv > 0) else (cmv if (cmv is not None and cmv > 0) else None)

                    for k in ratio_keys:
                        v = to_float(rec.get(k))
                        if v is None:
                            continue
                        numerators[k] += wf * v
                        denoms[k] += wf
                    for k in sum_keys:
                        v = to_float(rec.get(k))
                        if v is None:
                            continue
                        sums[k] += v
                        sums_count[k] += 1

                    if mv_used is not None and mv_used > 0:
                        mv_total += mv_used
                        pe_raw = to_float(rec.get("pe"))
                        pe_ttm_raw = to_float(rec.get("pe_ttm"))
                        pe_used = pe_raw if (pe_raw is not None and pe_raw > 0) else None
                        pe_ttm_used = pe_ttm_raw if (pe_ttm_raw is not None and pe_ttm_raw > 0) else None
                        cap_for_pe = tmv if (tmv is not None and tmv > 0) else mv_used
                        if (pe_used is None or pe_ttm_used is None) and cap_for_pe is not None and cap_for_pe > 0:
                            profit_info = _calc_profit_dedt(ts, d)
                            if profit_info:
                                pd = profit_info.get("profit_dedt")
                                pd_ttm = profit_info.get("profit_dedt_ttm")
                                if pe_used is None and pd is not None and pd > 0:
                                    pe_used = (cap_for_pe * 10000.0) / pd
                                if pe_ttm_used is None and pd_ttm is not None and pd_ttm > 0:
                                    pe_ttm_used = (cap_for_pe * 10000.0) / pd_ttm

                        if pe_used is not None and pe_used > 0:
                            pe_harm_num += mv_used
                            pe_harm_den += mv_used / pe_used
                            mv_pe += mv_used
                        if pe_ttm_used is not None and pe_ttm_used > 0:
                            pe_ttm_harm_num += mv_used
                            pe_ttm_harm_den += mv_used / pe_ttm_used
                            mv_pe_ttm += mv_used
                        pv = to_float(rec.get("pb"))
                        if pv is not None and pv > 0:
                            pb_harm_num += mv_used
                            pb_harm_den += mv_used / pv
                            mv_pb += mv_used
                        pv = to_float(rec.get("ps"))
                        if pv is not None and pv > 0:
                            ps_harm_num += mv_used
                            ps_harm_den += mv_used / pv
                            mv_ps += mv_used
                        pv = to_float(rec.get("ps_ttm"))
                        if pv is not None and pv > 0:
                            ps_ttm_harm_num += mv_used
                            ps_ttm_harm_den += mv_used / pv
                            mv_ps_ttm += mv_used
                        dv_val = to_float(rec.get("dv_ratio"))
                        dv_ttm_val = to_float(rec.get("dv_ttm"))
                        if dv_val is not None and dv_val >= 0:
                            dv_ratio_mv_sum += mv_used * dv_val
                        if dv_ttm_val is not None and dv_ttm_val >= 0:
                            dv_ttm_mv_sum += mv_used * dv_ttm_val
                        mv_sum_for_div += mv_used

                metrics = {}
                for k in ratio_keys:
                    if denoms[k] > 0:
                        v = numerators[k] / denoms[k]
                        metrics[k] = round(float(v), 6)
                    else:
                        metrics[k] = None
                for k in sum_keys:
                    if sums_count[k] > 0:
                        metrics[k] = round(float(sums[k]), 6)
                    else:
                        metrics[k] = None
                min_cov = 0.8
                pe_cov = (mv_pe / mv_total) if mv_total > 0 else 0.0
                pe_ttm_cov = (mv_pe_ttm / mv_total) if mv_total > 0 else 0.0
                pb_cov = (mv_pb / mv_total) if mv_total > 0 else 0.0
                ps_cov = (mv_ps / mv_total) if mv_total > 0 else 0.0
                ps_ttm_cov = (mv_ps_ttm / mv_total) if mv_total > 0 else 0.0
                metrics["pe"] = round(pe_harm_num / pe_harm_den, 6) if (pe_harm_den > 0 and pe_cov >= min_cov) else None
                metrics["pe_ttm"] = round(pe_ttm_harm_num / pe_ttm_harm_den, 6) if (pe_ttm_harm_den > 0 and pe_ttm_cov >= min_cov) else None
                metrics["pb"] = round(pb_harm_num / pb_harm_den, 6) if (pb_harm_den > 0 and pb_cov >= min_cov) else None
                metrics["ps"] = round(ps_harm_num / ps_harm_den, 6) if (ps_harm_den > 0 and ps_cov >= min_cov) else None
                metrics["ps_ttm"] = round(ps_ttm_harm_num / ps_ttm_harm_den, 6) if (ps_ttm_harm_den > 0 and ps_ttm_cov >= min_cov) else None
                if mv_sum_for_div > 0:
                    metrics["dv_ratio"] = round(dv_ratio_mv_sum / mv_sum_for_div, 6)
                    metrics["dv_ttm"] = round(dv_ttm_mv_sum / mv_sum_for_div, 6)
                if matched > 0 and mv_total > 0 and (pe_cov < min_cov or pb_cov < min_cov):
                    logger.warning(
                        f"估值覆盖率偏低，返回None以避免误导: date={d}, weight_date={wd}, matched={matched}, "
                        f"mv_total={round(mv_total, 6)}, pe_cov={round(pe_cov, 6)}, pb_cov={round(pb_cov, 6)}"
                    )
                items.append({
                    "trade_date": d,
                    "weight_date": wd,
                    "metrics": metrics,
                    "constituents": {
                        "total": len(slice_weights),
                        "matched": matched,
                        "missing_daily_basic": missing_daily_basic,
                        "weight_sum": round(weight_sum, 6) if weight_sum else None,
                        "mv_covered": round(mv_total, 6) if mv_total else None,
                        "pe_coverage": round(pe_cov, 6) if mv_total else None,
                        "pe_ttm_coverage": round(pe_ttm_cov, 6) if mv_total else None,
                        "pb_coverage": round(pb_cov, 6) if mv_total else None,
                        "ps_coverage": round(ps_cov, 6) if mv_total else None,
                        "ps_ttm_coverage": round(ps_ttm_cov, 6) if mv_total else None,
                    },
                })

            payload = {
                "index_code": index_code,
                "start_date": start_date,
                "end_date": end_date,
                "total": len(items),
                "items": items,
            }
            return success_response(payload)
        except Exception as e:
            logger.error(f"指数估值区间查询失败: {str(e)}")
            return error_response(f"指数估值区间查询失败: {str(e)}", 500)
