import math
from datetime import datetime, timedelta
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from common.response import success_response, error_response
from common.tushare_proxy import call_tushare
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from scheduled_tasks.serializers import ErrorResponseSerializer
from .serializers import (
    SuccessResponseIndexMemberAllSerializer,
    SuccessResponseIndexClassifySerializer,
    SuccessResponseSwDailySerializer,
    SuccessResponseSwValuationAnalysisSerializer,
)


def replace_nan(obj):
    """
    递归将数据中的 NaN 替换为 None，以便 JSON 序列化。
    """
    if isinstance(obj, float) and math.isnan(obj):
        return None
    elif isinstance(obj, dict):
        return {k: replace_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_nan(item) for item in obj]
    return obj


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
            "按分级或TS代码获取申万行业成分构成。\n"
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
    - level(str, 可选)：行业分级（L1/L2/L3）
    返回值：调用 success_response 返回数据；错误时调用 error_response。
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="申万行业分类",
        description=(
            "获取申万行业分类信息。\n"
            "参数（Query）：level。\n"
            "统一响应结构（success_response），data 为分类列表。"
        ),
        tags=["index"],
        parameters=[
            OpenApiParameter("level", OpenApiTypes.STR, OpenApiParameter.QUERY, description="行业分级：L1/L2/L3", required=False),
        ],
        responses={
            200: SuccessResponseIndexClassifySerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            params = {}
            level = request.query_params.get("level")
            if level:
                params["level"] = level

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
            "获取申万行业日线行情（默认是申万2021版行情）。\n"
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
    """
    permission_classes = [AllowAny]

    @extend_schema(
        summary="申万行业估值分析",
        description="获取指定level、日期范围的所有行业PE/PB现值及分位数。",
        tags=["index"],
        parameters=[
            OpenApiParameter("level", OpenApiTypes.STR, OpenApiParameter.QUERY, description="行业分级：L1/L2/L3", required=True),
            OpenApiParameter("start_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="开始日期 (YYYYMMDD)", required=True),
            OpenApiParameter("end_date", OpenApiTypes.STR, OpenApiParameter.QUERY, description="结束日期 (YYYYMMDD)", required=True),
        ],
        responses={
            200: SuccessResponseSwValuationAnalysisSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        try:
            level = request.query_params.get("level")
            start_date = request.query_params.get("start_date")
            end_date = request.query_params.get("end_date")

            if not all([level, start_date, end_date]):
                return error_response("缺少必要参数: level, start_date, end_date", 400)

            # 1. 获取该level下的所有行业代码
            resp_classify = call_tushare("index_classify", params={"level": level}, use_query=False)
            if resp_classify.get("code") != 200:
                return error_response(f"获取行业分类失败: {resp_classify.get('message')}", 500)
            
            classify_data = resp_classify.get("data", {}).get("records", [])
            valid_codes = {item["index_code"] for item in classify_data if item.get("index_code")}
            
            if not valid_codes:
                return success_response({"interface": "sw_valuation_analysis", "count": 0, "records": []}, "该Level下无行业数据")

            # 2. 策略选择：按日期循环 vs 按代码循环
            # 计算日期跨度
            try:
                start_dt = datetime.strptime(start_date, "%Y%m%d")
                end_dt = datetime.strptime(end_date, "%Y%m%d")
                days_diff = (end_dt - start_dt).days + 1
            except ValueError:
                return error_response("日期格式错误，应为YYYYMMDD", 400)

            all_records = []
            
            # 如果天数少于行业数，按日期循环（减少API调用次数）
            # 注意：sw_daily按日期查询返回所有行业，我们需要过滤
            if days_diff < len(valid_codes):
                current_dt = start_dt
                while current_dt <= end_dt:
                    date_str = current_dt.strftime("%Y%m%d")
                    # 查询当日所有申万行业行情
                    resp_daily = call_tushare("sw_daily", params={"trade_date": date_str}, use_query=False)
                    if resp_daily.get("code") == 200:
                        daily_records = resp_daily.get("data", {}).get("records", [])
                        # 过滤出属于该level的行业
                        filtered = [r for r in daily_records if r.get("ts_code") in valid_codes]
                        all_records.extend(filtered)
                    current_dt += timedelta(days=1)
            else:
                # 按代码循环
                for code in valid_codes:
                    resp_daily = call_tushare("sw_daily", params={"ts_code": code, "start_date": start_date, "end_date": end_date}, use_query=False)
                    if resp_daily.get("code") == 200:
                        daily_records = resp_daily.get("data", {}).get("records", [])
                        all_records.extend(daily_records)
            
            # 3. 分组处理数据，计算分位数并提取最后一天数据
            final_records = []
            
            # 按 ts_code 分组
            grouped_data = {}
            for record in all_records:
                code = record.get("ts_code")
                if code:
                    if code not in grouped_data:
                        grouped_data[code] = []
                    grouped_data[code].append(record)
            
            for code, records in grouped_data.items():
                if not records:
                    continue
                
                # 按日期排序，确保最后一条是该时间窗口内的最后一天
                records.sort(key=lambda x: x.get("trade_date", ""))
                
                # 获取最后一条记录
                latest_record = records[-1]
                
                # 计算PE分位数
                pe_values = [r.get("pe") for r in records if r.get("pe") is not None]
                current_pe = latest_record.get("pe")
                if current_pe is not None and pe_values:
                    # 分位数 = (小于等于当前值的数量 / 总数量) * 100
                    count_le = sum(1 for v in pe_values if v <= current_pe)
                    latest_record["pe_percentile"] = round((count_le / len(pe_values)) * 100, 2)
                else:
                    latest_record["pe_percentile"] = None
                    
                # 计算PB分位数
                pb_values = [r.get("pb") for r in records if r.get("pb") is not None]
                current_pb = latest_record.get("pb")
                if current_pb is not None and pb_values:
                    count_le = sum(1 for v in pb_values if v <= current_pb)
                    latest_record["pb_percentile"] = round((count_le / len(pb_values)) * 100, 2)
                else:
                    latest_record["pb_percentile"] = None
                
                final_records.append(latest_record)

            # 处理NaN
            final_records = replace_nan(final_records)
            
            # 按代码排序
            final_records.sort(key=lambda x: x.get("ts_code", ""))

            result_data = {
                "interface": "sw_valuation_analysis",
                "count": len(final_records),
                "records": final_records
            }
            
            return success_response(result_data, "查询申万行业估值分析成功")

        except Exception as e:
            return error_response(f"查询申万行业估值分析失败: {str(e)}", 500)
