from rest_framework.views import APIView
from common.response import success_response, error_response
from common.tushare_proxy import call_tushare
from .github_markdown_service import github_markdown_service
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from .serializers import (
    SuccessResponseDcDailySerializer,
    SuccessResponseDcIndexSerializer,
    SuccessResponseGitInfoSerializer,
    SuccessResponseAhComparisonSerializer,
    SuccessResponseBrokerRecommendSerializer,
    SuccessResponseCcassHoldDetailSerializer,
    SuccessResponseCcassHoldSerializer,
    SuccessResponseLimitStepSerializer,
    SuccessResponseHmDetailSerializer,
    SuccessResponseHkHoldSerializer,
    SuccessResponseStockHsgtSerializer,
    SuccessResponseHsgtTop10Serializer,
    SuccessResponseIrmQaShSerializer,
    SuccessResponseIrmQaSzSerializer,
    SuccessResponseCyqPerfSerializer,
    ErrorResponseSerializer,
)











class DcDailyProxyView(APIView):
    """
    东财概念/行业/地域板块日频行情直通代理接口（Tushare dc_daily）

    功能：
    - 代理调用 Tushare `dc_daily`，返回东财概念板块、行业指数板块、地域板块的日频行情数据。
    - 外层响应统一使用 success_response/error_response。

    参数（与 Tushare 文档一致）：
    - ts_code (str, 可选): 板块代码（格式：xxxxx.DC）
    - trade_date (str, 可选): 交易日期（YYYYMMDD）
    - start_date (str, 可选): 开始日期（YYYYMMDD）
    - end_date (str, 可选): 结束日期（YYYYMMDD）
    - idx_type (str, 可选): 板块类型（概念板块、行业板块、地域板块）
    - fields (str, 可选): 返回字段列表，逗号分隔
    - token (str, 可选): Tushare Token（覆盖环境变量）

    返回值：
    - code (int), message (str)
    - data (object):
      - interface (str): 固定为 "dc_daily"
      - count (int): 记录数
      - records (list[object]): 与 Tushare 文档一致的字段：
        - ts_code, trade_date, close, open, high, low, change, pct_change,
          vol, amount, swing, turnover_rate

    事件：无（后端接口，无前端事件）。
    """

    @extend_schema(
        summary="东财板块日频行情直通代理",
        description="Tushare dc_daily 的代理接口，统一返回格式。",
        tags=["Tushare Proxy"],
        parameters=[
            OpenApiParameter(name="ts_code", description="板块代码（格式：xxxxx.DC）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="trade_date", description="交易日期 YYYYMMDD", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="start_date", description="开始日期 YYYYMMDD", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="end_date", description="结束日期 YYYYMMDD", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="idx_type", description="板块类型：概念板块/行业板块/地域板块", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="fields", description="字段列表（逗号分隔）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="token", description="Tushare Token（覆盖环境变量）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
        ],
        responses={
            200: SuccessResponseDcDailySerializer,
            400: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        """
        GET 请求

        示例：
        - 获取 2025-05-13 概念板块行情：trade_date=20250513
        - 指定板块与区间：ts_code=BK1063.DC&start_date=20250101&end_date=20250131
        - 限定字段：fields=ts_code,trade_date,close,pct_change

        返回：success_response(data, "查询东财板块日频行情成功")
        - data.interface = "dc_daily"
        - data.count = 记录数
        - data.records = 记录数组
        """
        try:
            params = {}
            for key in ("ts_code", "trade_date", "start_date", "end_date", "idx_type"):
                val = request.query_params.get(key)
                if val:
                    params[key] = val

            fields = request.query_params.get("fields")
            token = request.query_params.get("token")

            resp = call_tushare("dc_daily", params=params, fields=fields, token=token, use_query=False)
            if resp.get("code") != 200:
                return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))

            data = resp.get("data") or {}
            return success_response(data, "查询东财板块日频行情成功")

        except Exception as e:
            return error_response(f"查询东财板块日频行情失败: {str(e)}", 500)


class DcIndexProxyView(APIView):
    """
    东方财富概念板块数据直通代理接口（Tushare dc_index）

    功能：
    - 代理调用 Tushare `dc_index`，返回东方财富概念板块在指定日期的统计数据。
    - 外层响应统一使用 success_response/error_response。

    参数（与 Tushare 文档一致）：
    - ts_code (str, 可选): 指数/概念代码（支持逗号分隔多个代码）
    - name (str, 可选): 板块名称（例如：人形机器人）
    - trade_date (str, 可选): 交易日期（YYYYMMDD）
    - start_date (str, 可选): 开始日期（YYYYMMDD）
    - end_date (str, 可选): 结束日期（YYYYMMDD）
    - fields (str, 可选): 返回字段列表，逗号分隔
    - token (str, 可选): Tushare Token（覆盖环境变量）

    返回值：
    - code (int), message (str)
    - data (object):
      - interface (str): 固定为 "dc_index"
      - count (int): 记录数
      - records (list[object]): 与 Tushare 文档一致的字段：
        - ts_code, trade_date, name, leading, leading_code, pct_change,
          leading_pct, total_mv, turnover_rate, up_num, down_num

    事件：无（后端接口，无前端事件）。
    """

    @extend_schema(
        summary="东方财富概念板块直通代理",
        description="Tushare dc_index 的代理接口，统一返回格式。",
        tags=["Tushare Proxy"],
        parameters=[
            OpenApiParameter(name="ts_code", description="概念代码（支持多个，逗号分隔）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="name", description="板块名称（例如：人形机器人）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="trade_date", description="交易日期 YYYYMMDD", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="start_date", description="开始日期 YYYYMMDD", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="end_date", description="结束日期 YYYYMMDD", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="fields", description="字段列表（逗号分隔）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="token", description="Tushare Token（覆盖环境变量）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
        ],
        responses={
            200: SuccessResponseDcIndexSerializer,
            400: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        """
        GET 请求

        示例：
        - 获取 2025-01-03 概念板块列表：trade_date=20250103&fields=ts_code,name,turnover_rate,up_num,down_num
        - 指定板块名称与日期：name=人形机器人&trade_date=20250103
        - 指定多个板块代码：ts_code=BK1186.DC,BK1185.DC&trade_date=20250103

        返回：success_response(data, "查询东方财富概念板块成功")
        - data.interface = "dc_index"
        - data.count = 记录数
        - data.records = 记录数组
        """
        try:
            params = {}
            for key in ("ts_code", "name", "trade_date", "start_date", "end_date"):
                val = request.query_params.get(key)
                if val:
                    params[key] = val

            fields = request.query_params.get("fields")
            token = request.query_params.get("token")

            resp = call_tushare("dc_index", params=params, fields=fields, token=token, use_query=False)
            if resp.get("code") != 200:
                return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))

            data = resp.get("data") or {}
            return success_response(data, "查询东方财富概念板块成功")

        except Exception as e:
            return error_response(f"查询东方财富概念板块失败: {str(e)}", 500)


class GitInfoView(APIView):
    """
    Git 仓库提交信息接口

    说明：封装 scheduled_tasks/other_tools/git_info_tool.py 中的功能为 HTTP 接口；
    返回统一的 success_response/error_response 外层结构。

    支持参数：
    - repo_path (str, 可选): 仓库本地路径，默认使用预设路径。
    - limit (int, 可选): 限制返回的提交数量（从最近开始）。

    返回值（统一外层结构）：
    - code (int), message (str)
    - data (object):
      - interface (str): 固定为 "git_info"
      - count (int): 提交记录数
      - records (list[object]): 每条记录包含 commit_id、authored_datetime、author_name、message
    错误返回：error_response。
    """

    @extend_schema(
        summary="Git 仓库提交信息",
        description="返回指定仓库的提交信息（最近提交在前）",
        tags=["Tools"],
        parameters=[
            OpenApiParameter(name="repo_path", description="仓库本地路径", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="limit", description="限制返回的提交数量", required=False, type=OpenApiTypes.INT, location=OpenApiParameter.QUERY),
        ],
        responses={
            200: SuccessResponseGitInfoSerializer,
            400: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            from .other_tools.git_info_tool import get_git_commits_info

            repo_path = request.query_params.get("repo_path")
            limit_param = request.query_params.get("limit")
            limit = None
            if limit_param is not None:
                try:
                    limit = int(limit_param)
                except ValueError:
                    return error_response("参数 limit 需为整数", 400)

            records = get_git_commits_info(repo_path=repo_path, limit=limit)
            data = {
                "interface": "git_info",
                "count": len(records),
                "records": records,
            }
            return success_response(data, "查询 Git 提交信息成功")

        except Exception as e:
            return error_response(f"查询 Git 提交信息失败: {str(e)}", 500)


# --------------------- 新增：特色/打板专题接口直通代理 ---------------------

class AhComparisonProxyView(APIView):
    """
    AH股比价直通代理接口（Tushare stk_ah_comparison）

    功能：
    - 代理调用 Tushare `stk_ah_comparison`，返回 A/H 股比价及溢价信息。
    - 外层响应统一使用 success_response/error_response。

    参数（与 Tushare 文档一致）：
    - hk_code (str, 可选): 港股股票代码（xxxxx.HK）
    - ts_code (str, 可选): A股股票代码（xxxxxx.SH/SZ/BJ）
    - trade_date (str, 可选): 交易日期（YYYYMMDD）
    - start_date (str, 可选): 开始日期
    - end_date (str, 可选): 结束日期
    - fields (str, 可选): 返回字段列表，逗号分隔
    - token (str, 可选): Tushare Token（覆盖环境变量）

    返回值：
    - code (int), message (str)
    - data (object):
      - interface (str): 固定为 "stk_ah_comparison"
      - count (int): 记录数
      - records (list[object]): 与文档一致字段（hk_code, ts_code, trade_date, hk_name, hk_pct_chg, hk_close, name, close, pct_chg, ah_comparison, ah_premium）

    事件：无（后端接口，无前端事件）。
    """

    @extend_schema(
        summary="AH股比价直通代理",
        description="Tushare stk_ah_comparison 的代理接口，统一返回格式。",
        tags=["Tushare Proxy"],
        parameters=[
            OpenApiParameter(name="hk_code", description="港股股票代码（xxxxx.HK）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="ts_code", description="A股股票代码（xxxxxx.SH/SZ/BJ）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="trade_date", description="交易日期 YYYYMMDD", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="start_date", description="开始日期", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="end_date", description="结束日期", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="fields", description="字段列表（逗号分隔）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="token", description="Tushare Token（覆盖环境变量）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
        ],
        responses={
            200: SuccessResponseAhComparisonSerializer,
            400: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            params = {}
            for key in ("hk_code", "ts_code", "trade_date", "start_date", "end_date"):
                val = request.query_params.get(key)
                if val:
                    params[key] = val

            fields = request.query_params.get("fields")
            token = request.query_params.get("token")

            resp = call_tushare("stk_ah_comparison", params=params, fields=fields, token=token, use_query=False)
            if resp.get("code") != 200:
                return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))

            data = resp.get("data") or {}
            return success_response(data, "查询AH股比价成功")

        except Exception as e:
            return error_response(f"查询AH股比价失败: {str(e)}", 500)


class BrokerRecommendProxyView(APIView):
    """
    券商月度金股直通代理接口（Tushare broker_recommend）

    功能：
    - 代理调用 Tushare `broker_recommend`，返回指定月份券商金股列表。
    - 外层响应统一使用 success_response/error_response。

    参数：
    - month (str, 必选): 月度（YYYYMM）
    - fields (str, 可选): 返回字段列表，逗号分隔
    - token (str, 可选): Tushare Token（覆盖环境变量）

    返回值：
    - code (int), message (str)
    - data (object):
      - interface (str): 固定为 "broker_recommend"
      - count (int): 记录数
      - records (list[object]): month, broker, ts_code, name

    事件：无。
    """

    @extend_schema(
        summary="券商月度金股直通代理",
        description="Tushare broker_recommend 的代理接口，统一返回格式。",
        tags=["Tushare Proxy"],
        parameters=[
            OpenApiParameter(name="month", description="月度（YYYYMM）", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="fields", description="字段列表（逗号分隔）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="token", description="Tushare Token（覆盖环境变量）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
        ],
        responses={
            200: SuccessResponseBrokerRecommendSerializer,
            400: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            month = request.query_params.get("month")
            if not month:
                return error_response("缺少必填参数: month", 400)

            params = {"month": month}
            fields = request.query_params.get("fields")
            token = request.query_params.get("token")

            resp = call_tushare("broker_recommend", params=params, fields=fields, token=token, use_query=False)
            if resp.get("code") != 200:
                return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))

            data = resp.get("data") or {}
            return success_response(data, "查询券商月度金股成功")

        except Exception as e:
            return error_response(f"查询券商月度金股失败: {str(e)}", 500)


class CcassHoldDetailProxyView(APIView):
    """
    中央结算系统持股明细直通代理接口（Tushare ccass_hold_detail）

    功能：
    - 代理调用 Tushare `ccass_hold_detail`，返回中央结算系统机构席位持股明细。

    参数：
    - ts_code (str, 可选): 股票代码（e.g. 605009.SH 或 00960.HK）
    - hk_code (str, 可选): 港交所代码（e.g. 95009）
    - trade_date (str, 可选): 交易日期（YYYYMMDD）
    - start_date (str, 可选): 开始日期
    - end_date (str, 可选): 结束日期
    - fields/token (str, 可选)

    返回值：
    - interface 固定为 "ccass_hold_detail"；records 字段与文档一致。

    事件：无。
    """

    @extend_schema(
        summary="中央结算系统持股明细直通代理",
        description="Tushare ccass_hold_detail 的代理接口，统一返回格式。",
        tags=["Tushare Proxy"],
        parameters=[
            OpenApiParameter(name="ts_code", description="股票代码（e.g. 605009.SH / 00960.HK）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="hk_code", description="港交所代码（e.g. 95009）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="trade_date", description="交易日期 YYYYMMDD", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="start_date", description="开始日期", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="end_date", description="结束日期", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="fields", description="字段列表（逗号分隔）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="token", description="Tushare Token（覆盖环境变量）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
        ],
        responses={
            200: SuccessResponseCcassHoldDetailSerializer,
            400: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            params = {}
            for key in ("ts_code", "hk_code", "trade_date", "start_date", "end_date"):
                val = request.query_params.get(key)
                if val:
                    params[key] = val
            fields = request.query_params.get("fields")
            token = request.query_params.get("token")

            resp = call_tushare("ccass_hold_detail", params=params, fields=fields, token=token, use_query=False)
            if resp.get("code") != 200:
                return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))

            data = resp.get("data") or {}
            return success_response(data, "查询中央结算系统持股明细成功")
        except Exception as e:
            return error_response(f"查询中央结算系统持股明细失败: {str(e)}", 500)


class CcassHoldProxyView(APIView):
    """
    中央结算系统持股汇总直通代理接口（Tushare ccass_hold）

    功能：
    - 代理调用 Tushare `ccass_hold`，返回中央结算系统持股汇总数据。

    参数：
    - ts_code (str, 可选), hk_code (str, 可选), trade_date (str, 可选), start_date (str, 可选), end_date (str, 可选)
    - fields/token (str, 可选)

    返回值：
    - interface 固定为 "ccass_hold"；records 字段与文档一致。

    事件：无。
    """

    @extend_schema(
        summary="中央结算系统持股汇总直通代理",
        description="Tushare ccass_hold 的代理接口，统一返回格式。",
        tags=["Tushare Proxy"],
        parameters=[
            OpenApiParameter(name="ts_code", description="股票代码（e.g. 605009.SH / 00960.HK）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="hk_code", description="港交所代码（e.g. 95009）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="trade_date", description="交易日期 YYYYMMDD", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="start_date", description="开始日期", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="end_date", description="结束日期", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="fields", description="字段列表（逗号分隔）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="token", description="Tushare Token（覆盖环境变量）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
        ],
        responses={
            200: SuccessResponseCcassHoldSerializer,
            400: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            params = {}
            for key in ("ts_code", "hk_code", "trade_date", "start_date", "end_date"):
                val = request.query_params.get(key)
                if val:
                    params[key] = val
            fields = request.query_params.get("fields")
            token = request.query_params.get("token")

            resp = call_tushare("ccass_hold", params=params, fields=fields, token=token, use_query=False)
            if resp.get("code") != 200:
                return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))

            data = resp.get("data") or {}
            return success_response(data, "查询中央结算系统持股汇总成功")
        except Exception as e:
            return error_response(f"查询中央结算系统持股汇总失败: {str(e)}", 500)


class HkHoldProxyView(APIView):
    """
    沪深港股通持股明细代理接口

    功能：代理调用 Tushare 接口 `hk_hold`，获取沪深港股通持股明细（港交所数据）。
    参数：支持查询参数 `code`、`ts_code`、`trade_date`、`start_date`、`end_date`、`exchange`、`fields`、`token`。
    返回值：统一 `success_response` / `error_response` 结构，`data.interface = "hk_hold"`。
    事件：仅记录调用与错误，无持久化事件。
    """

    @extend_schema(
        summary="沪深港股通持股明细",
        description=(
            "获取沪深港股通持股明细，数据来源港交所。\n"
            "参数：code(交易所代码)、ts_code、trade_date、start_date、end_date、exchange(SH/SZ/HK)"
        ),
        tags=["Tushare Proxy"],
        parameters=[
            OpenApiParameter("code", OpenApiTypes.STR, OpenApiParameter.QUERY, description="交易所代码", required=False),
            OpenApiParameter("ts_code", OpenApiTypes.STR, OpenApiParameter.QUERY, description="TS股票代码", required=False),
            OpenApiParameter("trade_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="交易日期YYYYMMDD", required=False),
            OpenApiParameter("start_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="开始日期YYYYMMDD", required=False),
            OpenApiParameter("end_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="结束日期YYYYMMDD", required=False),
            OpenApiParameter("exchange", OpenApiTypes.STR, OpenApiParameter.QUERY, description="SH沪股通/SZ深股通/HK港股通", required=False),
            OpenApiParameter("fields", OpenApiTypes.STR, OpenApiParameter.QUERY, description="限定返回字段列表", required=False),
            OpenApiParameter("token", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Tushare API Token", required=False),
        ],
        responses={
            200: SuccessResponseHkHoldSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            params = {}
            for key in ("code", "ts_code", "trade_date", "start_date", "end_date", "exchange"):
                val = request.query_params.get(key)
                if val:
                    params[key] = val
            fields = request.query_params.get("fields")
            token = request.query_params.get("token")

            resp = call_tushare("hk_hold", params=params, fields=fields, token=token, use_query=False)
            if resp.get("code") != 200:
                return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))
            data = resp.get("data") or {}
            return success_response(data, "查询沪深港股通持股明细成功")
        except Exception as e:
            return error_response(f"查询沪深港股通持股明细失败: {str(e)}", 500)


class StockHsgtProxyView(APIView):
    """
    沪深港通股票列表代理接口

    功能：代理调用 Tushare 接口 `stock_hsgt`，获取沪深港通股票列表。
    参数：支持 `ts_code`、`trade_date`、`type(HK_SZ/SZ_HK/HK_SH/SH_HK)`、`start_date`、`end_date`、`fields`、`token`。
    返回值：统一响应结构，`data.interface = "stock_hsgt"`。
    事件：无。
    """

    @extend_schema(
        summary="沪深港通股票列表",
        description="获取沪深港通股票列表，type为必选，HK_SZ/SZ_HK/HK_SH/SH_HK。",
        tags=["Tushare Proxy"],
        parameters=[
            OpenApiParameter("ts_code", OpenApiTypes.STR, OpenApiParameter.QUERY, description="股票代码", required=False),
            OpenApiParameter("trade_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="交易日期YYYYMMDD", required=False),
            OpenApiParameter("type", OpenApiTypes.STR, OpenApiParameter.QUERY, description="类型：HK_SZ/SZ_HK/HK_SH/SH_HK", required=False),
            OpenApiParameter("start_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="开始日期YYYYMMDD", required=False),
            OpenApiParameter("end_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="结束日期YYYYMMDD", required=False),
            OpenApiParameter("fields", OpenApiTypes.STR, OpenApiParameter.QUERY, description="限定返回字段列表", required=False),
            OpenApiParameter("token", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Tushare API Token", required=False),
        ],
        responses={
            200: SuccessResponseStockHsgtSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            params = {}
            for key in ("ts_code", "trade_date", "type", "start_date", "end_date"):
                val = request.query_params.get(key)
                if val:
                    params[key] = val
            fields = request.query_params.get("fields")
            token = request.query_params.get("token")

            resp = call_tushare("stock_hsgt", params=params, fields=fields, token=token, use_query=False)
            if resp.get("code") != 200:
                return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))
            data = resp.get("data") or {}
            return success_response(data, "查询沪深港通股票列表成功")
        except Exception as e:
            return error_response(f"查询沪深港通股票列表失败: {str(e)}", 500)


class HsgtTop10ProxyView(APIView):
    """
    沪深股通十大成交股代理接口

    功能：代理调用 Tushare 接口 `hsgt_top10`，获取每日沪深股通十大成交股。
    参数：支持 `ts_code`、`trade_date`、`start_date`、`end_date`、`market_type(1:上交所,3:深交所)`、`fields`、`token`。
    返回值：统一 `success_response` / `error_response` 结构，`data.interface = "hsgt_top10"`。
    事件：仅记录调用与错误，无持久化事件。
    """

    @extend_schema(
        summary="沪深股通十大成交股",
        description=(
            "获取每日沪深股通十大成交股；market_type: 1(上交所)、3(深交所)。\n"
            "参数：ts_code、trade_date、start_date、end_date、market_type"
        ),
        tags=["Tushare Proxy"],
        parameters=[
            OpenApiParameter("ts_code", OpenApiTypes.STR, OpenApiParameter.QUERY, description="股票代码", required=False),
            OpenApiParameter("trade_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="交易日期YYYYMMDD", required=False),
            OpenApiParameter("start_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="开始日期YYYYMMDD", required=False),
            OpenApiParameter("end_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="结束日期YYYYMMDD", required=False),
            OpenApiParameter("market_type", OpenApiTypes.INT, OpenApiParameter.QUERY, description="市场类型：1上交所/3深交所", required=False),
            OpenApiParameter("fields", OpenApiTypes.STR, OpenApiParameter.QUERY, description="限定返回字段列表", required=False),
            OpenApiParameter("token", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Tushare API Token", required=False),
        ],
        responses={
            200: SuccessResponseHsgtTop10Serializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            params = {}
            for key in ("ts_code", "trade_date", "start_date", "end_date", "market_type"):
                val = request.query_params.get(key)
                if val:
                    params[key] = val
            fields = request.query_params.get("fields")
            token = request.query_params.get("token")

            resp = call_tushare("hsgt_top10", params=params, fields=fields, token=token, use_query=False)
            if resp.get("code") != 200:
                return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))
            data = resp.get("data") or {}
            return success_response(data, "查询沪深股通十大成交股成功")
        except Exception as e:
            return error_response(f"查询沪深股通十大成交股失败: {str(e)}", 500)


class IrmQaShProxyView(APIView):
    """
    上证E互动问答代理接口

    功能：代理调用 Tushare 接口 `irm_qa_sh`，获取上交所 e 互动董秘问答文本数据。
    参数：支持 `ts_code`、`trade_date`、`start_date`、`end_date`、`pub_date_start`、`pub_date_end`、`fields`、`token`。
    返回值：统一响应结构，`data.interface = "irm_qa_sh"`，记录字段与 Tushare 文档一致。
    事件：无。

    注意：`pub_date_start` 与 `pub_date_end` 会分别映射为 Tushare 的 `pub_date` 参数，
    若同时传入，以后者覆盖前者（Tushare接收单一`pub_date`筛选）。
    """

    @extend_schema(
        summary="上证E互动问答",
        description=(
            "获取上交所e互动董秘问答文本数据。\n"
            "参数：ts_code、trade_date、start_date、end_date、pub_date_start、pub_date_end"
        ),
        tags=["Tushare Proxy"],
        parameters=[
            OpenApiParameter("ts_code", OpenApiTypes.STR, OpenApiParameter.QUERY, description="股票代码", required=False),
            OpenApiParameter("trade_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="交易日期YYYYMMDD", required=False),
            OpenApiParameter("start_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="开始日期YYYYMMDD", required=False),
            OpenApiParameter("end_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="结束日期YYYYMMDD", required=False),
            OpenApiParameter("pub_date_start", OpenApiTypes.STR, OpenApiParameter.QUERY, description="发布开始日期：YYYY-MM-DD HH:MM:SS", required=False),
            OpenApiParameter("pub_date_end", OpenApiTypes.STR, OpenApiParameter.QUERY, description="发布结束日期：YYYY-MM-DD HH:MM:SS", required=False),
            OpenApiParameter("fields", OpenApiTypes.STR, OpenApiParameter.QUERY, description="限定返回字段列表", required=False),
            OpenApiParameter("token", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Tushare API Token", required=False),
        ],
        responses={
            200: SuccessResponseIrmQaShSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            params = {}
            for key in ("ts_code", "trade_date", "start_date", "end_date"):
                val = request.query_params.get(key)
                if val:
                    params[key] = val

            pub_date_start = request.query_params.get("pub_date_start")
            pub_date_end = request.query_params.get("pub_date_end")
            # 按现有工具实现方式，二者分别映射到 'pub_date'，后者覆盖前者
            if pub_date_start:
                params["pub_date"] = pub_date_start
            if pub_date_end:
                params["pub_date"] = pub_date_end

            fields = request.query_params.get("fields")
            token = request.query_params.get("token")

            resp = call_tushare("irm_qa_sh", params=params, fields=fields, token=token, use_query=False)
            if resp.get("code") != 200:
                return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))
            data = resp.get("data") or {}
            return success_response(data, "查询上证E互动问答成功")
        except Exception as e:
            return error_response(f"查询上证E互动问答失败: {str(e)}", 500)


class IrmQaSzProxyView(APIView):
    """
    深证互动易问答代理接口

    功能：代理调用 Tushare 接口 `irm_qa_sz`，获取深交所互动易董秘问答文本数据。
    参数：支持 `ts_code`、`trade_date`、`start_date`、`end_date`、`pub_date_start`、`pub_date_end`、`fields`、`token`。
    返回值：统一响应结构，`data.interface = "irm_qa_sz"`，记录字段与 Tushare 文档一致。
    事件：无。

    注意：`pub_date_start` 与 `pub_date_end` 会分别映射为 Tushare 的 `pub_date` 参数，若同时传入，以后者覆盖前者。
    """

    @extend_schema(
        summary="深证互动易问答",
        description=(
            "获取深交所互动易董秘问答文本数据。\n"
            "参数：ts_code、trade_date、start_date、end_date、pub_date_start、pub_date_end"
        ),
        tags=["Tushare Proxy"],
        parameters=[
            OpenApiParameter("ts_code", OpenApiTypes.STR, OpenApiParameter.QUERY, description="股票代码", required=False),
            OpenApiParameter("trade_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="交易日期YYYYMMDD", required=False),
            OpenApiParameter("start_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="开始日期YYYYMMDD", required=False),
            OpenApiParameter("end_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="结束日期YYYYMMDD", required=False),
            OpenApiParameter("pub_date_start", OpenApiTypes.STR, OpenApiParameter.QUERY, description="发布开始日期：YYYY-MM-DD HH:MM:SS", required=False),
            OpenApiParameter("pub_date_end", OpenApiTypes.STR, OpenApiParameter.QUERY, description="发布结束日期：YYYY-MM-DD HH:MM:SS", required=False),
            OpenApiParameter("fields", OpenApiTypes.STR, OpenApiParameter.QUERY, description="限定返回字段列表", required=False),
            OpenApiParameter("token", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Tushare API Token", required=False),
        ],
        responses={
            200: SuccessResponseIrmQaSzSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            params = {}
            for key in ("ts_code", "trade_date", "start_date", "end_date"):
                val = request.query_params.get(key)
                if val:
                    params[key] = val

            pub_date_start = request.query_params.get("pub_date_start")
            pub_date_end = request.query_params.get("pub_date_end")
            if pub_date_start:
                params["pub_date"] = pub_date_start
            if pub_date_end:
                params["pub_date"] = pub_date_end

            fields = request.query_params.get("fields")
            token = request.query_params.get("token")

            resp = call_tushare("irm_qa_sz", params=params, fields=fields, token=token, use_query=False)
            if resp.get("code") != 200:
                return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))
            data = resp.get("data") or {}
            return success_response(data, "查询深证互动易问答成功")
        except Exception as e:
            return error_response(f"查询深证互动易问答失败: {str(e)}", 500)


class CyqPerfProxyView(APIView):
    """
    每日筹码及胜率代理接口

    功能：代理调用 Tushare 接口 `cyq_perf`，获取每日筹码分布及胜率。
    参数：支持 `ts_code`、`trade_date`、`start_date`、`end_date`、`fields`、`token`。
    返回值：统一响应结构，`data.interface = "cyq_perf"`。
    事件：无。
    """

    @extend_schema(
        summary="每日筹码及胜率",
        description="获取每日筹码分布与胜率，支持按 ts_code 或日期区间过滤。",
        tags=["Tushare Proxy"],
        parameters=[
            OpenApiParameter("ts_code", OpenApiTypes.STR, OpenApiParameter.QUERY, description="股票代码", required=False),
            OpenApiParameter("trade_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="交易日期YYYYMMDD", required=False),
            OpenApiParameter("start_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="开始日期YYYYMMDD", required=False),
            OpenApiParameter("end_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="结束日期YYYYMMDD", required=False),
            OpenApiParameter("fields", OpenApiTypes.STR, OpenApiParameter.QUERY, description="限定返回字段列表", required=False),
            OpenApiParameter("token", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Tushare API Token", required=False),
        ],
        responses={
            200: SuccessResponseCyqPerfSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            params = {}
            for key in ("ts_code", "trade_date", "start_date", "end_date"):
                val = request.query_params.get(key)
                if val:
                    params[key] = val
            fields = request.query_params.get("fields")
            token = request.query_params.get("token")

            resp = call_tushare("cyq_perf", params=params, fields=fields, token=token, use_query=False)
            if resp.get("code") != 200:
                return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))
            data = resp.get("data") or {}
            return success_response(data, "查询每日筹码及胜率成功")
        except Exception as e:
            return error_response(f"查询每日筹码及胜率失败: {str(e)}", 500)





class LimitStepProxyView(APIView):
    """
    连板天梯直通代理接口（Tushare limit_step）

    功能：
    - 代理调用 Tushare `limit_step`，返回每日涨停股票连板次数记录。

    参数：
    - trade_date, ts_code, start_date, end_date, nums（均可选）
    - fields/token（可选）

    返回值：
    - interface 固定为 "limit_step"；records 字段与文档一致。

    事件：无。
    """

    @extend_schema(
        summary="连板天梯直通代理",
        description="Tushare limit_step 的代理接口，统一返回格式。",
        tags=["Tushare Proxy"],
        parameters=[
            OpenApiParameter(name="trade_date", description="交易日期 YYYYMMDD", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="ts_code", description="股票代码", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="start_date", description="开始日期", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="end_date", description="结束日期", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="nums", description="连板次数，支持多个（如 2,3）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="fields", description="字段列表（逗号分隔）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="token", description="Tushare Token（覆盖环境变量）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
        ],
        responses={
            200: SuccessResponseLimitStepSerializer,
            400: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            params = {}
            for key in ("trade_date", "ts_code", "start_date", "end_date", "nums"):
                val = request.query_params.get(key)
                if val:
                    params[key] = val
            fields = request.query_params.get("fields")
            token = request.query_params.get("token")

            resp = call_tushare("limit_step", params=params, fields=fields, token=token, use_query=False)
            if resp.get("code") != 200:
                return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))

            data = resp.get("data") or {}
            return success_response(data, "查询连板天梯成功")
        except Exception as e:
            return error_response(f"查询连板天梯失败: {str(e)}", 500)


class HmDetailProxyView(APIView):
    """
    游资交易每日明细直通代理接口（Tushare hm_detail）

    功能：
    - 代理调用 Tushare `hm_detail`，返回每日游资交易明细。

    参数：
    - trade_date, ts_code, hm_name, start_date, end_date（可选）
    - fields/token（可选）

    返回值：
    - interface 固定为 "hm_detail"；records 字段与文档一致。

    事件：无。
    """

    @extend_schema(
        summary="游资每日明细直通代理",
        description="Tushare hm_detail 的代理接口，统一返回格式。",
        tags=["Tushare Proxy"],
        parameters=[
            OpenApiParameter(name="trade_date", description="交易日期 YYYYMMDD", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="ts_code", description="股票代码", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="hm_name", description="游资名称", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="start_date", description="开始日期 YYYYMMDD", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="end_date", description="结束日期 YYYYMMDD", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="fields", description="字段列表（逗号分隔）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="token", description="Tushare Token（覆盖环境变量）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
        ],
        responses={
            200: SuccessResponseHmDetailSerializer,
            400: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            params = {}
            for key in ("trade_date", "ts_code", "hm_name", "start_date", "end_date"):
                val = request.query_params.get(key)
                if val:
                    params[key] = val
            fields = request.query_params.get("fields")
            token = request.query_params.get("token")

            resp = call_tushare("hm_detail", params=params, fields=fields, token=token, use_query=False)
            if resp.get("code") != 200:
                return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))

            data = resp.get("data") or {}
            return success_response(data, "查询游资每日明细成功")
        except Exception as e:
            return error_response(f"查询游资每日明细失败: {str(e)}", 500)


class MybookDirectoryView(APIView):
    """
    GitHub mybook 仓库目录浏览接口。
    """

    @extend_schema(
        summary="GitHub mybook 目录浏览",
        description="列出配置仓库指定目录下的文件和子目录，供前端做文档树。",
        tags=["GitHub Mybook"],
        parameters=[
            OpenApiParameter(name="path", description="仓库内目录路径，空值表示根目录", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
        ],
        responses={200: dict, 400: ErrorResponseSerializer, 500: ErrorResponseSerializer},
    )
    def get(self, request):
        try:
            path = request.query_params.get("path", "")
            data = github_markdown_service.list_directory(path=path)
            return success_response(data, "查询 GitHub mybook 目录成功")
        except ValueError as e:
            return error_response(f"参数格式错误: {str(e)}", 400)
        except RuntimeError as e:
            return error_response(str(e), 500)
        except Exception as e:
            return error_response(f"查询 GitHub mybook 目录失败: {str(e)}", 500)


class MybookMarkdownFilesView(APIView):
    """
    GitHub mybook Markdown 文件列表接口。
    """

    @extend_schema(
        summary="GitHub mybook Markdown 文件列表",
        description="列出配置仓库中的 Markdown 文件，可递归扫描，供前端展示文档列表。",
        tags=["GitHub Mybook"],
        parameters=[
            OpenApiParameter(name="prefix", description="仓库内路径前缀，空值表示全仓库", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="recursive", description="是否递归扫描，默认 true", required=False, type=OpenApiTypes.BOOL, location=OpenApiParameter.QUERY),
        ],
        responses={200: dict, 400: ErrorResponseSerializer, 500: ErrorResponseSerializer},
    )
    def get(self, request):
        try:
            prefix = request.query_params.get("prefix", "")
            recursive_text = request.query_params.get("recursive", "true").strip().lower()
            recursive = recursive_text not in ("0", "false", "no", "off")
            data = github_markdown_service.list_markdown_files(prefix=prefix, recursive=recursive)
            return success_response(data, "查询 GitHub mybook Markdown 文件列表成功")
        except ValueError as e:
            return error_response(f"参数格式错误: {str(e)}", 400)
        except RuntimeError as e:
            return error_response(str(e), 500)
        except Exception as e:
            return error_response(f"查询 GitHub mybook Markdown 文件列表失败: {str(e)}", 500)


class MybookMarkdownContentView(APIView):
    """
    GitHub mybook Markdown 文件内容接口。
    """

    @extend_schema(
        summary="GitHub mybook Markdown 内容",
        description="读取配置仓库中指定 Markdown 文件内容，供前端渲染。",
        tags=["GitHub Mybook"],
        parameters=[
            OpenApiParameter(name="path", description="仓库内 Markdown 文件路径", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="max_chars", description="最大返回字符数，默认 200000，最大 500000", required=False, type=OpenApiTypes.INT, location=OpenApiParameter.QUERY),
        ],
        responses={200: dict, 400: ErrorResponseSerializer, 500: ErrorResponseSerializer},
    )
    def get(self, request):
        try:
            path = request.query_params.get("path", "")
            max_chars = int(request.query_params.get("max_chars", 200000))
            data = github_markdown_service.get_markdown_content(path=path, max_chars=max_chars)
            return success_response(data, "查询 GitHub mybook Markdown 内容成功")
        except ValueError as e:
            return error_response(f"参数格式错误: {str(e)}", 400)
        except RuntimeError as e:
            return error_response(str(e), 500)
        except Exception as e:
            return error_response(f"查询 GitHub mybook Markdown 内容失败: {str(e)}", 500)
