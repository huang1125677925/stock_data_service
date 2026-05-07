"""index_data 共享工具函数"""

from __future__ import annotations

import math
from typing import Any


def replace_nan(obj: Any) -> Any:
    """递归将数据中的 NaN 替换为 None，以便 JSON 序列化。"""
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if isinstance(obj, dict):
        return {k: replace_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [replace_nan(item) for item in obj]
    return obj
