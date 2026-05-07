from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from mcp_service.tools.tushare._registry import error_payload, safe_tool


def register_stock_special_tools(mcp: FastMCP) -> None:
    def _call(interface: str, params: Dict[str, Any], fields: Optional[str], token: Optional[str]) -> Dict[str, Any]:
        return call_tushare(interface=interface, params=params, fields=fields, token=token, use_query=False)

    def _clean(**kwargs: Any) -> Dict[str, Any]:
        return {k: v for k, v in kwargs.items() if v is not None and v != ""}

    @safe_tool(mcp, name="tushare.stock.special.broker_recommend", description="券商月度金股 broker_recommend")
    def broker_recommend(
        month: str,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not month:
            return error_payload("month 为必填参数", 400, interface="broker_recommend")
        params: Dict[str, Any] = _clean(month=month)
        return _call("broker_recommend", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.special.ccass_hold", description="中央结算系统持股统计 ccass_hold")
    def ccass_hold(
        ts_code: Optional[str] = None,
        hk_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, hk_code=hk_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _call("ccass_hold", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.special.ccass_hold_detail", description="中央结算系统持股明细 ccass_hold_detail")
    def ccass_hold_detail(
        ts_code: Optional[str] = None,
        hk_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, hk_code=hk_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _call("ccass_hold_detail", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.special.cyq_chips", description="每日筹码分布 cyq_chips")
    def cyq_chips(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _call("cyq_chips", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.special.cyq_perf", description="每日筹码及胜率 cyq_perf")
    def cyq_perf(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _call("cyq_perf", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.special.hk_hold", description="沪深股通持股明细 hk_hold")
    def hk_hold(
        code: Optional[str] = None,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(code=code, ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date, exchange=exchange)
        return _call("hk_hold", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.special.report_rc", description="券商盈利预测数据 report_rc")
    def report_rc(
        ts_code: Optional[str] = None,
        report_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, report_date=report_date, start_date=start_date, end_date=end_date)
        return _call("report_rc", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.special.stk_ah_comparison", description="AH股比价 stk_ah_comparison")
    def stk_ah_comparison(
        hk_code: Optional[str] = None,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(hk_code=hk_code, ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _call("stk_ah_comparison", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.special.stk_auction_c", description="股票收盘集合竞价数据 stk_auction_c")
    def stk_auction_c(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _call("stk_auction_c", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.special.stk_auction_o", description="股票开盘集合竞价数据 stk_auction_o")
    def stk_auction_o(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _call("stk_auction_o", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.special.stk_factor", description="股票技术面因子 stk_factor")
    def stk_factor(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _call("stk_factor", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.special.stk_factor_pro", description="股票技术面因子_专业版 stk_factor_pro")
    def stk_factor_pro(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _call("stk_factor_pro", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.special.stk_nineturn", description="神奇九转指标 stk_nineturn")
    def stk_nineturn(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        freq: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, freq=freq, start_date=start_date, end_date=end_date)
        return _call("stk_nineturn", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.special.stk_surv", description="机构调研数据 stk_surv")
    def stk_surv(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _call("stk_surv", params, fields, token)
