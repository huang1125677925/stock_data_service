from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from mcp_service.tools.tushare._registry import apply_pagination, error_payload, safe_tool


def register_stock_topic_tools(mcp: FastMCP) -> None:
    def _call(interface: str, params: Dict[str, Any], fields: Optional[str], token: Optional[str]) -> Dict[str, Any]:
        return call_tushare(interface=interface, params=params, fields=fields, token=token, use_query=False)

    def _clean(**kwargs: Any) -> Dict[str, Any]:
        return {k: v for k, v in kwargs.items() if v is not None and v != ""}

    @safe_tool(mcp, name="tushare.stock.topic.dc_daily", description="东财概念和行业指数行情 dc_daily")
    def dc_daily(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        idx_type: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取东财概念和行业指数行情数据

        Args:
            ts_code (str, optional): 板块代码，格式为 xxxxx.DC
            trade_date (str, optional): 交易日期，格式 YYYYMMDD
            start_date (str, optional): 开始日期，格式 YYYYMMDD
            end_date (str, optional): 结束日期，格式 YYYYMMDD
            idx_type (str, optional): 板块类型，可选值：概念板块、行业板块、地域板块
            limit (int): 返回记录条数上限，默认 200
            offset (int): 返回记录偏移量，默认 0
            fields (str, optional): 指定返回字段，逗号分隔
            token (str, optional): Tushare API token，优先级高于环境变量

        Returns:
            返回东财概念和行业指数行情数据，常用字段包括：
            - ts_code: 板块代码
            - trade_date: 交易日
            - close: 收盘点位
            - open: 开盘点位
            - high: 最高点位
            - low: 最低点位
            - change: 涨跌点位
            - pct_change: 涨跌幅
            - vol: 成交量（股）
            - amount: 成交额（元）
            - swing: 振幅
            - turnover_rate: 换手率

            分页元信息：total_count / count / limit / offset / has_more / next_offset / remaining
        """
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date, idx_type=idx_type)
        try:
            safe_offset = int(offset or 0)
        except Exception:
            safe_offset = 0
        safe_offset = max(safe_offset, 0)

        try:
            safe_limit = int(limit or 0)
        except Exception:
            safe_limit = 200
        if safe_limit <= 0:
            safe_limit = 200
        safe_limit = min(safe_limit, 500)

        resp = _call("dc_daily", params, fields, token)
        return apply_pagination(resp, safe_limit, safe_offset)

    @safe_tool(mcp, name="tushare.stock.topic.dc_hot", description="东方财富App热榜 dc_hot")
    def dc_hot(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        market: Optional[str] = None,
        hot_type: Optional[str] = None,
        is_new: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(trade_date=trade_date, ts_code=ts_code, market=market, hot_type=hot_type, is_new=is_new)
        return _call("dc_hot", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.topic.dc_index", description="东方财富概念板块 dc_index")
    def dc_index(
        ts_code: Optional[str] = None,
        name: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        idx_type: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取东方财富概念板块数据

        Args:
            ts_code (str, optional): 指数代码，支持多个代码，逗号分隔
            name (str, optional): 板块名称，例如：人形机器人
            trade_date (str, optional): 交易日期，格式 YYYYMMDD
            start_date (str, optional): 开始日期，格式 YYYYMMDD
            end_date (str, optional): 结束日期，格式 YYYYMMDD
            idx_type (str, optional): 板块类型，支持：行业板块、概念板块、地域板块
            limit (int): 返回记录条数上限，默认 200
            offset (int): 返回记录偏移量，默认 0
            fields (str, optional): 指定返回字段，逗号分隔
            token (str, optional): Tushare API token，优先级高于环境变量

        Returns:
            返回东方财富概念板块数据，常用字段包括：
            - ts_code: 概念代码
            - trade_date: 交易日期
            - name: 概念名称
            - leading: 领涨股票名称
            - leading_code: 领涨股票代码
            - pct_change: 涨跌幅
            - leading_pct: 领涨股票涨跌幅
            - total_mv: 总市值（万元）
            - turnover_rate: 换手率
            - up_num: 上涨家数
            - down_num: 下降家数
            - idx_type: 板块类型
            - level: 行业层级

            分页元信息：total_count / count / limit / offset / has_more / next_offset / remaining
        """
        if not idx_type:
            return error_payload("idx_type 为必填参数，支持：行业板块、概念板块、地域板块", 400, interface="dc_index")

        params: Dict[str, Any] = _clean(ts_code=ts_code, name=name, trade_date=trade_date, start_date=start_date, end_date=end_date, idx_type=idx_type)

        try:
            safe_offset = int(offset or 0)
        except Exception:
            safe_offset = 0
        safe_offset = max(safe_offset, 0)

        try:
            safe_limit = int(limit or 0)
        except Exception:
            safe_limit = 200
        if safe_limit <= 0:
            safe_limit = 200
        safe_limit = min(safe_limit, 500)

        resp = _call("dc_index", params, fields, token)
        return apply_pagination(resp, safe_limit, safe_offset)

    @safe_tool(mcp, name="tushare.stock.topic.dc_member", description="东方财富概念成分 dc_member")
    def dc_member(
        ts_code: Optional[str] = None,
        con_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取东方财富概念成分数据

        Args:
            ts_code (str, optional): 板块指数代码
            con_code (str, optional): 成分股票代码
            trade_date (str, optional): 交易日期，格式 YYYYMMDD
            limit (int): 返回记录条数上限，默认 200
            offset (int): 返回记录偏移量，默认 0
            fields (str, optional): 指定返回字段，逗号分隔
            token (str, optional): Tushare API token，优先级高于环境变量

        Returns:
            返回东方财富概念成分数据，常用字段包括：
            - trade_date: 交易日期
            - ts_code: 概念代码
            - con_code: 成分代码
            - name: 成分股名称

            分页元信息：total_count / count / limit / offset / has_more / next_offset / remaining
        """
        params: Dict[str, Any] = _clean(ts_code=ts_code, con_code=con_code, trade_date=trade_date)
        try:
            safe_offset = int(offset or 0)
        except Exception:
            safe_offset = 0
        safe_offset = max(safe_offset, 0)

        try:
            safe_limit = int(limit or 0)
        except Exception:
            safe_limit = 200
        if safe_limit <= 0:
            safe_limit = 200
        safe_limit = min(safe_limit, 500)

        resp = _call("dc_member", params, fields, token)
        return apply_pagination(resp, safe_limit, safe_offset)

    @safe_tool(mcp, name="tushare.stock.topic.hm_detail", description="游资交易每日明细 hm_detail")
    def hm_detail(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        hm_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(trade_date=trade_date, ts_code=ts_code, hm_name=hm_name, start_date=start_date, end_date=end_date)
        return _call("hm_detail", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.topic.hm_list", description="市场游资最全名录 hm_list")
    def hm_list(
        name: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(name=name)
        return _call("hm_list", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.topic.kpl_concept", description="题材数据_开盘啦 kpl_concept")
    def kpl_concept(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        name: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(trade_date=trade_date, ts_code=ts_code, name=name)
        return _call("kpl_concept", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.topic.kpl_concept_cons", description="题材成分_开盘啦 kpl_concept_cons")
    def kpl_concept_cons(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        con_code: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(trade_date=trade_date, ts_code=ts_code, con_code=con_code)
        return _call("kpl_concept_cons", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.topic.kpl_list", description="榜单数据_开盘啦 kpl_list")
    def kpl_list(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        tag: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, tag=tag, start_date=start_date, end_date=end_date)
        return _call("kpl_list", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.topic.limit_cpt_list", description="涨停最强板块统计 limit_cpt_list")
    def limit_cpt_list(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(trade_date=trade_date, ts_code=ts_code, start_date=start_date, end_date=end_date)
        return _call("limit_cpt_list", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.topic.limit_list_d", description="涨跌停和炸板数据 limit_list_d")
    def limit_list_d(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit_type: Optional[str] = None,
        exchange: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(trade_date=trade_date, ts_code=ts_code, limit_type=limit_type, exchange=exchange, start_date=start_date, end_date=end_date)
        return _call("limit_list_d", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.topic.limit_list_ths", description="同花顺涨跌停榜单 limit_list_ths")
    def limit_list_ths(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit_type: Optional[str] = None,
        market: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(trade_date=trade_date, ts_code=ts_code, limit_type=limit_type, market=market, start_date=start_date, end_date=end_date)
        return _call("limit_list_ths", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.topic.limit_step", description="涨停股票连板天梯 limit_step")
    def limit_step(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        nums: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(trade_date=trade_date, ts_code=ts_code, start_date=start_date, end_date=end_date, nums=nums)
        return _call("limit_step", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.topic.stk_auction", description="开盘竞价成交_当日 stk_auction")
    def stk_auction(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _call("stk_auction", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.topic.tdx_daily", description="通达信板块行情 tdx_daily")
    def tdx_daily(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _call("tdx_daily", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.topic.tdx_index", description="通达信板块信息 tdx_index")
    def tdx_index(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        idx_type: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, idx_type=idx_type)
        return _call("tdx_index", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.topic.tdx_member", description="通达信板块成分 tdx_member")
    def tdx_member(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date)
        return _call("tdx_member", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.topic.ths_daily", description="同花顺概念和行业指数行情 ths_daily")
    def ths_daily(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date)
        return _call("ths_daily", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.topic.ths_hot", description="同花顺App热榜数 ths_hot")
    def ths_hot(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        market: Optional[str] = None,
        is_new: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(trade_date=trade_date, ts_code=ts_code, market=market, is_new=is_new)
        return _call("ths_hot", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.topic.ths_index", description="同花顺行业概念板块 ths_index")
    def ths_index(
        ts_code: Optional[str] = None,
        exchange: Optional[str] = None,
        type: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取同花顺行业概念板块列表信息。

        Args:
            ts_code (str, optional): 指数代码，如 "885001.TI"
            exchange (str, optional): 市场类型，可选值：A-A股 / HK-港股 / US-美股
            type (str, optional): 指数类型，可选值：
                N-概念指数 / I-行业指数 / R-地域指数 /
                S-同花顺特色指数 / ST-同花顺风格指数 /
                TH-同花顺主题指数 / BB-同花顺宽基指数
            fields (str, optional): 指定返回字段，逗号分隔，默认返回全部字段
            token (str, optional): Tushare API token，优先级高于环境变量

        Returns:
            返回同花顺行业概念板块列表，字段包括：
            - ts_code (str): 板块代码
            - name (str): 板块名称
            - count (int): 成分股个数
            - exchange (str): 交易所（A/HK/US）
            - list_date (str): 上市日期，格式 YYYYMMDD
            - type (str): 指数类型（N-概念指数 / S-特色指数 等）
        """
        params: Dict[str, Any] = _clean(ts_code=ts_code, exchange=exchange, type=type)
        return _call("ths_index", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.topic.ths_member", description="同花顺行业概念成分 ths_member")
    def ths_member(
        ts_code: Optional[str] = None,
        con_code: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = _clean(ts_code=ts_code, con_code=con_code)
        return _call("ths_member", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.topic.top_inst", description="龙虎榜机构交易单 top_inst")
    def top_inst(
        trade_date: str,
        ts_code: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not trade_date:
            return error_payload("trade_date 为必填参数", 400, interface="top_inst")
        params: Dict[str, Any] = _clean(trade_date=trade_date, ts_code=ts_code)
        return _call("top_inst", params, fields, token)

    @safe_tool(mcp, name="tushare.stock.topic.top_list", description="龙虎榜每日统计单 top_list")
    def top_list(
        trade_date: str,
        ts_code: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not trade_date:
            return error_payload("trade_date 为必填参数", 400, interface="top_list")
        params: Dict[str, Any] = _clean(trade_date=trade_date, ts_code=ts_code)
        return _call("top_list", params, fields, token)
