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
    ErrorResponseSerializer,
)
from .services import etf_service

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