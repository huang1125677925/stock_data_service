from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from mcp_service.tools.tushare._registry import error_payload, safe_tool


def register_stock_reference_data_tools(mcp: FastMCP) -> None:
    def _call(interface: str, params: Dict[str, Any], fields: Optional[str], token: Optional[str]) -> Dict[str, Any]:
        return call_tushare(interface=interface, params=params, fields=fields, token=token, use_query=False)

    @safe_tool(mcp, name="tushare.stock.reference.top10_holders", description="前十大股东 top10_holders")
    def top10_holders(
        ts_code: str,
        period: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="top10_holders")
        params: Dict[str, Any] = {"ts_code": ts_code}
        if period:
            params["period"] = period
        if ann_date:
            params["ann_date"] = ann_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _call("top10_holders", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.reference.top10_floatholders", description="前十大流通股东 top10_floatholders")
    def top10_floatholders(
        ts_code: str,
        period: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="top10_floatholders")
        params: Dict[str, Any] = {"ts_code": ts_code}
        if period:
            params["period"] = period
        if ann_date:
            params["ann_date"] = ann_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _call("top10_floatholders", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.reference.pledge_detail", description="股权质押明细 pledge_detail")
    def pledge_detail(
        ts_code: str,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="pledge_detail")
        return _call("pledge_detail", {"ts_code": ts_code}, fields, token)

    @safe_tool(mcp, name="tushare.stock.reference.pledge_stat", description="股权质押统计 pledge_stat")
    def pledge_stat(
        ts_code: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if end_date:
            params["end_date"] = end_date
        if not params:
            return error_payload("ts_code 或 end_date 至少提供一个参数", 400, interface="pledge_stat")
        return _call("pledge_stat", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.reference.repurchase", description="股票回购 repurchase")
    def repurchase(
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if ann_date:
            params["ann_date"] = ann_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _call("repurchase", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.reference.share_float", description="限售股解禁 share_float")
    def share_float(
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        float_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if ann_date:
            params["ann_date"] = ann_date
        if float_date:
            params["float_date"] = float_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if not params:
            return error_payload(
                "ts_code、ann_date、float_date、start_date、end_date 至少提供一个参数",
                400,
                interface="share_float",
            )
        return _call("share_float", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.reference.block_trade", description="大宗交易 block_trade")
    def block_trade(
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
        if not (ts_code or trade_date or start_date or end_date):
            return error_payload("ts_code 或 trade_date 或起止日期至少提供一个参数", 400, interface="block_trade")
        return _call("block_trade", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.reference.stk_holdernumber", description="股东人数 stk_holdernumber")
    def stk_holdernumber(
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        end_date: Optional[str] = None,
        start_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if ann_date:
            params["ann_date"] = ann_date
        if end_date:
            params["end_date"] = end_date
        if start_date:
            params["start_date"] = start_date
        if not params:
            return error_payload("至少提供一个筛选参数", 400, interface="stk_holdernumber")
        return _call("stk_holdernumber", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.reference.stk_holdertrade", description="股东增减持 stk_holdertrade")
    def stk_holdertrade(
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        trade_type: Optional[str] = None,
        holder_type: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if ann_date:
            params["ann_date"] = ann_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if trade_type:
            params["trade_type"] = trade_type
        if holder_type:
            params["holder_type"] = holder_type
        if not params:
            return error_payload("至少提供一个筛选参数", 400, interface="stk_holdertrade")
        return _call("stk_holdertrade", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.reference.stk_account", description="股票账户开户数据（停更）stk_account")
    def stk_account(
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if date:
            params["date"] = date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if not params:
            return error_payload("date 或 start_date/end_date 至少提供一个参数", 400, interface="stk_account")
        return _call("stk_account", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.reference.stk_account_old", description="股票账户开户数据（旧）stk_account_old")
    def stk_account_old(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if not params:
            return error_payload("start_date 或 end_date 至少提供一个参数", 400, interface="stk_account_old")
        return _call("stk_account_old", params, fields, token)

