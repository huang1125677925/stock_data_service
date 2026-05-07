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


class ActualRiseRatioItemSerializer(serializers.Serializer):
    """
    5日实际上涨比例列表项序列化器
    功能：用于统一响应结构中 data 字段的列表项，字段完全对齐 StockSelectionRecord.to_dict()。
    参数：无
    返回值：
    - market(str): 市场
    - code(str): 代码
    - name(str): 名称
    - trade_date(str): 交易日期（YYYY-MM-DD）
    - predict_rise_prob(float): 预测上涨概率（百分比）
    - confidence(float): 预测置信度（百分比）
    - actual_rise_ratio_5d(float|null): 5日实际上涨比例（百分比），可为空
    - prediction_type(str): 预测类型
    - created_at(str): 创建时间（ISO格式）
    事件：无
    """
    market = serializers.CharField()
    code = serializers.CharField()
    name = serializers.CharField()
    trade_date = serializers.CharField()
    predict_rise_prob = serializers.FloatField()
    confidence = serializers.FloatField()
    actual_rise_ratio_5d = serializers.FloatField(allow_null=True)
    prediction_type = serializers.CharField()
    created_at = serializers.CharField()


class SuccessResponseActualRiseRatio5DSerializer(serializers.Serializer):
    """
    查询5日实际上涨比例统一响应序列化器（列表返回）
    功能：描述接口返回的统一结构，其中 data 为 ActualRiseRatioItemSerializer 列表。
    参数：无
    返回值：
    - code (int): 状态码
    - message (str): 信息
    - timestamp (str): 时间戳（ISO 格式）
    - data ([ActualRiseRatioItemSerializer]): 查询结果列表
    事件：无
    """
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = ActualRiseRatioItemSerializer(many=True)