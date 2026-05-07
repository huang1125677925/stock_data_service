from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from mcp_service.tools.tushare._registry import error_payload, safe_tool


def register_futures_tools(mcp: FastMCP) -> None:
    def _call(interface: str, params: Dict[str, Any], fields: Optional[str], token: Optional[str]) -> Dict[str, Any]:
        return call_tushare(interface=interface, params=params, fields=fields, token=token, use_query=False)

    def _clean(**kwargs: Any) -> Dict[str, Any]:
        return {k: v for k, v in kwargs.items() if v is not None and v != ""}

    @safe_tool(mcp, name="tushare.futures.trade_cal", description="期货交易日历 trade_cal")
    def trade_cal(
        exchange: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        is_open: Optional[int] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(exchange=exchange, start_date=start_date, end_date=end_date, is_open=is_open)
        return _call("trade_cal", params, fields, token)

    @safe_tool(mcp, name="tushare.futures.fut_basic", description="期货合约信息 fut_basic")
    def fut_basic(
        exchange: str,
        fut_type: Optional[str] = None,
        fut_code: Optional[str] = None,
        list_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not exchange:
            return error_payload("exchange 为必填参数", 400, interface="fut_basic")
        params: Dict[str, Any] = _clean(exchange=exchange, fut_type=fut_type, fut_code=fut_code, list_date=list_date)
        return _call("fut_basic", params, fields, token)

    @safe_tool(mcp, name="tushare.futures.fut_daily", description="期货日线行情 fut_daily")
    def fut_daily(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        exchange: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(
            trade_date=trade_date,
            ts_code=ts_code,
            exchange=exchange,
            start_date=start_date,
            end_date=end_date,
        )
        return _call("fut_daily", params, fields, token)

    @safe_tool(mcp, name="tushare.futures.fut_weekly_monthly", description="期货周/月线行情_每日更新 fut_weekly_monthly")
    def fut_weekly_monthly(
        freq: str,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not freq:
            return error_payload("freq 为必填参数", 400, interface="fut_weekly_monthly")
        params: Dict[str, Any] = _clean(
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            freq=freq,
            exchange=exchange,
        )
        return _call("fut_weekly_monthly", params, fields, token)

    @safe_tool(mcp, name="tushare.futures.fut_mapping", description="期货主力与连续合约映射 fut_mapping")
    def fut_mapping(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _call("fut_mapping", params, fields, token)

    @safe_tool(mcp, name="tushare.futures.fut_weekly_detail", description="期货主要品种交易周报 fut_weekly_detail")
    def fut_weekly_detail(
        week: Optional[str] = None,
        prd: Optional[str] = None,
        start_week: Optional[str] = None,
        end_week: Optional[str] = None,
        exchange: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(week=week, prd=prd, start_week=start_week, end_week=end_week, exchange=exchange)
        return _call("fut_weekly_detail", params, fields, token)

    @safe_tool(mcp, name="tushare.futures.fut_wsr", description="期货仓单日报 fut_wsr")
    def fut_wsr(
        trade_date: Optional[str] = None,
        symbol: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(
            trade_date=trade_date,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            exchange=exchange,
        )
        return _call("fut_wsr", params, fields, token)

    @safe_tool(mcp, name="tushare.futures.fut_settle", description="期货每日结算参数 fut_settle")
    def fut_settle(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not trade_date and not ts_code and not start_date and not end_date:
            return error_payload("trade_date 或 ts_code 或 start_date/end_date 至少提供一个参数", 400, interface="fut_settle")
        params: Dict[str, Any] = _clean(
            trade_date=trade_date,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            exchange=exchange,
        )
        return _call("fut_settle", params, fields, token)

    @safe_tool(mcp, name="tushare.futures.fut_holding", description="期货每日持仓排名 fut_holding")
    def fut_holding(
        trade_date: Optional[str] = None,
        symbol: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not trade_date and not symbol and not start_date and not end_date:
            return error_payload("trade_date 或 symbol 或 start_date/end_date 至少提供一个参数", 400, interface="fut_holding")
        params: Dict[str, Any] = _clean(
            trade_date=trade_date,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            exchange=exchange,
        )
        return _call("fut_holding", params, fields, token)

    @safe_tool(mcp, name="tushare.futures.ft_limit", description="期货合约涨跌停价格 ft_limit")
    def ft_limit(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        cont: Optional[str] = None,
        exchange: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            cont=cont,
            exchange=exchange,
        )
        return _call("ft_limit", params, fields, token)

    @safe_tool(mcp, name="tushare.futures.nanhua_index_daily", description="南华期货指数行情 index_daily")
    def nanhua_index_daily(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _call("index_daily", params, fields, token)
