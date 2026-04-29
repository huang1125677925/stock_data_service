from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from mcp_service.tools.tushare._registry import error_payload, safe_tool


def register_hk_stock_tools(mcp: FastMCP) -> None:
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
        name="tushare.hk_stock.hk_basic",
        description="港股列表 hk_basic",
    )
    def hk_basic(
        ts_code: Optional[str] = None,
        list_status: str = "L",
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if list_status:
            params["list_status"] = list_status
        return _call("hk_basic", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.hk_stock.hk_daily",
        description="港股日线行情 hk_daily",
    )
    def hk_daily(
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
                interface="hk_daily",
            )
        return _call("hk_daily", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.hk_stock.hk_mins",
        description="港股分钟行情 hk_mins",
    )
    def hk_mins(
        ts_code: str,
        freq: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="hk_mins")
        if not freq:
            return error_payload("freq 为必填参数", 400, interface="hk_mins")
        params: Dict[str, Any] = {"ts_code": ts_code, "freq": freq}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _call("hk_mins", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.hk_stock.hk_daily_adj",
        description="港股复权行情 hk_daily_adj",
    )
    def hk_daily_adj(
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
                interface="hk_daily_adj",
            )
        return _call("hk_daily_adj", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.hk_stock.hk_tradecal",
        description="港股交易日历 hk_tradecal",
    )
    def hk_tradecal(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        is_open: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if is_open:
            params["is_open"] = is_open
        return _call("hk_tradecal", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.hk_stock.rt_hk_k",
        description="港股实时日线 rt_hk_k",
    )
    def rt_hk_k(
        ts_code: str,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="rt_hk_k")
        return _call("rt_hk_k", {"ts_code": ts_code}, fields, token)

    @safe_tool(
        mcp,
        name="tushare.hk_stock.hk_income",
        description="港股利润表 hk_income",
    )
    def hk_income(
        ts_code: str,
        period: Optional[str] = None,
        ind_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="hk_income")
        params: Dict[str, Any] = {"ts_code": ts_code}
        if period:
            params["period"] = period
        if ind_name:
            params["ind_name"] = ind_name
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _call("hk_income", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.hk_stock.hk_balancesheet",
        description="港股资产负债表 hk_balancesheet",
    )
    def hk_balancesheet(
        ts_code: str,
        period: Optional[str] = None,
        ind_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload(
                "ts_code 为必填参数",
                400,
                interface="hk_balancesheet",
            )
        params: Dict[str, Any] = {"ts_code": ts_code}
        if period:
            params["period"] = period
        if ind_name:
            params["ind_name"] = ind_name
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _call("hk_balancesheet", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.hk_stock.hk_cashflow",
        description="港股现金流量表 hk_cashflow",
    )
    def hk_cashflow(
        ts_code: str,
        period: Optional[str] = None,
        ind_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="hk_cashflow")
        params: Dict[str, Any] = {"ts_code": ts_code}
        if period:
            params["period"] = period
        if ind_name:
            params["ind_name"] = ind_name
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _call("hk_cashflow", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.hk_stock.hk_fina_indicator",
        description="港股财务指标数据 hk_fina_indicator",
    )
    def hk_fina_indicator(
        ts_code: str,
        period: Optional[str] = None,
        report_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload(
                "ts_code 为必填参数",
                400,
                interface="hk_fina_indicator",
            )
        params: Dict[str, Any] = {"ts_code": ts_code}
        if period:
            params["period"] = period
        if report_type:
            params["report_type"] = report_type
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _call("hk_fina_indicator", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.hk_stock.hk_adjfactor",
        description="港股复权因子 hk_adjfactor",
    )
    def hk_adjfactor(
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
                interface="hk_adjfactor",
            )
        return _call("hk_adjfactor", params, fields, token)
