from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from mcp_service.tools.tushare._registry import error_payload, safe_tool


def register_stock_finance_tools(mcp: FastMCP) -> None:
    def _call(interface: str, params: Dict[str, Any], fields: Optional[str], token: Optional[str]) -> Dict[str, Any]:
        return call_tushare(interface=interface, params=params, fields=fields, token=token, use_query=False)

    def _clean(**kwargs: Any) -> Dict[str, Any]:
        return {k: v for k, v in kwargs.items() if v is not None and v != ""}

    @safe_tool(mcp, name="tushare.stock.finance.balancesheet", description="资产负债表 balancesheet")
    def balancesheet(
        ts_code: str,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        report_type: Optional[str] = None,
        comp_type: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="balancesheet")
        params: Dict[str, Any] = _clean(ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date, period=period, report_type=report_type, comp_type=comp_type)
        return _call("balancesheet", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.finance.cashflow", description="现金流量表 cashflow")
    def cashflow(
        ts_code: str,
        ann_date: Optional[str] = None,
        f_ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        report_type: Optional[str] = None,
        comp_type: Optional[str] = None,
        is_calc: Optional[int] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="cashflow")
        params: Dict[str, Any] = _clean(
            ts_code=ts_code,
            ann_date=ann_date,
            f_ann_date=f_ann_date,
            start_date=start_date,
            end_date=end_date,
            period=period,
            report_type=report_type,
            comp_type=comp_type,
            is_calc=is_calc,
        )
        return _call("cashflow", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.finance.disclosure_date", description="财报披露日期表 disclosure_date")
    def disclosure_date(
        ts_code: Optional[str] = None,
        end_date: Optional[str] = None,
        pre_date: Optional[str] = None,
        ann_date: Optional[str] = None,
        actual_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, end_date=end_date, pre_date=pre_date, ann_date=ann_date, actual_date=actual_date)
        return _call("disclosure_date", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.finance.dividend", description="分红送股数据 dividend")
    def dividend(
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        record_date: Optional[str] = None,
        ex_date: Optional[str] = None,
        imp_ann_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, ann_date=ann_date, record_date=record_date, ex_date=ex_date, imp_ann_date=imp_ann_date)
        return _call("dividend", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.finance.express", description="业绩快报 express")
    def express(
        ts_code: str,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="express")
        params: Dict[str, Any] = _clean(ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date, period=period)
        return _call("express", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.finance.fina_audit", description="财务审计意见 fina_audit")
    def fina_audit(
        ts_code: str,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="fina_audit")
        params: Dict[str, Any] = _clean(ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date, period=period)
        return _call("fina_audit", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.finance.fina_indicator", description="财务指标数据 fina_indicator")
    def fina_indicator(
        ts_code: str,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="fina_indicator")
        params: Dict[str, Any] = _clean(ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date, period=period)
        return _call("fina_indicator", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.finance.fina_mainbz", description="主营业务构成 fina_mainbz")
    def fina_mainbz(
        ts_code: str,
        period: Optional[str] = None,
        type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="fina_mainbz")
        params: Dict[str, Any] = _clean(ts_code=ts_code, period=period, type=type, start_date=start_date, end_date=end_date)
        return _call("fina_mainbz", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.finance.forecast", description="业绩预告 forecast")
    def forecast(
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        type: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code and not ann_date:
            return error_payload("ts_code 或 ann_date 至少提供一个参数", 400, interface="forecast")
        params: Dict[str, Any] = _clean(ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date, period=period, type=type)
        return _call("forecast", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.finance.income", description="利润表 income")
    def income(
        ts_code: str,
        ann_date: Optional[str] = None,
        f_ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        report_type: Optional[str] = None,
        comp_type: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="income")
        params: Dict[str, Any] = _clean(
            ts_code=ts_code,
            ann_date=ann_date,
            f_ann_date=f_ann_date,
            start_date=start_date,
            end_date=end_date,
            period=period,
            report_type=report_type,
            comp_type=comp_type,
        )
        return _call("income", params, fields, token)
