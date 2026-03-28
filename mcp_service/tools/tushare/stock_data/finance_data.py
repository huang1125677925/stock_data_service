from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from mcp_service.tools.tushare._registry import apply_pagination, error_payload, safe_tool


def register_stock_finance_tools(mcp: FastMCP) -> None:
    def _call(interface: str, params: Dict[str, Any], fields: Optional[str], token: Optional[str]) -> Dict[str, Any]:
        return call_tushare(interface=interface, params=params, fields=fields, token=token, use_query=False)

    def _clean(**kwargs: Any) -> Dict[str, Any]:
        return {k: v for k, v in kwargs.items() if v is not None and v != ""}

    def _paginate(resp: Dict[str, Any], limit: int, offset: int) -> Dict[str, Any]:
        safe_limit = max(1, min(int(limit or 10), 100))
        safe_offset = max(0, int(offset or 0))
        return apply_pagination(resp, safe_limit, safe_offset)

    # 资产负债表常用核心字段（全表 100+ 列）
    _BS_DEFAULT_FIELDS = (
        "ts_code,ann_date,f_ann_date,end_date,report_type,"
        "total_assets,total_liab,total_equity,total_cur_assets,total_cur_liab,"
        "money_cap,notes_receiv,accounts_receiv,inventories,fix_assets,"
        "lt_borr,st_borr,bonds_payable"
    )

    # 利润表常用核心字段
    _INCOME_DEFAULT_FIELDS = (
        "ts_code,ann_date,f_ann_date,end_date,report_type,"
        "total_revenue,revenue,total_cogs,grossprofit,"
        "operate_profit,ebit,ebitda,"
        "n_income,n_income_attr_p,minority_gain,"
        "basic_eps,diluted_eps"
    )

    # 现金流量表常用核心字段
    _CF_DEFAULT_FIELDS = (
        "ts_code,ann_date,f_ann_date,end_date,report_type,"
        "n_cashflow_act,n_cashflow_inv_act,n_cash_flows_fnc_act,"
        "n_incr_cash_cash_equ,c_cash_equ_end_period,"
        "free_cashflow"
    )

    # 财务指标常用核心字段（同 stock_data_tools.py 保持一致）
    _FINA_DEFAULT_FIELDS = (
        "ts_code,ann_date,end_date,"
        "eps,bps,ocfps,"
        "roe,roe_waa,roa,roic,"
        "netprofit_margin,grossprofit_margin,"
        "current_ratio,quick_ratio,"
        "debt_to_assets,"
        "tr_yoy,or_yoy,netprofit_yoy,dt_netprofit_yoy,"
        "ebitda,fcff,fcfe,"
        "basic_eps_yoy,assets_yoy,eqt_yoy"
    )

    @safe_tool(mcp, name="tushare.stock.finance.balancesheet", description="资产负债表 balancesheet")
    def balancesheet(
        ts_code: str,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        report_type: Optional[str] = None,
        comp_type: Optional[str] = None,
        limit: int = 8,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        资产负债表 balancesheet

        Args:
            ts_code (str): 股票代码（必填）
            ann_date / start_date / end_date / period / report_type / comp_type: 筛选条件
            limit (int): 返回记录条数，默认8，最大100（资产负债表字段多，请控制数量）
            offset (int): 偏移量，默认0
            fields (str): 返回字段（逗号分隔），默认只返回核心字段；传 "all" 返回全部字段

        默认返回核心字段：total_assets / total_liab / total_equity / money_cap 等
        额外元信息：total_count / count / limit / offset / has_more
        """
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="balancesheet")
        params: Dict[str, Any] = _clean(ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date, period=period, report_type=report_type, comp_type=comp_type)
        effective_fields = None if fields == "all" else (fields or _BS_DEFAULT_FIELDS)
        resp = _call("balancesheet", params, effective_fields, token)
        return _paginate(resp, limit, offset)

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
        limit: int = 8,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        现金流量表 cashflow

        Args:
            ts_code (str): 股票代码（必填）
            limit (int): 返回记录条数，默认8，最大100
            offset (int): 偏移量，默认0
            fields (str): 返回字段；默认只返回核心CF字段；传 "all" 返回全部

        默认返回核心字段：n_cashflow_act / n_cashflow_inv_act / n_cash_flows_fnc_act 等
        额外元信息：total_count / count / limit / offset / has_more
        """
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
        effective_fields = None if fields == "all" else (fields or _CF_DEFAULT_FIELDS)
        resp = _call("cashflow", params, effective_fields, token)
        return _paginate(resp, limit, offset)

    @safe_tool(mcp, name="tushare.stock.finance.disclosure_date", description="财报披露日期表 disclosure_date")
    def disclosure_date(
        ts_code: Optional[str] = None,
        end_date: Optional[str] = None,
        pre_date: Optional[str] = None,
        ann_date: Optional[str] = None,
        actual_date: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        财报披露日期表 disclosure_date

        Args:
            limit (int): 返回记录条数，默认20，最大200
            offset (int): 偏移量，默认0

        额外元信息：total_count / count / limit / offset / has_more
        """
        params: Dict[str, Any] = _clean(ts_code=ts_code, end_date=end_date, pre_date=pre_date, ann_date=ann_date, actual_date=actual_date)
        resp = _call("disclosure_date", params, fields, token)
        return _paginate(resp, limit, offset)

    @safe_tool(mcp, name="tushare.stock.finance.dividend", description="分红送股数据 dividend")
    def dividend(
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        record_date: Optional[str] = None,
        ex_date: Optional[str] = None,
        imp_ann_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        分红送股数据 dividend

        Args:
            limit (int): 返回记录条数，默认30，最大200
            offset (int): 偏移量，默认0

        额外元信息：total_count / count / limit / offset / has_more
        """
        params: Dict[str, Any] = _clean(ts_code=ts_code, ann_date=ann_date, record_date=record_date, ex_date=ex_date, imp_ann_date=imp_ann_date)
        resp = _call("dividend", params, fields, token)
        return _paginate(resp, limit, offset)

    @safe_tool(mcp, name="tushare.stock.finance.express", description="业绩快报 express")
    def express(
        ts_code: str,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        业绩快报 express

        Args:
            ts_code (str): 股票代码（必填）
            limit (int): 返回记录条数，默认10，最大100
            offset (int): 偏移量，默认0

        额外元信息：total_count / count / limit / offset / has_more
        """
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="express")
        params: Dict[str, Any] = _clean(ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date, period=period)
        resp = _call("express", params, fields, token)
        return _paginate(resp, limit, offset)

    @safe_tool(mcp, name="tushare.stock.finance.fina_audit", description="财务审计意见 fina_audit")
    def fina_audit(
        ts_code: str,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        财务审计意见 fina_audit

        Args:
            ts_code (str): 股票代码（必填）
            limit (int): 返回记录条数，默认10，最大100
            offset (int): 偏移量，默认0

        额外元信息：total_count / count / limit / offset / has_more
        """
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="fina_audit")
        params: Dict[str, Any] = _clean(ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date, period=period)
        resp = _call("fina_audit", params, fields, token)
        return _paginate(resp, limit, offset)

    @safe_tool(mcp, name="tushare.stock.finance.fina_indicator", description="财务指标数据 fina_indicator")
    def fina_indicator(
        ts_code: str,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        limit: int = 8,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        财务指标数据 fina_indicator

        Args:
            ts_code (str): 股票代码（必填）
            limit (int): 返回记录条数，默认8，最大50（字段极多，请控制数量）
            offset (int): 偏移量，默认0
            fields (str): 返回字段；默认只返回核心财务指标；传 "all" 返回全部字段

        默认返回核心字段：eps / roe / roa / netprofit_margin / grossprofit_margin 等
        额外元信息：total_count / count / limit / offset / has_more
        """
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="fina_indicator")
        params: Dict[str, Any] = _clean(ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date, period=period)
        effective_fields = None if fields == "all" else (fields or _FINA_DEFAULT_FIELDS)
        resp = _call("fina_indicator", params, effective_fields, token)
        return _paginate(resp, limit, offset)

    @safe_tool(mcp, name="tushare.stock.finance.fina_mainbz", description="主营业务构成 fina_mainbz")
    def fina_mainbz(
        ts_code: str,
        period: Optional[str] = None,
        type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        主营业务构成 fina_mainbz

        Args:
            ts_code (str): 股票代码（必填）
            limit (int): 返回记录条数，默认20，最大200
            offset (int): 偏移量，默认0

        额外元信息：total_count / count / limit / offset / has_more
        """
        if not ts_code:
            return error_payload("ts_code 为必填参数", 400, interface="fina_mainbz")
        params: Dict[str, Any] = _clean(ts_code=ts_code, period=period, type=type, start_date=start_date, end_date=end_date)
        resp = _call("fina_mainbz", params, fields, token)
        return _paginate(resp, limit, offset)

    @safe_tool(mcp, name="tushare.stock.finance.forecast", description="业绩预告 forecast")
    def forecast(
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        业绩预告 forecast

        Args:
            ts_code 或 ann_date 至少提供一个
            limit (int): 返回记录条数，默认20，最大200
            offset (int): 偏移量，默认0

        额外元信息：total_count / count / limit / offset / has_more
        """
        if not ts_code and not ann_date:
            return error_payload("ts_code 或 ann_date 至少提供一个参数", 400, interface="forecast")
        params: Dict[str, Any] = _clean(ts_code=ts_code, ann_date=ann_date, start_date=start_date, end_date=end_date, period=period, type=type)
        resp = _call("forecast", params, fields, token)
        return _paginate(resp, limit, offset)

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
        limit: int = 8,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        利润表 income

        Args:
            ts_code (str): 股票代码（必填）
            limit (int): 返回记录条数，默认8，最大100（字段较多，请控制数量）
            offset (int): 偏移量，默认0
            fields (str): 返回字段；默认只返回核心损益字段；传 "all" 返回全部字段

        默认返回核心字段：total_revenue / revenue / grossprofit / operate_profit /
            n_income / n_income_attr_p / basic_eps 等
        额外元信息：total_count / count / limit / offset / has_more
        """
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
        effective_fields = None if fields == "all" else (fields or _INCOME_DEFAULT_FIELDS)
        resp = _call("income", params, effective_fields, token)
        return _paginate(resp, limit, offset)
