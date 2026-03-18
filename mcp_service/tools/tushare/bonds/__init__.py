from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from mcp_service.tools.tushare._registry import error_payload, safe_tool


def register_bonds_tools(mcp: FastMCP) -> None:
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
        name="tushare.bonds.repo_daily",
        description="债券回购日行情 repo_daily",
    )
    def repo_daily(
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
                interface="repo_daily",
            )
        return _call("repo_daily", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.bonds.yc_cb",
        description="国债收益率曲线 yc_cb",
    )
    def yc_cb(
        ts_code: Optional[str] = None,
        curve_type: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        curve_term: Optional[float] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if curve_type:
            params["curve_type"] = curve_type
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if curve_term is not None:
            params["curve_term"] = curve_term
        if not params:
            return error_payload(
                "trade_date 或 start_date/end_date 或 ts_code 等至少提供一个参数",
                400,
                interface="yc_cb",
            )
        return _call("yc_cb", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.bonds.bond_blk",
        description="债券大宗交易 bond_blk",
    )
    def bond_blk(
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
                interface="bond_blk",
            )
        return _call("bond_blk", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.bonds.bond_blk_detail",
        description="债券大宗交易明细 bond_blk_detail",
    )
    def bond_blk_detail(
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
                interface="bond_blk_detail",
            )
        return _call("bond_blk_detail", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.bonds.bc_otcqt",
        description="柜台流通式债券报价 bc_otcqt",
    )
    def bc_otcqt(
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        bank: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if ts_code:
            params["ts_code"] = ts_code
        if bank:
            params["bank"] = bank
        if not params:
            return error_payload(
                "trade_date 或 start_date/end_date 或 ts_code 或 bank 至少提供一个参数",
                400,
                interface="bc_otcqt",
            )
        return _call("bc_otcqt", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.bonds.bc_bestotcqt",
        description="柜台流通式债券最优报价 bc_bestotcqt",
    )
    def bc_bestotcqt(
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if ts_code:
            params["ts_code"] = ts_code
        if not params:
            return error_payload(
                "trade_date 或 start_date/end_date 或 ts_code 至少提供一个参数",
                400,
                interface="bc_bestotcqt",
            )
        return _call("bc_bestotcqt", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.bonds.cb_basic",
        description="可转债基础信息 cb_basic",
    )
    def cb_basic(
        ts_code: Optional[str] = None,
        list_date: Optional[str] = None,
        exchange: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if list_date:
            params["list_date"] = list_date
        if exchange:
            params["exchange"] = exchange
        return _call("cb_basic", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.bonds.cb_daily",
        description="可转债行情 cb_daily",
    )
    def cb_daily(
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
                interface="cb_daily",
            )
        return _call("cb_daily", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.bonds.cb_issue",
        description="可转债发行 cb_issue",
    )
    def cb_issue(
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
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
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if not params:
            return error_payload(
                "ts_code 或 ann_date 或 start_date/end_date 至少提供一个参数",
                400,
                interface="cb_issue",
            )
        return _call("cb_issue", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.bonds.cb_call",
        description="可转债赎回信息 cb_call",
    )
    def cb_call(
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
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
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if not params:
            return error_payload(
                "ts_code 或 ann_date 或 start_date/end_date 至少提供一个参数",
                400,
                interface="cb_call",
            )
        return _call("cb_call", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.bonds.cb_rate",
        description="可转债票面利率 cb_rate",
    )
    def cb_rate(
        ts_code: str,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="cb_rate")
        return _call("cb_rate", {"ts_code": ts_code}, fields, token)

    @safe_tool(
        mcp,
        name="tushare.bonds.cb_price_chg",
        description="可转债转股价变动 cb_price_chg",
    )
    def cb_price_chg(
        ts_code: str,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload(
                "ts_code 为必填参数",
                400,
                interface="cb_price_chg",
            )
        return _call("cb_price_chg", {"ts_code": ts_code}, fields, token)

    @safe_tool(
        mcp,
        name="tushare.bonds.cb_share",
        description="可转债转股结果 cb_share",
    )
    def cb_share(
        ts_code: str,
        ann_date: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="cb_share")
        if not ann_date:
            return error_payload("ann_date 为必填参数", 400, interface="cb_share")
        params: Dict[str, Any] = {"ts_code": ts_code, "ann_date": ann_date}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return _call("cb_share", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.bonds.cb_factor_pro",
        description="可转债技术面因子(专业版) cb_factor_pro",
    )
    def cb_factor_pro(
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
                interface="cb_factor_pro",
            )
        return _call("cb_factor_pro", params, fields, token)

    @safe_tool(
        mcp,
        name="tushare.bonds.eco_cal",
        description="全球财经事件 eco_cal",
    )
    def eco_cal(
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        currency: Optional[str] = None,
        country: Optional[str] = None,
        event: Optional[str] = None,
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
        if currency:
            params["currency"] = currency
        if country:
            params["country"] = country
        if event:
            params["event"] = event
        if not params:
            return error_payload(
                "date 或 start_date/end_date 等至少提供一个参数",
                400,
                interface="eco_cal",
            )
        return _call("eco_cal", params, fields, token)
