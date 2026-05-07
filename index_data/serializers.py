from rest_framework import serializers


class IndexMemberAllRecordSerializer(serializers.Serializer):
    l1_code = serializers.CharField(required=False)
    l1_name = serializers.CharField(required=False)
    l2_code = serializers.CharField(required=False)
    l2_name = serializers.CharField(required=False)
    l3_code = serializers.CharField(required=False)
    l3_name = serializers.CharField(required=False)
    ts_code = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    in_date = serializers.CharField(required=False)
    out_date = serializers.CharField(required=False)
    is_new = serializers.CharField(required=False)


class IndexMemberAllDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = IndexMemberAllRecordSerializer(many=True)


class SuccessResponseIndexMemberAllSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = IndexMemberAllDataSerializer()


class IndexClassifyRecordSerializer(serializers.Serializer):
    """
    index_classify 记录字段序列化器

    功能：序列化申万行业分类记录（2014版/2021版）。
    参数：无。
    返回值：单条记录的序列化结构。
    事件：无。
    """
    industry_code = serializers.CharField(required=False)
    index_code = serializers.CharField(required=False)
    l1_name = serializers.CharField(required=False)
    l2_name = serializers.CharField(required=False)
    l3_name = serializers.CharField(required=False)
    category = serializers.CharField(required=False)
    is_pub = serializers.CharField(required=False)
    reason = serializers.CharField(required=False)
    cons_num = serializers.IntegerField(required=False)


class IndexClassifyDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = IndexClassifyRecordSerializer(many=True)


class SuccessResponseIndexClassifySerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = IndexClassifyDataSerializer()


class SwDailyRecordSerializer(serializers.Serializer):
    """
    sw_daily 记录字段序列化器
    """
    ts_code = serializers.CharField(required=False, help_text="指数代码")
    trade_date = serializers.CharField(required=False, help_text="交易日期")
    name = serializers.CharField(required=False, help_text="指数名称")
    open = serializers.FloatField(required=False, help_text="开盘点位")
    low = serializers.FloatField(required=False, help_text="最低点位")
    high = serializers.FloatField(required=False, help_text="最高点位")
    close = serializers.FloatField(required=False, help_text="收盘点位")
    change = serializers.FloatField(required=False, help_text="涨跌点位")
    pct_change = serializers.FloatField(required=False, help_text="涨跌幅")
    vol = serializers.FloatField(required=False, help_text="成交量（万股）")
    amount = serializers.FloatField(required=False, help_text="成交额（万元）")
    pe = serializers.FloatField(required=False, help_text="市盈率")
    pb = serializers.FloatField(required=False, help_text="市净率")
    float_mv = serializers.FloatField(required=False, help_text="流通市值（万元）")
    total_mv = serializers.FloatField(required=False, help_text="总市值（万元）")


class SwDailyDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = SwDailyRecordSerializer(many=True)


class SuccessResponseSwDailySerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = SwDailyDataSerializer()


class SwValuationAnalysisRecordSerializer(SwDailyRecordSerializer):
    """
    申万估值分析记录序列化器
    """
    # 继承 SwDailyRecordSerializer 的所有字段，并添加分位数等字段
    # PE/PB 分位数
    pe_quantile = serializers.FloatField(required=False, help_text="PE分位数")
    pb_quantile = serializers.FloatField(required=False, help_text="PB分位数")


class SwValuationAnalysisDataSerializer(serializers.Serializer):
    interface = serializers.CharField(default="sw_valuation_analysis")
    count = serializers.IntegerField()
    records = SwValuationAnalysisRecordSerializer(many=True)


class SuccessResponseSwValuationAnalysisSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = SwValuationAnalysisDataSerializer()


class ErrorResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = serializers.JSONField(allow_null=True, required=False)
    error = serializers.CharField(required=False)


# --- Migrated from scheduled_tasks ---

class IndexBasicRecordSerializer(serializers.Serializer):
    ts_code = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    fullname = serializers.CharField(required=False)
    market = serializers.CharField(required=False)
    publisher = serializers.CharField(required=False)
    index_type = serializers.CharField(required=False)
    category = serializers.CharField(required=False)
    base_date = serializers.CharField(required=False)
    base_point = serializers.FloatField(required=False)
    list_date = serializers.CharField(required=False)
    weight_rule = serializers.CharField(required=False)
    desc = serializers.CharField(required=False)
    exp_date = serializers.CharField(required=False)


class IndexBasicDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = IndexBasicRecordSerializer(many=True)


class SuccessResponseIndexBasicSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = IndexBasicDataSerializer()


class IndexDailyRecordSerializer(serializers.Serializer):
    ts_code = serializers.CharField(required=False)
    trade_date = serializers.CharField(required=False)
    close = serializers.FloatField(required=False)
    open = serializers.FloatField(required=False)
    high = serializers.FloatField(required=False)
    low = serializers.FloatField(required=False)
    pre_close = serializers.FloatField(required=False)
    change = serializers.FloatField(required=False)
    pct_chg = serializers.FloatField(required=False)
    vol = serializers.FloatField(required=False)
    amount = serializers.FloatField(required=False)


class IndexDailyDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = IndexDailyRecordSerializer(many=True)


class SuccessResponseIndexDailySerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = IndexDailyDataSerializer()


class IndexWeightRecordSerializer(serializers.Serializer):
    index_code = serializers.CharField(required=False)
    con_code = serializers.CharField(required=False)
    trade_date = serializers.CharField(required=False)
    weight = serializers.FloatField(required=False)


class IndexWeightDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = IndexWeightRecordSerializer(many=True)


class SuccessResponseIndexWeightSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = IndexWeightDataSerializer()


class IndexDailybasicRecordSerializer(serializers.Serializer):
    """
    index_dailybasic 记录字段序列化器

    功能：序列化大盘指数每日指标记录。
    参数：无。
    返回值：单条记录的序列化结构。
    事件：无。
    """
    ts_code = serializers.CharField(required=False)
    trade_date = serializers.CharField(required=False)
    total_mv = serializers.FloatField(required=False)
    float_mv = serializers.FloatField(required=False)
    total_share = serializers.FloatField(required=False)
    float_share = serializers.FloatField(required=False)
    free_share = serializers.FloatField(required=False)
    turnover_rate = serializers.FloatField(required=False)
    turnover_rate_f = serializers.FloatField(required=False)
    pe = serializers.FloatField(required=False)
    pe_ttm = serializers.FloatField(required=False)
    pb = serializers.FloatField(required=False)


class IndexDailybasicDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = IndexDailybasicRecordSerializer(many=True)


class SuccessResponseIndexDailybasicSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = IndexDailybasicDataSerializer()


class IndexValuationSummaryRecordSerializer(serializers.Serializer):
    label = serializers.CharField()
    value = serializers.CharField()
    pe = serializers.FloatField(allow_null=True)
    pb = serializers.FloatField(allow_null=True)
    total_mv = serializers.FloatField(allow_null=True)
    pe_quantile_5y = serializers.FloatField(allow_null=True)
    pb_quantile_5y = serializers.FloatField(allow_null=True)
    pe_quantile_10y = serializers.FloatField(allow_null=True)
    pb_quantile_10y = serializers.FloatField(allow_null=True)
    trade_date = serializers.CharField(allow_null=True)


class IndexValuationSummaryDataSerializer(serializers.Serializer):
    items = IndexValuationSummaryRecordSerializer(many=True)


class SuccessResponseIndexValuationSummarySerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = IndexValuationSummaryDataSerializer()
