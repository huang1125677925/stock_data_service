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