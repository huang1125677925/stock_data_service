from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from mcp_service.tools.tushare._registry import error_payload, safe_tool


def register_options_tools(mcp: FastMCP) -> None:
    def _call(interface: str, params: Dict[str, Any], fields: Optional[str], token: Optional[str]) -> Dict[str, Any]:
        return call_tushare(interface=interface, params=params, fields=fields, token=token, use_query=False)

    def _clean(**kwargs: Any) -> Dict[str, Any]:
        return {k: v for k, v in kwargs.items() if v is not None and v != ""}

    @safe_tool(mcp, name="tushare.options.opt_basic", description="期权合约信息 opt_basic")
    def opt_basic(
        ts_code: Optional[str] = None,
        exchange: Optional[str] = None,
        opt_code: Optional[str] = None,
        call_put: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, exchange=exchange, opt_code=opt_code, call_put=call_put)
        return _call("opt_basic", params, fields, token)

    @safe_tool(mcp, name="tushare.options.opt_daily", description="期权日线行情 opt_daily")
    def opt_daily(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code and not trade_date and not start_date and not end_date:
            return error_payload("ts_code 或 trade_date 或 start_date/end_date 至少提供一个参数", 400, interface="opt_daily")
        params: Dict[str, Any] = _clean(
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            exchange=exchange,
        )
        return _call("opt_daily", params, fields, token)
