import unittest
from unittest.mock import patch

import pandas as pd

from .auction_selection_strategy import AuctionSelectionStrategyService
from .industry_ma_breadth_strategy import IndustryMABreadthStrategy
from .industry_turnover_strategy import IndustryTurnoverStrategy
from .limit_board_service import LimitBoardDataService
from stock_strategy.data_tasks import dc_board_rps
from stock_strategy.data_tasks import dc_board_member_rps
from stock_strategy.data_tasks import major_index_rps
from stock_strategy.data_tasks import potential_stock_screen
from stock_strategy.data_tasks import stock_rps


class FakeTusharePro:
    """
    组件：伪造 Tushare Pro 客户端（FakeTusharePro）

    功能：
    - 为竞价选股策略测试提供稳定的交易日历、涨停池和竞价数据。

    参数：
    - 无

    返回值：
    - trade_cal/limit_list_d/stk_auction 均返回 DataFrame。

    事件：
    - 无。
    """

    def trade_cal(self, exchange="", start_date=None, end_date=None, fields=None):
        """
        功能：返回测试所需交易日历数据。

        参数：
        - exchange (str，可选): 交易所参数，测试中忽略。
        - start_date (str，可选): 开始日期。
        - end_date (str，可选): 结束日期。
        - fields (str，可选): 字段列表。

        返回值：
        - DataFrame: 交易日历数据。

        异常：
        - 无。
        """
        _ = (exchange, start_date, end_date, fields)
        return pd.DataFrame(
            [
                {"cal_date": "20260112", "is_open": 1},
                {"cal_date": "20260113", "is_open": 1},
                {"cal_date": "20260114", "is_open": 1},
            ]
        )

    def limit_list_d(self, trade_date=None, limit_type=None, fields=None):
        """
        功能：返回测试所需昨日涨停池数据。

        参数：
        - trade_date (str，可选): 交易日。
        - limit_type (str，可选): 涨停类型。
        - fields (str，可选): 字段列表。

        返回值：
        - DataFrame: 昨日涨停池数据。

        异常：
        - 无。
        """
        _ = (trade_date, limit_type, fields)
        return pd.DataFrame(
            [
                {
                    "trade_date": "20260113",
                    "ts_code": "000001.SZ",
                    "name": "测试股份",
                    "float_mv": 300000,
                    "amount": 100000000,
                    "fd_amount": 40000000,
                    "open_times": 0,
                    "last_time": "145000",
                    "limit_times": 2,
                },
                {
                    "trade_date": "20260113",
                    "ts_code": "000002.SZ",
                    "name": "三板龙头",
                    "float_mv": 500000,
                    "amount": 120000000,
                    "fd_amount": 60000000,
                    "open_times": 0,
                    "last_time": "144500",
                    "limit_times": 3,
                },
                {
                    "trade_date": "20260113",
                    "ts_code": "000003.SZ",
                    "name": "四板晋级",
                    "float_mv": 600000,
                    "amount": 140000000,
                    "fd_amount": 70000000,
                    "open_times": 0,
                    "last_time": "144800",
                    "limit_times": 4,
                },
            ]
        )

    def stk_auction(self, trade_date=None, fields=None):
        """
        功能：返回测试所需目标交易日竞价数据。

        参数：
        - trade_date (str，可选): 交易日。
        - fields (str，可选): 字段列表。

        返回值：
        - DataFrame: 集合竞价数据。

        异常：
        - 无。
        """
        _ = (trade_date, fields)
        return pd.DataFrame(
            [
                {
                    "ts_code": "000001.SZ",
                    "trade_date": "20260114",
                    "price": 13.0,
                    "pre_close": 12.0,
                    "amount": 2000000,
                }
            ]
        )


class AuctionSelectionStrategyServiceTests(unittest.TestCase):
    """
    组件：9点25竞价选股策略测试（AuctionSelectionStrategyServiceTests）

    功能：
    - 验证策略在给定的伪造行情数据下，能够输出候选池、情绪判断和评分拆解。

    参数：
    - 无

    返回值：
    - 无

    事件：
    - 无。
    """

    def test_get_strategy_result_returns_ranked_candidates_and_sentiment(self):
        """
        功能：验证策略输出包含排序候选股、市场情绪和评分拆解。

        参数：
        - 无

        返回值：
        - 无

        异常：
        - 断言失败时由测试框架抛出异常。
        """
        service = AuctionSelectionStrategyService(
            tushare_pro=FakeTusharePro(),
            sleep_func=lambda seconds: None,
        )

        result = service.get_strategy_result(trade_date="20260114", top_n=3)

        self.assertEqual(result["params"]["trade_date"], "20260114")
        self.assertEqual(result["params"]["prev_trade_date"], "20260113")
        self.assertEqual(result["market_sentiment"]["phase"], "attack")
        self.assertEqual(result["statistics"]["selected_count"], 1)
        self.assertEqual(result["top_candidates"][0]["code"], "000001.SZ")
        self.assertIn("score_breakdown", result["top_candidates"][0])
        self.assertGreaterEqual(result["top_candidates"][0]["score"], 16)


class FakeLimitBoardFetcher:
    """
    组件：伪造 Tushare 组合接口调用器。

    功能：
    - 为涨停打板组合数据服务测试提供稳定的多接口记录。
    """

    def __call__(self, interface, params=None, fields=None, token=None, use_query=False):
        _ = (fields, token, use_query)
        params = params or {}
        records = self._records(interface, params)
        return {
            "code": 200,
            "message": "success",
            "data": {
                "interface": interface,
                "count": len(records),
                "records": records,
            },
        }

    def _records(self, interface, params):
        """
        功能：根据接口名和查询参数返回预设测试记录。

        参数：
        - interface (str): Tushare 接口名称。
        - params (dict): 接口查询参数，支持按区间与涨跌停类型切换数据集。

        返回值：
        - list[dict]: 对应接口的伪造记录列表。

        异常：
        - 无。未知接口默认返回空列表。
        """
        is_range_query = bool(params.get("start_date") and params.get("end_date"))
        limit_type = params.get("limit_type")
        if interface == "limit_list_d" and limit_type == "U":
            records = [
                {
                    "trade_date": "20260114",
                    "ts_code": "000001.SZ",
                    "name": "一板股",
                    "industry": "机器人",
                    "amount": 1000,
                    "fd_amount": 200,
                    "turnover_ratio": 10.0,
                    "first_time": "093500",
                    "open_times": 0,
                    "up_stat": "1/1",
                    "limit_times": 1,
                },
                {
                    "trade_date": "20260114",
                    "ts_code": "000002.SZ",
                    "name": "二板股",
                    "industry": "机器人",
                    "amount": 2000,
                    "fd_amount": 500,
                    "turnover_ratio": 20.0,
                    "first_time": "094500",
                    "open_times": 1,
                    "up_stat": "2/3",
                    "limit_times": 2,
                },
            ]
            if is_range_query:
                records.extend([
                    {
                        "trade_date": "20260115",
                        "ts_code": "000001.SZ",
                        "name": "一板股",
                        "industry": "机器人",
                        "amount": 1500,
                        "fd_amount": 300,
                        "turnover_ratio": 12.0,
                        "first_time": "094000",
                        "open_times": 0,
                        "up_stat": "2/2",
                        "limit_times": 2,
                    },
                    {
                        "trade_date": "20260115",
                        "ts_code": "000006.SZ",
                        "name": "新启动",
                        "industry": "机器人",
                        "amount": 1200,
                        "fd_amount": 240,
                        "turnover_ratio": 8.0,
                        "first_time": "100000",
                        "open_times": 0,
                        "up_stat": "1/1",
                        "limit_times": 1,
                    },
                    {
                        "trade_date": "20260115",
                        "ts_code": "000007.SZ",
                        "name": "高标股",
                        "industry": "消费电子",
                        "amount": 2200,
                        "fd_amount": 600,
                        "turnover_ratio": 15.0,
                        "first_time": "095000",
                        "open_times": 0,
                        "up_stat": "3/4",
                        "limit_times": 3,
                    },
                ])
            return records
        if interface == "limit_list_d" and limit_type == "D":
            records = [{"trade_date": "20260114", "ts_code": "000003.SZ", "name": "跌停股"}]
            if is_range_query:
                records.append({"trade_date": "20260115", "ts_code": "000008.SZ", "name": "补跌股"})
            return records
        if interface == "limit_list_d" and limit_type == "Z":
            records = [{"trade_date": "20260114", "ts_code": "000004.SZ", "name": "炸板股", "amount": 3000, "open_times": 2}]
            if is_range_query:
                records.append({"trade_date": "20260115", "ts_code": "000002.SZ", "name": "二板股", "amount": 2500, "open_times": 3, "limit_times": 2})
            return records
        if interface == "limit_step":
            records = [
                {"trade_date": "20260114", "ts_code": "000002.SZ", "name": "二板股", "nums": "2"},
                {"trade_date": "20260114", "ts_code": "000005.SZ", "name": "三板股", "nums": "3"},
            ]
            if is_range_query:
                records.extend([
                    {"trade_date": "20260115", "ts_code": "000001.SZ", "name": "一板股", "nums": "2"},
                    {"trade_date": "20260115", "ts_code": "000007.SZ", "name": "高标股", "nums": "3"},
                ])
            return records
        if interface == "limit_cpt_list":
            records = [{"trade_date": "20260114", "ts_code": "885001.TI", "name": "机器人", "up_nums": 8, "cons_nums": 2, "up_stat": "3天3板", "pct_chg": 3.2, "rank": "1"}]
            if is_range_query:
                records.extend([
                    {"trade_date": "20260115", "ts_code": "885001.TI", "name": "机器人", "up_nums": 12, "cons_nums": 3, "up_stat": "4天4板", "pct_chg": 4.1, "rank": "1"},
                    {"trade_date": "20260115", "ts_code": "885002.TI", "name": "消费", "up_nums": 6, "cons_nums": 1, "up_stat": "2天2板", "pct_chg": 1.8, "rank": "2"},
                ])
            return records
        if interface == "limit_list_ths" and limit_type == "涨停池":
            return [
                {"trade_date": "20260114", "ts_code": "000001.SZ", "name": "一板股", "lu_desc": "机器人概念", "tag": "首板", "status": "一字板", "limit_times": 1, "turnover_ratio": 10.0, "open_num": 0, "first_lu_time": "093000", "limit_up_suc_rate": 0.85, "rise_rate": 3.2, "market_type": "HS"},
                {"trade_date": "20260114", "ts_code": "000002.SZ", "name": "二板股", "lu_desc": "机器人概念", "tag": "连板", "status": "换手板", "limit_times": 2, "turnover_ratio": 20.0, "open_num": 1},
                {"trade_date": "20260114", "ts_code": "000009.SZ", "name": "ST退市", "lu_desc": "重组预期", "tag": "首板", "status": "一字板", "limit_times": 1, "turnover_ratio": 5.0, "open_num": 0},
                {"trade_date": "20260114", "ts_code": "000010.SZ", "name": "无行业股", "lu_desc": "杂项", "tag": "首板", "status": "换手板", "limit_times": 1, "turnover_ratio": 6.0, "open_num": 0},
                {"trade_date": "20260115", "ts_code": "000001.SZ", "name": "一板股", "lu_desc": "机器人概念", "tag": "连板", "status": "T字板", "limit_times": 2, "turnover_ratio": 12.0, "open_num": 0},
                {"trade_date": "20260115", "ts_code": "000006.SZ", "name": "新启动", "lu_desc": "机器人概念", "tag": "首板", "status": "换手板", "limit_times": 1, "turnover_ratio": 8.0, "open_num": 0},
                {"trade_date": "20260115", "ts_code": "000007.SZ", "name": "高标股", "lu_desc": "消费电子", "tag": "连板", "status": "一字板", "limit_times": 3, "turnover_ratio": 15.0, "open_num": 0},
            ]
        if interface == "limit_list_ths":
            return [{"trade_date": "20260114", "ts_code": "000004.SZ", "name": "炸板股", "lu_desc": "题材催化", "open_num": 2}]
        if interface == "dc_daily":
            return [
                {"trade_date": "20260114", "ts_code": "BK001.DC", "pct_change": 1.5},
                {"trade_date": "20260115", "ts_code": "BK001.DC", "pct_change": 2.1},
                {"trade_date": "20260115", "ts_code": "BK002.DC", "pct_change": -0.8},
                {"trade_date": "20260116", "ts_code": "BK001.DC", "pct_change": -1.2},
                {"trade_date": "20260116", "ts_code": "BK002.DC", "pct_change": 0.6},
            ]
        if interface == "daily":
            trade_date = params.get("trade_date") or params.get("start_date")
            daily_by_date = {
                "20260114": [
                    {"trade_date": "20260114", "ts_code": "000001.SZ", "open": 10.0, "close": 10.5},
                    {"trade_date": "20260114", "ts_code": "000002.SZ", "open": 20.0, "close": 21.0},
                ],
                "20260115": [
                    {"trade_date": "20260115", "ts_code": "000001.SZ", "open": 10.8, "close": 11.2},
                    {"trade_date": "20260115", "ts_code": "000002.SZ", "open": 21.4, "close": 22.0},
                    {"trade_date": "20260115", "ts_code": "000006.SZ", "open": 8.0, "close": 8.6},
                    {"trade_date": "20260115", "ts_code": "000007.SZ", "open": 30.0, "close": 31.0},
                ],
                "20260116": [
                    {"trade_date": "20260116", "ts_code": "000001.SZ", "open": 11.0, "close": 11.1},
                    {"trade_date": "20260116", "ts_code": "000006.SZ", "open": 8.8, "close": 8.9},
                    {"trade_date": "20260116", "ts_code": "000007.SZ", "open": 31.3, "close": 30.8},
                ],
            }
            return daily_by_date.get(trade_date, [])
        if interface == "kpl_list":
            return [{"trade_date": "20260114", "ts_code": "000001.SZ", "name": "一板股", "tag": "涨停", "theme": "机器人", "status": "首板"}]
        if interface == "kpl_concept":
            return [{"trade_date": "20260114", "ts_code": "KPL001", "name": "机器人"}]
        if interface == "kpl_concept_cons":
            return [{"trade_date": "20260114", "ts_code": "KPL001", "con_code": "000001.SZ", "con_name": "一板股"}]
        if interface == "top_list":
            return [{"trade_date": "20260114", "ts_code": "000001.SZ", "name": "一板股", "net_amount": 100}]
        if interface == "hm_detail":
            return [{"trade_date": "20260114", "ts_code": "000001.SZ", "hm_name": "测试游资", "buy_amount": 300, "sell_amount": 100}]
        return []


