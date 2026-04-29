from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from mcp_service.tools.tushare._registry import apply_pagination, safe_tool


def register_corpus_tools(mcp: FastMCP) -> None:
    """大模型语料 / 研报等与 skill 索引对齐的补充接口（部分已在 news_data_tools 中）。"""

    def _call(interface: str, params: Dict[str, Any], fields: Optional[str], token: Optional[str]) -> Dict[str, Any]:
        return call_tushare(interface=interface, params=params, fields=fields, token=token, use_query=False)

    def _clean(**kwargs: Any) -> Dict[str, Any]:
        return {k: v for k, v in kwargs.items() if v is not None and v != ""}

    def _paginate(resp: Dict[str, Any], limit: int, offset: int, max_limit: int = 500) -> Dict[str, Any]:
        safe_limit = max(1, min(int(limit or 30), max_limit))
        safe_offset = max(0, int(offset or 0))
        return apply_pagination(resp, safe_limit, safe_offset)

    @safe_tool(mcp, name="tushare.corpus.research_report", description="券商研究报告 research_report")
    def research_report(
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        report_type: Optional[str] = None,
        ts_code: Optional[str] = None,
        inst_csname: Optional[str] = None,
        ind_name: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            report_type=report_type,
            ts_code=ts_code,
            inst_csname=inst_csname,
            ind_name=ind_name,
        )
        return _paginate(_call("research_report", params, fields, token), limit, offset)

    @safe_tool(mcp, name="tushare.corpus.npr", description="国家政策法规库 npr")
    def npr(
        org: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ptype: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(org=org, start_date=start_date, end_date=end_date, ptype=ptype)
        return _paginate(_call("npr", params, fields, token), limit, offset)
