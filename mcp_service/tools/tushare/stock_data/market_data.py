from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare, call_tushare_pro_bar
from mcp_service.tools.tushare._registry import apply_pagination, error_payload, safe_tool


def register_stock_market_tools(mcp: FastMCP) -> None:
    def _call(interface: str, params: Dict[str, Any], fields: Optional[str], token: Optional[str]) -> Dict[str, Any]:
        return call_tushare(interface=interface, params=params, fields=fields, token=token, use_query=False)

    def _clean(**kwargs: Any) -> Dict[str, Any]:
        return {k: v for k, v in kwargs.items() if v is not None and v != ""}

    def _paginate(resp: Dict[str, Any], limit: int, offset: int, max_limit: int = 500) -> Dict[str, Any]:
        safe_limit = max(1, min(int(limit or 30), max_limit))
        safe_offset = max(0, int(offset or 0))
        return apply_pagination(resp, safe_limit, safe_offset)

    @safe_tool(mcp, name="tushare.stock.market.adj_factor", description="复权因子 adj_factor")
    def adj_factor(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 60,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """复权因子 adj_factor。limit默认60，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _paginate(_call("adj_factor", params, fields, token), limit, offset)

    @safe_tool(mcp, name="tushare.stock.market.bak_daily", description="备用行情 bak_daily")
    def bak_daily(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        offset: Optional[str] = None,
        limit: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date, offset=offset, limit=limit)
        return _call("bak_daily", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.market.daily", description="历史日线 daily")
    def daily(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """历史日线 daily。limit默认30，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _paginate(_call("daily", params, fields, token), limit, offset)

    @safe_tool(mcp, name="tushare.stock.market.daily_basic", description="每日指标 daily_basic")
    def daily_basic(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """每日指标 daily_basic。limit默认30，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        if not ts_code and not trade_date:
            return error_payload("ts_code 或 trade_date 至少提供一个参数", 400, interface="daily_basic")
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _paginate(_call("daily_basic", params, fields, token), limit, offset)

    @safe_tool(mcp, name="tushare.stock.market.ggt_daily", description="港股通每日成交统计 ggt_daily")
    def ggt_daily(
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _call("ggt_daily", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.market.ggt_monthly", description="港股通每月成交统计 ggt_monthly")
    def ggt_monthly(
        month: Optional[str] = None,
        start_month: Optional[str] = None,
        end_month: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(month=month, start_month=start_month, end_month=end_month)
        return _call("ggt_monthly", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.market.ggt_top10", description="港股通十大成交股 ggt_top10")
    def ggt_top10(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        market_type: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code and not trade_date:
            return error_payload("ts_code 或 trade_date 至少提供一个参数", 400, interface="ggt_top10")
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date, market_type=market_type)
        return _call("ggt_top10", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.market.hsgt_top10", description="沪深股通十大成交股 hsgt_top10")
    def hsgt_top10(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        market_type: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code and not trade_date:
            return error_payload("ts_code 或 trade_date 至少提供一个参数", 400, interface="hsgt_top10")
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date, market_type=market_type)
        return _call("hsgt_top10", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.market.monthly", description="月线行情 monthly")
    def monthly(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 24,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """月线行情 monthly。limit默认24（2年），最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _paginate(_call("monthly", params, fields, token), limit, offset)

    @safe_tool(mcp, name="tushare.stock.market.realtime_list", description="实时排名_爬虫 realtime_list")
    def realtime_list(
        src: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(src=src)
        return _call("realtime_list", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.market.realtime_quote", description="实时Tick_爬虫 realtime_quote")
    def realtime_quote(
        ts_code: Optional[str] = None,
        src: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, src=src)
        return _call("realtime_quote", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.market.realtime_tick", description="实时成交_爬虫 realtime_tick")
    def realtime_tick(
        ts_code: Optional[str] = None,
        src: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, src=src)
        return _call("realtime_tick", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.market.rt_k", description="实时日线 rt_k")
    def rt_k(
        ts_code: str,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="rt_k")
        params: Dict[str, Any] = _clean(ts_code=ts_code)
        return _call("rt_k", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.market.stk_limit", description="每日涨跌停价格 stk_limit")
    def stk_limit(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """每日涨跌停价格 stk_limit。limit默认50，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _paginate(_call("stk_limit", params, fields, token), limit, offset)

    @safe_tool(mcp, name="tushare.stock.market.stk_week_month_adj", description="周_月线复权行情_每日更新 stk_week_month_adj")
    def stk_week_month_adj(
        freq: str,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """周/月线复权行情 stk_week_month_adj。limit默认30，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        if not freq:
            return error_payload("freq 为必填参数", 400, interface="stk_week_month_adj")
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date, freq=freq)
        return _paginate(_call("stk_week_month_adj", params, fields, token), limit, offset)

    @safe_tool(mcp, name="tushare.stock.market.stk_weekly_monthly", description="周_月线行情_每日更新 stk_weekly_monthly")
    def stk_weekly_monthly(
        freq: str,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """周/月线行情 stk_weekly_monthly。limit默认30，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        if not freq:
            return error_payload("freq 为必填参数", 400, interface="stk_weekly_monthly")
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date, freq=freq)
        return _paginate(_call("stk_weekly_monthly", params, fields, token), limit, offset)

    @safe_tool(mcp, name="tushare.stock.market.suspend_d", description="每日停复牌信息 suspend_d")
    def suspend_d(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        suspend_type: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date, suspend_type=suspend_type)
        return _call("suspend_d", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.market.weekly", description="周线行情 weekly")
    def weekly(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """周线行情 weekly。limit默认30，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _paginate(_call("weekly", params, fields, token), limit, offset)

    @safe_tool(mcp, name="tushare.stock.market.pro_bar", description="通用行情 ts.pro_bar（需本地 SDK）")
    def pro_bar(
        ts_code: str,
        asset: str,
        freq: str,
        adj: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjfactor: Optional[bool] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="pro_bar")
        if not asset:
            return error_payload("asset 为必填参数（E/I/C/FT/FD/O/CB）", 400, interface="pro_bar")
        if not freq:
            return error_payload("freq 为必填参数（如 D、W）", 400, interface="pro_bar")
        params: Dict[str, Any] = {
            "ts_code": ts_code,
            "asset": asset,
            "freq": freq,
        }
        if adj is not None:
            params["adj"] = adj
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if adjfactor is not None:
            params["adjfactor"] = adjfactor
        return call_tushare_pro_bar(params=params, token=token, fields=fields)