class LimitBoardDataServiceTests(unittest.TestCase):
    """
    组件：涨停打板组合数据服务测试。
    """

    def setUp(self):
        self.service = LimitBoardDataService(fetcher=FakeLimitBoardFetcher())

    def test_trend_analysis_returns_sentiment_concept_and_lifecycle_trends(self):
        """
        功能：验证区间趋势分析会返回情绪、题材与个股生命周期三类结果。

        参数：
        - 无。

        返回值：
        - 无。

        异常：
        - 断言失败时由测试框架抛出异常。
        """
        result = self.service.get_trend_analysis(start_date="20260114", end_date="20260115", top_n=10)

        self.assertEqual(result["summary"]["trade_day_count"], 2)
        self.assertEqual(len(result["sentiment_series"]), 2)
        self.assertEqual(result["sentiment_series"][1]["changes"]["limit_up_count"], 1)
        self.assertEqual(result["concept_trends"][0]["concept_name"], "机器人")
        lifecycle_by_code = {item["ts_code"]: item for item in result["stock_lifecycles"]}
        self.assertEqual(lifecycle_by_code["000001.SZ"]["lifecycle_stage"], "二板确认")

    def test_industry_trend_strength_groups_ths_limit_up_by_date_and_industry(self):
        """
        功能：验证行业涨停趋势强度分析以 limit_list_ths 为基础、按交易日 key 返回整体/行业/个股三个维度。

        参数：
        - 无。

        返回值：
        - 无。

        异常：
        - 断言失败时由测试框架抛出异常。
        """
        result = self.service.get_industry_trend_strength(start_date="20260114", end_date="20260115")

        self.assertEqual(result["summary"]["trade_day_count"], 2)
        self.assertEqual(result["summary"]["industry_count"], 2)
        # ST 股票与未知行业个股不计入统计范围
        self.assertEqual(result["summary"]["total_limit_up_count"], 5)
        self.assertEqual(result["summary"]["excluded_st_count"], 1)
        self.assertEqual(result["summary"]["excluded_unknown_industry_count"], 1)

        # 以交易日为 key
        self.assertEqual(sorted(result["data"].keys()), ["20260114", "20260115"])

        # 20260114：过滤 ST 与未知行业后，整体 2 只，均归入机器人行业
        day1 = result["data"]["20260114"]
        self.assertEqual(day1["overall"]["limit_up_count"], 2)
        self.assertEqual(day1["overall"]["industry_count"], 1)
        self.assertEqual(day1["overall"]["limit_down_count"], 1)
        self.assertEqual(day1["overall"]["broken_limit_count"], 1)
        self.assertEqual(day1["overall"]["limit_attempt_count"], 3)
        self.assertEqual(day1["overall"]["sealed_rate"], 66.67)
        self.assertEqual(day1["overall"]["max_board"], 3)
        self.assertEqual(day1["overall"]["phase"], "repair")
        self.assertEqual(day1["industries"], [
            {
                "industry": "机器人",
                "limit_up_count": 2,
                "status_counts": {"T字板": 0, "一字板": 1, "换手板": 1},
            }
        ])
        self.assertEqual(len(day1["stocks"]["机器人"]), 2)
        # 个股保留 limit_list_ths 原始字段，并补充所属行业
        robot_stock = day1["stocks"]["机器人"][0]
        self.assertEqual(robot_stock["industry"], "机器人")
        self.assertIn("lu_desc", robot_stock)
        self.assertIn("tag", robot_stock)
        # 个股保留 limit_list_ths 新增字段
        self.assertEqual(robot_stock["first_lu_time"], "093000")
        self.assertEqual(robot_stock["limit_up_suc_rate"], 0.85)
        self.assertEqual(robot_stock["rise_rate"], 3.2)
        self.assertEqual(robot_stock["market_type"], "HS")

        # 20260115：整体 3 只，细分到机器人(2)与消费电子(1)
        day2 = result["data"]["20260115"]
        self.assertEqual(day2["overall"]["limit_up_count"], 3)
        self.assertEqual(day2["overall"]["industry_count"], 2)
        self.assertEqual(day2["overall"]["broken_limit_count"], 1)
        self.assertEqual(day2["overall"]["limit_attempt_count"], 4)
        self.assertEqual(day2["overall"]["max_board"], 3)
        self.assertEqual(day2["overall"]["phase"], "repair")
        industry_counts = {item["industry"]: item["limit_up_count"] for item in day2["industries"]}
        self.assertEqual(industry_counts, {"机器人": 2, "消费电子": 1})
        # 行业维度涨停状态统计
        status_by_industry = {item["industry"]: item["status_counts"] for item in day2["industries"]}
        self.assertEqual(status_by_industry["机器人"], {"T字板": 1, "一字板": 0, "换手板": 1})
        self.assertEqual(status_by_industry["消费电子"], {"T字板": 0, "一字板": 1, "换手板": 0})

        # top_industries 汇总
        top = {item["industry"]: item["total_limit_up_count"] for item in result["summary"]["top_industries"]}
        self.assertEqual(top["机器人"], 4)
        self.assertEqual(top["消费电子"], 1)
    def test_industry_trend_strength_snapshot_mapping_still_contains_daily_sentiment(self):
        self.addCleanup(lambda: setattr(LimitBoardDataService, "_board_snapshot_cache", None))
        LimitBoardDataService._board_snapshot_cache = [
            {
                "sector_code": "BK001.DC",
                "sector_name": "机器人",
                "idx_type": "行业板块",
                "level": "东财二级行业",
                "members": ["000001.SZ", "000002.SZ", "000006.SZ"],
            },
            {
                "sector_code": "BK002.DC",
                "sector_name": "消费电子",
                "idx_type": "行业板块",
                "level": "东财二级行业",
                "members": ["000007.SZ"],
            },
        ]
        result = self.service.get_industry_trend_strength(
            start_date="20260114",
            end_date="20260116",
            industry_mapping="dc_l2",
        )

        self.assertEqual(sorted(result["data"].keys()), ["20260114", "20260115", "20260116"])
        self.assertEqual(result["summary"]["trade_day_count"], 3)

        day1 = result["data"]["20260114"]
        self.assertEqual(day1["overall"]["limit_up_count"], 2)
        self.assertEqual(day1["overall"]["broken_limit_count"], 1)
        self.assertEqual(day1["overall"]["phase"], "repair")
        day1_industries = {item["industry"]: item for item in day1["industries"]}
        self.assertEqual(day1_industries["机器人"]["industry_pct_change"], 1.5)

        day3 = result["data"]["20260116"]
        self.assertEqual(day3["overall"]["limit_up_count"], 0)
        self.assertEqual(day3["overall"]["industry_count"], 0)
        self.assertEqual(day3["stocks"], {})
        day3_industries = {item["industry"]: item for item in day3["industries"]}
        self.assertEqual(day3_industries["机器人"]["limit_up_count"], 0)
        self.assertEqual(day3_industries["机器人"]["industry_pct_change"], -1.2)
        self.assertEqual(day3_industries["消费电子"]["limit_up_count"], 0)
        self.assertEqual(day3_industries["消费电子"]["industry_pct_change"], 0.6)
        self.assertEqual(result["source_counts"]["limit_list_d_up"], 5)
        self.assertEqual(result["source_counts"]["limit_list_d_down"], 2)
        self.assertEqual(result["source_counts"]["limit_list_d_broken"], 2)
        self.assertEqual(result["source_counts"]["limit_step"], 5)
        self.assertEqual(result["source_counts"]["dc_daily"], 5)


