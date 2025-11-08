from rest_framework import serializers


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


class ErrorResponseSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = serializers.JSONField(allow_null=True, required=False)
    error = serializers.CharField(required=False)


class GitCommitRecordSerializer(serializers.Serializer):
    # commit_id = serializers.CharField(required=False)
    authored_datetime = serializers.CharField(required=False)
    # author_name = serializers.CharField(required=False)
    message = serializers.CharField(required=False)


class GitInfoDataSerializer(serializers.Serializer):
    interface = serializers.CharField()
    count = serializers.IntegerField()
    records = GitCommitRecordSerializer(many=True)


class SuccessResponseGitInfoSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = GitInfoDataSerializer()


# --- DC 概念/行业/地域板块日频行情（dc_daily） ---
class DcDailyRecordSerializer(serializers.Serializer):
    """
    dc_daily 记录字段序列化器

    字段说明参考 Tushare 文档：东财概念板块、行业指数板块、地域板块日频行情。
    """
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
    """
    dc_index 记录字段序列化器

    字段说明参考 Tushare 文档：东方财富概念板块。
    """
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