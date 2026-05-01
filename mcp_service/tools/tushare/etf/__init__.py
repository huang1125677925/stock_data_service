from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from index_data.utils import replace_nan
from mcp_service.tools.tushare._registry import apply_pagination, error_payload, safe_tool

_ETF_BASIC_NAME_FIELDS = (
    "ts_code,csname,extname,cname,index_code,index_name,setup_date,list_date,"
    "delist_date,list_status,exchange,mgr_name,custod_name,mgt_fee,etf_type"
)


def _etf_basic_record_matches_name(record: dict, needle_lower: str) -> bool:
    """子串匹配（不区分大小写）：中文简称、扩位简称、全称、ts_code。"""
    for key in ("csname", "extname", "cname"):
        val = record.get(key)
        if isinstance(val, str) and needle_lower in val.lower():
            return True
    ts_code = record.get("ts_code")
    if isinstance(ts_code, str) and needle_lower in ts_code.lower():
        return True
    return False


def register_etf_tools(mcp: FastMCP) -> None:
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

    def _paginate(
        resp: Dict[str, Any], limit: int, offset: int, max_limit: int = 500
    ) -> Dict[str, Any]:
        safe_limit = max(1, min(int(limit or 30), max_limit))
        safe_offset = max(0, int(offset or 0))
        return apply_pagination(resp, safe_limit, safe_offset)

    @safe_tool(
        mcp,
        name="tushare.etf.etf_basic",
        description="ETF基础信息 etf_basic",
    )
    def etf_basic(
        ts_code: Optional[str] = None,
        index_code: Optional[str] = None,
        list_date: Optional[str] = None,
        list_status: str = "L",
        exchange: Optional[str] = None,
        mgr: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if index_code:
            params["index_code"] = index_code
        if list_date:
            params["list_date"] = list_date
        if list_status:
            params["list_status"] = list_status
        if exchange:
            params["exchange"] = exchange
        if mgr:
            params["mgr"] = mgr
        return _paginate(_call("etf_basic", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.etf.etf_basic_search_by_name",
        description=(
            "按名称/代码子串模糊查询 ETF：拉取 etf_basic 后在本地匹配 csname、extname、cname、ts_code；"
            "可选 exchange、list_status、mgr 先收窄上游数据。"
        ),
    )
    def etf_basic_search_by_name(
        name_query: str,
        exchange: Optional[str] = None,
        list_status: str = "L",
        mgr: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        q = (name_query or "").strip()
        if not q:
            return error_payload("name_query 不能为空", 400, interface="etf_basic_search_by_name")

        params: Dict[str, Any] = {}
        if exchange:
            params["exchange"] = exchange
        if list_status:
            params["list_status"] = list_status
        if mgr:
            params["mgr"] = mgr

        use_fields = fields or _ETF_BASIC_NAME_FIELDS
        resp = _call("etf_basic", params, use_fields, token)
        if resp.get("code") != 200:
            return resp

        data = resp.get("data") or {}
        records = data.get("records") or []
        needle = q.lower()
        matched = [replace_nan(r) for r in records if _etf_basic_record_matches_name(r, needle)]

        wrapped = {
            "code": 200,
            "message": resp.get("message", "success"),
            "timestamp": resp.get("timestamp"),
            "data": {
                "interface": "etf_basic_search_by_name",
                "count": len(matched),
                "records": matched,
                "name_query": q,
            },
        }
        return _paginate(wrapped, limit, offset)

    @safe_tool(
        mcp,
        name="tushare.etf.etf_index",
        description="ETF基准指数列表 etf_index",
    )
    def etf_index(
        ts_code: Optional[str] = None,
        pub_date: Optional[str] = None,
        base_date: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if pub_date:
            params["pub_date"] = pub_date
        if base_date:
            params["base_date"] = base_date
        return _paginate(_call("etf_index", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.etf.fund_daily",
        description="ETF日线行情 fund_daily",
    )
    def fund_daily(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
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
                interface="fund_daily",
            )
        return _paginate(_call("fund_daily", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.etf.rt_etf_k",
        description="ETF实时日线 rt_etf_k",
    )
    def rt_etf_k(
        ts_code: str,
        topic: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="rt_etf_k")
        ts_code_upper = ts_code.upper()
        if ".SH" in ts_code_upper and not topic:
            return error_payload(
                "沪市ETF需提供 topic 参数（如 HQ_FND_TICK）",
                400,
                interface="rt_etf_k",
            )
        params: Dict[str, Any] = {"ts_code": ts_code}
        if topic:
            params["topic"] = topic
        return _paginate(_call("rt_etf_k", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.etf.fund_adj",
        description="基金复权因子 fund_adj",
    )
    def fund_adj(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        tushare_offset: Optional[int] = None,
        tushare_limit: Optional[int] = None,
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
        if tushare_offset is not None:
            params["offset"] = tushare_offset
        if tushare_limit is not None:
            params["limit"] = tushare_limit
        if not params:
            return error_payload(
                "ts_code 或 trade_date 或 start_date/end_date 至少提供一个参数",
                400,
                interface="fund_adj",
            )
        return _paginate(_call("fund_adj", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.etf.stk_mins",
        description="ETF历史分钟行情 stk_mins",
    )
    def stk_mins(
        ts_code: str,
        freq: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 60,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="stk_mins")
        if not freq:
            return error_payload("freq 为必填参数", 400, interface="stk_mins")
        params: Dict[str, Any] = {"ts_code": ts_code, "freq": freq}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _paginate(_call("stk_mins", params, fields, token), limit, offset)

    @safe_tool(mcp, name="tushare.etf.etf_share_size", description="ETF份额规模 etf_share_size")
    def etf_share_size(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
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
        return _paginate(_call("etf_share_size", params, fields, token), limit, offset)