class BoardRpsTradeDayTests(unittest.TestCase):
    """
    组件：板块 RPS 交易日回看测试。

    功能：
    - 验证板块 RPS 的起始日期按交易日历回推，而不是按自然日回推。

    参数：
    - 无。

    返回值：
    - 无。

    事件：
    - 使用 mock 隔离交易日历、板块列表与日线行情依赖。
    """

    @patch("stock_strategy.data_tasks.dc_board_rps.get_open_trade_dates")
    def test_get_period_start_trade_date_uses_trade_calendar(self, mock_get_open_trade_dates):
        """
        功能：验证起始交易日会根据交易日历回推 period 个交易日。

        参数：
        - mock_get_open_trade_dates: 模拟交易日历查询结果。

        返回值：
        - 无。

        异常：
        - 断言失败时由测试框架抛出异常。
        """
        mock_get_open_trade_dates.return_value = [
            "20260102",
            "20260105",
            "20260106",
            "20260107",
            "20260108",
            "20260109",
        ]

        start_date = dc_board_rps._get_period_start_trade_date("20260109", 5)

        self.assertEqual(start_date, "20260102")

    @patch("stock_strategy.data_tasks.dc_board_rps.cache")
    @patch("stock_strategy.data_tasks.dc_board_rps._fetch_dc_daily_trade_date")
    @patch("stock_strategy.data_tasks.dc_board_rps._get_period_start_trade_dates")
    @patch("stock_strategy.data_tasks.dc_board_rps._get_board_map_by_date")
    def test_compute_board_rps_fetches_trade_date_snapshots_for_periods(
        self,
        mock_get_board_map_by_date,
        mock_get_period_start_trade_dates,
        mock_fetch_dc_daily_trade_date,
        mock_cache,
    ):
        """
        功能：验证 compute_board_rps 按各起始交易日与截止交易日拉取单日快照，并复用于多个周期。

        参数：
        - mock_get_board_map_by_date: 模拟板块列表。
        - mock_get_period_start_trade_dates: 模拟多周期交易日起始日计算。
        - mock_fetch_dc_daily_trade_date: 模拟单日快照行情。
        - mock_cache: 模拟缓存对象。

        返回值：
        - 无。

        异常：
        - 断言失败时由测试框架抛出异常。
        """
        mock_get_board_map_by_date.return_value = {
            "BK001": {"name": "机器人", "level": ""},
            "BK002": {"name": "算力", "level": ""},
        }
        mock_get_period_start_trade_dates.return_value = {
            5: "20260106",
            20: "20260102",
        }
        mock_fetch_dc_daily_trade_date.side_effect = [
            pd.DataFrame(
                [
                    {"ts_code": "BK001", "trade_date": "20260102", "close": 100, "pct_change": 0.0},
                    {"ts_code": "BK002", "trade_date": "20260102", "close": 100, "pct_change": 0.0},
                ]
            ),
            pd.DataFrame(
                [
                    {"ts_code": "BK001", "trade_date": "20260106", "close": 108, "pct_change": 0.0},
                    {"ts_code": "BK002", "trade_date": "20260106", "close": 102, "pct_change": 0.0},
                ]
            ),
            pd.DataFrame(
                [
                    {"ts_code": "BK001", "trade_date": "20260109", "close": 110, "pct_change": 5.0},
                    {"ts_code": "BK002", "trade_date": "20260109", "close": 105, "pct_change": 2.0},
                ]
            ),
        ]
        mock_cache.get.return_value = None

        result_df, errors = dc_board_rps.compute_board_rps(
            periods=[5, 20],
            idx_type="概念板块",
            trade_date="20260109",
        )

        self.assertEqual(errors, [])
        self.assertIsNotNone(result_df)
        mock_get_period_start_trade_dates.assert_called_once_with("20260109", [5, 20], token=None)
        self.assertEqual(
            mock_fetch_dc_daily_trade_date.call_args_list,
            [
                unittest.mock.call("20260102", idx_type="概念板块", token=None),
                unittest.mock.call("20260106", idx_type="概念板块", token=None),
                unittest.mock.call("20260109", idx_type="概念板块", token=None),
            ],
        )
        self.assertIn("RPS_5", result_df.columns)
        self.assertIn("RPS_20", result_df.columns)
        self.assertIn("pct_change", result_df.columns)
        self.assertIn("RPS_today", result_df.columns)
        result_map = result_df.set_index("ts_code")
        self.assertEqual(result_map.loc["BK001", "pct_change"], 5.0)
        self.assertEqual(result_map.loc["BK002", "pct_change"], 2.0)
        self.assertGreater(result_map.loc["BK001", "RPS_today"], result_map.loc["BK002", "RPS_today"])
        mock_cache.set.assert_called_once()

    @patch("stock_strategy.data_tasks.dc_board_rps.cache")
    @patch("stock_strategy.data_tasks.dc_board_rps._fetch_dc_daily_trade_date")
    @patch("stock_strategy.data_tasks.dc_board_rps._get_period_start_trade_dates")
    @patch("stock_strategy.data_tasks.dc_board_rps._get_recent_trade_dates")
    @patch("stock_strategy.data_tasks.dc_board_rps._get_board_map_by_date")
    @patch("stock_strategy.data_tasks.dc_board_rps._get_latest_trade_date")
    def test_compute_board_rps_falls_back_to_previous_trade_date_when_latest_snapshot_missing(
        self,
        mock_get_latest_trade_date,
        mock_get_board_map_by_date,
        mock_get_recent_trade_dates,
        mock_get_period_start_trade_dates,
        mock_fetch_dc_daily_trade_date,
        mock_cache,
    ):
        """
        功能：验证未显式传入 trade_date 时，若最新开市日无 dc_daily 快照，会自动回退到最近可用交易日。

        参数：
        - mock_get_latest_trade_date: 模拟最近开市日查询结果。
        - mock_get_board_map_by_date: 模拟板块列表查询结果。
        - mock_get_recent_trade_dates: 模拟最近交易日候选列表。
        - mock_get_period_start_trade_dates: 模拟周期起始交易日映射。
        - mock_fetch_dc_daily_trade_date: 模拟单日板块快照数据。
        - mock_cache: 模拟缓存对象。

        返回值：
        - 无。

        异常：
        - 断言失败时由测试框架抛出异常。
        """
        board_map = {
            "BK001": {"name": "机器人", "level": ""},
            "BK002": {"name": "算力", "level": ""},
        }
        mock_get_latest_trade_date.return_value = "20260109"
        mock_get_recent_trade_dates.return_value = ["20260109", "20260108"]
        mock_get_board_map_by_date.side_effect = [board_map, board_map]
        mock_get_period_start_trade_dates.return_value = {5: "20260102"}
        mock_fetch_dc_daily_trade_date.side_effect = [
            pd.DataFrame(columns=["ts_code", "trade_date", "close", "pct_change"]),
            pd.DataFrame(
                [
                    {"ts_code": "BK001", "trade_date": "20260108", "close": 110, "pct_change": 5.0},
                    {"ts_code": "BK002", "trade_date": "20260108", "close": 104, "pct_change": 1.0},
                ]
            ),
            pd.DataFrame(
                [
                    {"ts_code": "BK001", "trade_date": "20260102", "close": 100, "pct_change": 0.0},
                    {"ts_code": "BK002", "trade_date": "20260102", "close": 100, "pct_change": 0.0},
                ]
            ),
            pd.DataFrame(
                [
                    {"ts_code": "BK001", "trade_date": "20260108", "close": 110, "pct_change": 5.0},
                    {"ts_code": "BK002", "trade_date": "20260108", "close": 104, "pct_change": 1.0},
                ]
            ),
        ]
        mock_cache.get.return_value = None

        result_df, errors = dc_board_rps.compute_board_rps(
            periods=[5],
            idx_type="行业板块",
            level="东财一级行业",
            trade_date=None,
        )

        self.assertIsNotNone(result_df)
        self.assertTrue(
            any("已自动回退至最近可用交易日20260108" in error for error in errors),
            msg=f"unexpected errors: {errors}",
        )
        mock_get_period_start_trade_dates.assert_called_once_with("20260108", [5], token=None)
        self.assertEqual(result_df.attrs.get("trade_date"), "20260108")
        mock_cache.set.assert_called_once()


