"""
股票数据工具模块
提供股票基础数据、行情数据、财务数据、参考数据等接口
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from common.tushare_proxy import call_tushare
from mcp_service.tools.tushare._registry import error_payload


def register_stock_data_tools(mcp: FastMCP) -> None:
    """注册股票数据相关的工具"""

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

    @mcp.tool()
    def get_stock_basic(
        list_status: str = "L",
        exchange: Optional[str] = None,
        ts_code: Optional[str] = None,
        name: Optional[str] = None,
        market: Optional[str] = None,
        is_hs: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取股票基础信息列表

        Args:
            list_status (str): 上市状态 L上市 D退市 P暂停上市，默认是L
            exchange (str, optional): 交易所 SSE上交所 SZSE深交所 BSE北交所
            ts_code (str, optional): TS股票代码
            name (str, optional): 名称
            market (str, optional): 市场类别 主板/创业板/科创板/CDR/北交所
            is_hs (str, optional): 是否沪深港通标的，N否 H沪股通 S深股通
            limit (int): 返回记录条数上限，默认 200（仅影响返回内容，不影响上游接口拉取）
            offset (int): 返回记录偏移量，用于分页，默认 0
            fields (str, optional): 返回字段列表（逗号分隔）
            token (str, optional): Tushare API token（覆盖环境变量）

        Returns:
            包含股票基础信息的数据，字段包括：
            - ts_code: TS股票代码
            - symbol: 股票代码
            - name: 股票名称
            - area: 地域
            - industry: 所属行业
            - fullname: 股票全称
            - enname: 英文全称
            - cnspell: 拼音缩写
            - market: 市场类型
            - exchange: 交易所代码
            - curr_type: 交易货币
            - list_status: 上市状态
            - list_date: 上市日期
            - delist_date: 退市日期
            - is_hs: 是否沪深港通标的

            额外返回元信息字段：
            - total_count: 上游接口返回的总记录数
            - count: 当前返回 records 的记录数
            - limit: 本次返回上限
            - offset: 本次返回偏移
            - truncated: 是否发生截断
        """
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if name:
            params["name"] = name
        if market:
            params["market"] = market
        if list_status:
            params["list_status"] = list_status
        if exchange:
            params["exchange"] = exchange
        if is_hs:
            params["is_hs"] = is_hs

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
        safe_limit = min(safe_limit, 10)

        default_fields = (
            "ts_code,symbol,name,area,industry,market,exchange,"
            "list_status,list_date,is_hs"
        )
        resp = _call("stock_basic", params, fields or default_fields, token)
        if resp.get("code") != 200:
            return resp

        data = resp.get("data") or {}
        records = data.get("records") or []
        total_count = data.get("count", len(records))
        sliced = records[safe_offset:safe_offset + safe_limit]

        data["total_count"] = total_count
        data["count"] = len(sliced)
        data["limit"] = safe_limit
        data["offset"] = safe_offset
        data["truncated"] = (safe_offset != 0) or (len(records) > len(sliced))
        data["records"] = sliced
        resp["data"] = data
        return resp

    @mcp.tool()
    def get_daily_data(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取A股日线行情数据

        Args:
            ts_code (str, optional): 股票代码（如：000001.SZ）
            trade_date (str, optional): 交易日期（YYYYMMDD格式）
            start_date (str, optional): 开始日期（YYYYMMDD格式）
            end_date (str, optional): 结束日期（YYYYMMDD格式）

        注意：ts_code和trade_date至少需要输入一个参数

        Returns:
            包含日线行情数据，字段包括：
            - ts_code: TS股票代码
            - trade_date: 交易日期
            - open: 开盘价
            - high: 最高价
            - low: 最低价
            - close: 收盘价
            - pre_close: 昨收价
            - change: 涨跌额
            - pct_chg: 涨跌幅（%）
            - vol: 成交量（手）
            - amount: 成交额（千元）
        """
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
                interface="daily",
            )
        return _call("daily", params, fields, token)

    @mcp.tool()
    def get_daily_basic(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取股票每日基本面指标

        Args:
            ts_code (str, optional): 股票代码（如：000001.SZ）
            trade_date (str, optional): 交易日期（YYYYMMDD格式）
            start_date (str, optional): 开始日期（YYYYMMDD格式）
            end_date (str, optional): 结束日期（YYYYMMDD格式）

        注意：ts_code和trade_date至少需要输入一个参数

        Returns:
            包含每日基本面指标，字段包括：
            - ts_code: TS股票代码
            - trade_date: 交易日期
            - close: 当日收盘价
            - turnover_rate: 换手率（%）
            - turnover_rate_f: 换手率（自由流通股）
            - volume_ratio: 量比
            - pe: 市盈率（总市值/净利润，亏损的PE为空）
            - pe_ttm: 市盈率（TTM，亏损的PE为空）
            - pb: 市净率（总市值/净资产）
            - ps: 市销率
            - ps_ttm: 市销率（TTM）
            - dv_ratio: 股息率（%）
            - dv_ttm: 股息率（TTM）（%）
            - total_share: 总股本（万股）
            - float_share: 流通股本（万股）
            - free_share: 自由流通股本（万）
            - total_mv: 总市值（万元）
            - circ_mv: 流通市值（万元）
        """
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
                interface="daily_basic",
            )
        return _call("daily_basic", params, fields, token)

    @mcp.tool()
    def get_financial_indicator(
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取上市公司财务指标数据

        Args:
            ts_code (str, optional): 股票代码（如：000001.SZ）
            ann_date (str, optional): 公告日期（YYYYMMDD格式）
            start_date (str, optional): 开始日期（YYYYMMDD格式）
            end_date (str, optional): 结束日期（YYYYMMDD格式）
            period (str, optional): 报告期（如：20191231）

        Returns:
            包含财务指标数据，字段包括：
            - ts_code: TS股票代码
            - ann_date: 公告日期
            - end_date: 报告期
            - eps: 基本每股收益
            - dt_eps: 稀释每股收益
            - total_revenue_ps: 每股营业总收入
            - revenue_ps: 每股营业收入
            - capital_rese_ps: 每股资本公积
            - surplus_rese_ps: 每股盈余公积
            - undist_profit_ps: 每股未分配利润
            - extra_item: 非经常性损益
            - profit_dedt: 扣除非经常性损益后的净利润
            - gross_margin: 毛利
            - current_ratio: 流动比率
            - quick_ratio: 速动比率
            - cash_ratio: 保守速动比率
            - invturn_days: 存货周转天数
            - arturn_days: 应收账款周转天数
            - inv_turn: 存货周转率
            - ar_turn: 应收账款周转率
            - ca_turn: 流动资产周转率
            - fa_turn: 固定资产周转率
            - assets_turn: 总资产周转率
            - op_income: 经营活动净收益
            - valuechange_income: 价值变动净收益
            - interst_income: 利息费用
            - daa: 总资产/全部投入资本
            - ebit: 息税前利润
            - ebitda: 息税折旧摊销前利润
            - fcff: 企业自由现金流量
            - fcfe: 股权自由现金流量
            - current_exint: 无息流动负债
            - noncurrent_exint: 无息非流动负债
            - interestdebt: 带息债务
            - netdebt: 净债务
            - tangible_asset: 有形资产
            - working_capital: 营运资金
            - networking_capital: 营运流动资本
            - invest_capital: 全部投入资本
            - retained_earnings: 留存收益
            - diluted2_eps: 期末摊薄每股收益
            - bps: 每股净资产
            - ocfps: 每股经营活动产生的现金流量净额
            - retainedps: 每股留存收益
            - cfps: 每股现金流量净额
            - ebit_ps: 每股息税前利润
            - fcff_ps: 每股企业自由现金流量
            - fcfe_ps: 每股股东自由现金流量
            - netprofit_margin: 销售净利率
            - grossprofit_margin: 销售毛利率
            - cogs_of_sales: 销售成本率
            - expense_of_sales: 销售期间费用率
            - profit_to_gr: 净利润/营业总收入
            - saleexp_to_gr: 销售费用/营业总收入
            - adminexp_of_gr: 管理费用/营业总收入
            - finaexp_of_gr: 财务费用/营业总收入
            - impai_ttm: 资产减值损失/营业总收入
            - gc_of_gr: 营业总成本/营业总收入
            - op_of_gr: 营业利润/营业总收入
            - ebit_of_gr: 息税前利润/营业总收入
            - roe: 净资产收益率
            - roe_waa: 加权平均净资产收益率
            - roe_dt: 净资产收益率(扣除非经常损益)
            - roa: 总资产报酬率
            - npta: 总资产净利润
            - roic: 投入资本回报率
            - roe_yearly: 年化净资产收益率
            - roa2_yearly: 年化总资产报酬率
            - roe_avg: 平均净资产收益率(增发条件)
            - opincome_of_ebt: 经营活动净收益/利润总额
            - investincome_of_ebt: 价值变动净收益/利润总额
            - n_op_profit_of_ebt: 营业外收支净额/利润总额
            - tax_to_ebt: 所得税/利润总额
            - dtprofit_to_profit: 扣除非经常损益后的净利润/净利润
            - salescash_to_or: 销售商品提供劳务收到的现金/营业收入
            - ocf_to_or: 经营活动产生的现金流量净额/营业收入
            - ocf_to_opincome: 经营活动产生的现金流量净额/经营活动净收益
            - capitalized_to_da: 资本支出/折旧和摊销
            - debt_to_assets: 资产负债率
            - assets_to_eqt: 权益乘数
            - dp_assets_to_eqt: 权益乘数(杜邦分析)
            - ca_to_assets: 流动资产/总资产
            - nca_to_assets: 非流动资产/总资产
            - tbassets_to_totalassets: 有形资产/总资产
            - int_to_talcap: 带息债务/全部投入资本
            - eqt_to_talcapital: 归属于母公司的股东权益/全部投入资本
            - currentdebt_to_debt: 流动负债/负债合计
            - longdeb_to_debt: 非流动负债/负债合计
            - ocf_to_shortdebt: 经营活动产生的现金流量净额/流动负债
            - debt_to_eqt: 产权比率
            - eqt_to_debt: 归属于母公司的股东权益/负债合计
            - eqt_to_interestdebt: 归属于母公司的股东权益/带息债务
            - tangibleasset_to_debt: 有形资产/负债合计
            - tangasset_to_intdebt: 有形资产/带息债务
            - tangibleasset_to_netdebt: 有形资产/净债务
            - ocf_to_debt: 经营活动产生的现金流量净额/负债合计
            - ocf_to_interestdebt: 经营活动产生的现金流量净额/带息债务
            - ocf_to_netdebt: 经营活动产生的现金流量净额/净债务
            - ebit_to_interest: 已获利息倍数(EBIT/利息费用)
            - longdebt_to_workingcapital: 长期债务与营运资金比率
            - ebitda_to_debt: 息税折旧摊销前利润/负债合计
            - turn_days: 营业周期
            - roa_yearly: 年化总资产净利率
            - roa_dp: 总资产净利率(杜邦分析)
            - fixed_assets: 固定资产合计
            - profit_prefin_exp: 扣除财务费用前营业利润
            - non_op_profit: 非营业利润
            - op_to_ebt: 营业利润／利润总额
            - nop_to_ebt: 非营业利润／利润总额
            - ocf_to_profit: 经营活动产生的现金流量净额／营业利润
            - cash_to_liqdebt: 货币资金／流动负债
            - cash_to_liqdebt_withinterest: 货币资金／带息流动负债
            - op_to_liqdebt: 营业利润／流动负债
            - op_to_debt: 营业利润／负债合计
            - roic_yearly: 年化投入资本回报率
            - total_fa_trun: 固定资产合计周转率
            - profit_to_op: 利润总额／营业收入
            - q_opincome: 经营活动单季度净收益
            - q_investincome: 价值变动单季度净收益
            - q_dtprofit: 扣除非经常损益后的单季度净利润
            - q_eps: 每股收益(单季度)
            - q_netprofit_margin: 销售净利率(单季度)
            - q_gsprofit_margin: 销售毛利率(单季度)
            - q_exp_to_sales: 销售期间费用率(单季度)
            - q_profit_to_gr: 净利润／营业总收入(单季度)
            - q_saleexp_to_gr: 销售费用／营业总收入 (单季度)
            - q_adminexp_to_gr: 管理费用／营业总收入 (单季度)
            - q_finaexp_to_gr: 财务费用／营业总收入 (单季度)
            - q_impair_to_gr_ttm: 资产减值损失／营业总收入(单季度)
            - q_gc_to_gr: 营业总成本／营业总收入 (单季度)
            - q_op_to_gr: 营业利润／营业总收入(单季度)
            - q_roe: 净资产收益率(单季度)
            - q_dt_roe: 净资产收益率(扣除非经常损益)(单季度)
            - q_npta: 总资产净利润(单季度)
            - q_opincome_to_ebt: 经营活动净收益／利润总额(单季度)
            - q_investincome_to_ebt: 价值变动净收益／利润总额(单季度)
            - q_dtprofit_to_profit: 扣除非经常损益后的净利润／净利润(单季度)
            - q_salescash_to_or: 销售商品提供劳务收到的现金／营业收入(单季度)
            - q_ocf_to_sales: 经营活动产生的现金流量净额／营业收入(单季度)
            - q_ocf_to_or: 经营活动产生的现金流量净额／经营活动净收益(单季度)
            - basic_eps_yoy: 基本每股收益同比增长率(%)
            - dt_eps_yoy: 稀释每股收益同比增长率(%)
            - cfps_yoy: 每股经营活动产生的现金流量净额同比增长率(%)
            - op_yoy: 营业利润同比增长率(%)
            - ebt_yoy: 利润总额同比增长率(%)
            - netprofit_yoy: 归属母公司股东的净利润同比增长率(%)
            - dt_netprofit_yoy: 归属母公司股东的净利润(扣除非经常损益)同比增长率(%)
            - ocf_yoy: 经营活动产生的现金流量净额同比增长率(%)
            - roe_yoy: 净资产收益率(摊薄)同比增长率(%)
            - bps_yoy: 每股净资产相对年初增长率(%)
            - assets_yoy: 资产总计相对年初增长率(%)
            - eqt_yoy: 归属母公司的股东权益相对年初增长率(%)
            - tr_yoy: 营业总收入同比增长率(%)
            - or_yoy: 营业收入同比增长率(%)
            - q_gr_yoy: 营业总收入同比增长率(%)(单季度)
            - q_gr_qoq: 营业总收入环比增长率(%)(单季度)
            - q_sales_yoy: 营业收入同比增长率(%)(单季度)
            - q_sales_qoq: 营业收入环比增长率(%)(单季度)
            - q_op_yoy: 营业利润同比增长率(%)(单季度)
            - q_op_qoq: 营业利润环比增长率(%)(单季度)
            - q_profit_yoy: 净利润同比增长率(%)(单季度)
            - q_profit_qoq: 净利润环比增长率(%)(单季度)
            - q_netprofit_yoy: 归属母公司股东的净利润同比增长率(%)(单季度)
            - q_netprofit_qoq: 归属母公司股东的净利润环比增长率(%)(单季度)
            - equity_yoy: 净资产同比增长率
            - rd_exp: 研发费用
            - update_flag: 更新标识
        """
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if ann_date:
            params["ann_date"] = ann_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if period:
            params["period"] = period
        if not params:
            return error_payload(
                "ts_code 或 ann_date 或 start_date/end_date 或 period 至少提供一个参数",
                400,
                interface="fina_indicator",
            )
        return _call("fina_indicator", params, fields, token)

    @mcp.tool()
    def get_top_list(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取龙虎榜每日交易明细

        Args:
            trade_date (str, optional): 交易日期（YYYYMMDD格式）
            ts_code (str, optional): 股票代码（如：000001.SZ）

        注意：trade_date和ts_code至少需要输入一个参数

        Returns:
            包含龙虎榜数据，字段包括：
            - trade_date: 交易日期
            - ts_code: TS股票代码
            - name: 名称
            - close: 收盘价
            - pct_change: 涨跌幅
            - turnover_rate: 换手率
            - amount: 总成交额
            - l_sell: 龙虎榜卖出额
            - l_buy: 龙虎榜买入额
            - l_amount: 龙虎榜成交额
            - net_amount: 龙虎榜净买入额
            - net_rate: 龙虎榜净买额占比
            - amount_rate: 龙虎榜成交额占比
            - float_values: 当日流通市值
            - reason: 上榜理由
        """
        params: Dict[str, Any] = {}
        if trade_date:
            params["trade_date"] = trade_date
        if ts_code:
            params["ts_code"] = ts_code
        if not params:
            return error_payload(
                "trade_date 或 ts_code 至少提供一个参数", 400, interface="top_list"
            )
        return _call("top_list", params, fields, token)

    @mcp.tool()
    def get_block_trade(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取大宗交易数据

        Args:
            ts_code (str, optional): 股票代码（如：000001.SZ）
            trade_date (str, optional): 交易日期（YYYYMMDD格式）
            start_date (str, optional): 开始日期（YYYYMMDD格式）
            end_date (str, optional): 结束日期（YYYYMMDD格式）

        注意：股票代码和日期至少输入一个参数

        Returns:
            包含大宗交易数据，字段包括：
            - ts_code: TS股票代码
            - trade_date: 交易日期
            - price: 成交价
            - vol: 成交量（万股）
            - amount: 成交金额
            - buyer: 买方营业部
            - seller: 卖方营业部
        """
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
                interface="block_trade",
            )
        return _call("block_trade", params, fields, token)

    @mcp.tool()
    def get_margin_data(
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange_id: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取融资融券交易汇总数据

        Args:
            trade_date (str, optional): 交易日期（YYYYMMDD格式）
            start_date (str, optional): 开始日期（YYYYMMDD格式）
            end_date (str, optional): 结束日期（YYYYMMDD格式）
            exchange_id (str, optional): 交易所代码（SSE上交所 SZSE深交所 BSE北交所）

        Returns:
            包含融资融券数据，字段包括：
            - trade_date: 交易日期
            - exchange_id: 交易所代码
            - rzye: 融资余额（元）
            - rzmre: 融资买入额（元）
            - rzche: 融资偿还额（元）
            - rqye: 融券余额（元）
            - rqmcl: 融券卖出量（股）
            - rzrqye: 融资融券余额（元）
        """
        params: Dict[str, Any] = {}
        if trade_date:
            params["trade_date"] = trade_date
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if exchange_id:
            params["exchange_id"] = exchange_id
        if not params:
            return error_payload(
                "trade_date 或 start_date/end_date 或 exchange_id 至少提供一个参数",
                400,
                interface="margin",
            )
        return _call("margin", params, fields, token)

    @mcp.tool()
    def get_trade_calendar(
        exchange: str = "SSE",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        is_open: Optional[int] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取交易日历数据

        Args:
            exchange (str): 交易所代码，默认SSE（SSE上交所 SZSE深交所 CFFEX中金所
                SHFE上期所 CZCE郑商所 DCE大商所 INE上能源）
            start_date (str, optional): 开始日期（YYYYMMDD格式）
            end_date (str, optional): 结束日期（YYYYMMDD格式）
            is_open (int, optional): 是否交易 0休市 1交易

        Returns:
            包含交易日历数据，字段包括：
            - exchange: 交易所代码
            - cal_date: 日历日期
            - is_open: 是否交易（0休市 1交易）
            - pretrade_date: 上一交易日
        """
        params: Dict[str, Any] = {"exchange": exchange}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if is_open is not None:
            params["is_open"] = is_open
        return _call("trade_cal", params, fields, token)

    @mcp.tool()
    def get_stock_company(
        ts_code: Optional[str] = None,
        exchange: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取上市公司基础信息

        Args:
            ts_code (str, optional): 股票代码（如：000001.SZ）
            exchange (str, optional): 交易所代码（SSE上交所 SZSE深交所 BSE北交所）

        Returns:
            包含上市公司基础信息，字段包括：
            - ts_code: TS股票代码
            - exchange: 交易所代码
            - chairman: 法人代表
            - manager: 总经理
            - secretary: 董秘
            - reg_capital: 注册资本
            - setup_date: 注册日期
            - province: 所在省份
            - city: 所在城市
            - introduction: 公司介绍
            - website: 公司主页
            - email: 电子邮件
            - office: 办公室
            - employees: 员工人数
            - main_business: 主要业务及产品
            - business_scope: 经营范围
        """
        params: Dict[str, Any] = {}
        if ts_code:
            params["ts_code"] = ts_code
        if exchange:
            params["exchange"] = exchange
        if not params:
            return error_payload(
                "ts_code 或 exchange 至少提供一个参数", 400, interface="stock_company"
            )
        return _call("stock_company", params, fields, token)

    @mcp.tool()
    def get_new_share(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取IPO新股上市列表数据

        Args:
            start_date (str, optional): 开始日期（YYYYMMDD格式）
            end_date (str, optional): 结束日期（YYYYMMDD格式）

        Returns:
            包含新股上市数据，字段包括：
            - ts_code: TS股票代码
            - sub_code: 申购代码
            - name: 名称
            - ipo_date: 上网发行日期
            - issue_date: 上市日期
            - amount: 发行总量（万股）
            - market_amount: 上网发行总量（万股）
            - price: 发行价格
            - pe: 市盈率
            - limit_amount: 个人申购上限（万股）
            - funds: 募集资金（亿元）
            - ballot: 中签率
        """
        params: Dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if not params:
            return error_payload(
                "start_date 或 end_date 至少提供一个参数", 400, interface="new_share"
            )
        return _call("new_share", params, fields, token)
