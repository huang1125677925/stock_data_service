"""
金十数据工具：快讯（get_flash_list）。
快讯清洗与过滤对齐 openclaw-skill-jin10 collector.js。
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
from mcp.server.fastmcp import FastMCP

from mcp_service.tools.tushare._registry import error_payload

JIN10_BASE = "https://flash-api.jin10.com/get_flash_list"

# 金十 get_flash_list 常用 channel（与官网分类一致）
JIN10_FLASH_CHANNEL_FOREX = "-8200"  # 外汇
JIN10_FLASH_CHANNEL_A_SHARE = "-8100"  # A股
JIN10_FLASH_CHANNEL_FUTURES = "-8300"  # 期货
JIN10_FLASH_CHANNEL_US_HK = "-8400"  # 美港

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
    max_time: Optional[str] = None,
) -> List[Dict[str, Any]]:
    headers = {
        **DEFAULT_HEADERS,
        "x-app-id": os.getenv("JIN10_X_APP_ID", DEFAULT_HEADERS["x-app-id"]).strip(),
        "x-version": os.getenv("JIN10_X_VERSION", DEFAULT_HEADERS["x-version"]).strip(),
    }
    params: Dict[str, str] = {"channel": channel, "vip": str(vip)}
    # 翻页：传上一页最后一条的 id（金十接口参数名为 max_time，取值与 collector 单页无关）
    if max_time:
        params["max_time"] = max_time
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


def _fetch_merged_pages(
    channel: str,
    vip: int,
    timeout: float,
    max_pages: int,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    链式请求多页并去重。单页约 20 条；下一页请求带 max_time=上一页末条 id。
    返回 (按时间新→旧合并后的条目列表, 实际发起的请求次数)。
    """
    merged: List[Dict[str, Any]] = []
    seen: set[str] = set()
    cursor: Optional[str] = None
    pages_done = 0

    for _ in range(max_pages):
        batch = _fetch_raw(channel, vip, timeout, max_time=cursor)
        pages_done += 1
        if not batch:
            break
        added = 0
        for item in batch:
            if not isinstance(item, dict):
                continue
            iid = item.get("id")
            if not iid or iid in seen:
                continue
            seen.add(iid)
            merged.append(item)
            added += 1
        last_id = batch[-1].get("id") if isinstance(batch[-1], dict) else None
        if not last_id:
            break
        cursor = str(last_id)
        if added == 0:
            break

    return merged, pages_done


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
        channel: str = "-8100",
        vip: int = 1,
        limit: int = 100,
        offset: int = 0,
        max_pages: int = 5,
        filter_noise: bool = True,
        important_only: bool = False,
    ) -> Dict[str, Any]:
        """
        获取金十财经快讯列表（https://flash-api.jin10.com/get_flash_list）。

        与 openclaw-skill-jin10 的 collector 一致：同一接口、HTML 清洗、广告/空内容/诱导点击/长文汇总等过滤。

        - channel: 快讯分类（免费可用）。常用取值：`-8100` A股（默认）、`-8200` 外汇、`-8300` 期货、`-8400` 美港。
        - vip: 与金十客户端一致，默认 1
        - max_pages: 向后翻页次数（每页约 20 条，页间用 max_time=上一页末条 id 衔接，默认 5 页约 100 条量级）
        - limit / offset: 在合并去重后的结果上分页
        - filter_noise: True 时去掉广告、空内容、HTML 列表块、诱导点击、超长汇总类
        - important_only: True 时仅保留 important 为真的条目（在过滤之后应用）

        环境变量 JIN10_MAX_PAGES 可作为 max_pages 上限（默认 30）；单次 max_pages 入参也会被限制在该上限内。
        """
        timeout = float(os.getenv("JIN10_HTTP_TIMEOUT", "15"))
        cap = max(1, min(int(os.getenv("JIN10_MAX_PAGES", "30")), 50))
        safe_pages = max(1, min(int(max_pages or 1), cap))
        safe_limit = max(1, min(int(limit or 100), 500))
        safe_offset = max(0, int(offset or 0))

        try:
            raw_items, pages_fetched = _fetch_merged_pages(
                channel=str(channel), vip=int(vip), timeout=timeout, max_pages=safe_pages
            )
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
                "pages_fetched": pages_fetched,
                "raw_merged_count": len(raw_items),
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
