from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from mcp_service.tools.tushare._registry import error_payload, safe_tool


def register_public_fund_tools(mcp: FastMCP) -> None:
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
        name="tushare.public_fund.fund_basic",
        description="公募基金列表 fund_basic",
    )
    def fund_basic(
        ts_code: Optional[str] = None,
        market: str = "E",
        status: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if market:
            params["market"] = market
        if status:
            params["status"] = status
        return _call("fund_basic", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.public_fund.fund_nav",
        description="公募基金净值 fund_nav",
    )
    def fund_nav(
        ts_code: Optional[str] = None,
        nav_date: Optional[str] = None,
        market: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not (ts_code or nav_date):
            return error_payload(
                "ts_code 或 nav_date 至少提供一个参数",
                400,
                interface="fund_nav",
            )
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if nav_date:
            params["nav_date"] = nav_date
        if market:
            params["market"] = market
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _call("fund_nav", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.public_fund.fund_portfolio",
        description="公募基金持仓 fund_portfolio",
    )
    def fund_portfolio(
        ts_code: Optional[str] = None,
        symbol: Optional[str] = None,
        ann_date: Optional[str] = None,
        period: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if symbol:
            params["symbol"] = symbol
        if ann_date:
            params["ann_date"] = ann_date
        if period:
            params["period"] = period
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if not params:
            return error_payload(
                "ts_code 或 symbol 或 ann_date 或 period 或 start_date/end_date 至少提供一个参数",
                400,
                interface="fund_portfolio",
            )
        return _call("fund_portfolio", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.public_fund.fund_company",
        description="公募基金公司 fund_company",
    )
    def fund_company(
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        return _call("fund_company", {}, fields, token)

    @safe_tool(
        mcp,
        name="tushare.public_fund.fund_manager",
        description="基金经理 fund_manager",
    )
    def fund_manager(
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        name: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if ann_date:
            params["ann_date"] = ann_date
        if name:
            params["name"] = name
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = limit
        return _call("fund_manager", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.public_fund.fund_div",
        description="公募基金分红 fund_div",
    )
    def fund_div(
        ann_date: Optional[str] = None,
        ex_date: Optional[str] = None,
        pay_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if ann_date:
            params["ann_date"] = ann_date
        if ex_date:
            params["ex_date"] = ex_date
        if pay_date:
            params["pay_date"] = pay_date
        if ts_code:
            params["ts_code"] = ts_code
        if not params:
            return error_payload(
                "ann_date 或 ex_date 或 pay_date 或 ts_code 至少提供一个参数",
                400,
                interface="fund_div",
            )
        return _call("fund_div", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.public_fund.fund_share",
        description="基金规模 fund_share",
    )
    def fund_share(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        market: Optional[str] = None,
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
        if market:
            params["market"] = market
        if not params:
            return error_payload(
                "ts_code 或 trade_date 或 start_date/end_date 或 market 至少提供一个参数",
                400,
                interface="fund_share",
            )
        return _call("fund_share", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.public_fund.fund_factor_pro",
        description="场内基金技术因子(专业版) fund_factor_pro",
    )
    def fund_factor_pro(
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
        if not params:
            return error_payload(
                "ts_code 或 trade_date 或 start_date/end_date 至少提供一个参数",
                400,
                interface="fund_factor_pro",
            )
        return _call("fund_factor_pro", params, fields, token)
