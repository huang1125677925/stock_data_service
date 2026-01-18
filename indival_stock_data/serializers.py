from rest_framework import serializers
from .models import IndividualStock, IndividualStockDaily, StrategyResult, BalanceSheet, IncomeStatement, CashFlowStatement, StockTag
import json


class IndividualStockSerializer(serializers.ModelSerializer):
    """
    个股基本信息序列化器
    用于将 IndividualStock 模型实例序列化为 JSON 格式
    """
    # 处理日期字段格式
    list_date = serializers.DateField(format='%Y-%m-%d', required=False, allow_null=True)
    created_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)
    updated_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)
    
    # 处理 Decimal 字段，确保输出为 float 类型
    pe_ratio = serializers.FloatField(required=False, allow_null=True)
    pb_ratio = serializers.FloatField(required=False, allow_null=True)
    total_market_cap = serializers.FloatField(required=False, allow_null=True)
    circulating_market_cap = serializers.FloatField(required=False, allow_null=True)
    latest_price = serializers.FloatField(required=False, allow_null=True)
    change_percent = serializers.FloatField(required=False, allow_null=True)
    change_amount = serializers.FloatField(required=False, allow_null=True)
    amount = serializers.FloatField(required=False, allow_null=True)
    amplitude = serializers.FloatField(required=False, allow_null=True)
    high = serializers.FloatField(required=False, allow_null=True)
    low = serializers.FloatField(required=False, allow_null=True)
    open_price = serializers.FloatField(required=False, allow_null=True)
    close_price = serializers.FloatField(required=False, allow_null=True)
    volume_ratio = serializers.FloatField(required=False, allow_null=True)
    turnover_rate = serializers.FloatField(required=False, allow_null=True)
    price_change_speed = serializers.FloatField(required=False, allow_null=True)
    change_5min = serializers.FloatField(required=False, allow_null=True)
    change_60d = serializers.FloatField(required=False, allow_null=True)
    change_ytd = serializers.FloatField(required=False, allow_null=True)
    
    class Meta:
        model = IndividualStock
        fields = '__all__'  # 序列化所有字段


class IndividualStockDailySerializer(serializers.ModelSerializer):
    """
    个股日频数据序列化器
    用于将 IndividualStockDaily 模型实例序列化为 JSON 格式
    """
    date = serializers.DateField(format='%Y-%m-%d')
    created_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)
    
    # 处理 Decimal 字段，确保输出为 float 类型
    open_price = serializers.FloatField()
    close_price = serializers.FloatField()
    high_price = serializers.FloatField()
    low_price = serializers.FloatField()
    change_percent = serializers.FloatField()
    change_amount = serializers.FloatField()
    amount = serializers.FloatField()
    amplitude = serializers.FloatField(required=False, allow_null=True)
    turnover_rate = serializers.FloatField(required=False, allow_null=True)
    
    class Meta:
        model = IndividualStockDaily
        fields = '__all__'  # 序列化所有字段


