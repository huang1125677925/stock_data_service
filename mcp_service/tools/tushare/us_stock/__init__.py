from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from mcp_service.tools.tushare._registry import error_payload, safe_tool


def register_us_stock_tools(mcp: FastMCP) -> None:
    def _call(
        interface: str,
        params: Dict[str, Any],
        fields: Optional[str],
        token: Optional[str],
    ) -> Dict[str, Any]:
        return call_tushare(
            interface=interface,
            params=params,
            fields=fields,
            token=token,
            use_query=False,
        )

    @safe_tool(
        mcp,
        name="tushare.us_stock.us_tradecal",
        description="美股交易日历 us_tradecal",
    )
    def us_tradecal(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        is_open: Optional[int] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if is_open is not None:
            params["is_open"] = is_open
        return _call("us_tradecal", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.us_stock.us_basic",
        description="美股列表 us_basic",
    )
    def us_basic(
        ts_code: Optional[str] = None,
        classify: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if classify:
            params["classify"] = classify
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = limit
        return _call("us_basic", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.us_stock.us_daily",
        description="美股行情(未复权) us_daily",
    )
    def us_daily(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if not params:
            return error_payload(
                "ts_code 或 trade_date 或 start_date/end_date 至少提供一个参数",
                400,
                interface="us_daily",
            )
        return _call("us_daily", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.us_stock.us_daily_adj",
        description="美股复权行情 us_daily_adj",
    )
    def us_daily_adj(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if exchange:
            params["exchange"] = exchange
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = limit
        if not (ts_code or trade_date or start_date or end_date):
            return error_payload(
                "ts_code 或 trade_date 或 start_date/end_date 至少提供一个参数",
                400,
                interface="us_daily_adj",
            )
        return _call("us_daily_adj", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.us_stock.us_income",
        description="美股利润表 us_income",
    )
    def us_income(
        ts_code: str,
        period: Optional[str] = None,
        ind_name: Optional[str] = None,
        report_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="us_income")
        params: Dict[str, Any] = {"ts_code": ts_code}
        if period:
            params["period"] = period
        if ind_name:
            params["ind_name"] = ind_name
        if report_type:
            params["report_type"] = report_type
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _call("us_income", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.us_stock.us_balancesheet",
        description="美股资产负债表 us_balancesheet",
    )
    def us_balancesheet(
        ts_code: str,
        period: Optional[str] = None,
        ind_name: Optional[str] = None,
        report_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="us_balancesheet")
        params: Dict[str, Any] = {"ts_code": ts_code}
        if period:
            params["period"] = period
        if ind_name:
            params["ind_name"] = ind_name
        if report_type:
            params["report_type"] = report_type
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _call("us_balancesheet", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.us_stock.us_cashflow",
        description="美股现金流量表 us_cashflow",
    )
    def us_cashflow(
        ts_code: str,
        period: Optional[str] = None,
        ind_name: Optional[str] = None,
        report_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="us_cashflow")
        params: Dict[str, Any] = {"ts_code": ts_code}
        if period:
            params["period"] = period
        if ind_name:
            params["ind_name"] = ind_name
        if report_type:
            params["report_type"] = report_type
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _call("us_cashflow", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.us_stock.us_fina_indicator",
        description="美股财务指标 us_fina_indicator",
    )
    def us_fina_indicator(
        ts_code: str,
        period: Optional[str] = None,
        report_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="us_fina_indicator")
        params: Dict[str, Any] = {"ts_code": ts_code}
        if period:
            params["period"] = period
        if report_type:
            params["report_type"] = report_type
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _call("us_fina_indicator", params, fields, token)
