from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from mcp_service.tools.tushare._registry import error_payload, safe_tool


def register_stock_margin_tools(mcp: FastMCP) -> None:
    def _call(interface: str, params: Dict[str, Any], fields: Optional[str], token: Optional[str]) -> Dict[str, Any]:
        return call_tushare(interface=interface, params=params, fields=fields, token=token, use_query=False)

    def _clean(**kwargs: Any) -> Dict[str, Any]:
        return {k: v for k, v in kwargs.items() if v is not None and v != ""}

    @safe_tool(mcp, name="tushare.stock.margin.margin", description="融资融券交易汇总 margin")
    def margin(
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange_id: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(trade_date=trade_date, start_date=start_date, end_date=end_date, exchange_id=exchange_id)
        return _call("margin", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.margin.margin_detail", description="融资融券交易明细 margin_detail")
    def margin_detail(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(trade_date=trade_date, ts_code=ts_code, start_date=start_date, end_date=end_date)
        return _call("margin_detail", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.margin.margin_secs", description="融资融券标的_盘前 margin_secs")
    def margin_secs(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        exchange: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, exchange=exchange, start_date=start_date, end_date=end_date)
        return _call("margin_secs", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.margin.slb_len", description="转融资交易汇总 slb_len")
    def slb_len(
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _call("slb_len", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.margin.slb_len_mm", description="做市借券交易汇总_停 slb_len_mm")
    def slb_len_mm(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(trade_date=trade_date, ts_code=ts_code, start_date=start_date, end_date=end_date)
        return _call("slb_len_mm", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.margin.slb_sec", description="转融券交易汇总_停 slb_sec")
    def slb_sec(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(trade_date=trade_date, ts_code=ts_code, start_date=start_date, end_date=end_date)
        return _call("slb_sec", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.margin.slb_sec_detail", description="转融券交易明细_停 slb_sec_detail")
    def slb_sec_detail(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(trade_date=trade_date, ts_code=ts_code, start_date=start_date, end_date=end_date)
        return _call("slb_sec_detail", params, fields, token)