class StrategyResultSerializer(serializers.ModelSerializer):
    """
    策略选股结果序列化器
    用于将 StrategyResult 模型实例序列化为 JSON 格式
    """
    created_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)
    updated_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)
    strategy_result = serializers.JSONField()
    
    class Meta:
        model = StrategyResult
        fields = '__all__'
    
    def validate_strategy_result(self, value):
        """
        验证策略结果字段，确保是有效的JSON格式
        """
        if isinstance(value, str):
            try:
                json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("策略结果必须是有效的JSON格式")
        return value
    
    def to_representation(self, instance):
        """
        自定义序列化输出，将strategy_result字段从字符串转换为JSON对象
        """
        data = super().to_representation(instance)
        if data.get('strategy_result'):
            try:
                # 如果已经是字符串，尝试解析为JSON
                if isinstance(data['strategy_result'], str):
                    data['strategy_result'] = json.loads(data['strategy_result'])
                # 如果已经是对象，直接返回
                elif isinstance(data['strategy_result'], (dict, list)):
                    pass  # 保持原样
            except (json.JSONDecodeError, TypeError) as e:
                # 记录错误信息，但保留原始数据而不是返回空字典
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"JSON解析失败: {str(e)}, 原始数据: {data['strategy_result']}")
                # 如果解析失败，尝试修复常见的JSON格式问题
                if isinstance(data['strategy_result'], str):
                    try:
                        # 尝试修复中文标点符号问题
                        fixed_json = data['strategy_result'].replace('，', ',').replace('：', ':')
                        data['strategy_result'] = json.loads(fixed_json)
                    except (json.JSONDecodeError, TypeError):
                        # 如果修复后仍然失败，保留原始字符串
                        logger.error(f"JSON修复失败，保留原始字符串: {data['strategy_result']}")
        return data
    
    def to_internal_value(self, data):
        """
        自定义反序列化，将strategy_result字段从JSON对象转换为字符串存储
        """
        # 创建数据副本以避免修改原始数据
        data_copy = data.copy() if hasattr(data, 'copy') else dict(data)
        
        if 'strategy_result' in data_copy:
            strategy_result = data_copy['strategy_result']
            
            # 如果不是字符串，需要转换为JSON字符串
            if not isinstance(strategy_result, str):
                try:
                    # 使用ensure_ascii=False保持中文字符
                    data_copy['strategy_result'] = json.dumps(strategy_result, ensure_ascii=False)
                except (TypeError, ValueError) as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"JSON序列化失败: {str(e)}, 原始数据: {strategy_result}")
                    raise serializers.ValidationError(f"策略结果JSON序列化失败: {str(e)}")
            else:
                # 如果已经是字符串，验证是否为有效JSON
                try:
                    json.loads(strategy_result)
                    data_copy['strategy_result'] = strategy_result
                except json.JSONDecodeError as e:
                    # 尝试修复常见的JSON格式问题
                    try:
                        fixed_json = strategy_result.replace('，', ',').replace('：', ':')
                        json.loads(fixed_json)  # 验证修复后的JSON
                        data_copy['strategy_result'] = fixed_json
                    except json.JSONDecodeError:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"无效的JSON格式: {str(e)}, 原始数据: {strategy_result}")
                        raise serializers.ValidationError(f"策略结果必须是有效的JSON格式: {str(e)}")
        
        return super().to_internal_value(data_copy)


class BalanceSheetSerializer(serializers.ModelSerializer):
    """
    资产负债表序列化器
    功能：将BalanceSheet模型实例序列化为JSON格式。
    参数：
    - model: BalanceSheet模型
    - fields: 所有字段
    返回值：序列化后的JSON数据
    事件：无
    """
    # 处理日期字段格式
    announcement_date = serializers.DateField(format='%Y-%m-%d', required=False, allow_null=True)
    created_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)
    updated_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)
    
    # 处理 Decimal 字段，确保输出为 float 类型
    monetary_funds = serializers.FloatField(required=False, allow_null=True)
    accounts_receivable = serializers.FloatField(required=False, allow_null=True)
    inventory = serializers.FloatField(required=False, allow_null=True)
    total_assets = serializers.FloatField(required=False, allow_null=True)
    total_assets_growth_rate = serializers.FloatField(required=False, allow_null=True)
    accounts_payable = serializers.FloatField(required=False, allow_null=True)
    total_liabilities = serializers.FloatField(required=False, allow_null=True)
    advance_receipts = serializers.FloatField(required=False, allow_null=True)
    total_liabilities_growth_rate = serializers.FloatField(required=False, allow_null=True)
    debt_to_asset_ratio = serializers.FloatField(required=False, allow_null=True)
    total_equity = serializers.FloatField(required=False, allow_null=True)
    
    # 添加股票信息字段
    stock_code = serializers.CharField(source='stock.code', read_only=True)
    stock_name = serializers.CharField(source='stock.name', read_only=True)
    
    class Meta:
        model = BalanceSheet
        fields = '__all__'


class IncomeStatementSerializer(serializers.ModelSerializer):
    """
    利润表序列化器
    功能：将IncomeStatement模型实例序列化为JSON格式。
    参数：
    - model: IncomeStatement模型
    - fields: 所有字段
    返回值：序列化后的JSON数据
    事件：无
    """
    # 处理日期字段格式
    announcement_date = serializers.DateField(format='%Y-%m-%d', required=False, allow_null=True)
    created_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)
    updated_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)
    
    # 处理 Decimal 字段，确保输出为 float 类型
    net_profit = serializers.FloatField(required=False, allow_null=True)
    net_profit_growth_rate = serializers.FloatField(required=False, allow_null=True)
    operating_revenue = serializers.FloatField(required=False, allow_null=True)
    operating_revenue_growth_rate = serializers.FloatField(required=False, allow_null=True)
    operating_expenses = serializers.FloatField(required=False, allow_null=True)
    sales_expenses = serializers.FloatField(required=False, allow_null=True)
    management_expenses = serializers.FloatField(required=False, allow_null=True)
    financial_expenses = serializers.FloatField(required=False, allow_null=True)
    total_operating_expenses = serializers.FloatField(required=False, allow_null=True)
    operating_profit = serializers.FloatField(required=False, allow_null=True)
    total_profit = serializers.FloatField(required=False, allow_null=True)
    
    # 添加股票信息字段
    stock_code = serializers.CharField(source='stock.code', read_only=True)
    stock_name = serializers.CharField(source='stock.name', read_only=True)
    
    class Meta:
        model = IncomeStatement
        fields = '__all__'


