import concurrent.futures
from datetime import datetime, timedelta
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from common.response import success_response, error_response
from common.tushare_proxy import call_tushare
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from .sw_valuation_analysis import run_sw_valuation_analysis
from .serializers import (
    SuccessResponseIndexMemberAllSerializer,
    SuccessResponseIndexClassifySerializer,
    SuccessResponseSwDailySerializer,
    SuccessResponseSwValuationAnalysisSerializer,
    SuccessResponseIndexBasicSerializer,
    SuccessResponseIndexDailySerializer,
    SuccessResponseIndexWeightSerializer,
    SuccessResponseIndexDailybasicSerializer,
    SuccessResponseIndexValuationSummarySerializer,
    SuccessResponseMajorIndexDailySerializer,
    ErrorResponseSerializer,
)

from .utils import replace_nan


class IndexMemberAllProxyView(APIView):
    """
    申万行业成分构成(分级)查询接口
    功能：按分级或TS代码获取申万行业成分构成。
    参数（Query）：
    - l1_code(str, 可选)：一级行业代码
    - l2_code(str, 可选)：二级行业代码
    - l3_code(str, 可选)：三级行业代码
    - ts_code(str, 可选)：行业或指数TS代码
    - is_new(int, 可选)：是否最新：1是/0否
    - fields(str, 可选)：限定返回字段列表
    - token(str, 可选)：Tushare API Token
    返回值：调用 success_response 返回数据；错误时调用 error_response。
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="申万行业成分构成(分级)",
        description=(
            "按分级或 TS 代码获取申万行业成分股（谁属于哪个行业）。\n"
            "不含行业指数涨跌幅或 PE/PB；行业指数行情请用「申万行业日线行情」sw_daily。\n"
            "参数（Query）：l1_code, l2_code, l3_code, ts_code, is_new, fields, token。\n"
            "统一响应结构（success_response），data 为成分列表。"
        ),
        tags=["index"],
        parameters=[
            OpenApiParameter("l1_code", OpenApiTypes.STR, OpenApiParameter.QUERY, description="一级行业代码", required=False),
            OpenApiParameter("l2_code", OpenApiTypes.STR, OpenApiParameter.QUERY, description="二级行业代码", required=False),
            OpenApiParameter("l3_code", OpenApiTypes.STR, OpenApiParameter.QUERY, description="三级行业代码", required=False),
            OpenApiParameter("ts_code", OpenApiTypes.STR, OpenApiParameter.QUERY, description="行业或指数TS代码", required=False),
            OpenApiParameter("is_new", OpenApiTypes.INT, OpenApiParameter.QUERY, description="是否最新：1是/0否", required=False),
            OpenApiParameter("fields", OpenApiTypes.STR, OpenApiParameter.QUERY, description="限定返回字段列表", required=False),
            OpenApiParameter("token", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Tushare API Token", required=False),
        ],
        responses={
            200: SuccessResponseIndexMemberAllSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            params = {}
            for key in ("l1_code", "l2_code", "l3_code", "ts_code", "is_new"):
                val = request.query_params.get(key)
                if val:
                    params[key] = val
            fields = request.query_params.get("fields")
            token = request.query_params.get("token")

            resp = call_tushare("index_member_all", params=params, fields=fields, token=token, use_query=False)
            if resp.get("code") != 200:
                return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))
            data = resp.get("data") or {}
            data = replace_nan(data)
            return success_response(data, "查询申万行业成分构成成功")
        except Exception as e:
            return error_response(f"查询申万行业成分构成失败: {str(e)}", 500)


class IndexClassifyProxyView(APIView):
    """
    申万行业分类查询接口
    功能：获取申万行业分类信息。
    参数（Query）：
    - index_code(str, 可选)：指数代码
    - level(str, 可选)：行业分级（L1/L2/L3）
    - parent_code(str, 可选)：父级代码（一级为0）
    - src(str, 可选)：指数来源（SW2014/SW2021），默认 SW2021
    返回值：调用 success_response 返回数据；错误时调用 error_response。
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="申万行业分类",
        description=(
            "仅返回申万行业的分类树与行业代码（index_classify），无行情、无涨跌、无成交量。\n"
            "用户要「申万行业数据 / 行业表现 / 行业分析」时，应主要使用「申万行业日线行情」或估值分析接口，勿只靠本接口。\n"
            "参数（Query）：index_code, level, parent_code, src（取值 SW2014 或 SW2021，勿使用 SW）。\n"
            "默认 src 为 SW2021。\n"
            "统一响应结构（success_response），data 为分类列表。"
        ),
        tags=["index"],
        parameters=[
            OpenApiParameter("index_code", OpenApiTypes.STR, OpenApiParameter.QUERY, description="指数代码", required=False),
            OpenApiParameter("level", OpenApiTypes.STR, OpenApiParameter.QUERY, description="行业分级：L1/L2/L3", required=False),
            OpenApiParameter("parent_code", OpenApiTypes.STR, OpenApiParameter.QUERY, description="父级代码（一级为0）", required=False),
            OpenApiParameter("src", OpenApiTypes.STR, OpenApiParameter.QUERY, description="指数来源：SW2014/SW2021，默认 SW2021", required=False),
        ],
        responses={
            200: SuccessResponseIndexClassifySerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            params = {}
            # 处理查询参数
            for key in ("index_code", "level", "parent_code", "src"):
                val = request.query_params.get(key)
                if val:
                    params[key] = val
            
            # 设置默认值
            if "src" not in params:
                params["src"] = "SW2021"

            resp = call_tushare("index_classify", params=params, use_query=False)
            if resp.get("code") != 200:
                return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))
            data = resp.get("data") or {}
            data = replace_nan(data)
            return success_response(data, "查询申万行业分类成功")
        except Exception as e:
            return error_response(f"查询申万行业分类失败: {str(e)}", 500)


