from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from mcp_service.tools.tushare._registry import safe_tool


def register_macro_tools(mcp: FastMCP) -> None:
    def _call(interface: str, params: Dict[str, Any], fields: Optional[str], token: Optional[str]) -> Dict[str, Any]:
        return call_tushare(interface=interface, params=params, fields=fields, token=token, use_query=False)

    def _clean(**kwargs: Any) -> Dict[str, Any]:
        return {k: v for k, v in kwargs.items() if v is not None and v != ""}

    @safe_tool(mcp, name="tushare.macro.shibor", description="Shibor利率 shibor")
    def shibor(
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(date=date, start_date=start_date, end_date=end_date)
        return _call("shibor", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.shibor_quote", description="Shibor报价数据 shibor_quote")
    def shibor_quote(
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(date=date, start_date=start_date, end_date=end_date)
        return _call("shibor_quote", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.lpr", description="LPR贷款基础利率 lpr")
    def lpr(
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(date=date, start_date=start_date, end_date=end_date)
        return _call("lpr", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.shibor_lpr", description="LPR贷款基础利率 shibor_lpr（与文档同名接口）")
    def shibor_lpr(
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(date=date, start_date=start_date, end_date=end_date)
        return _call("shibor_lpr", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.libor", description="Libor利率 libor")
    def libor(
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        curr_type: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(date=date, start_date=start_date, end_date=end_date, curr_type=curr_type)
        return _call("libor", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.hibor", description="Hibor利率 hibor")
    def hibor(
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(date=date, start_date=start_date, end_date=end_date)
        return _call("hibor", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.cn_gdp", description="国内生产总值（GDP） cn_gdp")
    def cn_gdp(
        quarter: Optional[str] = None,
        start_quarter: Optional[str] = None,
        end_quarter: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(quarter=quarter, start_quarter=start_quarter, end_quarter=end_quarter)
        return _call("cn_gdp", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.cn_cpi", description="居民消费价格指数（CPI） cn_cpi")
    def cn_cpi(
        month: Optional[str] = None,
        start_month: Optional[str] = None,
        end_month: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(month=month, start_month=start_month, end_month=end_month)
        return _call("cn_cpi", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.cn_ppi", description="工业生产者出厂价格指数（PPI） cn_ppi")
    def cn_ppi(
        month: Optional[str] = None,
        start_month: Optional[str] = None,
        end_month: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(month=month, start_month=start_month, end_month=end_month)
        return _call("cn_ppi", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.cn_pmi", description="采购经理人指数（PMI） cn_pmi")
    def cn_pmi(
        m: Optional[str] = None,
        start_m: Optional[str] = None,
        end_m: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(m=m, start_m=start_m, end_m=end_m)
        return _call("cn_pmi", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.sf_month", description="社融增量（月度） sf_month")
    def sf_month(
        m: Optional[str] = None,
        start_m: Optional[str] = None,
        end_m: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(m=m, start_m=start_m, end_m=end_m)
        return _call("sf_month", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.cn_m", description="货币供应量（月） cn_m")
    def cn_m(
        m: Optional[str] = None,
        start_m: Optional[str] = None,
        end_m: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(m=m, start_m=start_m, end_m=end_m)
        return _call("cn_m", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.wz_index", description="温州民间借贷利率（温州指数） wz_index")
    def wz_index(
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(date=date, start_date=start_date, end_date=end_date)
        return _call("wz_index", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.gz_index", description="广州民间借贷利率 gz_index")
    def gz_index(
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(date=date, start_date=start_date, end_date=end_date)
        return _call("gz_index", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.us_tycr", description="美国国债收益率曲线利率（日频） us_tycr")
    def us_tycr(
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(date=date, start_date=start_date, end_date=end_date)
        return _call("us_tycr", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.us_tbr", description="美国短期国债利率 us_tbr")
    def us_tbr(
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(date=date, start_date=start_date, end_date=end_date)
        return _call("us_tbr", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.us_trycr", description="美国国债实际收益率曲线利率 us_trycr")
    def us_trycr(
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(date=date, start_date=start_date, end_date=end_date)
        return _call("us_trycr", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.us_tltr", description="美国国债长期利率 us_tltr")
    def us_tltr(
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(date=date, start_date=start_date, end_date=end_date)
        return _call("us_tltr", params, fields, token)

    @safe_tool(mcp, name="tushare.macro.us_trltr", description="美国国债实际长期利率平均值 us_trltr")
    def us_trltr(
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(date=date, start_date=start_date, end_date=end_date)
        return _call("us_trltr", params, fields, token)
