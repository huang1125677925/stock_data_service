from rest_framework import serializers
from .models import IndividualStock, IndividualStockDaily


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