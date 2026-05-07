from rest_framework import serializers

class PromptConfigSerializer(serializers.Serializer):
    interface_name = serializers.CharField(required=True, help_text="接口名称，唯一标识")
    prompt_template = serializers.CharField(required=True, help_text="Prompt 模板，支持 {data} 占位符")
    is_active = serializers.BooleanField(required=False, default=True, help_text="是否启用")
    created_at = serializers.DateTimeField(read_only=True, help_text="创建时间")
    updated_at = serializers.DateTimeField(read_only=True, help_text="更新时间")

class PromptConfigListSerializer(serializers.Serializer):
    interface_name = serializers.CharField(help_text="接口名称")
    prompt_template = serializers.CharField(help_text="Prompt 模板")
    is_active = serializers.BooleanField(help_text="是否启用")
    created_at = serializers.DateTimeField(help_text="创建时间")
    updated_at = serializers.DateTimeField(help_text="更新时间")

class AiAnalyzeRequestSerializer(serializers.Serializer):
    interface_name = serializers.CharField(required=False, allow_blank=True, default="default", help_text="接口名称，默认为 default")
    data = serializers.JSONField(required=True, help_text="需要分析的数据，可以是任意 JSON 结构")

class AiAnalyzeResponseSerializer(serializers.Serializer):
    interface_name = serializers.CharField(help_text="接口名称")
    prompt_source = serializers.CharField(help_text="Prompt 来源 (configured/default)")
    prompt = serializers.CharField(help_text="生成的完整 Prompt")
    result = serializers.CharField(help_text="AI 分析结果")