class CashFlowStatementSerializer(serializers.ModelSerializer):
    """
    现金流量表序列化器
    功能：将CashFlowStatement模型实例序列化为JSON格式。
    参数：
    - model: CashFlowStatement模型
    - fields: 所有字段
    返回值：序列化后的JSON数据
    事件：无
    """
    # 处理日期字段格式
    announcement_date = serializers.DateField(format='%Y-%m-%d', required=False, allow_null=True)
    created_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)
    updated_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)
    
    # 处理 Decimal 字段，确保输出为 float 类型
    net_cash_flow = serializers.FloatField(required=False, allow_null=True)
    net_cash_flow_growth_rate = serializers.FloatField(required=False, allow_null=True)
    operating_cash_flow = serializers.FloatField(required=False, allow_null=True)
    operating_cash_flow_ratio = serializers.FloatField(required=False, allow_null=True)
    investing_cash_flow = serializers.FloatField(required=False, allow_null=True)
    investing_cash_flow_ratio = serializers.FloatField(required=False, allow_null=True)
    financing_cash_flow = serializers.FloatField(required=False, allow_null=True)
    financing_cash_flow_ratio = serializers.FloatField(required=False, allow_null=True)
    
    # 添加股票信息字段
    stock_code = serializers.CharField(source='stock.code', read_only=True)
    stock_name = serializers.CharField(source='stock.name', read_only=True)
    
    class Meta:
        model = CashFlowStatement
        fields = '__all__'


class StockTagSerializer(serializers.ModelSerializer):
    """
    股票标记序列化器
    用于将 StockTag 模型实例序列化为 JSON 格式
    支持多种标记因子的序列化和反序列化
    """
    # 处理日期字段格式
    created_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)
    updated_at = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%S.%fZ', read_only=True)
    
    # 添加股票信息字段
    stock_code = serializers.CharField(source='stock.code', read_only=True)
    stock_name = serializers.CharField(source='stock.name', read_only=True)
    
    # 添加选择字段的显示名称
    pattern_type_display = serializers.CharField(source='get_pattern_type_display', read_only=True)
    technical_indicator_type_display = serializers.CharField(source='get_technical_indicator_type_display', read_only=True)
    stock_type_display = serializers.CharField(source='get_stock_type_display', read_only=True)
    market_cap_type_display = serializers.CharField(source='get_market_cap_type_display', read_only=True)
    pe_range_type_display = serializers.CharField(source='get_pe_range_type_display', read_only=True)
    pb_range_type_display = serializers.CharField(source='get_pb_range_type_display', read_only=True)
    industry_type_display = serializers.CharField(source='get_industry_type_display', read_only=True)
    volume_type_display = serializers.CharField(source='get_volume_type_display', read_only=True)
    volatility_type_display = serializers.CharField(source='get_volatility_type_display', read_only=True)
    trend_type_display = serializers.CharField(source='get_trend_type_display', read_only=True)
    
    class Meta:
        model = StockTag
        fields = '__all__'
    
    def validate(self, data):
        """
        验证整个对象，确保至少有一个标记因子被设置
        """
        tag_fields = [
            'pattern_type', 'technical_indicator_type', 'stock_type',
            'market_cap_type', 'pe_range_type', 'pb_range_type',
            'industry_type', 'volume_type', 'volatility_type', 'trend_type'
        ]
        
        # 检查是否至少有一个标记因子被设置
        has_tag = any(data.get(field) for field in tag_fields)
        if not has_tag:
            raise serializers.ValidationError("至少需要设置一个标记因子")
        
        return data


