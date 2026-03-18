from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from mcp_service.tools.tushare._registry import error_payload, safe_tool


def register_stock_basic_tools(mcp: FastMCP) -> None:
    def _call(interface: str, params: Dict[str, Any], fields: Optional[str], token: Optional[str]) -> Dict[str, Any]:
        return call_tushare(interface=interface, params=params, fields=fields, token=token, use_query=False)

    def _clean(**kwargs: Any) -> Dict[str, Any]:
        return {k: v for k, v in kwargs.items() if v is not None and v != ""}

    @safe_tool(mcp, name="tushare.stock.basic.bak_basic", description="股票历史列表 bak_basic")
    def bak_basic(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(trade_date=trade_date, ts_code=ts_code)
        return _call("bak_basic", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.basic.bse_mapping", description="北交所新旧代码对照 bse_mapping")
    def bse_mapping(
        o_code: Optional[str] = None,
        n_code: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(o_code=o_code, n_code=n_code)
        return _call("bse_mapping", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.basic.namechange", description="股票曾用名 namechange")
    def namechange(
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, start_date=start_date, end_date=end_date)
        return _call("namechange", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.basic.new_share", description="IPO新股上市 new_share")
    def new_share(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(start_date=start_date, end_date=end_date)
        return _call("new_share", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.basic.stk_managers", description="上市公司管理层 stk_managers")
    def stk_managers(
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date)
        return _call("stk_managers", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.basic.stk_premarket", description="每日股本_盘前 stk_premarket")
    def stk_premarket(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _call("stk_premarket", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.basic.stk_rewards", description="管理层薪酬和持股 stk_rewards")
    def stk_rewards(
        ts_code: str,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="stk_rewards")
        params: Dict[str, Any] = _clean(ts_code=ts_code, end_date=end_date)
        return _call("stk_rewards", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.basic.stock_basic", description="股票列表 stock_basic")
    def stock_basic(
        ts_code: Optional[str] = None,
        name: Optional[str] = None,
        market: Optional[str] = None,
        list_status: Optional[str] = None,
        exchange: Optional[str] = None,
        is_hs: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, name=name, market=market, list_status=list_status, exchange=exchange, is_hs=is_hs)
        return _call("stock_basic", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.basic.stock_company", description="上市公司基本信息 stock_company")
    def stock_company(
        ts_code: Optional[str] = None,
        exchange: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, exchange=exchange)
        return _call("stock_company", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.basic.stock_hsgt", description="沪深港通股票列表 stock_hsgt")
    def stock_hsgt(
        type: str,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not type:
            return error_payload("type 为必填参数", 400, interface="stock_hsgt")
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, type=type, start_date=start_date, end_date=end_date)
        return _call("stock_hsgt", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.basic.stock_st", description="ST股票列表 stock_st")
    def stock_st(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _call("stock_st", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.basic.trade_cal", description="交易日历 trade_cal")
    def trade_cal(
        exchange: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        is_open: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(exchange=exchange, start_date=start_date, end_date=end_date, is_open=is_open)
        return _call("trade_cal", params, fields, token)