class SwDailyProxyView(APIView):
    """
    申万行业日线行情查询接口
    功能：获取申万行业日线行情（默认是申万2021版行情）。
    参数（Query）：
    - ts_code(str, 可选)：行业代码
    - trade_date(str, 可选)：交易日期
    - start_date(str, 可选)：开始日期
    - end_date(str, 可选)：结束日期
    - fields(str, 可选)：限定返回字段列表
    - token(str, 可选)：Tushare API Token
    返回值：调用 success_response 返回数据；错误时调用 error_response。
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="申万行业日线行情",
        description=(
            "申万行业指数日线 sw_daily：行业涨跌幅、开高低收、成交量、PE/PB 等，是「申万行业数据/行业表现」类问题的首选行情源。\n"
            "与「指数日线行情」index_daily 不同：index_daily 不包含申万行业指数；申万行业代码如 801xxx.SI 请用本接口。\n"
            "与「申万行业分类」不同：分类接口只有代码表，没有价格。\n"
            "参数（Query）：ts_code, trade_date, start_date, end_date, fields, token。\n"
            "统一响应结构（success_response），data 为行情列表。"
        ),
        tags=["index"],
        parameters=[
            OpenApiParameter("ts_code", OpenApiTypes.STR, OpenApiParameter.QUERY, description="行业代码", required=False),
            OpenApiParameter("trade_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="交易日期", required=False),
            OpenApiParameter("start_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="开始日期", required=False),
            OpenApiParameter("end_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="结束日期", required=False),
            OpenApiParameter("fields", OpenApiTypes.STR, OpenApiParameter.QUERY, description="限定返回字段列表", required=False),
            OpenApiParameter("token", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Tushare API Token", required=False),
        ],
        responses={
            200: SuccessResponseSwDailySerializer,
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

            resp = call_tushare("sw_daily", params=params, fields=fields, token=token, use_query=False)
            if resp.get("code") != 200:
                return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))
            data = resp.get("data") or {}
            data = replace_nan(data)
            return success_response(data, "查询申万行业日线行情成功")
        except Exception as e:
            return error_response(f"查询申万行业日线行情失败: {str(e)}", 500)


class SwValuationAnalysisView(APIView):
    """
    申万行业估值分析接口
    功能：获取指定level、日期范围的所有行业PE/PB现值及分位数。
    参数（Query）：
    - level(str, 必选)：行业分级（L1/L2/L3）
    - start_date(str, 必选)：开始日期 (YYYYMMDD)
    - end_date(str, 必选)：结束日期 (YYYYMMDD)
    - index_codes(str, 可选)：行业代码列表，逗号分隔；若提供则优先使用该列表
    """
    permission_classes = [AllowAny]

    @extend_schema(
        summary="申万行业估值分析",
        description=(
            "在指定日期区间内，汇总申万行业 PE/PB 现值及历史分位数（适合「行业贵不贵、估值分位」类分析）。\n"
            "底层使用 sw_daily；需要原始逐日 K 线或单日全行业截面时直接调申万行业日线接口。\n"
            "仅需行业代码层级结构时使用申万行业分类接口。"
        ),
        tags=["index"],
        parameters=[
            OpenApiParameter("level", OpenApiTypes.STR, OpenApiParameter.QUERY, description="行业分级：L1/L2/L3", required=True),
            OpenApiParameter("start_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="开始日期 (YYYYMMDD)", required=True),
            OpenApiParameter("end_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="结束日期 (YYYYMMDD)", required=True),
            OpenApiParameter("index_codes", OpenApiTypes.STR, OpenApiParameter.QUERY, description="行业代码列表，逗号分隔；若提供则优先使用", required=False),
        ],
        responses={
            200: SuccessResponseSwValuationAnalysisSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            out = run_sw_valuation_analysis(
                request.query_params.get("start_date") or "",
                request.query_params.get("end_date") or "",
                level=request.query_params.get("level"),
                index_codes_str=request.query_params.get("index_codes"),
            )
            if out.code == 200:
                return success_response(out.data, out.message)
            return error_response(out.message, out.code)
        except Exception as e:
            return error_response(f"查询申万行业估值分析失败: {str(e)}", 500)

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
        description=(
            "指数元数据目录 index_basic（名称、发布方、基期等），非涨跌幅行情。\n"
            "可筛选 market=SW 查看申万指数条目；分析申万行业涨跌与估值请配合申万行业日线或估值分析接口。"
        ),
        tags=["index"],
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
            data = replace_nan(data)
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
        description=(
            "通用指数日线 index_daily（如沪深300、上证50）。\n"
            "按 Tushare 文档，本接口不包含申万行业指数日线；申万行业代码请使用「申万行业日线行情」接口。"
        ),
        tags=["index"],
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
            data = replace_nan(data)
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
        tags=["index"],
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
            data = replace_nan(data)
            return success_response(data, "查询指数成分和权重成功")

        except Exception as e:
            return error_response(f"查询指数成分和权重失败: {str(e)}", 500)


class IndexDailybasicProxyView(APIView):
    """
    大盘指数每日指标代理接口

    功能：代理调用 Tushare 接口 `index_dailybasic`，获取大盘指数每日指标。
    参数：支持 `trade_date`、`ts_code`、`start_date`、`end_date`、`fields`、`token`（至少提供 trade_date 或 ts_code）。
    返回值：统一响应结构，`data.interface = "index_dailybasic"`。
    事件：无。
    """

    @extend_schema(
        summary="大盘指数每日指标",
        description="获取大盘指数每日指标，至少提供 trade_date 或 ts_code。",
        tags=["index"],
        parameters=[
            OpenApiParameter("trade_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="交易日期YYYYMMDD", required=False),
            OpenApiParameter("ts_code", OpenApiTypes.STR, OpenApiParameter.QUERY, description="指数TS代码", required=False),
            OpenApiParameter("start_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="开始日期YYYYMMDD", required=False),
            OpenApiParameter("end_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="结束日期YYYYMMDD", required=False),
            OpenApiParameter("fields", OpenApiTypes.STR, OpenApiParameter.QUERY, description="限定返回字段列表", required=False),
            OpenApiParameter("token", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Tushare API Token", required=False),
        ],
        responses={
            200: SuccessResponseIndexDailybasicSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            trade_date = request.query_params.get("trade_date")
            ts_code = request.query_params.get("ts_code")
            if not (trade_date or ts_code):
                return error_response("至少提供 trade_date 或 ts_code", 400)

            params = {}
            for key in ("trade_date", "ts_code", "start_date", "end_date"):
                val = request.query_params.get(key)
                if val:
                    params[key] = val
            fields = request.query_params.get("fields")
            token = request.query_params.get("token")

            resp = call_tushare("index_dailybasic", params=params, fields=fields, token=token, use_query=False)
            if resp.get("code") != 200:
                return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))
            data = resp.get("data") or {}
            data = replace_nan(data)
            return success_response(data, "查询大盘指数每日指标成功")
        except Exception as e:
            return error_response(f"查询大盘指数每日指标失败: {str(e)}", 500)


class IndexValuationSummaryProxyView(APIView):
    """
    指数估值摘要接口

    功能：获取主要指数的当前PE/PB/市值，以及5年和10年的PE/PB分位数。
    参数：无（固定返回特定指数集合）。
    返回值：包含各指数当前估值及历史分位数的列表。
    事件：无。
    """
    @extend_schema(
        summary="指数估值摘要",
        description="获取主要指数（上证综指、沪深300等）的当前估值及历史分位数。",
        tags=["index"],
        responses={
            200: SuccessResponseIndexValuationSummarySerializer,
            500: ErrorResponseSerializer,
        }
    )
    def get(self, request):
        try:
            from django.core.cache import cache
            import pandas as pd
            import numpy as np
            
            cache_key = "index_valuation_summary_v1"
            cached_data = cache.get(cache_key)
            if cached_data:
                 return success_response({"items": cached_data}, "获取指数估值摘要成功(Cached)")

            indices = [
               { 'label': '上证综指', 'value': '000001.SH' }, 
               { 'label': '沪深300', 'value': '000300.SH' }, 
               { 'label': '中证500', 'value': '000905.SH' }, 
               { 'label': '深证成指', 'value': '399001.SZ' }, 
               { 'label': '中小板指', 'value': '399005.SZ' }, 
               { 'label': '创业板指', 'value': '399006.SZ' }, 
               { 'label': '深证创新', 'value': '399016.SZ' }, 
               { 'label': '沪深300(深)', 'value': '399300.SZ' },
            ]
            
            start_date_10y = (datetime.now() - timedelta(days=365*10 + 100)).strftime('%Y%m%d')
            
            def fetch_process(idx):
                ts_code = idx['value']
                # Fetch 10 years + buffer
                resp = call_tushare(
                    "index_dailybasic", 
                    params={"ts_code": ts_code, "start_date": start_date_10y}, 
                    fields="trade_date,pe,pe_ttm,pb,total_mv"
                )
                
                if resp.get("code") != 200:
                    return None
                
                records = resp.get("data", {}).get("records", [])
                if not records:
                    return None
                    
                df = pd.DataFrame(records)
                cols = ['pe', 'pb', 'total_mv']
                for c in cols:
                    if c in df.columns:
                        df[c] = pd.to_numeric(df[c], errors='coerce')
                
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                df = df.sort_values('trade_date')
                
                if df.empty:
                    return None
                    
                latest = df.iloc[-1]
                latest_date = latest['trade_date']
                
                current_pe = latest.get('pe')
                current_pb = latest.get('pb')
                current_mv = latest.get('total_mv')
                
                # 5 Year window
                date_5y = latest_date - pd.Timedelta(days=365*5)
                df_5y = df[df['trade_date'] > date_5y]
                
                # 10 Year window (already fetched approx 10y)
                df_10y = df 
                
                def calc_quantile(series, value):
                    if value is None or np.isnan(value) or series.empty:
                        return None
                    valid = series.dropna()
                    if valid.empty:
                        return None
                    return (valid < value).mean()
                    
                pe_q5 = calc_quantile(df_5y['pe'], current_pe)
                pb_q5 = calc_quantile(df_5y['pb'], current_pb)
                pe_q10 = calc_quantile(df_10y['pe'], current_pe)
                pb_q10 = calc_quantile(df_10y['pb'], current_pb)
                
                return {
                    "label": idx['label'],
                    "value": ts_code,
                    "pe": current_pe,
                    "pb": current_pb,
                    "total_mv": current_mv,
                    "pe_quantile_5y": pe_q5,
                    "pb_quantile_5y": pb_q5,
                    "pe_quantile_10y": pe_q10,
                    "pb_quantile_10y": pb_q10,
                    "trade_date": latest_date.strftime('%Y%m%d')
                }

            results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(fetch_process, idx) for idx in indices]
                for f in concurrent.futures.as_completed(futures):
                    res = f.result()
                    if res:
                        results.append(res)
            
            results_map = {r['value']: r for r in results}
            ordered_results = []
            for idx in indices:
                if idx['value'] in results_map:
                    ordered_results.append(results_map[idx['value']])
            
            ordered_results = replace_nan(ordered_results)
            
            if ordered_results:
                # 缓存4小时
                cache.set(cache_key, ordered_results, 60 * 60 * 4)
                
            return success_response({"items": ordered_results}, "获取指数估值摘要成功")
        except Exception as e:
            return error_response(f"获取指数估值摘要失败: {str(e)}", 500)


class MarketCombinedDailyBasicView(APIView):
    """
    全市场综合指标接口
    
    功能：利用上证综指(000001.SH)和深证成指(399001.SZ)计算全市场综合指标。
    参数：
    - trade_date(str, 可选): 交易日期
    - start_date(str, 可选): 开始日期
    - end_date(str, 可选): 结束日期
    - token(str, 可选): Tushare API Token
    """
    
    @extend_schema(
        summary="全市场综合指标",
        description="利用上证综指和深证成指计算全市场综合指标。",
        tags=["index"],
        parameters=[
            OpenApiParameter("trade_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="交易日期YYYYMMDD", required=False),
            OpenApiParameter("start_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="开始日期YYYYMMDD", required=False),
            OpenApiParameter("end_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="结束日期YYYYMMDD", required=False),
            OpenApiParameter("token", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Tushare API Token", required=False),
        ],
        responses={
            200: SuccessResponseIndexDailybasicSerializer, 
            500: ErrorResponseSerializer,
        }
    )
    def get(self, request):
        try:
            import pandas as pd
            import numpy as np
            
            trade_date = request.query_params.get("trade_date")
            start_date = request.query_params.get("start_date")
            end_date = request.query_params.get("end_date")
            token = request.query_params.get("token")
            
            fields = "ts_code,trade_date,total_mv,float_mv,total_share,float_share,free_share,turnover_rate,turnover_rate_f,pe,pe_ttm,pb"
            
            targets = ["000001.SH", "399001.SZ"]
            all_records = []
            for ts in targets:
                params = {"ts_code": ts}
                if trade_date:
                    params["trade_date"] = trade_date
                if start_date:
                    params["start_date"] = start_date
                if end_date:
                    params["end_date"] = end_date
                resp = call_tushare("index_dailybasic", params=params, fields=fields, token=token, use_query=False)
                if resp.get("code") != 200:
                    return error_response(resp.get("message", "Tushare调用失败"), resp.get("code", 500), error=resp.get("error"))
                data = resp.get("data")
                recs = data.get("records", []) if isinstance(data, dict) else []
                if recs:
                    all_records.extend(recs)
            
            if not all_records:
                return success_response({"items": [], "fields": fields.split(',')}, "查询成功(无数据)")

            df = pd.DataFrame(all_records)
            
            # Convert numeric columns
            numeric_cols = ['total_mv', 'float_mv', 'total_share', 'float_share', 'free_share', 
                            'turnover_rate', 'turnover_rate_f', 'pe', 'pe_ttm', 'pb']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # Group by trade_date
            grouped = df.groupby('trade_date')
            
            results = []
            
            for date, group in grouped:
                # Sums
                total_mv = group['total_mv'].sum()
                float_mv = group['float_mv'].sum()
                total_share = group['total_share'].sum()
                float_share = group['float_share'].sum()
                free_share = group['free_share'].sum()
                
                # PE/PB Calculation (Harmonic Mean weighted by MV effectively)
                # PE = Total MV / Total Earnings
                # Earnings = MV / PE
                earnings_sum = 0
                earnings_ttm_sum = 0
                net_assets_sum = 0
                
                for _, row in group.iterrows():
                    pe = row.get('pe')
                    pe_ttm = row.get('pe_ttm')
                    pb = row.get('pb')
                    mv = row.get('total_mv', 0)
                    
                    if pe and pe != 0 and not np.isnan(pe):
                        earnings_sum += mv / pe
                    if pe_ttm and pe_ttm != 0 and not np.isnan(pe_ttm):
                        earnings_ttm_sum += mv / pe_ttm
                    if pb and pb != 0 and not np.isnan(pb):
                        net_assets_sum += mv / pb
                        
                pe_avg = total_mv / earnings_sum if earnings_sum else None
                pe_ttm_avg = total_mv / earnings_ttm_sum if earnings_ttm_sum else None
                pb_avg = total_mv / net_assets_sum if net_assets_sum else None
                
                # Turnover Rate Calculation
                # Weighted by float share (or free share)
                implied_vol_sum = 0
                implied_vol_f_sum = 0
                
                for _, row in group.iterrows():
                    tr = row.get('turnover_rate')
                    fs = row.get('float_share', 0)
                    if tr is not None and not np.isnan(tr):
                         implied_vol_sum += tr * fs
                    
                    tr_f = row.get('turnover_rate_f')
                    frs = row.get('free_share', 0)
                    if tr_f is not None and not np.isnan(tr_f):
                         implied_vol_f_sum += tr_f * frs
                
                tr_avg = implied_vol_sum / float_share if float_share else None
                tr_f_avg = implied_vol_f_sum / free_share if free_share else None
                
                results.append({
                    "ts_code": "TOTAL_MARKET",
                    "trade_date": date,
                    "total_mv": total_mv,
                    "float_mv": float_mv,
                    "total_share": total_share,
                    "float_share": float_share,
                    "free_share": free_share,
                    "turnover_rate": round(tr_avg, 4) if tr_avg is not None else None,
                    "turnover_rate_f": round(tr_f_avg, 4) if tr_f_avg is not None else None,
                    "pe": round(pe_avg, 4) if pe_avg is not None else None,
                    "pe_ttm": round(pe_ttm_avg, 4) if pe_ttm_avg is not None else None,
                    "pb": round(pb_avg, 4) if pb_avg is not None else None,
                })
            
            # Sort by date descending
            results.sort(key=lambda x: x['trade_date'], reverse=True)
            
            # Format return to match Tushare proxy style
            return success_response({
                "interface": "market_combined_daily_basic",
                "count": len(results),
                "records": replace_nan(results)
            }, "计算全市场综合指标成功")

        except Exception as e:
            return error_response(f"计算全市场综合指标失败: {str(e)}", 500)


def _parse_code_list(raw: str | None) -> list[str]:
    """
    解析逗号分隔的代码列表

    Args:
        raw: 逗号分隔字符串（如 "000001.SH,000300.SH"），允许为空或 None

    Returns:
        解析后的代码列表（去空白、去空项、保持顺序）

    Raises:
        无（函数内部不抛异常）
    """
    if not raw:
        return []
    items = []
    for s in raw.split(","):
        s = (s or "").strip()
        if s:
            items.append(s)
    return items


def _validate_yyyymmdd(date_str: str | None, field_name: str) -> str | None:
    """
    校验 YYYYMMDD 日期字符串

    Args:
        date_str: 日期字符串
        field_name: 字段名，用于错误提示

    Returns:
        原样返回 date_str（为空则返回 None）

    Raises:
        ValueError: 当 date_str 非空且不符合 YYYYMMDD 格式时抛出
    """
    if not date_str:
        return None
    s = str(date_str).strip()
    if len(s) != 8 or not s.isdigit():
        raise ValueError(f"{field_name} 必须为 YYYYMMDD 格式")
    return s


class MajorIndexDailyProxyView(APIView):
    """
    国内 + 国际主要指数日线行情接口

    功能：同时调用 Tushare 的 index_daily（国内指数）与 index_global（国际主要指数），聚合输出主要指数日线行情。
    参数（Query）：
    - scope(str, 可选)：domestic/global/all，默认 all
    - trade_date(str, 可选)：YYYYMMDD
    - start_date(str, 可选)：YYYYMMDD
    - end_date(str, 可选)：YYYYMMDD
    - domestic_codes(str, 可选)：国内指数代码列表（逗号分隔），默认内置主要指数集合
    - global_codes(str, 可选)：国际指数代码列表（逗号分隔），默认内置主要指数集合
    - token(str, 可选)：Tushare API Token
    - domestic_fields(str, 可选)：index_daily 字段列表（逗号分隔）
    - global_fields(str, 可选)：index_global 字段列表（逗号分隔）
    返回值：success_response(data)；data.interface 固定为 "major_index_daily"，records 为聚合后的行情列表。
    异常：参数非法/拉取失败时返回 error_response。
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="国内+国际主要指数日线行情",
        description=(
            "聚合主要指数日线行情：国内走 index_daily（如 000001.SH、000300.SH），国际走 index_global（如 SPX、IXIC、HSI）。\n"
            "默认返回内置“主要指数”集合；也支持通过 domestic_codes/global_codes 自定义。\n"
            "统一响应结构（success_response），data.records 为合并后的行情记录，每条记录包含 source/domestic|global 标识。"
        ),
        tags=["index"],
        parameters=[
            OpenApiParameter("scope", OpenApiTypes.STR, OpenApiParameter.QUERY, description="范围：domestic/global/all，默认 all", required=False),
            OpenApiParameter("trade_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="交易日期 YYYYMMDD", required=False),
            OpenApiParameter("start_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="开始日期 YYYYMMDD", required=False),
            OpenApiParameter("end_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="结束日期 YYYYMMDD", required=False),
            OpenApiParameter("domestic_codes", OpenApiTypes.STR, OpenApiParameter.QUERY, description="国内指数代码列表（逗号分隔），默认内置", required=False),
            OpenApiParameter("global_codes", OpenApiTypes.STR, OpenApiParameter.QUERY, description="国际指数代码列表（逗号分隔），默认内置", required=False),
            OpenApiParameter("domestic_fields", OpenApiTypes.STR, OpenApiParameter.QUERY, description="index_daily 字段列表（逗号分隔）", required=False),
            OpenApiParameter("global_fields", OpenApiTypes.STR, OpenApiParameter.QUERY, description="index_global 字段列表（逗号分隔）", required=False),
            OpenApiParameter("token", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Tushare API Token", required=False),
        ],
        responses={
            200: SuccessResponseMajorIndexDailySerializer,
            400: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        """
        GET 请求

        查询参数：
        - scope: domestic/global/all（默认 all）
        - trade_date/start_date/end_date: YYYYMMDD
        - domestic_codes/global_codes: 逗号分隔的指数代码列表
        - token: Tushare Token
        - domestic_fields/global_fields: 字段列表（逗号分隔）

        返回：
        - success_response(data, "查询主要指数日线行情成功")
        - data.interface = "major_index_daily"
        - data.count = records 数量
        - data.records = 聚合后的行情记录数组
        - data.meta = scope、codes、errors（如有）
        """
        try:
            scope = (request.query_params.get("scope") or "all").strip()
            if scope not in ("all", "domestic", "global"):
                return error_response("参数 scope 仅支持 domestic/global/all", 400)

            trade_date = _validate_yyyymmdd(request.query_params.get("trade_date"), "trade_date")
            start_date = _validate_yyyymmdd(request.query_params.get("start_date"), "start_date")
            end_date = _validate_yyyymmdd(request.query_params.get("end_date"), "end_date")

            token = request.query_params.get("token")

            default_domestic = [
                {"ts_code": "000001.SH", "name": "上证综指"},
                {"ts_code": "000300.SH", "name": "沪深300"},
                {"ts_code": "000905.SH", "name": "中证500"},
                {"ts_code": "000016.SH", "name": "上证50"},
                {"ts_code": "399001.SZ", "name": "深证成指"},
                {"ts_code": "399006.SZ", "name": "创业板指"},
                {"ts_code": "399107.SZ", "name": "深证A指"},
            ]
            default_global = [
                {"ts_code": "SPX", "name": "标普500指数"},
                {"ts_code": "IXIC", "name": "纳斯达克指数"},
                {"ts_code": "DJI", "name": "道琼斯工业指数"},
                {"ts_code": "HSI", "name": "恒生指数"},
                {"ts_code": "HKTECH", "name": "恒生科技指数"},
                {"ts_code": "XIN9", "name": "富时中国A50指数"},
                {"ts_code": "N225", "name": "日经225指数"},
                {"ts_code": "FTSE", "name": "富时100指数"},
                {"ts_code": "GDAXI", "name": "德国DAX指数"},
                {"ts_code": "TWII", "name": "台湾加权指数"},
            ]

            domestic_codes = _parse_code_list(request.query_params.get("domestic_codes"))
            global_codes = _parse_code_list(request.query_params.get("global_codes"))

            domestic_code_map = {x["ts_code"]: x.get("name") for x in default_domestic}
            global_code_map = {x["ts_code"]: x.get("name") for x in default_global}

            if not domestic_codes:
                domestic_codes = [x["ts_code"] for x in default_domestic]
            if not global_codes:
                global_codes = [x["ts_code"] for x in default_global]

            if scope == "domestic":
                global_codes = []
            if scope == "global":
                domestic_codes = []

            domestic_fields = request.query_params.get("domestic_fields") or "ts_code,trade_date,open,close,high,low,pre_close,change,pct_chg,vol,amount"
            global_fields = request.query_params.get("global_fields") or "ts_code,trade_date,open,close,high,low,pre_close,change,pct_chg,swing,vol,amount"

            def fetch_one(source: str, interface: str, ts_code: str, name: str | None, fields: str | None):
                """
                拉取单个指数的日线行情并打上来源标签

                Args:
                    source: 数据来源标识（domestic/global）
                    interface: Tushare 接口名（index_daily/index_global）
                    ts_code: 指数代码
                    name: 指数名称（可空）
                    fields: 字段列表（可空）

                Returns:
                    (records, error): records 为行情记录列表，error 为失败信息字典或 None

                Raises:
                    无（异常会被捕获并以 error 形式返回）
                """
                params = {"ts_code": ts_code}
                if trade_date:
                    params["trade_date"] = trade_date
                if start_date:
                    params["start_date"] = start_date
                if end_date:
                    params["end_date"] = end_date

                try:
                    resp = call_tushare(interface, params=params, fields=fields, token=token, use_query=False)
                except Exception as e:
                    return [], {"source": source, "ts_code": ts_code, "message": "Tushare调用异常", "error": str(e)}

                if resp.get("code") != 200:
                    return [], {
                        "source": source,
                        "ts_code": ts_code,
                        "message": resp.get("message", "Tushare调用失败"),
                        "code": resp.get("code", 500),
                        "error": resp.get("error"),
                    }

                data = resp.get("data") or {}
                recs = data.get("records") or []
                out = []
                for r in recs:
                    row = dict(r)
                    row["source"] = source
                    if name:
                        row["name"] = name
                    out.append(row)
                return out, None

            records = []
            errors = []

            with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
                futures = []
                for code in domestic_codes:
                    futures.append(
                        executor.submit(fetch_one, "domestic", "index_daily", code, domestic_code_map.get(code), domestic_fields)
                    )
                for code in global_codes:
                    futures.append(
                        executor.submit(fetch_one, "global", "index_global", code, global_code_map.get(code), global_fields)
                    )

                for f in concurrent.futures.as_completed(futures):
                    recs, err = f.result()
                    if recs:
                        records.extend(recs)
                    if err:
                        errors.append(err)

            if not records and errors:
                return error_response("获取主要指数日线行情失败", 500, errors=errors)

            out = {
                "interface": "major_index_daily",
                "count": len(records),
                "records": replace_nan(records),
                "meta": {
                    "scope": scope,
                    "domestic_codes": domestic_codes,
                    "global_codes": global_codes,
                    "errors": errors,
                },
            }
            return success_response(out, "查询主要指数日线行情成功")
        except ValueError as e:
            return error_response(str(e), 400)
        except Exception as e:
            return error_response(f"查询主要指数日线行情失败: {str(e)}", 500)
