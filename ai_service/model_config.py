"""
AI 模型配置模块

集中管理 DeepSeek、豆包 Seed、Qwen2API（OpenAI 兼容）等模型的 API 配置。
通过 AI_MODEL_PROVIDER 切换当前使用的模型提供商（默认 deepseek，需配置 DEEPSEEK_API_KEY）。
"""

from django.conf import settings
from typing import TypedDict, Dict, Any, Optional


class ModelConfig(TypedDict, total=False):
    """模型配置结构"""

    api_key: str
    base_url: str
    model_name: str
    model_kwargs: Optional[Dict[str, Any]]
    # 厂商扩展字段（thinking、reasoning_effort 等）；勿放入 model_kwargs，经 extra_body 进入请求体
    extra_body: Optional[Dict[str, Any]]
    # 为 True 时允许 api_key 为空（如 smanx 公开 Qwen2API，可不传 Authorization）
    api_key_optional: bool


# DeepSeek 配置（保留原有配置）
DEEPSEEK_CONFIG: ModelConfig = {
    "api_key": getattr(settings, "DEEPSEEK_API_KEY", None) or "sk-901c17c669a241f098b25144957667ec",
    "base_url": getattr(settings, "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    "model_name": getattr(settings, "DEEPSEEK_MODEL_NAME", "deepseek-chat"),
}

# 豆包 Seed 配置
# API 文档: https://www.volcengine.com/docs/6492/2250683
# 支持多模态输入（图片+文本），OpenAI 兼容接口
# thinking / reasoning_effort 均放在 extra_body。部分机型不支持 type=auto，mini 等需用 enabled/disabled。
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
    "extra_body": {
        "thinking": {"type": "enabled"},
        "reasoning_effort": "low",
    },
}

# Qwen2API（OpenAI 兼容），参考 https://github.com/smanx/qwen2api
# 公开 Netlify 实例可免登录、API Key 留空；自建时可设置 QWEN2API_API_KEY
QWEN2API_CONFIG: ModelConfig = {
    "api_key": getattr(settings, "QWEN2API_API_KEY", None) or "",
    "base_url": getattr(
        settings,
        "QWEN2API_BASE_URL",
        "https://qwen2api-n.smanx.xx.kg/v1",
    ),
    "model_name": getattr(settings, "QWEN2API_MODEL_NAME", "qwen3.5-plus"),
    "api_key_optional": True,
}

# 模型提供商映射
MODEL_PROVIDERS = {
    "deepseek": DEEPSEEK_CONFIG,
    "doubao_seed": DOUBAO_SEED_CONFIG,
    "qwen2api": QWEN2API_CONFIG,
}


def get_active_model_config() -> ModelConfig:
    """
    获取当前激活的模型配置。

    通过 settings.AI_MODEL_PROVIDER 指定：
    - "deepseek": DeepSeek 模型（默认）
    - "qwen2api": Qwen2API 千问（公开服务可免 key）
    - "doubao_seed": 豆包 Seed 模型

    返回值:
        ModelConfig: 包含 api_key、base_url、model_name、model_kwargs、extra_body（可选）
    """
    provider = getattr(settings, "AI_MODEL_PROVIDER", "deepseek")
    return MODEL_PROVIDERS.get(provider, DEEPSEEK_CONFIG)