class DcBoardMemberRpsTests(unittest.TestCase):
    """
    组件：东财板块成分股 RPS 测试。

    功能：
    - 验证指定板块成分股 RPS 计算会先读取成分股，再按交易日快照拉取成分股日线并计算多周期 RPS。

    参数：
    - 无。

    返回值：
    - 无。

    事件：
    - 使用 mock 隔离成分股、板块名称、交易日历和日线行情依赖。
    """

    @patch("stock_strategy.data_tasks.dc_board_member_rps.cache")
    @patch("stock_strategy.data_tasks.dc_board_member_rps._fetch_stock_daily_trade_date")
    @patch("stock_strategy.data_tasks.dc_board_member_rps._get_period_start_trade_dates")
    @patch("stock_strategy.data_tasks.dc_board_member_rps._fetch_dc_board_name")
    @patch("stock_strategy.data_tasks.dc_board_member_rps._fetch_dc_board_members")
    def test_compute_dc_board_member_rps_fetches_member_snapshots_for_periods(
        self,
        mock_fetch_dc_board_members,
        mock_fetch_dc_board_name,
        mock_get_period_start_trade_dates,
        mock_fetch_stock_daily_trade_date,
        mock_cache,
    ):
        """
        功能：验证 compute_dc_board_member_rps 会按成分股集合和各交易日快照计算 RPS。

        参数：
        - mock_fetch_dc_board_members: 模拟板块成分股列表。
        - mock_fetch_dc_board_name: 模拟板块名称查询。
        - mock_get_period_start_trade_dates: 模拟多周期交易日起始日计算。
        - mock_fetch_stock_daily_trade_date: 模拟成分股日线快照。
        - mock_cache: 模拟缓存对象。

        返回值：
        - 无。

        异常：
        - 断言失败时由测试框架抛出异常。
        """
        mock_fetch_dc_board_members.return_value = pd.DataFrame(
            [
                {"trade_date": "20260109", "ts_code": "BK1462.DC", "con_code": "000001.SZ", "name": "机器人一号"},
                {"trade_date": "20260109", "ts_code": "BK1462.DC", "con_code": "000002.SZ", "name": "机器人二号"},
            ]
        )
        mock_fetch_dc_board_name.return_value = "机器人概念"
        mock_get_period_start_trade_dates.return_value = {
            5: "20260106",
            20: "20260102",
        }
        mock_fetch_stock_daily_trade_date.side_effect = [
            pd.DataFrame(
                [
                    {"ts_code": "000001.SZ", "trade_date": "20260102", "close": 10.0, "pct_change": 0.0},
                    {"ts_code": "000002.SZ", "trade_date": "20260102", "close": 10.0, "pct_change": 0.0},
                ]
            ),
            pd.DataFrame(
                [
                    {"ts_code": "000001.SZ", "trade_date": "20260106", "close": 11.0, "pct_change": 0.0},
                    {"ts_code": "000002.SZ", "trade_date": "20260106", "close": 10.2, "pct_change": 0.0},
                ]
            ),
            pd.DataFrame(
                [
                    {"ts_code": "000001.SZ", "trade_date": "20260109", "close": 12.0, "pct_change": 5.0},
                    {"ts_code": "000002.SZ", "trade_date": "20260109", "close": 10.5, "pct_change": 1.5},
                ]
            ),
        ]
        mock_cache.get.return_value = None

        result_df, meta, errors = dc_board_member_rps.compute_dc_board_member_rps(
            periods=[5, 20],
            board_ts_code="BK1462.DC",
            trade_date="20260109",
        )

        self.assertEqual(errors, [])
        self.assertIsNotNone(result_df)
        self.assertEqual(meta["board_name"], "机器人概念")
        self.assertEqual(meta["member_count"], 2)
        mock_get_period_start_trade_dates.assert_called_once_with("20260109", [5, 20], token=None)
        self.assertEqual(
            mock_fetch_stock_daily_trade_date.call_args_list,
            [
                unittest.mock.call("20260102", stock_codes=["000001.SZ", "000002.SZ"], token=None),
                unittest.mock.call("20260106", stock_codes=["000001.SZ", "000002.SZ"], token=None),
                unittest.mock.call("20260109", stock_codes=["000001.SZ", "000002.SZ"], token=None),
            ],
        )
        self.assertIn("RPS_5", result_df.columns)
        self.assertIn("RPS_20", result_df.columns)
        self.assertIn("pct_change", result_df.columns)
        self.assertIn("RPS_today", result_df.columns)
        result_map = result_df.set_index("ts_code")
        self.assertEqual(result_map.loc["000001.SZ", "pct_change"], 5.0)
        self.assertEqual(result_map.loc["000002.SZ", "pct_change"], 1.5)
        self.assertGreater(result_map.loc["000001.SZ", "RPS_5"], result_map.loc["000002.SZ", "RPS_5"])
        self.assertGreater(result_map.loc["000001.SZ", "RPS_today"], result_map.loc["000002.SZ", "RPS_today"])
        mock_cache.set.assert_called_once()


class StockRpsTests(unittest.TestCase):
    """
    组件：股票 RPS 计算测试。

    功能：
    - 验证股票 RPS 会基于 `stock_basic` 股票池和 `daily` 单日快照计算多周期收益率与 RPS。
    - 验证未显式传入 `trade_date` 时，若最新开市日缺少日线快照，会自动回退到最近可用交易日。
    """

    @patch(
        "stock_strategy.data_tasks.stock_rps._fetch_daily_basic_by_trade_date",
        return_value=pd.DataFrame(
            [
                {"ts_code": "000001.SZ", "close": 12.0, "total_mv": 1.0e11, "circ_mv": 9.0e10},
                {"ts_code": "000002.SZ", "close": 10.5, "total_mv": 8.0e10, "circ_mv": 7.0e10},
            ]
        ),
    )
    @patch("stock_strategy.data_tasks.stock_rps.cache")
    @patch("stock_strategy.data_tasks.stock_rps._fetch_daily_snapshot_by_trade_date")
    @patch("stock_strategy.data_tasks.stock_rps._get_period_start_trade_dates")
    @patch("stock_strategy.data_tasks.stock_rps._fetch_stock_basic_all_statuses")
    def test_compute_stock_rps_fetches_snapshots_for_periods(
        self,
        mock_fetch_stock_basic_all_statuses,
        mock_get_period_start_trade_dates,
        mock_fetch_daily_snapshot_by_trade_date,
        mock_cache,
        mock_fetch_daily_basic_by_trade_date,
    ):
        """
        功能：验证 `compute_stock_rps` 会按多个周期起始交易日和截止交易日拉取股票快照并计算排名。

        参数：
        - mock_fetch_stock_basic_all_statuses: 模拟股票基础信息股票池。
        - mock_get_period_start_trade_dates: 模拟多周期起始交易日映射。
        - mock_fetch_daily_snapshot_by_trade_date: 模拟股票日线快照。
        - mock_cache: 模拟缓存对象。

        返回值：
        - 无。

        异常：
        - 断言失败时由测试框架抛出异常。
        """
        mock_fetch_stock_basic_all_statuses.return_value = pd.DataFrame(
            [
                {
                    "ts_code": "000001.SZ",
                    "symbol": "000001",
                    "name": "平安银行",
                    "industry": "银行",
                    "market": "主板",
                    "list_date": "19910403",
                    "delist_date": "",
                    "list_status": "L",
                },
                {
                    "ts_code": "000002.SZ",
                    "symbol": "000002",
                    "name": "万科A",
                    "industry": "房地产",
                    "market": "主板",
                    "list_date": "19910129",
                    "delist_date": "",
                    "list_status": "L",
                },
                {
                    "ts_code": "000003.SZ",
                    "symbol": "000003",
                    "name": "未来上市",
                    "industry": "测试",
                    "market": "主板",
                    "list_date": "20260110",
                    "delist_date": "",
                    "list_status": "L",
                },
            ]
        )
        mock_get_period_start_trade_dates.return_value = {
            5: "20260106",
            20: "20260102",
        }
        mock_fetch_daily_snapshot_by_trade_date.side_effect = [
            pd.DataFrame(
                [
                    {"ts_code": "000001.SZ", "trade_date": "20260102", "close": 10.0, "pct_change": 0.0},
                    {"ts_code": "000002.SZ", "trade_date": "20260102", "close": 10.0, "pct_change": 0.0},
                ]
            ),
            pd.DataFrame(
                [
                    {"ts_code": "000001.SZ", "trade_date": "20260106", "close": 11.0, "pct_change": 0.0},
                    {"ts_code": "000002.SZ", "trade_date": "20260106", "close": 10.2, "pct_change": 0.0},
                ]
            ),
            pd.DataFrame(
                [
                    {"ts_code": "000001.SZ", "trade_date": "20260109", "close": 12.0, "pct_change": 5.0},
                    {"ts_code": "000002.SZ", "trade_date": "20260109", "close": 10.5, "pct_change": 1.5},
                ]
            ),
        ]
        mock_cache.get.return_value = None

        result_df, errors = stock_rps.compute_stock_rps(
            periods=[5, 20],
            trade_date="20260109",
        )

        self.assertEqual(errors, [])
        self.assertIsNotNone(result_df)
        self.assertEqual(
            set(result_df["ts_code"].tolist()),
            {"000001.SZ", "000002.SZ"},
        )
        mock_get_period_start_trade_dates.assert_called_once_with("20260109", [5, 20], token=None)
        self.assertEqual(
            mock_fetch_daily_snapshot_by_trade_date.call_args_list,
            [
                unittest.mock.call("20260102", token=None),
                unittest.mock.call("20260106", token=None),
                unittest.mock.call("20260109", token=None),
            ],
        )
        self.assertIn("RPS_5", result_df.columns)
        self.assertIn("RPS_20", result_df.columns)
        self.assertIn("pct_change", result_df.columns)
        self.assertIn("RPS_today", result_df.columns)
        result_map = result_df.set_index("ts_code")
        self.assertEqual(result_map.loc["000001.SZ", "pct_change"], 5.0)
        self.assertEqual(result_map.loc["000002.SZ", "pct_change"], 1.5)
        self.assertGreater(result_map.loc["000001.SZ", "RPS_5"], result_map.loc["000002.SZ", "RPS_5"])
        self.assertGreater(result_map.loc["000001.SZ", "RPS_today"], result_map.loc["000002.SZ", "RPS_today"])
        mock_cache.set.assert_called_once()

    @patch("stock_strategy.data_tasks.stock_rps._fetch_daily_basic_by_trade_date")
    @patch("stock_strategy.data_tasks.stock_rps.cache")
    @patch("stock_strategy.data_tasks.stock_rps._fetch_daily_snapshot_by_trade_date")
    @patch("stock_strategy.data_tasks.stock_rps._get_period_start_trade_dates")
    @patch("stock_strategy.data_tasks.stock_rps._get_recent_trade_dates")
    @patch("stock_strategy.data_tasks.stock_rps._fetch_stock_basic_all_statuses")
    @patch("stock_strategy.data_tasks.stock_rps._get_latest_trade_date")
    def test_compute_stock_rps_falls_back_to_previous_trade_date_when_latest_snapshot_missing(
        self,
        mock_get_latest_trade_date,
        mock_fetch_stock_basic_all_statuses,
        mock_get_recent_trade_dates,
        mock_get_period_start_trade_dates,
        mock_fetch_daily_snapshot_by_trade_date,
        mock_cache,
        mock_fetch_daily_basic_by_trade_date,
    ):
        """
        功能：验证未传 `trade_date` 时，若最新开市日无 `daily` 快照，会自动回退到最近可用交易日。

        参数：
        - mock_get_latest_trade_date: 模拟最近开市日查询结果。
        - mock_fetch_stock_basic_all_statuses: 模拟股票基础信息股票池。
        - mock_get_recent_trade_dates: 模拟最近开市日候选列表。
        - mock_get_period_start_trade_dates: 模拟多周期起始交易日映射。
        - mock_fetch_daily_snapshot_by_trade_date: 模拟股票日线快照。
        - mock_cache: 模拟缓存对象。

        返回值：
        - 无。

        异常：
        - 断言失败时由测试框架抛出异常。
        """
        mock_get_latest_trade_date.return_value = "20260109"
        mock_fetch_stock_basic_all_statuses.return_value = pd.DataFrame(
            [
                {
                    "ts_code": "000001.SZ",
                    "symbol": "000001",
                    "name": "平安银行",
                    "industry": "银行",
                    "market": "主板",
                    "list_date": "19910403",
                    "delist_date": "",
                    "list_status": "L",
                },
                {
                    "ts_code": "000002.SZ",
                    "symbol": "000002",
                    "name": "万科A",
                    "industry": "房地产",
                    "market": "主板",
                    "list_date": "19910129",
                    "delist_date": "",
                    "list_status": "L",
                },
            ]
        )
        mock_get_recent_trade_dates.return_value = ["20260109", "20260108"]
        mock_get_period_start_trade_dates.return_value = {5: "20260102"}
        mock_fetch_daily_snapshot_by_trade_date.side_effect = [
            pd.DataFrame(columns=["ts_code", "trade_date", "close", "pct_change"]),
            pd.DataFrame(
                [
                    {"ts_code": "000001.SZ", "trade_date": "20260108", "close": 11.0, "pct_change": 5.0},
                    {"ts_code": "000002.SZ", "trade_date": "20260108", "close": 10.4, "pct_change": 1.0},
                ]
            ),
            pd.DataFrame(
                [
                    {"ts_code": "000001.SZ", "trade_date": "20260102", "close": 10.0, "pct_change": 0.0},
                    {"ts_code": "000002.SZ", "trade_date": "20260102", "close": 10.0, "pct_change": 0.0},
                ]
            ),
            pd.DataFrame(
                [
                    {"ts_code": "000001.SZ", "trade_date": "20260108", "close": 11.0, "pct_change": 5.0},
                    {"ts_code": "000002.SZ", "trade_date": "20260108", "close": 10.4, "pct_change": 1.0},
                ]
            ),
        ]
        mock_cache.get.return_value = None

        result_df, errors = stock_rps.compute_stock_rps(
            periods=[5],
            trade_date=None,
        )

        self.assertIsNotNone(result_df)
        self.assertTrue(
            any("已自动回退至最近可用交易日20260108" in error for error in errors),
            msg=f"unexpected errors: {errors}",
        )
        mock_get_period_start_trade_dates.assert_called_once_with("20260108", [5], token=None)
        self.assertEqual(
            mock_fetch_daily_snapshot_by_trade_date.call_args_list,
            [
                unittest.mock.call("20260109", token=None),
                unittest.mock.call("20260108", token=None),
                unittest.mock.call("20260102", token=None),
                unittest.mock.call("20260108", token=None),
            ],
        )
        self.assertEqual(result_df.attrs.get("trade_date"), "20260108")
        mock_cache.set.assert_called_once()


