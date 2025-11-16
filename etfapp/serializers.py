from rest_framework import serializers
from .models import EtfBasic, EtfDaily


class EtfBasicSerializer(serializers.ModelSerializer):
    """
    ETF 基本信息序列化器
    功能：将 EtfBasic 模型实例序列化为 JSON。
    参数：model=EtfBasic, fields='__all__'
    返回值：序列化后的JSON数据
    事件：无
    """
    setup_date = serializers.DateField(format='%Y-%m-%d', required=False, allow_null=True)
    list_date = serializers.DateField(format='%Y-%m-%d', required=False, allow_null=True)
    delist_date = serializers.DateField(format='%Y-%m-%d', required=False, allow_null=True)
    created_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)
    updated_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)
    mgt_fee = serializers.FloatField(required=False, allow_null=True)

    class Meta:
        model = EtfBasic
        fields = '__all__'


class EtfDailySerializer(serializers.ModelSerializer):
    """
    ETF 日线行情序列化器
    功能：将 EtfDaily 模型实例序列化为 JSON。
    参数：model=EtfDaily, fields='__all__'；并支持注解字段 csname。
    返回值：序列化后的JSON数据（包含 csname 中文简称，若存在注解）。
    事件：无
    """
    trade_date = serializers.DateField(format='%Y-%m-%d')
    created_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)

    # 注解中文简称（来自 EtfBasic），不是模型字段
    csname = serializers.CharField(required=False, allow_null=True)

    # Decimal 转 float 保持风格一致
    open = serializers.FloatField()
    high = serializers.FloatField()
    low = serializers.FloatField()
    close = serializers.FloatField()
    pre_close = serializers.FloatField(required=False, allow_null=True)
    change = serializers.FloatField(required=False, allow_null=True)
    pct_chg = serializers.FloatField(required=False, allow_null=True)
    amount = serializers.FloatField()

    class Meta:
        model = EtfDaily
        fields = '__all__'


class SuccessResponseEtfBasicListSerializer(serializers.Serializer):
    """
    ETF 基本信息列表统一响应序列化器
    功能：描述接口返回的统一结构，其中 data 为 EtfBasicSerializer 列表。
    参数：无
    返回值：
    - code (int): 状态码
    - message (str): 信息
    - timestamp (str): 时间戳（ISO 格式）
    - data (object): 分页载荷对象，包含 items 列表与分页元信息
    事件：无
    """
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    class EtfBasicListPayloadSerializer(serializers.Serializer):
        """
        ETF 基本信息分页载荷
        功能：描述统一响应中的 data 字段结构。
        参数：无
        返回值：
        - items (EtfBasicSerializer[]): 当前页数据列表
        - page (int): 当前页码
        - page_size (int): 每页数量
        - total (int): 总记录数
        - pages (int): 总页数
        事件：无
        """
        items = EtfBasicSerializer(many=True)
        page = serializers.IntegerField()
        page_size = serializers.IntegerField()
        total = serializers.IntegerField()
        pages = serializers.IntegerField()

    data = EtfBasicListPayloadSerializer()


class SuccessResponseEtfDailyListSerializer(serializers.Serializer):
    """
    ETF 日线行情列表统一响应序列化器
    功能：描述接口返回的统一结构，其中 data 为 EtfDailySerializer 列表。
    参数：无
    返回值：
    - code (int): 状态码
    - message (str): 信息
    - timestamp (str): 时间戳（ISO 格式）
    - data (EtfDailySerializer[]): ETF 日线行情列表
    事件：无
    """
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = EtfDailySerializer(many=True)


class ErrorResponseSerializer(serializers.Serializer):
    """
    错误响应序列化器
    功能：描述错误时的统一返回结构。
    参数：无
    返回值：
    - code (int): 错误码
    - message (str): 错误信息
    - timestamp (str): 时间戳
    - data (any|null): 为空或附加数据
    - error (str, 可选): 具体错误描述
    事件：无
    """
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = serializers.JSONField(allow_null=True, required=False)
    error = serializers.CharField(required=False)