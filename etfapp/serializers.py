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


class CorrelationMatrixPayloadSerializer(serializers.Serializer):
    """
    ETF 收盘价相关性矩阵载荷
    功能：用于描述相似度热力图所需的数据结构（标签与矩阵）。
    参数：无
    返回值：
    - labels (str[]): ETF代码标签列表（矩阵行列顺序）
    - matrix (number[][]): 相关性矩阵，取值范围[-1,1]，无数据用null
    - start_date (str, 可选): 开始日期（YYYY-MM-DD）
    - end_date (str, 可选): 结束日期（YYYY-MM-DD）
    事件：无
    """
    labels = serializers.ListField(child=serializers.CharField())
    matrix = serializers.ListField(child=serializers.ListField(child=serializers.FloatField(allow_null=True)))
    start_date = serializers.CharField(required=False, allow_null=True)
    end_date = serializers.CharField(required=False, allow_null=True)


class SuccessResponseEtfCorrelationSerializer(serializers.Serializer):
    """
    ETF 收盘价相关性统一响应序列化器
    功能：描述统一返回结构，其中 data 为相关性矩阵载荷。
    参数：无
    返回值：
    - code (int): 状态码
    - message (str): 信息
    - timestamp (str): 时间戳（ISO 格式）
    - data (CorrelationMatrixPayloadSerializer): 相关性矩阵载荷
    事件：无
    """
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = CorrelationMatrixPayloadSerializer()


class EtfVolatilityItemSerializer(serializers.Serializer):
    """
    ETF 波动度指标项
    功能：描述单个ETF在区间内的波动度统计。
    参数：无
    返回值：
    - ts_code (str)
    - start_date (str)
    - end_date (str)
    - highest_value (float)
    - highest_date (str)
    - lowest_value (float)
    - lowest_date (str)
    - max_drawdown_pct (float)
    - mdd_start_date (str)
    - mdd_end_date (str)
    - mdd_days (int)
    - max_rise_pct (float)
    - rise_start_date (str)
    - rise_end_date (str)
    - rise_days (int)
    - latest_price (float)
    - latest_date (str)
    - percentile_between_min_max (float)
    - mean (float)
    - variance (float)
    - stddev (float)
    - trend (str)  # up/down/range
    - grid_applicable (bool)
    - sample_used (bool)
    - sample_n (int, 可选)
    事件：无
    """
    ts_code = serializers.CharField()
    start_date = serializers.CharField()
    end_date = serializers.CharField()
    highest_value = serializers.FloatField()
    highest_date = serializers.CharField()
    lowest_value = serializers.FloatField()
    lowest_date = serializers.CharField()
    max_drawdown_pct = serializers.FloatField()
    mdd_start_date = serializers.CharField()
    mdd_end_date = serializers.CharField()
    mdd_days = serializers.IntegerField()
    max_rise_pct = serializers.FloatField()
    rise_start_date = serializers.CharField()
    rise_end_date = serializers.CharField()
    rise_days = serializers.IntegerField()
    latest_price = serializers.FloatField()
    latest_date = serializers.CharField()
    percentile_between_min_max = serializers.FloatField()
    mean = serializers.FloatField()
    variance = serializers.FloatField()
    stddev = serializers.FloatField()
    trend = serializers.CharField()
    grid_applicable = serializers.BooleanField()
    sample_used = serializers.BooleanField()
    sample_n = serializers.IntegerField(required=False, allow_null=True)


class SuccessResponseEtfVolatilityListSerializer(serializers.Serializer):
    """
    ETF 波动度列表统一响应
    功能：描述统一返回结构，其中 data 为指标项列表。
    参数：无
    返回值：
    - code (int)
    - message (str)
    - timestamp (str)
    - data (object): 包含 items、total、start_date、end_date
    事件：无
    """
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()

    class Payload(serializers.Serializer):
        items = EtfVolatilityItemSerializer(many=True)
        total = serializers.IntegerField()
        start_date = serializers.CharField(allow_null=True, required=False)
        end_date = serializers.CharField(allow_null=True, required=False)
        skipped = serializers.IntegerField(required=False)

    data = Payload()