class PotentialStockScreenTests(unittest.TestCase):
    """
    组件：主板潜力股票筛选测试。

    功能：
    - 验证潜力股票筛选会先按价格/流通市值缩小股票池，再基于 OHLCV 历史行情计算 RPS、突破前高、放量和均线多头形态。
    """

    @patch("stock_strategy.data_tasks.potential_stock_screen.cache")
    @patch("stock_strategy.data_tasks.potential_stock_screen._fetch_daily_ohlcv_by_trade_date")
    @patch("stock_strategy.data_tasks.potential_stock_screen._fetch_daily_basic_by_trade_date")
    @patch("stock_strategy.data_tasks.potential_stock_screen._fetch_stock_basic_all_statuses")
    @patch("stock_strategy.data_tasks.potential_stock_screen._get_recent_trade_dates")
    def test_compute_potential_stock_candidates_filters_breakout_setup(
        self,
        mock_get_recent_trade_dates,
        mock_fetch_stock_basic_all_statuses,
        mock_fetch_daily_basic_by_trade_date,
        mock_fetch_daily_ohlcv_by_trade_date,
        mock_cache,
    ):
        mock_fetch_stock_basic_all_statuses.return_value = pd.DataFrame(
            [
                {
                    "ts_code": "000001.SZ",
                    "symbol": "000001",
                    "name": "强势主板",
                    "industry": "测试行业",
                    "market": "主板",
                    "list_date": "20200101",
                    "delist_date": "",
                    "list_status": "L",
                },
                {
                    "ts_code": "000002.SZ",
                    "symbol": "000002",
                    "name": "弱势主板",
                    "industry": "测试行业",
                    "market": "主板",
                    "list_date": "20200101",
                    "delist_date": "",
                    "list_status": "L",
                },
                {
                    "ts_code": "000003.SZ",
                    "symbol": "000003",
                    "name": "高价大盘",
                    "industry": "测试行业",
                    "market": "主板",
                    "list_date": "20200101",
                    "delist_date": "",
                    "list_status": "L",
                },
            ]
        )
        mock_fetch_daily_basic_by_trade_date.return_value = pd.DataFrame(
            [
                {"ts_code": "000001.SZ", "latest_price": 14.0, "total_mv": 15000000000.0, "circ_mv": 12000000000.0},
                {"ts_code": "000002.SZ", "latest_price": 10.0, "total_mv": 9000000000.0, "circ_mv": 8000000000.0},
                {"ts_code": "000003.SZ", "latest_price": 50.0, "total_mv": 70000000000.0, "circ_mv": 60000000000.0},
            ]
        )
        mock_get_recent_trade_dates.return_value = (
            [f"202512{day:02d}" for day in range(1, 32)]
            + [f"202601{day:02d}" for day in range(1, 32)]
        )

        def fake_daily(trade_date, token=None):
            day = int(trade_date[-2:])
            strong_close = 10.0 + day * 0.1
            strong_vol = 1000.0
            if day == 31:
                strong_close = 14.0
                strong_vol = 5000.0
            return pd.DataFrame(
                [
                    {
                        "ts_code": "000001.SZ",
                        "trade_date": trade_date,
                        "open": strong_close - 0.1,
                        "high": strong_close,
                        "low": strong_close - 0.2,
                        "close": strong_close,
                        "vol": strong_vol,
                        "pct_change": 7.5 if day == 31 else 0.5,
                    },
                    {
                        "ts_code": "000002.SZ",
                        "trade_date": trade_date,
                        "open": 10.0,
                        "high": 10.2,
                        "low": 9.8,
                        "close": 10.0,
                        "vol": 1000.0,
                        "pct_change": 0.1,
                    },
                    {
                        "ts_code": "000003.SZ",
                        "trade_date": trade_date,
                        "open": 50.0,
                        "high": 51.0,
                        "low": 49.0,
                        "close": 50.0,
                        "vol": 1000.0,
                        "pct_change": 0.1,
                    },
                ]
            )

        mock_fetch_daily_ohlcv_by_trade_date.side_effect = fake_daily
        mock_cache.get.return_value = None

        result_df, errors, meta = potential_stock_screen.compute_potential_stock_candidates(
            periods=[5, 20, 60],
            trade_date="20260131",
            exchange="SSE",
            lookback_days=20,
            min_rps_20=40,
            min_rps_60=40,
            min_volume_ratio=1.3,
            max_breakout_pct=20,
            max_price=30,
            max_circ_mv=50000000000.0,
        )

        self.assertEqual(errors, [])
        self.assertIsNotNone(result_df)
        self.assertEqual(result_df["ts_code"].tolist(), ["000001.SZ"])
        self.assertTrue(result_df.iloc[0]["is_breakout"])
        self.assertTrue(result_df.iloc[0]["volume_confirmed"])
        self.assertIn("突破前高", result_df.iloc[0]["setup_tags"])
        self.assertEqual(meta["trade_date"], "20260131")
        self.assertEqual(meta["rps_total"], 3)
        self.assertEqual(meta["universe_total"], 3)
        self.assertEqual(meta["prefiltered_total"], 2)
        self.assertEqual(meta["scanned_total"], 2)
        self.assertNotIn("000003.SZ", result_df["ts_code"].tolist())
        mock_fetch_stock_basic_all_statuses.assert_called_once_with(token=None, exchange="SSE", market="主板")
        mock_cache.set.assert_called_once()


