"""
Tushare 直通代理接口（迁移自 scheduled_tasks）。

包含东财板块日频行情（dc_daily）、东方财富概念板块（dc_index）、
连板天梯（limit_step）三个直通代理视图，统一使用 success_response/error_response。
"""
from rest_framework import serializers
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from common.response import success_response, error_response
from common.tushare_proxy import call_tushare
from etfapp.serializers import ErrorResponseSerializer


# --- DC 概念/行业/地域板块日频行情（dc_daily） ---
class DcDailyRecordSerializer(serializers.Serializer):
    """dc_daily 记录字段序列化器（东财概念/行业/地域板块日频行情）。"""
    ts_code = serializers.CharField(required=False)
    trade_date = serializers.CharField(required=False)
    close = serializers.FloatField(required=False)
    open = serializers.FloatField(required=False)
    high = serializers.FloatField(required=False)
    low = serializers.FloatField(required=False)
    change = serializers.FloatField(required=False)
    pct_change = serializers.FloatField(required=False)
    vol = serializers.FloatField(required=False)
    amount = serializers.FloatField(required=False)
    swing = serializers.FloatField(required=False)
    turnover_rate = serializers.FloatField(required=False)


class DcDailyDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = DcDailyRecordSerializer(many=True)


class SuccessResponseDcDailySerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = DcDailyDataSerializer()


# --- 东方财富概念板块（dc_index） ---
class DcIndexRecordSerializer(serializers.Serializer):
    """dc_index 记录字段序列化器（东方财富概念板块）。"""
    ts_code = serializers.CharField(required=False)
    trade_date = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    leading = serializers.CharField(required=False)
    leading_code = serializers.CharField(required=False)
    pct_change = serializers.FloatField(required=False)
    leading_pct = serializers.FloatField(required=False)
    total_mv = serializers.FloatField(required=False)
    turnover_rate = serializers.FloatField(required=False)
    up_num = serializers.IntegerField(required=False)
    down_num = serializers.IntegerField(required=False)


class DcIndexDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = DcIndexRecordSerializer(many=True)


class SuccessResponseDcIndexSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = DcIndexDataSerializer()


# --- 连板天梯（limit_step） ---
class LimitStepRecordSerializer(serializers.Serializer):
    """limit_step 记录字段序列化器（涨停股票连板天梯）。"""
    ts_code = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    trade_date = serializers.CharField(required=False)
    nums = serializers.CharField(required=False)


class LimitStepDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = LimitStepRecordSerializer(many=True)


class SuccessResponseLimitStepSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = LimitStepDataSerializer()


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


class LimitStepProxyView(APIView):
    """
    连板天梯直通代理接口（Tushare limit_step）

    功能：
    - 代理调用 Tushare `limit_step`，返回每日涨停股票连板次数记录。

    参数：
    - trade_date, ts_code, start_date, end_date, nums（均可选）
    - fields/token（可选）
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
