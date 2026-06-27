"""
Django 策略类 HTTP 接口的同源封装（非 HTTP），供 MCP 调用。
走 ORM 回退路径时需数据库与 DJANGO_SETTINGS_MODULE（默认 stock_data_service.settings）。

未设置 DJANGO_STRATEGY_TOOLS_BASE_URL 时，默认先请求本机 http://127.0.0.1:8000（与
runserver 常见端口一致），与 Web 同源；连不上再回退 ORM。若需指定其他后端，设置该变量；
若只想走数据库、不要先发 HTTP，可将变量设为 0 / none / false / -（或置空字符串）。
可选：DJANGO_STRATEGY_TOOLS_HTTP_TIMEOUT（秒，默认 120）。
若网关或中间件要求登录态，设置 DJANGO_STRATEGY_TOOLS_API_TOKEN（用户登录返回的 token，
不含 “Bearer ” 前缀即可；也可直接写完整 “Bearer xxx”）。与 user_management 中间件一致。
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from mcp.server.fastmcp import FastMCP

from mcp_service.tools.tushare._registry import error_payload, safe_tool

_django_ready = False
logger = logging.getLogger(__name__)


def _strategy_tools_http_base() -> Optional[str]:
    if "DJANGO_STRATEGY_TOOLS_BASE_URL" in os.environ:
        raw = os.environ["DJANGO_STRATEGY_TOOLS_BASE_URL"].strip()
    else:
        raw = "https://huanguncle.cn"
    low = raw.lower()
    if not raw or low in ("none", "false", "0", "off", "disable", "-"):
        return None
    return raw.rstrip("/")


def _strategy_tools_http_headers() -> Dict[str, str]:
    headers: Dict[str, str] = {"Accept": "application/json"}
    raw = os.environ.get("DJANGO_STRATEGY_TOOLS_API_TOKEN", "").strip()
    if not raw or raw.lower() in ("0", "none", "false", "-", "off"):
        return headers
    if raw.lower().startswith("bearer "):
        headers["Authorization"] = raw
    else:
        headers["Authorization"] = f"Bearer {raw}"
    return headers


def _fetch_strategy_via_http(
    path: str,
    params: Optional[Dict[str, str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    GET 与 Web 相同的策略接口；成功返回解析后的 JSON 字典（含 code/message/data）。
    使用线程执行 urlopen，避免在 asyncio 事件循环中直接阻塞。
    """
    import concurrent.futures

    base = _strategy_tools_http_base()
    if not base:
        return None
    try:
        timeout_s = int(os.environ.get("DJANGO_STRATEGY_TOOLS_HTTP_TIMEOUT", "120"))
    except ValueError:
        timeout_s = 120
    q = {k: v for k, v in (params or {}).items() if v is not None and str(v).strip() != ""}
    url = f"{base}{path}"
    if q:
        url = f"{url}?{urlencode(q)}"

    def _do_request() -> Optional[Dict[str, Any]]:
        try:
            req = Request(url, headers=_strategy_tools_http_headers())
            with urlopen(req, timeout=timeout_s) as resp:
                raw = resp.read().decode("utf-8")
            body = json.loads(raw)
            if isinstance(body, dict) and body.get("code") == 200:
                return body
            logger.warning("策略 HTTP 返回非成功: path=%s code=%s", path, body.get("code"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            logger.warning("策略 HTTP 请求失败 path=%s: %s", path, e)
        return None

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_do_request)
            return future.result(timeout=timeout_s + 5)
    except concurrent.futures.TimeoutError:
        logger.warning("策略 HTTP 请求超时 path=%s", path)
    except Exception as e:
        logger.warning("策略 HTTP 线程执行失败 path=%s: %s", path, e)
    return None


def _ensure_django() -> None:
    global _django_ready
    if _django_ready:
        return
    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stock_data_service.settings")
    # FastMCP 在 asyncio 事件循环中运行，Django ORM 会检测到 async 上下文并报错。
    # DJANGO_ALLOW_ASYNC_UNSAFE=true 跳过该检查（MCP 单进程单线程，无并发写入风险）。
    os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
    import django

    django.setup()
    _django_ready = True


def register_django_strategy_tools(mcp: FastMCP) -> None:
    @safe_tool(
        mcp,
        name="django.strategy.industry_scale_breadth",
        description=(
            "行业规模宽度指标（与 GET /django/api/strategy/industry-scale-breadth/ 同源，非 HTTP）。"
            "指标 = (行业总市值/市场总市值) × (行业公司数/市场总公司数)。"
            "默认只返回 top 50 行业（按指标降序），可用 limit 调整；传 sector_codes 可精确查询指定板块。"
        ),
    )
    def industry_scale_breadth(
        sector_codes: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        查询行业规模宽度指标数据。

        Args:
            sector_codes: 可选，逗号分隔的行业板块代码；不传则计算全部板块。
            limit: 返回明细条数上限（默认 50，最大 200），避免 token 超限；total 仍反映全量行业数。
        """
        parsed: Optional[List[str]] = None
        if sector_codes and str(sector_codes).strip():
            parsed = [c.strip() for c in str(sector_codes).split(",") if c.strip()]
        try:
            limit = max(1, min(int(limit), 200))
        except (TypeError, ValueError):
            limit = 50

        http_params: Dict[str, str] = {}
        if parsed:
            http_params["sector_codes"] = ",".join(parsed)
        http_body = _fetch_strategy_via_http(
            "/django/api/strategy/industry-scale-breadth/",
            http_params,
        )
        if http_body is not None:
            inner = http_body.get("data") or {}
            rows: List[Dict] = inner.get("data", []) if isinstance(inner, dict) else []
            total = inner.get("total", len(rows)) if isinstance(inner, dict) else len(rows)
            truncated = rows[:limit]
            now = datetime.now().isoformat()
            return {
                "code": 200,
                "message": "success",
                "timestamp": now,
                "interface": "industry_scale_breadth",
                "data": {
                    "total": total,
                    "returned": len(truncated),
                    "limit": limit,
                    "summary": {
                        "top_sector": truncated[0]["sector_name"] if truncated else None,
                        "top_scale_breadth": truncated[0]["scale_breadth"] if truncated else None,
                    },
                    "data": truncated,
                    "sector_codes": parsed,
                    "query_time": now,
                },
            }

        try:
            _ensure_django()
        except Exception as e:
            return error_payload(
                f"Django 初始化失败（请检查环境与数据库配置）: {e}",
                503,
                interface="industry_scale_breadth",
            )

        try:
            from stock_strategy.industry_scale_breadth_strategy import (
                industry_scale_breadth_strategy,
            )
        except Exception as e:
            return error_payload(
                f"加载策略模块失败: {e}",
                500,
                interface="industry_scale_breadth",
            )

        try:
            result = industry_scale_breadth_strategy.get_industry_scale_breadth(
                sector_codes=parsed,
            )
        except Exception as e:
            return error_payload(
                f"获取行业规模宽度数据失败: {e}",
                500,
                interface="industry_scale_breadth",
            )

        if result is None:
            return error_payload(
                "获取行业规模宽度数据失败（无数据或计算异常）",
                500,
                interface="industry_scale_breadth",
            )

        total = len(result)
        truncated = result[:limit]
        now = datetime.now().isoformat()
        return {
            "code": 200,
            "message": "success",
            "timestamp": now,
            "data": {
                "total": total,
                "returned": len(truncated),
                "limit": limit,
                "summary": {
                    "top_sector": truncated[0]["sector_name"] if truncated else None,
                    "top_scale_breadth": truncated[0]["scale_breadth"] if truncated else None,
                },
                "data": truncated,
                "sector_codes": parsed,
                "query_time": now,
            },
        }

    @safe_tool(
        mcp,
        name="django.strategy.industry_ma_breadth",
        description=(
            "行业 MA 市场宽度（与 GET /django/api/strategy/industry-ma-breadth/ 同源，非 HTTP）。"
            "统计各行业内收盘价高于 N 日均线的股票占比；日期为 YYYY-MM-DD。"
            "支持 idx_type 与 level 参数筛选东财行业层级；也可用 limit 直接限制返回条数。"
        ),
    )
    def industry_ma_breadth(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ma_window: int = 20,
        idx_type: str = "行业板块",
        level: Optional[str] = None,
        limit: int = 300,
    ) -> Dict[str, Any]:
        """
        查询行业 MA 市场宽度（收盘价高于 MA 的占比）。

        Args:
            start_date: 开始日期 YYYY-MM-DD；空则策略内默认约过去 90 天
            end_date: 结束日期 YYYY-MM-DD；空则默认当天
            ma_window: 移动平均窗口（交易日），默认 20
            idx_type: 东方财富板块类型，默认行业板块
            level: 东财行业层级，仅 idx_type=行业板块 时生效
            limit: 返回明细条数上限（默认 300，最大 2000）；total 仍反映全量记录数。
        """
        try:
            ma_w = int(ma_window)
        except (TypeError, ValueError):
            return error_payload(
                "参数格式错误：ma_window 应为整数",
                400,
                interface="industry_ma_breadth",
            )
        try:
            limit = max(1, min(int(limit), 2000))
        except (TypeError, ValueError):
            limit = 300
        effective_idx_type = str(idx_type or "行业板块").strip() or "行业板块"
        allowed_levels = {"东财一级行业", "东财二级行业", "东财三级行业"}
        effective_level = level if effective_idx_type == "行业板块" else None
        if effective_level and effective_level not in allowed_levels:
            return error_payload(
                "level参数错误，仅支持：东财一级行业、东财二级行业、东财三级行业",
                400,
                interface="industry_ma_breadth",
            )

        http_params: Dict[str, str] = {"ma_window": str(ma_w), "idx_type": effective_idx_type}
        if start_date and str(start_date).strip():
            http_params["start_date"] = str(start_date).strip()
        if end_date and str(end_date).strip():
            http_params["end_date"] = str(end_date).strip()
        if effective_level:
            http_params["level"] = effective_level
        http_body = _fetch_strategy_via_http(
            "/django/api/strategy/industry-ma-breadth/",
            http_params,
        )
        if http_body is not None:
            inner = http_body.get("data") or {}
            rows: List[Dict] = inner.get("data", []) if isinstance(inner, dict) else []
            total = inner.get("total", len(rows)) if isinstance(inner, dict) else len(rows)
            truncated = rows[:limit]
            now = datetime.now().isoformat()
            # 汇总最新一日各行业宽度，便于 AI 快速判断趋势
            latest_date = max((r.get("date", "") for r in truncated), default=None)
            latest_rows = [r for r in truncated if r.get("date") == latest_date]
            avg_breadth = (
                round(sum(r.get("breadth_ratio", 0) for r in latest_rows) / len(latest_rows), 4)
                if latest_rows else None
            )
            return {
                "code": 200,
                "message": "success",
                "timestamp": now,
                "interface": "industry_ma_breadth",
                "data": {
                    "total": total,
                    "returned": len(truncated),
                    "limit": limit,
                    "summary": {
                        "latest_date": latest_date,
                        "avg_breadth_ratio": avg_breadth,
                        "sector_count_on_latest_date": len(latest_rows),
                    },
                    "data": truncated,
                    "start_date": inner.get("start_date") if isinstance(inner, dict) else start_date,
                    "end_date": inner.get("end_date") if isinstance(inner, dict) else end_date,
                    "ma_window": ma_w,
                    "idx_type": inner.get("idx_type", effective_idx_type) if isinstance(inner, dict) else effective_idx_type,
                    "level": inner.get("level", effective_level) if isinstance(inner, dict) else effective_level,
                    "query_time": now,
                },
            }

        try:
            _ensure_django()
        except Exception as e:
            return error_payload(
                f"Django 初始化失败（请检查环境与数据库配置）: {e}",
                503,
                interface="industry_ma_breadth",
            )

        try:
            from stock_strategy.industry_ma_breadth_strategy import (
                industry_ma_breadth_strategy,
            )
        except Exception as e:
            return error_payload(
                f"加载策略模块失败: {e}",
                500,
                interface="industry_ma_breadth",
            )

        try:
            result = industry_ma_breadth_strategy.get_industry_ma_breadth(
                start_date=start_date,
                end_date=end_date,
                ma_window=ma_w,
                idx_type=effective_idx_type,
                level=effective_level,
            )
        except Exception as e:
            return error_payload(
                f"获取行业MA市场宽度数据失败: {e}",
                500,
                interface="industry_ma_breadth",
            )

        if result is None:
            return error_payload(
                "获取行业MA市场宽度数据失败",
                500,
                interface="industry_ma_breadth",
            )

        total = len(result)
        truncated = result[:limit]
        latest_date = max((r.get("date", "") for r in truncated), default=None)
        latest_rows = [r for r in truncated if r.get("date") == latest_date]
        avg_breadth = (
            round(sum(r.get("breadth_ratio", 0) for r in latest_rows) / len(latest_rows), 4)
            if latest_rows else None
        )
        now = datetime.now().isoformat()
        return {
            "code": 200,
            "message": "success",
            "timestamp": now,
            "data": {
                "total": total,
                "returned": len(truncated),
                "limit": limit,
                "summary": {
                    "latest_date": latest_date,
                    "avg_breadth_ratio": avg_breadth,
                    "sector_count_on_latest_date": len(latest_rows),
                },
                "data": truncated,
                "start_date": start_date,
                "end_date": end_date,
                "ma_window": ma_w,
                "idx_type": effective_idx_type,
                "level": effective_level,
                "query_time": now,
            },
        }

    @safe_tool(
        mcp,
        name="django.strategy.index_rps",
        description=(
            "指数/板块 RPS 强度排名（与 GET /django/api/strategy/index-rps/ 同源，基于 Tushare dc_index/dc_daily，非 HTTP）。"
            "支持 periods、idx_type（如 地域板块）、trade_date、token、save"
        ),
    )
    def index_rps(
        periods: str = "5,20,60",
        idx_type: str = "概念板块",
        trade_date: Optional[str] = None,
        token: Optional[str] = None,
        save: bool = False,
    ) -> Dict[str, Any]:
        """
        查询东方财富板块 RPS 排名，参数与 HTTP 接口一致。

        Args:
            periods: 逗号分隔周期（交易日），默认 5,20,60
            idx_type: 板块类型，如 概念板块、行业板块、地域板块
            trade_date: 截止交易日 YYYYMMDD，空则取 dc_index 最新交易日
            token: Tushare Token（可选）
            save: 为 true 时将结果写入 index_rps 表（列名与 pywencai 版 save 接口对齐）
        """
        periods_str = (periods or "5,20,60").strip()
        try:
            period_list = [int(p.strip()) for p in periods_str.split(",") if p.strip()]
            if not period_list:
                period_list = [5, 20, 60]
        except ValueError:
            return error_payload(
                "周期参数格式错误，应为逗号分隔的整数",
                400,
                interface="index_rps",
            )

        try:
            from scheduled_tasks.stock_data_query_tasks.dc_board_rps import (
                compute_board_rps,
            )
        except Exception as e:
            return error_payload(
                f"加载 RPS 计算模块失败: {e}",
                500,
                interface="index_rps",
            )

        try:
            df, errors = compute_board_rps(
                periods=period_list,
                idx_type=idx_type or "概念板块",
                trade_date=trade_date,
                token=token,
            )
        except Exception as e:
            return error_payload(
                f"获取指数RPS强度排名失败: {e}",
                500,
                interface="index_rps",
            )

        if df is None:
            return error_payload(
                f'获取RPS数据失败: {", ".join(errors) if errors else "未知错误"}',
                500,
                interface="index_rps",
            )

        saved_count = 0
        if save:
            try:
                _ensure_django()
            except Exception as e:
                return error_payload(
                    f"Django 初始化失败，无法保存: {e}",
                    503,
                    interface="index_rps",
                )
            try:
                from stock_strategy.services import rps_service

                rename_map: Dict[str, str] = {
                    "ts_code": "指数代码",
                    "name": "指数简称",
                }
                for p in period_list:
                    c = f"return_{p}"
                    if c in df.columns:
                        rename_map[c] = f"{p}日涨跌幅"
                save_df = df.rename(columns=rename_map)
                saved_count = int(rps_service.save_rps_data(save_df, period_list))
            except Exception as e:
                return error_payload(
                    f"保存 RPS 到数据库失败: {e}",
                    500,
                    interface="index_rps",
                )

        result = df.fillna("").to_dict(orient="records")
        now = datetime.now().isoformat()
        return {
            "code": 200,
            "message": "success",
            "timestamp": now,
            "data": {
                "total": len(result),
                "data": result,
                "periods": period_list,
                "idx_type": idx_type,
                "trade_date": trade_date,
                "errors": errors,
                "saved_count": saved_count,
                "query_time": now,
            },
        }
