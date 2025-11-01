"""
股票数据工具模块
提供股票基础数据、行情数据、财务数据、参考数据等接口
"""

import json
from typing import Dict, Any, Optional, List
from mcp.server import Server
from mcp.types import Tool, TextContent


def register_stock_data_tools(server: Server):
    """注册股票数据相关的工具"""
    
    @server.tool()
    def get_stock_basic(
        list_status: str = "L",
        exchange: Optional[str] = None,
        ts_code: Optional[str] = None,
        market: Optional[str] = None,
        is_hs: Optional[str] = None
    ) -> List[TextContent]:
        """
        获取股票基础信息列表
        
        Args:
            list_status (str): 上市状态 L上市 D退市 P暂停上市，默认是L
            exchange (str, optional): 交易所 SSE上交所 SZSE深交所 BSE北交所
            ts_code (str, optional): TS股票代码
            market (str, optional): 市场类别 主板/创业板/科创板/CDR/北交所
            is_hs (str, optional): 是否沪深港通标的，N否 H沪股通 S深股通
            
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
        """
        return [TextContent(
            type="text",
            text=json.dumps({
                "interface": "stock_basic",
                "description": "获取股票基础信息列表",
                "input_params": {
                    "list_status": list_status,
                    "exchange": exchange,
                    "ts_code": ts_code,
                    "market": market,
                    "is_hs": is_hs
                },
                "output_fields": [
                    "ts_code", "symbol", "name", "area", "industry", 
                    "fullname", "enname", "cnspell", "market", "exchange",
                    "curr_type", "list_status", "list_date", "delist_date", "is_hs"
                ],
                "note": "此接口返回股票基础信息，建议保存到本地后使用"
            }, ensure_ascii=False, indent=2)
        )]

    @server.tool()
    def get_daily_data(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[TextContent]:
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
        return [TextContent(
            type="text",
            text=json.dumps({
                "interface": "daily",
                "description": "获取A股日线行情数据（未复权）",
                "input_params": {
                    "ts_code": ts_code,
                    "trade_date": trade_date,
                    "start_date": start_date,
                    "end_date": end_date
                },
                "output_fields": [
                    "ts_code", "trade_date", "open", "high", "low", "close",
                    "pre_close", "change", "pct_chg", "vol", "amount"
                ],
                "note": "交易日每天15点～16点之间入库，停牌期间不提供数据"
            }, ensure_ascii=False, indent=2)
        )]

    @server.tool()
    def get_daily_basic(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[TextContent]:
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
        return [TextContent(
            type="text",
            text=json.dumps({
                "interface": "daily_basic",
                "description": "获取股票每日基本面指标",
                "input_params": {
                    "ts_code": ts_code,
                    "trade_date": trade_date,
                    "start_date": start_date,
                    "end_date": end_date
                },
                "output_fields": [
                    "ts_code", "trade_date", "close", "turnover_rate", "turnover_rate_f",
                    "volume_ratio", "pe", "pe_ttm", "pb", "ps", "ps_ttm",
                    "dv_ratio", "dv_ttm", "total_share", "float_share", "free_share",
                    "total_mv", "circ_mv"
                ],
                "note": "交易日每日15点～17点之间更新"
            }, ensure_ascii=False, indent=2)
        )]

    @server.tool()
    def get_financial_indicator(
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None
    ) -> List[TextContent]:
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
        return [TextContent(
            type="text",
            text=json.dumps({
                "interface": "fina_indicator",
                "description": "获取上市公司财务指标数据",
                "input_params": {
                    "ts_code": ts_code,
                    "ann_date": ann_date,
                    "start_date": start_date,
                    "end_date": end_date,
                    "period": period
                },
                "output_fields": [
                    "ts_code", "ann_date", "end_date", "eps", "dt_eps", "total_revenue_ps",
                    "revenue_ps", "capital_rese_ps", "surplus_rese_ps", "undist_profit_ps",
                    "extra_item", "profit_dedt", "gross_margin", "current_ratio", "quick_ratio",
                    "cash_ratio", "invturn_days", "arturn_days", "inv_turn", "ar_turn",
                    "ca_turn", "fa_turn", "assets_turn", "op_income", "valuechange_income",
                    "interst_income", "daa", "ebit", "ebitda", "fcff", "fcfe",
                    "current_exint", "noncurrent_exint", "interestdebt", "netdebt",
                    "tangible_asset", "working_capital", "networking_capital", "invest_capital",
                    "retained_earnings", "diluted2_eps", "bps", "ocfps", "retainedps",
                    "cfps", "ebit_ps", "fcff_ps", "fcfe_ps", "netprofit_margin",
                    "grossprofit_margin", "cogs_of_sales", "expense_of_sales", "profit_to_gr",
                    "saleexp_to_gr", "adminexp_of_gr", "finaexp_of_gr", "impai_ttm",
                    "gc_of_gr", "op_of_gr", "ebit_of_gr", "roe", "roe_waa", "roe_dt",
                    "roa", "npta", "roic", "roe_yearly", "roa2_yearly", "roe_avg",
                    "opincome_of_ebt", "investincome_of_ebt", "n_op_profit_of_ebt",
                    "tax_to_ebt", "dtprofit_to_profit", "salescash_to_or", "ocf_to_or",
                    "ocf_to_opincome", "capitalized_to_da", "debt_to_assets", "assets_to_eqt",
                    "dp_assets_to_eqt", "ca_to_assets", "nca_to_assets", "tbassets_to_totalassets",
                    "int_to_talcap", "eqt_to_talcapital", "currentdebt_to_debt", "longdeb_to_debt",
                    "ocf_to_shortdebt", "debt_to_eqt", "eqt_to_debt", "eqt_to_interestdebt",
                    "tangibleasset_to_debt", "tangasset_to_intdebt", "tangibleasset_to_netdebt",
                    "ocf_to_debt", "ocf_to_interestdebt", "ocf_to_netdebt", "ebit_to_interest",
                    "longdebt_to_workingcapital", "ebitda_to_debt", "turn_days", "roa_yearly",
                    "roa_dp", "fixed_assets", "profit_prefin_exp", "non_op_profit",
                    "op_to_ebt", "nop_to_ebt", "ocf_to_profit", "cash_to_liqdebt",
                    "cash_to_liqdebt_withinterest", "op_to_liqdebt", "op_to_debt",
                    "roic_yearly", "total_fa_trun", "profit_to_op", "q_opincome",
                    "q_investincome", "q_dtprofit", "q_eps", "q_netprofit_margin",
                    "q_gsprofit_margin", "q_exp_to_sales", "q_profit_to_gr", "q_saleexp_to_gr",
                    "q_adminexp_to_gr", "q_finaexp_to_gr", "q_impair_to_gr_ttm", "q_gc_to_gr",
                    "q_op_to_gr", "q_roe", "q_dt_roe", "q_npta", "q_opincome_to_ebt",
                    "q_investincome_to_ebt", "q_dtprofit_to_profit", "q_salescash_to_or",
                    "q_ocf_to_sales", "q_ocf_to_or", "basic_eps_yoy", "dt_eps_yoy",
                    "cfps_yoy", "op_yoy", "ebt_yoy", "netprofit_yoy", "dt_netprofit_yoy",
                    "ocf_yoy", "roe_yoy", "bps_yoy", "assets_yoy", "eqt_yoy", "tr_yoy",
                    "or_yoy", "q_gr_yoy", "q_gr_qoq", "q_sales_yoy", "q_sales_qoq",
                    "q_op_yoy", "q_op_qoq", "q_profit_yoy", "q_profit_qoq", "q_netprofit_yoy",
                    "q_netprofit_qoq", "equity_yoy", "rd_exp", "update_flag"
                ],
                "note": "单次最多返回100条记录，可通过设置日期多次请求获取更多数据"
            }, ensure_ascii=False, indent=2)
        )]

    @server.tool()
    def get_top_list(
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> List[TextContent]:
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
        return [TextContent(
            type="text",
            text=json.dumps({
                "interface": "top_list",
                "description": "获取龙虎榜每日交易明细",
                "input_params": {
                    "trade_date": trade_date,
                    "ts_code": ts_code
                },
                "output_fields": [
                    "trade_date", "ts_code", "name", "close", "pct_change",
                    "turnover_rate", "amount", "l_sell", "l_buy", "l_amount",
                    "net_amount", "net_rate", "amount_rate", "float_values", "reason"
                ],
                "note": "数据历史从2005年至今，单次请求返回最大10000行数据"
            }, ensure_ascii=False, indent=2)
        )]

    @server.tool()
    def get_block_trade(
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[TextContent]:
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
        return [TextContent(
            type="text",
            text=json.dumps({
                "interface": "block_trade",
                "description": "获取大宗交易数据",
                "input_params": {
                    "ts_code": ts_code,
                    "trade_date": trade_date,
                    "start_date": start_date,
                    "end_date": end_date
                },
                "output_fields": [
                    "ts_code", "trade_date", "price", "vol", "amount", "buyer", "seller"
                ],
                "note": "单次最大1000条，总量不限制"
            }, ensure_ascii=False, indent=2)
        )]

    @server.tool()
    def get_margin_data(
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange_id: Optional[str] = None
    ) -> List[TextContent]:
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
        return [TextContent(
            type="text",
            text=json.dumps({
                "interface": "margin",
                "description": "获取融资融券每日交易汇总数据",
                "input_params": {
                    "trade_date": trade_date,
                    "start_date": start_date,
                    "end_date": end_date,
                    "exchange_id": exchange_id
                },
                "output_fields": [
                    "trade_date", "exchange_id", "rzye", "rzmre", "rzche",
                    "rqye", "rqmcl", "rzrqye"
                ],
                "note": "单次请求最大返回4000行数据，可根据日期循环"
            }, ensure_ascii=False, indent=2)
        )]

    @server.tool()
    def get_trade_calendar(
        exchange: str = "SSE",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        is_open: Optional[int] = None
    ) -> List[TextContent]:
        """
        获取交易日历数据
        
        Args:
            exchange (str): 交易所代码，默认SSE（SSE上交所 SZSE深交所 CFFEX中金所 SHFE上期所 CZCE郑商所 DCE大商所 INE上能源）
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
        return [TextContent(
            type="text",
            text=json.dumps({
                "interface": "trade_cal",
                "description": "获取各大交易所交易日历数据",
                "input_params": {
                    "exchange": exchange,
                    "start_date": start_date,
                    "end_date": end_date,
                    "is_open": is_open
                },
                "output_fields": [
                    "exchange", "cal_date", "is_open", "pretrade_date"
                ],
                "note": "默认提取的是上交所数据"
            }, ensure_ascii=False, indent=2)
        )]

    @server.tool()
    def get_stock_company(
        ts_code: Optional[str] = None,
        exchange: Optional[str] = None
    ) -> List[TextContent]:
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
        return [TextContent(
            type="text",
            text=json.dumps({
                "interface": "stock_company",
                "description": "获取上市公司基础信息",
                "input_params": {
                    "ts_code": ts_code,
                    "exchange": exchange
                },
                "output_fields": [
                    "ts_code", "exchange", "chairman", "manager", "secretary",
                    "reg_capital", "setup_date", "province", "city", "introduction",
                    "website", "email", "office", "employees", "main_business", "business_scope"
                ],
                "note": "单次提取4500条，可以根据交易所分批提取"
            }, ensure_ascii=False, indent=2)
        )]

    @server.tool()
    def get_new_share(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[TextContent]:
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
        return [TextContent(
            type="text",
            text=json.dumps({
                "interface": "new_share",
                "description": "获取新股上市列表数据",
                "input_params": {
                    "start_date": start_date,
                    "end_date": end_date
                },
                "output_fields": [
                    "ts_code", "sub_code", "name", "ipo_date", "issue_date",
                    "amount", "market_amount", "price", "pe", "limit_amount",
                    "funds", "ballot"
                ],
                "note": "单次最大2000条，总量不限制"
            }, ensure_ascii=False, indent=2)
        )]