class StockTagQuerySerializer(serializers.Serializer):
    """
    股票标记查询序列化器
    用于处理查询参数的验证和序列化
    支持多种标记因子的单选和多选查询
    """
    # 股票代码查询
    stock_codes = serializers.ListField(
        child=serializers.CharField(max_length=10),
        required=False,
        help_text="股票代码列表，支持多选"
    )
    
    # 各种标记因子查询字段
    pattern_types = serializers.ListField(
        child=serializers.ChoiceField(choices=StockTag.PATTERN_TYPE_CHOICES),
        required=False,
        help_text="形态类型列表，支持多选"
    )
    
    technical_indicator_types = serializers.ListField(
        child=serializers.ChoiceField(choices=StockTag.TECHNICAL_INDICATOR_TYPE_CHOICES),
        required=False,
        help_text="技术指标类型列表，支持多选"
    )
    
    stock_types = serializers.ListField(
        child=serializers.ChoiceField(choices=StockTag.STOCK_TYPE_CHOICES),
        required=False,
        help_text="股票类型列表，支持多选"
    )
    
    market_cap_types = serializers.ListField(
        child=serializers.ChoiceField(choices=StockTag.MARKET_CAP_TYPE_CHOICES),
        required=False,
        help_text="市值大小类型列表，支持多选"
    )
    
    pe_range_types = serializers.ListField(
        child=serializers.ChoiceField(choices=StockTag.PE_RANGE_TYPE_CHOICES),
        required=False,
        help_text="PE区间类型列表，支持多选"
    )
    
    pb_range_types = serializers.ListField(
        child=serializers.ChoiceField(choices=StockTag.PB_RANGE_TYPE_CHOICES),
        required=False,
        help_text="PB区间类型列表，支持多选"
    )
    
    industry_types = serializers.ListField(
        child=serializers.ChoiceField(choices=StockTag.INDUSTRY_TYPE_CHOICES),
        required=False,
        help_text="行业类型列表，支持多选"
    )
    
    volume_types = serializers.ListField(
        child=serializers.ChoiceField(choices=StockTag.VOLUME_TYPE_CHOICES),
        required=False,
        help_text="成交量类型列表，支持多选"
    )
    
    volatility_types = serializers.ListField(
        child=serializers.ChoiceField(choices=StockTag.VOLATILITY_TYPE_CHOICES),
        required=False,
        help_text="波动率类型列表，支持多选"
    )
    
    trend_types = serializers.ListField(
        child=serializers.ChoiceField(choices=StockTag.TREND_TYPE_CHOICES),
        required=False,
        help_text="趋势类型列表，支持多选"
    )
    
    # 日期范围查询
    start_date = serializers.DateField(
        required=False,
        help_text="开始日期，格式：YYYY-MM-DD"
    )
    
    end_date = serializers.DateField(
        required=False,
        help_text="结束日期，格式：YYYY-MM-DD"
    )
    
    # 分页参数
    page = serializers.IntegerField(
        min_value=1,
        required=False,
        default=1,
        help_text="页码，从1开始"
    )
    
    page_size = serializers.IntegerField(
        min_value=1,
        max_value=100,
        required=False,
        default=20,
        help_text="每页数量，最大100"
    )
    
    def validate(self, data):
        """
        验证查询参数
        """
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # 验证日期范围
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("开始日期不能大于结束日期")
        
        return data


class SuccessResponseConceptListSerializer(serializers.Serializer):
    """
    东财概念列表统一响应序列化器
    功能：描述接口返回的统一结构，其中 data 为概念字符串数组。
    参数：无
    返回值：
    - code (int): 状态码
    - message (str): 信息
    - timestamp (str): 时间戳（ISO 格式）
    - data (list[str]): 概念名称列表
    事件：无
    """
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = serializers.ListField(child=serializers.CharField())


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


class StockCorrelationMatrixPayloadSerializer(serializers.Serializer):
    labels = serializers.ListField(child=serializers.CharField())
    matrix = serializers.ListField(child=serializers.ListField(child=serializers.FloatField(allow_null=True)))
    start_date = serializers.CharField(required=False, allow_null=True)
    end_date = serializers.CharField(required=False, allow_null=True)


class SuccessResponseStockCorrelationSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    data = StockCorrelationMatrixPayloadSerializer()


class StockVolatilityItemSerializer(serializers.Serializer):
    stock_code = serializers.CharField()
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


class SuccessResponseStockVolatilityListSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()
    timestamp = serializers.CharField()
    class Payload(serializers.Serializer):
        items = StockVolatilityItemSerializer(many=True)
        total = serializers.IntegerField()
        start_date = serializers.CharField(allow_null=True, required=False)
        end_date = serializers.CharField(allow_null=True, required=False)
        skipped = serializers.IntegerField(required=False)
    data = Payload()
