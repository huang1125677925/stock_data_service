from rest_framework.views import APIView
from common.response import success_response, error_response
from common.tushare_proxy import call_tushare
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from .serializers import (
    SuccessResponseIndexBasicSerializer,
    SuccessResponseIndexDailySerializer,
    SuccessResponseIndexWeightSerializer,
    SuccessResponseDcDailySerializer,
    SuccessResponseDcIndexSerializer,
    SuccessResponseGitInfoSerializer,
    ErrorResponseSerializer,
)


class IndexBasicProxyView(APIView):
    """
    指数基本信息直通代理接口（Tushare index_basic）

    说明：遵循架构规范，外部数据获取逻辑依赖 scheduled_tasks 下的模块与 common 中的代理；
    本接口接受与 Tushare 文档一致的查询参数，并返回记录字段与文档一致，外层响应使用统一 success_response/error_response。

    支持参数（与 Tushare 文档一致）：
    - ts_code (str, 可选): 指数代码
    - name (str, 可选): 指数简称
    - market (str, 可选): 市场（MSCI/CSI/SSE/SZSE/CICC/SW/OTH）
    - publisher (str, 可选): 发布方
    - category (str, 可选): 指数类别
    - fields (str, 可选): 返回字段列表，逗号分隔
    - token (str, 可选): Tushare Token（覆盖环境变量）

    返回值（统一外层结构）：
    - code (int): 状态码，成功为 200
    - message (str): 提示信息
    - data (object): 数据对象
      - interface (str): 固定为 "index_basic"
      - count (int): 记录数
      - records (list[object]): 记录列表，字段与 Tushare 对齐，常见字段：
        - ts_code (str): TS代码
        - name (str): 简称
        - fullname (str): 全称
        - market (str): 市场
        - publisher (str): 发布方
        - index_type (str): 指数风格
        - category (str): 指数类别
        - base_date (str): 基期
        - base_point (float): 基点
        - list_date (str): 发布日期
        - weight_rule (str): 加权方式
        - desc (str): 描述
        - exp_date (str): 终止日期
    错误返回：error_response，包含 code/message/error。
    """

    @extend_schema(
        summary="指数基本信息直通代理",
        description="Tushare index_basic 的代理接口，统一返回格式。",
        tags=["Tushare Proxy"],
        parameters=[
            OpenApiParameter(name="ts_code", description="指数代码", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="name", description="指数简称", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="market", description="市场：MSCI/CSI/SSE/SZSE/CICC/SW/OTH", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="publisher", description="发布方", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="category", description="指数类别", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="fields", description="返回字段列表，逗号分隔", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="token", description="Tushare Token（覆盖环境变量）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
        ],
        responses={
            200: SuccessResponseIndexBasicSerializer,
            400: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        """
        GET 请求

        查询参数：同类 docstring 中“支持参数”说明；常用示例：
        - 仅查询申万指数基本信息：market=SW
        - 限定字段返回：fields=ts_code,name,market
        - 指定 token 调试：token=<your_tushare_token>

        返回：success_response(data, message)
        - data.interface = "index_basic"
        - data.count = 记录数
        - data.records = 记录数组（字段受 fields 控制）
        """
        try:
            params = {}
            for key in ("ts_code", "name", "market", "publisher", "category"):
                val = request.query_params.get(key)
                if val:
                    params[key] = val

            fields = request.query_params.get("fields")
            token = request.query_params.get("token")

            resp = call_tushare("index_basic", params=params, fields=fields, token=token, use_query=False)
            if resp.get("code") != 200:
                return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))

            # 直接返回记录，与Tushare字段一致，外层包裹统一响应格式
            data = resp.get("data") or {}
            return success_response(data, "查询指数基本信息成功")

        except Exception as e:
            return error_response(f"查询指数基本信息失败: {str(e)}", 500)


class IndexDailyProxyView(APIView):
    """
    指数日线行情直通代理接口（Tushare index_daily）

    支持参数（与Tushare文档一致）：
    - ts_code (str, 必选): 指数代码
    - trade_date (str, 可选): 交易日期 YYYYMMDD
    - start_date (str, 可选): 开始日期 YYYYMMDD
    - end_date (str, 可选): 结束日期 YYYYMMDD
    - fields (str, 可选): 字段列表（逗号分隔）
    - token (str, 可选): 覆盖环境中的 Tushare Token

    返回值（统一外层结构）：
    - code (int), message (str)
    - data (object):
      - interface (str): 固定为 "index_daily"
      - count (int): 记录数
      - records (list[object]): 与 Tushare 字段一致，常见字段：
        - ts_code (str), trade_date (str), close (float), open (float),
          high (float), low (float), pre_close (float), change (float),
          pct_chg (float), vol (float), amount (float)
    错误返回：error_response。
    """

    @extend_schema(
        summary="指数日线行情直通代理",
        description="Tushare index_daily 的代理接口，统一返回格式。",
        tags=["Tushare Proxy"],
        parameters=[
            OpenApiParameter(name="ts_code", description="指数代码（必填）", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="trade_date", description="交易日期 YYYYMMDD", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="start_date", description="开始日期 YYYYMMDD", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="end_date", description="结束日期 YYYYMMDD", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="fields", description="字段列表（逗号分隔）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="token", description="Tushare Token（覆盖环境变量）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
        ],
        responses={
            200: SuccessResponseIndexDailySerializer,
            400: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        """
        GET 请求

        必填参数：ts_code；可选：trade_date/start_date/end_date/fields/token。
        示例：
        - 按区间查询：ts_code=399300.SZ&start_date=20180101&end_date=20181010
        - 限定字段：fields=ts_code,trade_date,close

        返回：success_response(data, "查询指数日线行情成功")
        - data.interface = "index_daily"
        - data.count = 记录数
        - data.records = 记录数组
        """
        try:
            ts_code = request.query_params.get("ts_code")
            if not ts_code:
                return error_response("缺少必填参数: ts_code", 400)

            params = {"ts_code": ts_code}
            for key in ("trade_date", "start_date", "end_date"):
                val = request.query_params.get(key)
                if val:
                    params[key] = val

            fields = request.query_params.get("fields")
            token = request.query_params.get("token")

            resp = call_tushare("index_daily", params=params, fields=fields, token=token, use_query=False)
            if resp.get("code") != 200:
                return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))

            data = resp.get("data") or {}
            return success_response(data, "查询指数日线行情成功")

        except Exception as e:
            return error_response(f"查询指数日线行情失败: {str(e)}", 500)


class IndexWeightProxyView(APIView):
    """
    指数成分和权重直通代理接口（Tushare index_weight）

    支持参数（与Tushare文档一致）：
    - index_code (str, 必选): 指数代码
    - trade_date (str, 可选): 交易日期 YYYYMMDD
    - start_date (str, 可选): 开始日期 YYYYMMDD
    - end_date (str, 可选): 结束日期 YYYYMMDD
    - fields (str, 可选): 字段列表（逗号分隔）
    - token (str, 可选): 覆盖环境中的 Tushare Token

    返回值（统一外层结构）：
    - code (int), message (str)
    - data (object):
      - interface (str): 固定为 "index_weight"
      - count (int): 记录数
      - records (list[object]): 与 Tushare 字段一致：
        - index_code (str): 指数代码
        - con_code (str): 成分代码
        - trade_date (str): 交易日期
        - weight (float): 权重
    错误返回：error_response。
    """

    @extend_schema(
        summary="指数成分和权重直通代理",
        description="Tushare index_weight 的代理接口，统一返回格式。",
        tags=["Tushare Proxy"],
        parameters=[
            OpenApiParameter(name="index_code", description="指数代码（必填）", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="trade_date", description="交易日期 YYYYMMDD", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="start_date", description="开始日期 YYYYMMDD", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="end_date", description="结束日期 YYYYMMDD", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="fields", description="字段列表（逗号分隔）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="token", description="Tushare Token（覆盖环境变量）", required=False, type=OpenApiTypes.STR, location=OpenApiParameter.QUERY),
        ],
        responses={
            200: SuccessResponseIndexWeightSerializer,
            400: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        """
        GET 请求

        必填参数：index_code；可选：trade_date/start_date/end_date/fields/token。
        示例：
        - 查询沪深300权重：index_code=399300.SZ&start_date=20180901&end_date=20180930
        - 限定字段：fields=index_code,con_code,trade_date,weight

        返回：success_response(data, "查询指数成分和权重成功")
        - data.interface = "index_weight"
        - data.count = 记录数
        - data.records = 记录数组
        """
        try:
            index_code = request.query_params.get("index_code")
            if not index_code:
                return error_response("缺少必填参数: index_code", 400)

            params = {"index_code": index_code}
            for key in ("trade_date", "start_date", "end_date"):
                val = request.query_params.get(key)
                if val:
                    params[key] = val

            fields = request.query_params.get("fields")
            token = request.query_params.get("token")

            resp = call_tushare("index_weight", params=params, fields=fields, token=token, use_query=False)
            if resp.get("code") != 200:
                return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))

            data = resp.get("data") or {}
            return success_response(data, "查询指数成分和权重成功")

        except Exception as e:
            return error_response(f"查询指数成分和权重失败: {str(e)}", 500)


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