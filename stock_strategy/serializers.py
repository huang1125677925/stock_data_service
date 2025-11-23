from rest_framework import serializers


class MacdXgbGrowthDatesParamsSerializer(serializers.Serializer):
    """
    MACD XGBoost 预测参数序列化器
    功能：描述预测过程中使用的关键参数。
    参数：无
    返回值：lookback_days(int)、forecast_days(int)、growth_threshold(float)
    事件：无
    """
    lookback_days = serializers.IntegerField(required=False)
    forecast_days = serializers.IntegerField(required=False)
    growth_threshold = serializers.FloatField(required=False)


class MacdXgbGrowthDatesDataSerializer(serializers.Serializer):
    """
    指数最近上涨预测日期数据序列化器
    功能：描述统一响应结构中的 data 字段内容。
    参数：无
    返回值：
    - ts_code(str): 指数TS代码
    - list(str[]): 预测为“上涨”的交易日期列表（YYYYMMDD）
    - count(int): 日期数量
    - params(object): 预测参数
    事件：无
    """
    ts_code = serializers.CharField()
    list = serializers.ListField(child=serializers.CharField())
    count = serializers.IntegerField()
    params = MacdXgbGrowthDatesParamsSerializer()


class SuccessResponseMacdXgbGrowthDatesSerializer(serializers.Serializer):
    """
    指数MACD XGBoost最近上涨日预测统一响应序列化器
    功能：描述接口返回的统一结构，其中 data 为 MacdXgbGrowthDatesDataSerializer。
    参数：无
    返回值：
    - code (int): 状态码
    - message (str): 信息
    - timestamp (str): 时间戳（ISO 格式）
    - data (MacdXgbGrowthDatesDataSerializer): 预测结果载荷
    事件：无
    """
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = MacdXgbGrowthDatesDataSerializer()