class MajorIndexRpsTests(unittest.TestCase):
    """
    组件：国内+国际大盘指数 RPS 测试。

    功能：
    - 验证 `compute_major_index_rps` 会综合国内 `index_daily` 与国际 `index_global` 行情，
      按各指数自身交易序列计算多周期收益率与 RPS。

    参数：
    - 无。

    返回值：
    - 无。

    事件：
    - 使用 mock 隔离 Tushare 行情接口与缓存依赖。
    """

    @patch("stock_strategy.data_tasks.major_index_rps.cache")
    @patch.dict(
        "stock_strategy.data_tasks.major_index_rps.DOMESTIC_LARGE_CAP_INDEXES",
        {"000001.SH": "上证综指", "399001.SZ": "深证成指"},
        clear=True,
    )
    @patch.dict(
        "stock_strategy.data_tasks.major_index_rps.GLOBAL_LARGE_CAP_INDEXES",
        {"SPX": "标普500指数", "IXIC": "纳斯达克指数"},
        clear=True,
    )
    @patch("stock_strategy.data_tasks.major_index_rps.call_tushare")
    def test_compute_major_index_rps_combines_domestic_and_global_histories(
        self,
        mock_call_tushare,
        mock_cache,
    ):
        """
        功能：验证综合指数 RPS 会同时使用国内与国际指数行情，并输出统一的多周期 RPS 结果。

        参数：
        - mock_call_tushare: 模拟 Tushare 接口返回。
        - mock_cache: 模拟缓存对象。

        返回值：
        - 无。

        异常：
        - 断言失败时由测试框架抛出异常。
        """
        mock_cache.get.return_value = None

        histories = {
            ("index_daily", "000001.SH"): [
                {"ts_code": "000001.SH", "trade_date": "20251212", "close": 100.0, "pct_chg": 0.0},
                {"ts_code": "000001.SH", "trade_date": "20251219", "close": 102.0, "pct_chg": 0.0},
                {"ts_code": "000001.SH", "trade_date": "20260102", "close": 105.0, "pct_chg": 0.0},
                {"ts_code": "000001.SH", "trade_date": "20260106", "close": 108.0, "pct_chg": 0.0},
                {"ts_code": "000001.SH", "trade_date": "20260109", "close": 110.0, "pct_chg": 5.0},
            ],
            ("index_daily", "399001.SZ"): [
                {"ts_code": "399001.SZ", "trade_date": "20251212", "close": 100.0, "pct_chg": 0.0},
                {"ts_code": "399001.SZ", "trade_date": "20251219", "close": 101.0, "pct_chg": 0.0},
                {"ts_code": "399001.SZ", "trade_date": "20260102", "close": 102.0, "pct_chg": 0.0},
                {"ts_code": "399001.SZ", "trade_date": "20260106", "close": 103.0, "pct_chg": 0.0},
                {"ts_code": "399001.SZ", "trade_date": "20260109", "close": 104.0, "pct_chg": 1.5},
            ],
            ("index_global", "SPX"): [
                {"ts_code": "SPX", "trade_date": "20251212", "close": 100.0, "pct_chg": 0.0},
                {"ts_code": "SPX", "trade_date": "20251219", "close": 103.0, "pct_chg": 0.0},
                {"ts_code": "SPX", "trade_date": "20260102", "close": 106.0, "pct_chg": 0.0},
                {"ts_code": "SPX", "trade_date": "20260106", "close": 109.0, "pct_chg": 0.0},
                {"ts_code": "SPX", "trade_date": "20260109", "close": 112.0, "pct_chg": 4.0},
            ],
            ("index_global", "IXIC"): [
                {"ts_code": "IXIC", "trade_date": "20251212", "close": 100.0, "pct_chg": 0.0},
                {"ts_code": "IXIC", "trade_date": "20251219", "close": 100.5, "pct_chg": 0.0},
                {"ts_code": "IXIC", "trade_date": "20260102", "close": 101.0, "pct_chg": 0.0},
                {"ts_code": "IXIC", "trade_date": "20260106", "close": 101.5, "pct_chg": 0.0},
                {"ts_code": "IXIC", "trade_date": "20260109", "close": 102.0, "pct_chg": 1.0},
            ],
        }

        def _side_effect(interface, params=None, fields=None, token=None, use_query=False):
            _ = (fields, token, use_query)
            params = params or {}
            records = histories.get((interface, params.get("ts_code")))
            if records is None:
                raise AssertionError(f"unexpected request: {interface}, {params}")
            return {"code": 200, "data": {"records": records}}

        mock_call_tushare.side_effect = _side_effect

        result_df, errors = major_index_rps.compute_major_index_rps(
            periods=[3, 5],
            trade_date="20260109",
        )

        self.assertEqual(errors, [])
        self.assertIsNotNone(result_df)
        self.assertEqual(result_df.attrs.get("trade_date"), "20260109")
        self.assertIn("market", result_df.columns)
        self.assertIn("source", result_df.columns)
        self.assertIn("RPS_today", result_df.columns)
        self.assertIn("RPS_3", result_df.columns)
        self.assertIn("RPS_5", result_df.columns)
        result_map = result_df.set_index("ts_code")
        self.assertEqual(result_map.loc["000001.SH", "market"], "国内")
        self.assertEqual(result_map.loc["SPX", "market"], "国际")
        self.assertEqual(result_map.loc["000001.SH", "source"], "index_daily")
        self.assertEqual(result_map.loc["SPX", "source"], "index_global")
        self.assertGreater(result_map.loc["SPX", "RPS_3"], result_map.loc["IXIC", "RPS_3"])
        self.assertGreater(result_map.loc["000001.SH", "RPS_today"], result_map.loc["399001.SZ", "RPS_today"])
        mock_cache.set.assert_called_once()

    @patch("stock_strategy.data_tasks.major_index_rps.cache")
    @patch.dict(
        "stock_strategy.data_tasks.major_index_rps.DOMESTIC_LARGE_CAP_INDEXES",
        {"000001.SH": "上证综指"},
        clear=True,
    )
    @patch.dict(
        "stock_strategy.data_tasks.major_index_rps.GLOBAL_LARGE_CAP_INDEXES",
        {"SPX": "标普500指数"},
        clear=True,
    )
    @patch("stock_strategy.data_tasks.major_index_rps.call_tushare")
    def test_compute_major_index_rps_uses_latest_available_bar_before_anchor_date(
        self,
        mock_call_tushare,
        mock_cache,
    ):
        """
        功能：验证当目标日期不是对应市场的交易日时，会自动使用该指数在目标日期之前最近的可用行情。

        参数：
        - mock_call_tushare: 模拟 Tushare 接口返回。
        - mock_cache: 模拟缓存对象。

        返回值：
        - 无。

        异常：
        - 断言失败时由测试框架抛出异常。
        """
        mock_cache.get.return_value = None

        def _side_effect(interface, params=None, fields=None, token=None, use_query=False):
            _ = (fields, token, use_query)
            params = params or {}
            if interface == "index_daily":
                return {
                    "code": 200,
                    "data": {
                        "records": [
                            {"ts_code": "000001.SH", "trade_date": "20260102", "close": 100.0, "pct_chg": 0.0},
                            {"ts_code": "000001.SH", "trade_date": "20260108", "close": 105.0, "pct_chg": 2.0},
                        ]
                    },
                }
            if interface == "index_global":
                return {
                    "code": 200,
                    "data": {
                        "records": [
                            {"ts_code": "SPX", "trade_date": "20260102", "close": 100.0, "pct_chg": 0.0},
                            {"ts_code": "SPX", "trade_date": "20260109", "close": 108.0, "pct_chg": 1.0},
                        ]
                    },
                }
            raise AssertionError(f"unexpected interface: {interface}")

        mock_call_tushare.side_effect = _side_effect

        result_df, errors = major_index_rps.compute_major_index_rps(
            periods=[1],
            trade_date="20260110",
        )

        self.assertEqual(errors, [])
        self.assertIsNotNone(result_df)
        result_map = result_df.set_index("ts_code")
        self.assertEqual(result_map.loc["000001.SH", "trade_date"], "20260108")
        self.assertEqual(result_map.loc["SPX", "trade_date"], "20260109")
        self.assertAlmostEqual(result_map.loc["000001.SH", "return_1"], 5.0)
        self.assertAlmostEqual(result_map.loc["SPX", "return_1"], 8.0)


