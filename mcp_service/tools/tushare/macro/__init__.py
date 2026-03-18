from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from mcp_service.tools.tushare._registry import safe_tool


def register_macro_tools(mcp: FastMCP) -> None:
    def _call(interface: str, params: Dict[str, Any], fields: Optional[str], token: Optional[str]) -> Dict[str, Any]:
        return call_tushare(interface=interface, params=params, fields=fields, token=token, use_query=False)

    def _clean(**kwargs: Any) -> Dict[str, Any]:
        return {k: v for k, v in kwargs.items() if v is not None and v != ""}

    @safe_tool(mcp, name="tushare.macro.shibor", description="Shibor利率 shibor")
    def shibor(
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(date=date, start_date=start_date, end_date=end_date)
        return _call("shibor", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.shibor_quote", description="Shibor报价数据 shibor_quote")
    def shibor_quote(
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(date=date, start_date=start_date, end_date=end_date)
        return _call("shibor_quote", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.lpr", description="LPR贷款基础利率 lpr")
    def lpr(
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(date=date, start_date=start_date, end_date=end_date)
        return _call("lpr", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.libor", description="Libor利率 libor")
    def libor(
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        curr_type: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(date=date, start_date=start_date, end_date=end_date, curr_type=curr_type)
        return _call("libor", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.hibor", description="Hibor利率 hibor")
    def hibor(
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(date=date, start_date=start_date, end_date=end_date)
        return _call("hibor", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.cn_gdp", description="国内生产总值（GDP） cn_gdp")
    def cn_gdp(
        quarter: Optional[str] = None,
        start_quarter: Optional[str] = None,
        end_quarter: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(quarter=quarter, start_quarter=start_quarter, end_quarter=end_quarter)
        return _call("cn_gdp", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.cn_cpi", description="居民消费价格指数（CPI） cn_cpi")
    def cn_cpi(
        month: Optional[str] = None,
        start_month: Optional[str] = None,
        end_month: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(month=month, start_month=start_month, end_month=end_month)
        return _call("cn_cpi", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.cn_ppi", description="工业生产者出厂价格指数（PPI） cn_ppi")
    def cn_ppi(
        month: Optional[str] = None,
        start_month: Optional[str] = None,
        end_month: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(month=month, start_month=start_month, end_month=end_month)
        return _call("cn_ppi", params, fields, token)
