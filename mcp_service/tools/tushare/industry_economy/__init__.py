from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from mcp_service.tools.tushare._registry import error_payload, safe_tool


def register_industry_economy_tools(mcp: FastMCP) -> None:
    def _call(interface: str, params: Dict[str, Any], fields: Optional[str], token: Optional[str]) -> Dict[str, Any]:
        return call_tushare(interface=interface, params=params, fields=fields, token=token, use_query=False)

    def _clean(**kwargs: Any) -> Dict[str, Any]:
        return {k: v for k, v in kwargs.items() if v is not None and v != ""}

    @safe_tool(mcp, name="tushare.industry_economy.bo_daily", description="电影日度票房 bo_daily")
    def bo_daily(
        date: str,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not date:
            return error_payload("date 为必填参数（YYYYMMDD）", 400, interface="bo_daily")
        return _call("bo_daily", {"date": date}, fields, token)

    @safe_tool(mcp, name="tushare.industry_economy.bo_weekly", description="电影周度票房 bo_weekly")
    def bo_weekly(
        date: str,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not date:
            return error_payload("date 为必填参数（每周一日期 YYYYMMDD）", 400, interface="bo_weekly")
        return _call("bo_weekly", {"date": date}, fields, token)

    @safe_tool(mcp, name="tushare.industry_economy.bo_monthly", description="电影月度票房 bo_monthly")
    def bo_monthly(
        date: str,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not date:
            return error_payload("date 为必填参数（每月1号 YYYYMMDD）", 400, interface="bo_monthly")
        return _call("bo_monthly", {"date": date}, fields, token)

    @safe_tool(mcp, name="tushare.industry_economy.bo_cinema", description="影院每日票房 bo_cinema")
    def bo_cinema(
        date: str,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not date:
            return error_payload("date 为必填参数（YYYYMMDD）", 400, interface="bo_cinema")
        return _call("bo_cinema", {"date": date}, fields, token)

    @safe_tool(mcp, name="tushare.industry_economy.film_record", description="全国电影剧本备案 film_record")
    def film_record(
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ann_date=ann_date, start_date=start_date, end_date=end_date)
        if not params:
            return error_payload("ann_date 或 start_date/end_date 至少提供一个参数", 400, interface="film_record")
        return _call("film_record", params, fields, token)

    @safe_tool(mcp, name="tushare.industry_economy.teleplay_record", description="全国电视剧备案公示 teleplay_record")
    def teleplay_record(
        report_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(report_date=report_date, start_date=start_date, end_date=end_date)
        return _call("teleplay_record", params, fields, token)

    @safe_tool(mcp, name="tushare.industry_economy.tmt_twincome", description="台湾电子产业月营收 tmt_twincome")
    def tmt_twincome(
        item: str,
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not item:
            return error_payload("item 为必填参数（产品代码）", 400, interface="tmt_twincome")
        params: Dict[str, Any] = _clean(item=item, date=date, start_date=start_date, end_date=end_date)
        return _call("tmt_twincome", params, fields, token)

    @safe_tool(mcp, name="tushare.industry_economy.tmt_twincomedetail", description="台湾电子产业月营收明细 tmt_twincomedetail")
    def tmt_twincomedetail(
        date: Optional[str] = None,
        item: Optional[str] = None,
        symbol: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(
            date=date, item=item, symbol=symbol, start_date=start_date, end_date=end_date
        )
        return _call("tmt_twincomedetail", params, fields, token)