class IndustryMABreadthStrategyTests(unittest.TestCase):
    """
    组件：行业 MA 市场宽度策略测试。

    功能：
    - 验证行业宽度改为基于 `dc_index`、`dc_member`、`stk_factor_pro` 计算后，仍能输出正确的每日行业宽度结果。

    参数：
    - 无。

    返回值：
    - 无。

    事件：
    - 使用 mock 隔离 Tushare 调用与缓存依赖。
    """

    @patch("stock_strategy.industry_ma_breadth_strategy.cache")
    @patch("stock_strategy.industry_ma_breadth_strategy.get_open_trade_dates")
    @patch("stock_strategy.industry_ma_breadth_strategy.call_tushare")
    def test_get_industry_ma_breadth_uses_precomputed_ma_fields_for_supported_windows(
        self,
        mock_call_tushare,
        mock_get_open_trade_dates,
        mock_cache,
    ):
        """
        功能：验证内置均线窗口会直接使用 `stk_factor_pro` 的预计算均线字段。

        参数：
        - mock_call_tushare: 模拟 Tushare 接口返回。
        - mock_cache: 模拟缓存对象。

        返回值：
        - 无。

        异常：
        - 断言失败时由测试框架抛出异常。
        """
        mock_cache.get.return_value = None
        mock_get_open_trade_dates.return_value = ["20260102", "20260103"]

        def _side_effect(interface, params=None, fields=None, token=None, use_query=False):
            _ = (token, use_query)
            params = params or {}
            if interface == "dc_index":
                self.assertEqual(params["idx_type"], "行业板块")
                self.assertEqual(params["trade_date"], "20260103")
                return {
                    "code": 200,
                    "data": {
                        "records": [
                            {"ts_code": "BK001.DC", "trade_date": "20260103", "name": "行业A"},
                            {"ts_code": "BK002.DC", "trade_date": "20260103", "name": "行业B"},
                        ]
                    },
                }
            if interface == "dc_member":
                self.assertEqual(params["trade_date"], "20260103")
                if params["ts_code"] == "BK001.DC":
                    return {
                        "code": 200,
                        "data": {
                            "records": [
                                {"trade_date": "20260103", "ts_code": "BK001.DC", "con_code": "000001.SZ"},
                                {"trade_date": "20260103", "ts_code": "BK001.DC", "con_code": "000002.SZ"},
                            ]
                        },
                    }
                if params["ts_code"] == "BK002.DC":
                    return {
                        "code": 200,
                        "data": {
                            "records": [
                                {"trade_date": "20260103", "ts_code": "BK002.DC", "con_code": "000003.SZ"},
                            ]
                        },
                    }
                return {
                    "code": 500,
                    "data": {"records": []},
                }
            if interface == "stk_factor_pro":
                self.assertEqual(fields, "ts_code,trade_date,close,ma_bfq_20")
                records_by_date = {
                    "20260102": [
                        {"ts_code": "000001.SZ", "trade_date": "20260102", "close": 10.0, "ma_bfq_20": 9.0},
                        {"ts_code": "000002.SZ", "trade_date": "20260102", "close": 8.0, "ma_bfq_20": 8.0},
                        {"ts_code": "000003.SZ", "trade_date": "20260102", "close": 7.0, "ma_bfq_20": 10.0},
                    ],
                    "20260103": [
                        {"ts_code": "000001.SZ", "trade_date": "20260103", "close": 11.0, "ma_bfq_20": 10.0},
                        {"ts_code": "000002.SZ", "trade_date": "20260103", "close": 9.0, "ma_bfq_20": 8.0},
                        {"ts_code": "000003.SZ", "trade_date": "20260103", "close": 11.0, "ma_bfq_20": 10.0},
                    ],
                }
                return {
                    "code": 200,
                    "data": {
                        "records": records_by_date[params["trade_date"]]
                    },
                }
            raise AssertionError(f"unexpected interface: {interface}")

        mock_call_tushare.side_effect = _side_effect
        strategy = IndustryMABreadthStrategy()

        result = strategy.get_industry_ma_breadth(
            start_date="2026-01-02",
            end_date="2026-01-03",
            ma_window=20,
        )

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 4)
        self.assertEqual(
            result,
            [
                {
                    "date": "2026-01-02",
                    "sector_code": "BK001.DC",
                    "sector_name": "行业A",
                    "count_above_ma": 1,
                    "eligible_count": 2,
                    "breadth_ratio": 0.5,
                },
                {
                    "date": "2026-01-02",
                    "sector_code": "BK002.DC",
                    "sector_name": "行业B",
                    "count_above_ma": 0,
                    "eligible_count": 1,
                    "breadth_ratio": 0.0,
                },
                {
                    "date": "2026-01-03",
                    "sector_code": "BK001.DC",
                    "sector_name": "行业A",
                    "count_above_ma": 2,
                    "eligible_count": 2,
                    "breadth_ratio": 1.0,
                },
                {
                    "date": "2026-01-03",
                    "sector_code": "BK002.DC",
                    "sector_name": "行业B",
                    "count_above_ma": 1,
                    "eligible_count": 1,
                    "breadth_ratio": 1.0,
                },
            ],
        )
        mock_cache.set.assert_called_once()

    @patch("stock_strategy.industry_ma_breadth_strategy.cache")
    @patch("stock_strategy.industry_ma_breadth_strategy.get_open_trade_dates")
    @patch("stock_strategy.industry_ma_breadth_strategy.call_tushare")
    def test_get_industry_ma_breadth_computes_rolling_ma_for_custom_window(
        self,
        mock_call_tushare,
        mock_get_open_trade_dates,
        mock_cache,
    ):
        """
        功能：验证非内置均线窗口会基于 `stk_factor_pro` 的收盘价快照本地滚动计算均线。

        参数：
        - mock_call_tushare: 模拟 Tushare 接口返回。
        - mock_cache: 模拟缓存对象。

        返回值：
        - 无。

        异常：
        - 断言失败时由测试框架抛出异常。
        """
        mock_cache.get.return_value = None
        mock_get_open_trade_dates.side_effect = [
            ["20260102", "20260105"],
            ["20251230", "20251231", "20260102", "20260105"],
        ]

        def _side_effect(interface, params=None, fields=None, token=None, use_query=False):
            _ = (token, use_query)
            params = params or {}
            if interface == "dc_index":
                return {
                    "code": 200,
                    "data": {
                        "records": [
                            {"ts_code": "BK001.DC", "trade_date": "20260105", "name": "行业A"},
                        ]
                    },
                }
            if interface == "dc_member":
                self.assertEqual(params["trade_date"], "20260105")
                self.assertEqual(params["ts_code"], "BK001.DC")
                return {
                    "code": 200,
                    "data": {
                        "records": [
                            {"trade_date": "20260105", "ts_code": "BK001.DC", "con_code": "000001.SZ"},
                            {"trade_date": "20260105", "ts_code": "BK001.DC", "con_code": "000002.SZ"},
                        ]
                    },
                }
            if interface == "stk_factor_pro":
                self.assertEqual(fields, "ts_code,trade_date,close")
                records_by_date = {
                    "20251230": [
                        {"ts_code": "000001.SZ", "trade_date": "20251230", "close": 1.0},
                        {"ts_code": "000002.SZ", "trade_date": "20251230", "close": 3.0},
                    ],
                    "20251231": [
                        {"ts_code": "000001.SZ", "trade_date": "20251231", "close": 2.0},
                        {"ts_code": "000002.SZ", "trade_date": "20251231", "close": 2.0},
                    ],
                    "20260102": [
                        {"ts_code": "000001.SZ", "trade_date": "20260102", "close": 3.0},
                        {"ts_code": "000002.SZ", "trade_date": "20260102", "close": 1.0},
                    ],
                    "20260105": [
                        {"ts_code": "000001.SZ", "trade_date": "20260105", "close": 4.0},
                        {"ts_code": "000002.SZ", "trade_date": "20260105", "close": 1.0},
                    ],
                }
                return {
                    "code": 200,
                    "data": {
                        "records": records_by_date[params["trade_date"]]
                    },
                }
            raise AssertionError(f"unexpected interface: {interface}")

        mock_call_tushare.side_effect = _side_effect
        strategy = IndustryMABreadthStrategy()

        result = strategy.get_industry_ma_breadth(
            start_date="2026-01-02",
            end_date="2026-01-05",
            ma_window=3,
        )

        self.assertIsNotNone(result)
        self.assertEqual(
            result,
            [
                {
                    "date": "2026-01-02",
                    "sector_code": "BK001.DC",
                    "sector_name": "行业A",
                    "count_above_ma": 1,
                    "eligible_count": 2,
                    "breadth_ratio": 0.5,
                },
                {
                    "date": "2026-01-05",
                    "sector_code": "BK001.DC",
                    "sector_name": "行业A",
                    "count_above_ma": 1,
                    "eligible_count": 2,
                    "breadth_ratio": 0.5,
                },
            ],
        )
        mock_cache.set.assert_called_once()

    @patch("stock_strategy.industry_ma_breadth_strategy.cache")
    @patch("stock_strategy.industry_ma_breadth_strategy.get_open_trade_dates")
    @patch("stock_strategy.industry_ma_breadth_strategy.call_tushare")
    def test_get_industry_ma_breadth_filters_by_dc_industry_level(
        self,
        mock_call_tushare,
        mock_get_open_trade_dates,
        mock_cache,
    ):
        """
        功能：验证当传入东财行业层级时，只返回指定 level 的板块宽度结果。

        参数：
        - mock_call_tushare: 模拟 Tushare 接口返回。
        - mock_cache: 模拟缓存对象。

        返回值：
        - 无。

        异常：
        - 断言失败时由测试框架抛出异常。
        """
        mock_cache.get.return_value = None
        mock_get_open_trade_dates.return_value = ["20260103"]

        def _side_effect(interface, params=None, fields=None, token=None, use_query=False):
            _ = (fields, token, use_query)
            params = params or {}
            if interface == "dc_index":
                self.assertEqual(params["idx_type"], "行业板块")
                self.assertEqual(params["trade_date"], "20260103")
                return {
                    "code": 200,
                    "data": {
                        "records": [
                            {
                                "ts_code": "BK001.DC",
                                "trade_date": "20260103",
                                "name": "一级行业A",
                                "idx_type": "行业板块",
                                "level": "东财一级行业",
                            },
                            {
                                "ts_code": "BK002.DC",
                                "trade_date": "20260103",
                                "name": "二级行业B",
                                "idx_type": "行业板块",
                                "level": "东财二级行业",
                            },
                        ]
                    },
                }
            if interface == "dc_member":
                self.assertEqual(params["trade_date"], "20260103")
                if params["ts_code"] == "BK001.DC":
                    return {
                        "code": 200,
                        "data": {
                            "records": [
                                {"trade_date": "20260103", "ts_code": "BK001.DC", "con_code": "000001.SZ"},
                            ]
                        },
                    }
                return {
                    "code": 200,
                    "data": {"records": []},
                }
            if interface == "stk_factor_pro":
                return {
                    "code": 200,
                    "data": {
                        "records": [
                            {"ts_code": "000001.SZ", "trade_date": "20260103", "close": 11.0, "ma_bfq_20": 10.0},
                            {"ts_code": "000002.SZ", "trade_date": "20260103", "close": 8.0, "ma_bfq_20": 10.0},
                        ]
                    },
                }
            raise AssertionError(f"unexpected interface: {interface}")

        mock_call_tushare.side_effect = _side_effect
        strategy = IndustryMABreadthStrategy()

        result = strategy.get_industry_ma_breadth(
            start_date="2026-01-03",
            end_date="2026-01-03",
            ma_window=20,
            idx_type="行业板块",
            level="东财一级行业",
        )

        self.assertEqual(
            result,
            [
                {
                    "date": "2026-01-03",
                    "sector_code": "BK001.DC",
                    "sector_name": "一级行业A",
                    "count_above_ma": 1,
                    "eligible_count": 1,
                    "breadth_ratio": 1.0,
                }
            ],
        )