class IndexValuationMetricsSerializer(serializers.Serializer):
    pe = serializers.FloatField(required=False, allow_null=True)
    pe_ttm = serializers.FloatField(required=False, allow_null=True)
    pb = serializers.FloatField(required=False, allow_null=True)
    ps = serializers.FloatField(required=False, allow_null=True)
    ps_ttm = serializers.FloatField(required=False, allow_null=True)
    dv_ratio = serializers.FloatField(required=False, allow_null=True)
    dv_ttm = serializers.FloatField(required=False, allow_null=True)
    turnover_rate = serializers.FloatField(required=False, allow_null=True)
    volume_ratio = serializers.FloatField(required=False, allow_null=True)
    total_mv = serializers.FloatField(required=False, allow_null=True)
    circ_mv = serializers.FloatField(required=False, allow_null=True)


class IndexValuationConstituentsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    matched = serializers.IntegerField()
    missing_daily_basic = serializers.IntegerField()
    weight_sum = serializers.FloatField(required=False, allow_null=True)
    mv_covered = serializers.FloatField(required=False, allow_null=True)
    pe_coverage = serializers.FloatField(required=False, allow_null=True)
    pe_ttm_coverage = serializers.FloatField(required=False, allow_null=True)
    pb_coverage = serializers.FloatField(required=False, allow_null=True)
    ps_coverage = serializers.FloatField(required=False, allow_null=True)
    ps_ttm_coverage = serializers.FloatField(required=False, allow_null=True)


class ConstituentDetailSerializer(serializers.Serializer):
    ts_code = serializers.CharField()
    weight = serializers.FloatField(required=False, allow_null=True)
    pe = serializers.FloatField(required=False, allow_null=True)
    pe_ttm = serializers.FloatField(required=False, allow_null=True)
    pe_filled = serializers.FloatField(required=False, allow_null=True)
    pe_ttm_filled = serializers.FloatField(required=False, allow_null=True)
    pe_source = serializers.CharField(required=False, allow_null=True)
    pe_ttm_source = serializers.CharField(required=False, allow_null=True)
    profit_end_date = serializers.CharField(required=False, allow_null=True)
    profit_dedt = serializers.FloatField(required=False, allow_null=True)
    profit_dedt_ttm = serializers.FloatField(required=False, allow_null=True)
    pb = serializers.FloatField(required=False, allow_null=True)
    ps = serializers.FloatField(required=False, allow_null=True)
    ps_ttm = serializers.FloatField(required=False, allow_null=True)
    dv_ratio = serializers.FloatField(required=False, allow_null=True)
    dv_ttm = serializers.FloatField(required=False, allow_null=True)
    total_mv = serializers.FloatField(required=False, allow_null=True)
    circ_mv = serializers.FloatField(required=False, allow_null=True)
    mv_used = serializers.FloatField(required=False, allow_null=True)
    mv_type = serializers.CharField(required=False, allow_null=True)


class SuccessResponseIndexValuationSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()

    class Payload(serializers.Serializer):
        index_code = serializers.CharField()
        trade_date = serializers.CharField()
        index_basic = serializers.JSONField(required=False, allow_null=True)
        constituents = IndexValuationConstituentsSerializer()
        metrics = IndexValuationMetricsSerializer()
        details = ConstituentDetailSerializer(many=True, required=False)

    data = Payload()


class IndexValuationDailyItemSerializer(serializers.Serializer):
    trade_date = serializers.CharField()
    weight_date = serializers.CharField(required=False, allow_null=True)
    metrics = IndexValuationMetricsSerializer()
    constituents = IndexValuationConstituentsSerializer()


class SuccessResponseIndexValuationRangeSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()

    class Payload(serializers.Serializer):
        index_code = serializers.CharField()
        start_date = serializers.CharField()
        end_date = serializers.CharField()
        total = serializers.IntegerField()
        items = IndexValuationDailyItemSerializer(many=True)

    data = Payload()
