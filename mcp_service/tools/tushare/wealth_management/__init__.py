from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from mcp_service.tools.tushare._registry import apply_pagination, safe_tool


def register_wealth_management_tools(mcp: FastMCP) -> None:
    def _call(interface: str, params: Dict[str, Any], fields: Optional[str], token: Optional[str]) -> Dict[str, Any]:
        return call_tushare(interface=interface, params=params, fields=fields, token=token, use_query=False)

    def _clean(**kwargs: Any) -> Dict[str, Any]:
        return {k: v for k, v in kwargs.items() if v is not None and v != ""}

    def _paginate(resp: Dict[str, Any], limit: int, offset: int, max_limit: int = 500) -> Dict[str, Any]:
        safe_limit = max(1, min(int(limit or 30), max_limit))
        safe_offset = max(0, int(offset or 0))
        return apply_pagination(resp, safe_limit, safe_offset)

    @safe_tool(
        mcp,
        name="tushare.wealth_management.fund_sales_vol",
        description="销售机构公募基金销售保有规模 fund_sales_vol",
    )
    def fund_sales_vol(
        year: Optional[str] = None,
        quarter: Optional[str] = None,
        name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(year=year, quarter=quarter, name=name)
        return _paginate(_call("fund_sales_vol", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.wealth_management.fund_sales_ratio",
        description="各渠道公募基金销售保有规模占比 fund_sales_ratio",
    )
    def fund_sales_ratio(
        year: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(year=year)
        return _paginate(_call("fund_sales_ratio", params, fields, token), limit, offset)
