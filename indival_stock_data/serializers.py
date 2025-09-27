from rest_framework import serializers
from .models import IndividualStock, IndividualStockDaily, StrategyResult
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