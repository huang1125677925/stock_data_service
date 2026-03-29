"""
Django 策略类 HTTP 接口的同源封装（非 HTTP），供 MCP 调用。
需配置数据库与 DJANGO_SETTINGS_MODULE（默认 stock_data_service.settings）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from mcp_service.tools.tushare._registry import error_payload, safe_tool

_django_ready = False


def _ensure_django() -> None:
    global _django_ready
    if _django_ready:
        return
    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stock_data_service.settings")
    import django

    django.setup()
    _django_ready = True


def register_django_strategy_tools(mcp: FastMCP) -> None:
    @safe_tool(
        mcp,
        name="django.strategy.industry_scale_breadth",
        description=(
            "行业规模宽度指标（与 GET /django/api/strategy/industry-scale-breadth/ 同源，非 HTTP）。"
            "指标 = (行业总市值/市场总市值) × (行业公司数/市场总公司数)"
        ),
    )
    def industry_scale_breadth(
        sector_codes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        查询行业规模宽度指标数据。

        Args:
            sector_codes: 可选，逗号分隔的行业板块代码；不传则计算全部板块。

        Returns:
            与 Django 接口一致：data 内含 total、data（列表）、sector_codes、query_time。
        """
        parsed: Optional[List[str]] = None
        if sector_codes and str(sector_codes).strip():
            parsed = [c.strip() for c in str(sector_codes).split(",") if c.strip()]

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

        now = datetime.now().isoformat()
        return {
            "code": 200,
            "message": "success",
            "timestamp": now,
            "data": {
                "total": len(result),
                "data": result,
                "sector_codes": parsed,
                "query_time": now,
            },
        }

    @safe_tool(
        mcp,
        name="django.strategy.industry_ma_breadth",
        description=(
            "行业 MA 市场宽度（与 GET /django/api/strategy/industry-ma-breadth/ 同源，非 HTTP）。"
            "统计各行业内收盘价高于 N 日均线的股票占比；日期为 YYYY-MM-DD"
        ),
    )
    def industry_ma_breadth(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ma_window: int = 20,
        sector_codes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        查询行业 MA 市场宽度（收盘价高于 MA 的占比）。

        Args:
            start_date: 开始日期 YYYY-MM-DD；空则策略内默认约过去 90 天
            end_date: 结束日期 YYYY-MM-DD；空则默认当天
            ma_window: 移动平均窗口（交易日），默认 20
            sector_codes: 可选，逗号分隔板块代码；空则全部板块
        """
        parsed: Optional[List[str]] = None
        if sector_codes and str(sector_codes).strip():
            parsed = [c.strip() for c in str(sector_codes).split(",") if c.strip()]

        try:
            ma_w = int(ma_window)
        except (TypeError, ValueError):
            return error_payload(
                "参数格式错误：ma_window 应为整数",
                400,
                interface="industry_ma_breadth",
            )

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
                sector_codes=parsed,
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

        now = datetime.now().isoformat()
        return {
            "code": 200,
            "message": "success",
            "timestamp": now,
            "data": {
                "total": len(result),
                "data": result,
                "start_date": start_date,
                "end_date": end_date,
                "ma_window": ma_w,
                "sector_codes": parsed,
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
            periods: 逗号分隔周期（自然日），默认 5,20,60
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