class IndustryTurnoverStrategyTests(unittest.TestCase):
    @patch("stock_strategy.industry_turnover_strategy.cache")
    @patch("stock_strategy.industry_turnover_strategy.get_latest_trade_date")
    @patch("stock_strategy.industry_turnover_strategy.get_open_trade_dates")
    @patch("stock_strategy.industry_turnover_strategy.call_tushare")
    def test_get_industry_turnover_percentile_defaults_to_latest_trade_date(
        self,
        mock_call_tushare,
        mock_get_open_trade_dates,
        mock_get_latest_trade_date,
        mock_cache,
    ):
        """
        功能：验证未传 end_date 时，会以最新开市日作为默认截止日期。

        参数：
        - mock_call_tushare: 模拟 Tushare 接口返回。
        - mock_get_open_trade_dates: 模拟交易日历返回。
        - mock_get_latest_trade_date: 模拟最新开市日。
        - mock_cache: 模拟缓存对象。

        返回值：
        - 无。

        异常：
        - 断言失败时由测试框架抛出异常。
        """
        mock_cache.get.return_value = None
        mock_get_latest_trade_date.return_value = "20260103"
        mock_get_open_trade_dates.side_effect = [
            ["20260103"],
            ["20260103"],
        ]

        def _side_effect(interface, params=None, fields=None, token=None, use_query=False):
            _ = (fields, token, use_query)
            params = params or {}
            if interface == "dc_index":
                self.assertEqual(params["trade_date"], "20260103")
                return {
                    "code": 200,
                    "data": {
                        "records": [
                            {
                                "ts_code": "BK001.DC",
                                "trade_date": "20260103",
                                "name": "概念A",
                                "idx_type": "概念板块",
                                "level": "",
                            }
                        ]
                    },
                }
            if interface == "dc_daily":
                self.assertEqual(params["trade_date"], "20260103")
                return {
                    "code": 200,
                    "data": {
                        "records": [
                            {"ts_code": "BK001.DC", "trade_date": "20260103", "amount": 100.0},
                        ]
                    },
                }
            raise AssertionError(f"unexpected interface: {interface}")

        mock_call_tushare.side_effect = _side_effect
        strategy = IndustryTurnoverStrategy()

        result = strategy.get_industry_turnover_percentile(
            start_date="2026-01-03",
            end_date=None,
            idx_type="概念板块",
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["date"], "2026-01-03")
        mock_get_latest_trade_date.assert_called_once()
        mock_cache.set.assert_called_once()

    @patch("stock_strategy.industry_turnover_strategy.cache")
    @patch("stock_strategy.industry_turnover_strategy.get_open_trade_dates")
    @patch("stock_strategy.industry_turnover_strategy.call_tushare")
    def test_get_industry_turnover_percentile_filters_by_dc_industry_level(
        self,
        mock_call_tushare,
        mock_get_open_trade_dates,
        mock_cache,
    ):
        """
        功能：验证当传入东财行业层级时，只统计指定 level 的板块成交额结果。

        参数：
        - mock_call_tushare: 模拟 Tushare 接口返回。
        - mock_get_open_trade_dates: 模拟交易日历返回。
        - mock_cache: 模拟缓存对象。

        返回值：
        - 无。

        异常：
        - 断言失败时由测试框架抛出异常。
        """
        mock_cache.get.return_value = None
        mock_get_open_trade_dates.side_effect = [
            ["20260105", "20260104", "20260103"],
            ["20260103", "20260105"],
        ]

        def _side_effect(interface, params=None, fields=None, token=None, use_query=False):
            _ = (fields, token, use_query)
            params = params or {}
            if interface == "dc_index":
                self.assertEqual(params["idx_type"], "行业板块")
                self.assertEqual(params["trade_date"], "20260105")
                return {
                    "code": 200,
                    "data": {
                        "records": [
                            {
                                "ts_code": "BK001.DC",
                                "trade_date": "20260105",
                                "name": "一级行业A",
                                "idx_type": "行业板块",
                                "level": "东财一级行业",
                            },
                            {
                                "ts_code": "BK002.DC",
                                "trade_date": "20260105",
                                "name": "一级行业B",
                                "idx_type": "行业板块",
                                "level": "东财一级行业",
                            },
                            {
                                "ts_code": "BK003.DC",
                                "trade_date": "20260105",
                                "name": "二级行业C",
                                "idx_type": "行业板块",
                                "level": "东财二级行业",
                            },
                        ]
                    },
                }
            if interface == "dc_daily":
                trade_date = params["trade_date"]
                if trade_date == "20260105":
                    return {
                        "code": 200,
                        "data": {
                            "records": [
                                {"ts_code": "BK001.DC", "trade_date": "20260105", "amount": 100.0},
                                {"ts_code": "BK002.DC", "trade_date": "20260105", "amount": 300.0},
                                {"ts_code": "BK003.DC", "trade_date": "20260105", "amount": 900.0},
                            ]
                        },
                    }
                if trade_date == "20260103":
                    return {
                        "code": 200,
                        "data": {
                            "records": [
                                {"ts_code": "BK001.DC", "trade_date": "20260103", "amount": 200.0},
                                {"ts_code": "BK002.DC", "trade_date": "20260103", "amount": 600.0},
                                {"ts_code": "BK003.DC", "trade_date": "20260103", "amount": 1000.0},
                            ]
                        },
                    }
                raise AssertionError(f"unexpected trade_date: {trade_date}")
            raise AssertionError(f"unexpected interface: {interface}")

        mock_call_tushare.side_effect = _side_effect
        strategy = IndustryTurnoverStrategy()

        result = strategy.get_industry_turnover_percentile(
            start_date="2026-01-03",
            end_date="2026-01-05",
            idx_type="行业板块",
            level="东财一级行业",
        )

        self.assertEqual(
            result,
            [
                {
                    "date": "2026-01-03",
                    "sector_code": "BK001.DC",
                    "sector_name": "一级行业A",
                    "idx_type": "行业板块",
                    "level": "东财一级行业",
                    "amount": 200.0,
                    "daily_total_amount": 800.0,
                    "amount_ratio": 0.25,
                    "amount_percentile": 50,
                },
                {
                    "date": "2026-01-03",
                    "sector_code": "BK002.DC",
                    "sector_name": "一级行业B",
                    "idx_type": "行业板块",
                    "level": "东财一级行业",
                    "amount": 600.0,
                    "daily_total_amount": 800.0,
                    "amount_ratio": 0.75,
                    "amount_percentile": 100,
                },
                {
                    "date": "2026-01-05",
                    "sector_code": "BK001.DC",
                    "sector_name": "一级行业A",
                    "idx_type": "行业板块",
                    "level": "东财一级行业",
                    "amount": 100.0,
                    "daily_total_amount": 400.0,
                    "amount_ratio": 0.25,
                    "amount_percentile": 50,
                },
                {
                    "date": "2026-01-05",
                    "sector_code": "BK002.DC",
                    "sector_name": "一级行业B",
                    "idx_type": "行业板块",
                    "level": "东财一级行业",
                    "amount": 300.0,
                    "daily_total_amount": 400.0,
                    "amount_ratio": 0.75,
                    "amount_percentile": 100,
                },
            ],
        )
        mock_cache.set.assert_called_once()

    @patch("stock_strategy.industry_turnover_strategy.cache")
    @patch("stock_strategy.industry_turnover_strategy.get_open_trade_dates")
    @patch("stock_strategy.industry_turnover_strategy.call_tushare")
    def test_get_industry_turnover_percentile_falls_back_when_latest_dc_daily_missing(
        self,
        mock_call_tushare,
        mock_get_open_trade_dates,
        mock_cache,
    ):
        """
        功能：验证当最新开市日无 dc_daily 快照时，会自动回退到最近可用交易日。

        参数：
        - mock_call_tushare: 模拟 Tushare 接口返回。
        - mock_get_open_trade_dates: 模拟交易日历返回。
        - mock_cache: 模拟缓存对象。

        返回值：
        - 无。

        异常：
        - 断言失败时由测试框架抛出异常。
        """
        mock_cache.get.return_value = None
        mock_get_open_trade_dates.side_effect = [
            ["20260105", "20260104", "20260103"],
            ["20260103", "20260104"],
        ]

        def _side_effect(interface, params=None, fields=None, token=None, use_query=False):
            _ = (fields, token, use_query)
            params = params or {}
            if interface == "dc_index":
                return {
                    "code": 200,
                    "data": {
                        "records": [
                            {
                                "ts_code": "BK001.DC",
                                "trade_date": params["trade_date"],
                                "name": "概念A",
                                "idx_type": "概念板块",
                                "level": "",
                            },
                            {
                                "ts_code": "BK002.DC",
                                "trade_date": params["trade_date"],
                                "name": "概念B",
                                "idx_type": "概念板块",
                                "level": "",
                            },
                        ]
                    },
                }
            if interface == "dc_daily":
                trade_date = params["trade_date"]
                if trade_date == "20260105":
                    return {"code": 200, "data": {"records": []}}
                if trade_date == "20260104":
                    return {
                        "code": 200,
                        "data": {
                            "records": [
                                {"ts_code": "BK001.DC", "trade_date": "20260104", "amount": 150.0},
                                {"ts_code": "BK002.DC", "trade_date": "20260104", "amount": 450.0},
                            ]
                        },
                    }
                if trade_date == "20260103":
                    return {
                        "code": 200,
                        "data": {
                            "records": [
                                {"ts_code": "BK001.DC", "trade_date": "20260103", "amount": 100.0},
                                {"ts_code": "BK002.DC", "trade_date": "20260103", "amount": 300.0},
                            ]
                        },
                    }
                raise AssertionError(f"unexpected trade_date: {trade_date}")
            raise AssertionError(f"unexpected interface: {interface}")

        mock_call_tushare.side_effect = _side_effect
        strategy = IndustryTurnoverStrategy()

        result = strategy.get_industry_turnover_percentile(
            start_date="2026-01-03",
            end_date="2026-01-05",
            idx_type="概念板块",
        )

        self.assertEqual(len(result), 4)
        self.assertEqual(result[-1]["date"], "2026-01-04")
        self.assertEqual(result[-1]["amount_percentile"], 100)
        self.assertNotIn("2026-01-05", [item["date"] for item in result])

    @patch("stock_strategy.industry_turnover_strategy.cache")
    @patch("stock_strategy.industry_turnover_strategy.get_open_trade_dates")
    @patch("stock_strategy.industry_turnover_strategy.call_tushare")
    def test_get_industry_turnover_percentile_uses_recent_board_snapshot_for_history(
        self,
        mock_call_tushare,
        mock_get_open_trade_dates,
        mock_cache,
    ):
        """
        功能：验证历史日期缺少同日 dc_index 时，会回退使用最近可用板块清单映射历史 dc_daily。

        参数：
        - mock_call_tushare: 模拟 Tushare 接口返回。
        - mock_get_open_trade_dates: 模拟交易日历返回。
        - mock_cache: 模拟缓存对象。

        返回值：
        - 无。

        异常：
        - 断言失败时由测试框架抛出异常。
        """
        mock_cache.get.return_value = None
        mock_get_open_trade_dates.side_effect = [
            ["20200612", "20200611", "20200610"],
            ["20200610", "20200611", "20200612"],
        ]

        def _side_effect(interface, params=None, fields=None, token=None, use_query=False):
            _ = (fields, token, use_query)
            params = params or {}
            if interface == "dc_index":
                trade_date = params.get("trade_date")
                if trade_date:
                    return {"code": 200, "data": {"records": []}}
                self.assertEqual(params["idx_type"], "行业板块")
                return {
                    "code": 200,
                    "data": {
                        "records": [
                            {
                                "ts_code": "BK001.DC",
                                "trade_date": "20250530",
                                "name": "一级行业A",
                                "idx_type": "行业板块",
                                "level": "东财一级行业",
                            },
                            {
                                "ts_code": "BK002.DC",
                                "trade_date": "20250530",
                                "name": "一级行业B",
                                "idx_type": "行业板块",
                                "level": "东财一级行业",
                            },
                            {
                                "ts_code": "BK003.DC",
                                "trade_date": "20250530",
                                "name": "二级行业C",
                                "idx_type": "行业板块",
                                "level": "东财二级行业",
                            },
                        ]
                    },
                }
            if interface == "dc_daily":
                trade_date = params["trade_date"]
                if trade_date == "20200612":
                    return {
                        "code": 200,
                        "data": {
                            "records": [
                                {"ts_code": "BK001.DC", "trade_date": "20200612", "amount": 100.0},
                                {"ts_code": "BK002.DC", "trade_date": "20200612", "amount": 300.0},
                                {"ts_code": "BK099.DC", "trade_date": "20200612", "amount": 900.0},
                            ]
                        },
                    }
                if trade_date == "20200611":
                    return {
                        "code": 200,
                        "data": {
                            "records": [
                                {"ts_code": "BK001.DC", "trade_date": "20200611", "amount": 200.0},
                                {"ts_code": "BK002.DC", "trade_date": "20200611", "amount": 600.0},
                            ]
                        },
                    }
                if trade_date == "20200610":
                    return {
                        "code": 200,
                        "data": {
                            "records": [
                                {"ts_code": "BK001.DC", "trade_date": "20200610", "amount": 150.0},
                                {"ts_code": "BK002.DC", "trade_date": "20200610", "amount": 450.0},
                            ]
                        },
                    }
                raise AssertionError(f"unexpected trade_date: {trade_date}")
            raise AssertionError(f"unexpected interface: {interface}")

        mock_call_tushare.side_effect = _side_effect
        strategy = IndustryTurnoverStrategy()

        result = strategy.get_industry_turnover_percentile(
            start_date="2020-06-10",
            end_date="2020-06-12",
            idx_type="行业板块",
            level="东财一级行业",
        )

        self.assertEqual(len(result), 6)
        self.assertEqual(result[0]["date"], "2020-06-10")
        self.assertEqual(result[-1]["date"], "2020-06-12")
        self.assertEqual(
            {item["sector_code"] for item in result},
            {"BK001.DC", "BK002.DC"},
        )
        self.assertEqual(result[-1]["daily_total_amount"], 400.0)
        self.assertEqual(result[-1]["amount_percentile"], 100)
