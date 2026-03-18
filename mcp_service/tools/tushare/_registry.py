from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, Optional, TypeVar

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

