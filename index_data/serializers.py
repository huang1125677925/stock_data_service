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
    pe_ttm = serializers.FloatField(required=False, help_text="滚动市盈率")
    pe_percentile = serializers.FloatField(required=False, help_text="PE分位数")
    pb_percentile = serializers.FloatField(required=False, help_text="PB分位数")


class SwValuationAnalysisDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = SwValuationAnalysisRecordSerializer(many=True)


class SuccessResponseSwValuationAnalysisSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = SwValuationAnalysisDataSerializer()
