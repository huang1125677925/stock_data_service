from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from mcp_service.tools.tushare._registry import apply_pagination, error_payload, safe_tool


def register_stock_moneyflow_tools(mcp: FastMCP) -> None:
    def _call(interface: str, params: Dict[str, Any], fields: Optional[str], token: Optional[str]) -> Dict[str, Any]:
        return call_tushare(interface=interface, params=params, fields=fields, token=token, use_query=False)

    def _clean(**kwargs: Any) -> Dict[str, Any]:
        return {k: v for k, v in kwargs.items() if v is not None and v != ""}

    def _paginate(resp: Dict[str, Any], limit: int, offset: int) -> Dict[str, Any]:
        safe_limit = max(1, min(int(limit or 30), 500))
        safe_offset = max(0, int(offset or 0))
        return apply_pagination(resp, safe_limit, safe_offset)

    @safe_tool(mcp, name="tushare.stock.moneyflow.moneyflow", description="个股资金流向 moneyflow")
    def moneyflow(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """个股资金流向 moneyflow。limit默认30，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _paginate(_call("moneyflow", params, fields, token), limit, offset)

    @safe_tool(mcp, name="tushare.stock.moneyflow.moneyflow_cnt_ths", description="板块资金流向_THS moneyflow_cnt_ths")
    def moneyflow_cnt_ths(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """板块资金流向_THS moneyflow_cnt_ths。limit默认30，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _paginate(_call("moneyflow_cnt_ths", params, fields, token), limit, offset)

    @safe_tool(mcp, name="tushare.stock.moneyflow.moneyflow_dc", description="个股资金流向_DC moneyflow_dc")
    def moneyflow_dc(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """个股资金流向_DC moneyflow_dc。limit默认30，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _paginate(_call("moneyflow_dc", params, fields, token), limit, offset)

    @safe_tool(mcp, name="tushare.stock.moneyflow.moneyflow_hsgt", description="沪深港通资金流向 moneyflow_hsgt")
    def moneyflow_hsgt(
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 60,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """沪深港通资金流向 moneyflow_hsgt。limit默认60，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        if not trade_date and not start_date:
            return error_payload("trade_date 或 start_date 至少提供一个参数", 400, interface="moneyflow_hsgt")
        params: Dict[str, Any] = _clean(trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _paginate(_call("moneyflow_hsgt", params, fields, token), limit, offset)

    @safe_tool(mcp, name="tushare.stock.moneyflow.moneyflow_ind_dc", description="板块资金流向_DC moneyflow_ind_dc")
    def moneyflow_ind_dc(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """板块资金流向_DC moneyflow_ind_dc。limit默认30，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date, content_type=content_type)
        return _paginate(_call("moneyflow_ind_dc", params, fields, token), limit, offset)

    @safe_tool(mcp, name="tushare.stock.moneyflow.moneyflow_ind_ths", description="行业资金流向_THS moneyflow_ind_ths")
    def moneyflow_ind_ths(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """行业资金流向_THS moneyflow_ind_ths。limit默认30，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _paginate(_call("moneyflow_ind_ths", params, fields, token), limit, offset)

    @safe_tool(mcp, name="tushare.stock.moneyflow.moneyflow_mkt_dc", description="大盘资金流向_DC moneyflow_mkt_dc")
    def moneyflow_mkt_dc(
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 60,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """大盘资金流向_DC moneyflow_mkt_dc。limit默认60，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = _clean(trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _paginate(_call("moneyflow_mkt_dc", params, fields, token), limit, offset)

    @safe_tool(mcp, name="tushare.stock.moneyflow.moneyflow_ths", description="个股资金流向_THS moneyflow_ths")
    def moneyflow_ths(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """个股资金流向_THS moneyflow_ths。limit默认30，最大500；offset用于翻页。额外元信息：total_count/count/limit/offset/has_more"""
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _paginate(_call("moneyflow_ths", params, fields, token), limit, offset)
