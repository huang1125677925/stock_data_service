from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TypeVar

from mcp.server.fastmcp import FastMCP

TFunc = TypeVar("TFunc", bound=Callable[..., Any])


def tool_exists(mcp: FastMCP, name: str) -> bool:
    tool_manager = getattr(mcp, "_tool_manager", None)
    tools = getattr(tool_manager, "_tools", None) if tool_manager is not None else None
    return isinstance(tools, dict) and name in tools


def safe_tool(
    mcp: FastMCP,
    *,
    name: str,
    description: Optional[str] = None,
) -> Callable[[TFunc], TFunc]:
    def decorator(fn: TFunc) -> TFunc:
        if tool_exists(mcp, name):
            return fn
        return mcp.tool(name=name, description=description)(fn)

    return decorator


def error_payload(message: str, code: int = 400, **kwargs: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "code": code,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "data": None,
    }
    payload.update(kwargs)
    return payload


def apply_pagination(
    resp: Dict[str, Any],
    limit: int,
    offset: int = 0,
) -> Dict[str, Any]:
    """对 tushare 代理响应做服务端分页，单次只返回一页；大模型用 limit/offset 精确控制体量并可翻页拿全量。

    成功响应结构：{ code, message, timestamp, data: { interface, count, records } }
    处理后在 data 中注入：
        total_count   上游返回的总记录数（分页前）
        count         本页记录数
        limit / offset  本页参数（回显，便于模型核对）
        has_more      是否还有下一页
        next_offset   有下一页时为应传入的 offset；否则为 None
        remaining     尚未返回的记录条数（本页之后还剩多少条）
    """
    if resp.get("code") != 200:
        return resp
    data = resp.get("data") or {}
    records: List[Any] = data.get("records") or []
    total_count = data.get("count", len(records))
    sliced = records[offset: offset + limit]
    end_exclusive = offset + len(sliced)
    has_more = end_exclusive < total_count
    data["total_count"] = total_count
    data["count"] = len(sliced)
    data["limit"] = limit
    data["offset"] = offset
    data["has_more"] = has_more
    data["next_offset"] = end_exclusive if has_more else None
    data["remaining"] = max(0, total_count - end_exclusive)
    data["records"] = sliced
    resp["data"] = data
    return resp

