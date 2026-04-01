"""
金十快讯工具：调用金十 flash API，清洗与过滤逻辑对齐 openclaw-skill-jin10 collector.js。
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from mcp.server.fastmcp import FastMCP

from mcp_service.tools.tushare._registry import error_payload

JIN10_BASE = "https://flash-api.jin10.com/get_flash_list"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "x-app-id": "bVBF4FyRTn5NJF5n",
    "x-version": "1.0.0",
}


def _clean_html(html: Optional[str]) -> str:
    if not html:
        return ""
    text = html.replace(" ", "\n")
    text = re.sub(r"<[^>]+>", "", text)
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
    )
    return text.strip()


def _should_skip_reason(item: Dict[str, Any]) -> Optional[str]:
    extras = item.get("extras") or {}
    if extras.get("ad") is True:
        return "ad"
    raw = (item.get("data") or {}).get("content") or ""
    if "section-news" in raw:
        return "html-list"
    content = _clean_html(raw)
    if not content or len(content) < 5:
        return "empty"
    if re.match(r"^.{0,30}点击查看[…\.]{1,3}$", content):
        return "click-bait"
    if len(content) < 30 and "点击查看" in content:
        return "click-bait"
    if len(content) > 1000 and re.match(r"^[①②③④⑤\d]+[.、)）]", content):
        return "summary-digest"
    if len(content) > 1000 and re.search(r"\n[①②③]", content):
        return "summary-digest"
    return None


def _fetch_raw(
    channel: str,
    vip: int,
    timeout: float,
) -> List[Dict[str, Any]]:
    headers = {
        **DEFAULT_HEADERS,
        "x-app-id": os.getenv("JIN10_X_APP_ID", DEFAULT_HEADERS["x-app-id"]).strip(),
        "x-version": os.getenv("JIN10_X_VERSION", DEFAULT_HEADERS["x-version"]).strip(),
    }
    params = {"channel": channel, "vip": str(vip)}
    resp = requests.get(
        JIN10_BASE,
        params=params,
        headers=headers,
        timeout=timeout,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("status") != 200:
        raise RuntimeError(f"Jin10 API status={body.get('status')}")
    data = body.get("data")
    if not isinstance(data, list):
        raise RuntimeError("Jin10 API returned invalid data")
    return data


def _normalize_record(item: Dict[str, Any], skip_reason: Optional[str]) -> Dict[str, Any]:
    data = item.get("data") or {}
    content = _clean_html(data.get("content") or "")
    rec: Dict[str, Any] = {
        "id": item.get("id"),
        "time": item.get("time") or "",
        "content": content,
        "title": (data.get("title") or "").strip(),
        "source": data.get("source") or "",
        "important": bool(item.get("important")),
        "type": item.get("type"),
        "channel": item.get("channel") or [],
        "tags": item.get("tags") or [],
    }
    if skip_reason is not None:
        rec["skip_reason"] = skip_reason
    return rec


def register_jin10_flash_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def get_jin10_flash(
        channel: str = "-8200",
        vip: int = 1,
        limit: int = 20,
        offset: int = 0,
        filter_noise: bool = True,
        important_only: bool = False,
    ) -> Dict[str, Any]:
        """
        获取金十财经快讯列表（flash-api.jin10.com）。

        与 openclaw-skill-jin10 的 collector 一致：同一 API、HTML 清洗、广告/空内容/诱导点击/长文汇总等过滤。

        - channel: 频道参数，默认 -8200（与参考脚本一致）
        - vip: 1 与参考脚本一致
        - limit / offset: 在「本批 API 返回结果」上分页；单次 API 条数通常约 20 条
        - filter_noise: True 时去掉广告、空内容、HTML 列表块、诱导点击、超长汇总类
        - important_only: True 时仅保留 important 为真的条目（在过滤之后应用）
        """
        timeout = float(os.getenv("JIN10_HTTP_TIMEOUT", "15"))
        safe_limit = max(1, min(int(limit or 20), 100))
        safe_offset = max(0, int(offset or 0))

        try:
            raw_items = _fetch_raw(channel=str(channel), vip=int(vip), timeout=timeout)
        except requests.RequestException as e:
            return error_payload(f"金十 API 请求失败: {e}", code=502)
        except (ValueError, RuntimeError, TypeError) as e:
            return error_payload(str(e), code=502)

        built: List[Dict[str, Any]] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            reason = _should_skip_reason(item)
            rec = _normalize_record(item, reason)
            if filter_noise and reason is not None:
                continue
            if important_only and not rec.get("important"):
                continue
            built.append(rec)

        total = len(built)
        page = built[safe_offset : safe_offset + safe_limit]
        end = safe_offset + len(page)
        has_more = end < total

        return {
            "code": 200,
            "message": "success",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "source": "jin10_flash",
                "total_count": total,
                "count": len(page),
                "limit": safe_limit,
                "offset": safe_offset,
                "has_more": has_more,
                "next_offset": end if has_more else None,
                "remaining": max(0, total - end),
                "records": page,
            },
        }
