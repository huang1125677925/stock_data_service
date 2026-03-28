from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from mcp_service.tools.tushare._registry import apply_pagination, error_payload, safe_tool


def register_index_tools(mcp: FastMCP) -> None:
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

    def _paginate(resp: Dict[str, Any], limit: int, offset: int, max_limit: int = 500) -> Dict[str, Any]:
        safe_limit = max(1, min(int(limit or 30), max_limit))
        safe_offset = max(0, int(offset or 0))
        return apply_pagination(resp, safe_limit, safe_offset)

    @safe_tool(
        mcp,
        name="tushare.index.index_basic",
        description="指数基本信息 index_basic",
    )
    def index_basic(
        ts_code: Optional[str] = None,
        name: Optional[str] = None,
        market: Optional[str] = None,
        publisher: Optional[str] = None,
        category: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if name:
            params["name"] = name
        if market:
            params["market"] = market
        if publisher:
            params["publisher"] = publisher
        if category:
            params["category"] = category
        return _call("index_basic", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.index.index_daily",
        description="指数日线行情 index_daily",
    )
    def index_daily(
        ts_code: str,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """指数日线行情 index_daily。limit默认30，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="index_daily")
        params: Dict[str, Any] = {"ts_code": ts_code}
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _paginate(_call("index_daily", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.index_weekly",
        description="指数周线行情 index_weekly",
    )
    def index_weekly(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 26,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """指数周线行情 index_weekly。limit默认26（半年），最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _paginate(_call("index_weekly", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.index_monthly",
        description="指数月线行情 index_monthly",
    )
    def index_monthly(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 24,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """指数月线行情 index_monthly。limit默认24（2年），最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _paginate(_call("index_monthly", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.index_weight",
        description="指数成分和权重 index_weight",
    )
    def index_weight(
        index_code: str,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """指数成分和权重 index_weight。limit默认100，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        if not index_code:
            return error_payload(
                "index_code 为必填参数",
                400,
                interface="index_weight",
            )
        params: Dict[str, Any] = {"index_code": index_code}
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _paginate(_call("index_weight", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.index_dailybasic",
        description="大盘指数每日指标 index_dailybasic",
    )
    def index_dailybasic(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """大盘指数每日指标 index_dailybasic。limit默认30，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = {}
        if trade_date:
            params["trade_date"] = trade_date
        if ts_code:
            params["ts_code"] = ts_code
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if not (trade_date or ts_code or start_date or end_date):
            return error_payload(
                "trade_date 或 ts_code 或 start_date/end_date 至少提供一个参数",
                400,
                interface="index_dailybasic",
            )
        return _paginate(_call("index_dailybasic", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.index_global",
        description="国际主要指数日线行情 index_global",
    )
    def index_global(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """国际主要指数日线行情 index_global。limit默认30，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _paginate(_call("index_global", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.idx_factor_pro",
        description="指数技术因子(专业版) idx_factor_pro",
    )
    def idx_factor_pro(
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        trade_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if trade_date:
            params["trade_date"] = trade_date
        return _call("idx_factor_pro", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.index.daily_info",
        description="市场交易统计 daily_info",
    )
    def daily_info(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        exchange: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if trade_date:
            params["trade_date"] = trade_date
        if ts_code:
            params["ts_code"] = ts_code
        if exchange:
            params["exchange"] = exchange
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _call("daily_info", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.index.sz_daily_info",
        description="深圳市场每日交易概况 sz_daily_info",
    )
    def sz_daily_info(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if trade_date:
            params["trade_date"] = trade_date
        if ts_code:
            params["ts_code"] = ts_code
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _call("sz_daily_info", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.index.index_classify",
        description="申万行业分类 index_classify",
    )
    def index_classify(
        index_code: Optional[str] = None,
        level: Optional[str] = None,
        parent_code: Optional[str] = None,
        src: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if index_code:
            params["index_code"] = index_code
        if level:
            params["level"] = level
        if parent_code:
            params["parent_code"] = parent_code
        if src:
            params["src"] = src
        return _call("index_classify", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.index.index_member_all",
        description="申万行业成分构成(分级) index_member_all",
    )
    def index_member_all(
        l1_code: Optional[str] = None,
        l2_code: Optional[str] = None,
        l3_code: Optional[str] = None,
        ts_code: Optional[str] = None,
        is_new: str = "Y",
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if l1_code:
            params["l1_code"] = l1_code
        if l2_code:
            params["l2_code"] = l2_code
        if l3_code:
            params["l3_code"] = l3_code
        if ts_code:
            params["ts_code"] = ts_code
        if is_new:
            params["is_new"] = is_new
        return _call("index_member_all", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.index.sw_daily",
        description="申万行业日线行情 sw_daily",
    )
    def sw_daily(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """申万行业日线行情 sw_daily。limit默认30，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _paginate(_call("sw_daily", params, fields, token), limit, offset)

    @safe_tool(
        mcp,
        name="tushare.index.ci_index_member",
        description="中信行业成分 ci_index_member",
    )
    def ci_index_member(
        l1_code: Optional[str] = None,
        l2_code: Optional[str] = None,
        l3_code: Optional[str] = None,
        ts_code: Optional[str] = None,
        is_new: str = "Y",
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if l1_code:
            params["l1_code"] = l1_code
        if l2_code:
            params["l2_code"] = l2_code
        if l3_code:
            params["l3_code"] = l3_code
        if ts_code:
            params["ts_code"] = ts_code
        if is_new:
            params["is_new"] = is_new
        return _call("ci_index_member", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.index.ci_daily",
        description="中信行业指数日线行情 ci_daily",
    )
    def ci_daily(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """中信行业指数日线行情 ci_daily。limit默认30，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _paginate(_call("ci_daily", params, fields, token), limit, offset)
