"""
AI 模型配置模块

集中管理 DeepSeek、豆包 Seed 等模型的 API 配置。
通过 AI_MODEL_PROVIDER 切换当前使用的模型提供商（默认 doubao_seed）。
"""

from django.conf import settings
from typing import TypedDict, Dict, Any, Optional


class ModelConfig(TypedDict, total=False):
    """模型配置结构"""

    api_key: str
    base_url: str
    model_name: str
    model_kwargs: Optional[Dict[str, Any]]
    # 厂商扩展字段（如豆包 thinking）；勿放入 model_kwargs，否则会作为 create() 顶层参数触发 SDK 报错
    extra_body: Optional[Dict[str, Any]]


# DeepSeek 配置（保留原有配置）
DEEPSEEK_CONFIG: ModelConfig = {
    "api_key": getattr(settings, "DEEPSEEK_API_KEY", None) or "sk-901c17c669a241f098b25144957667ec",
    "base_url": getattr(settings, "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    "model_name": getattr(settings, "DEEPSEEK_MODEL_NAME", "deepseek-chat"),
}

# 豆包 Seed 配置
# API 文档: https://www.volcengine.com/docs/6492/2250683
# 支持多模态输入（图片+文本），OpenAI 兼容接口
# thinking.type=disabled 关闭深度思考模式，避免额外延迟与 token 消耗（经 extra_body 传递，兼容 OpenAI SDK）
DOUBAO_SEED_CONFIG: ModelConfig = {
    "api_key": getattr(
        settings,
        "DOUBAO_SEED_API_KEY",
        "483dda0a-1fdc-4f79-9827-977f90b3175a",
    ),
    "base_url": getattr(
        settings,
        "DOUBAO_SEED_BASE_URL",
        "https://ark.cn-beijing.volces.com/api/v3",
    ),
    "model_name": getattr(
        settings,
        "DOUBAO_SEED_MODEL_NAME",
        "doubao-seed-2-0-mini-260215",
    ),
    "extra_body": {"thinking": {"type": "disabled"}},
}

# 模型提供商映射
MODEL_PROVIDERS = {
    "deepseek": DEEPSEEK_CONFIG,
    "doubao_seed": DOUBAO_SEED_CONFIG,
}


def get_active_model_config() -> ModelConfig:
    """
    获取当前激活的模型配置。

    通过 settings.AI_MODEL_PROVIDER 指定：
    - "doubao_seed": 豆包 Seed 模型（默认）
    - "deepseek": DeepSeek 模型

    返回值:
        ModelConfig: 包含 api_key、base_url、model_name、model_kwargs、extra_body（可选）
    """
    provider = getattr(settings, "AI_MODEL_PROVIDER", "doubao_seed")
    return MODEL_PROVIDERS.get(provider, DOUBAO_SEED_CONFIG)
