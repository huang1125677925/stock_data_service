from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from mcp_service.tools.tushare._registry import error_payload, safe_tool


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
        return _call("etf_basic", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.etf.etf_index",
        description="ETF基准指数列表 etf_index",
    )
    def etf_index(
        ts_code: Optional[str] = None,
        pub_date: Optional[str] = None,
        base_date: Optional[str] = None,
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
        return _call("etf_index", params, fields, token)

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
        return _call("fund_daily", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.etf.rt_etf_k",
        description="ETF实时日线 rt_etf_k",
    )
    def rt_etf_k(
        ts_code: str,
        topic: Optional[str] = None,
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
        return _call("rt_etf_k", params, fields, token)

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
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = limit
        if not params:
            return error_payload(
                "ts_code 或 trade_date 或 start_date/end_date 至少提供一个参数",
                400,
                interface="fund_adj",
            )
        return _call("fund_adj", params, fields, token)

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
        return _call("stk_mins", params, fields, token)
