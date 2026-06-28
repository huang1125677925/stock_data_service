import unittest
from unittest.mock import patch

import pandas as pd

from .auction_selection_strategy import AuctionSelectionStrategyService
from .industry_ma_breadth_strategy import IndustryMABreadthStrategy
from .industry_turnover_strategy import IndustryTurnoverStrategy
from .limit_board_service import LimitBoardDataService
from scheduled_tasks.stock_data_query_tasks import dc_board_rps
from scheduled_tasks.stock_data_query_tasks import dc_board_member_rps
from scheduled_tasks.stock_data_query_tasks import major_index_rps


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
        is_range_query = bool(params.get("start_date") and params.get("end_date"))
        limit_type = params.get("limit_type")
        if interface == "limit_list_d" and limit_type == "U":
            records = [
                {"trade_date": "20260114", "ts_code": "000001.SZ", "name": "一板股", "amount": 1000, "fd_amount": 200, "open_times": 0, "limit_times": 1},
                {"trade_date": "20260114", "ts_code": "000002.SZ", "name": "二板股", "amount": 2000, "fd_amount": 500, "open_times": 1, "limit_times": 2},
            ]
            if is_range_query:
                records.extend([
                    {"trade_date": "20260115", "ts_code": "000001.SZ", "name": "一板股", "amount": 1500, "fd_amount": 300, "open_times": 0, "limit_times": 2},
                    {"trade_date": "20260115", "ts_code": "000006.SZ", "name": "新启动", "amount": 1200, "fd_amount": 240, "open_times": 0, "limit_times": 1},
                    {"trade_date": "20260115", "ts_code": "000007.SZ", "name": "高标股", "amount": 2200, "fd_amount": 600, "open_times": 0, "limit_times": 3},
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
        if interface == "limit_list_ths":
            return [{"trade_date": "20260114", "ts_code": "000004.SZ", "name": "炸板股", "lu_desc": "题材催化", "open_num": 2}]
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

    def test_daily_sentiment_returns_summary_and_distribution(self):
        result = self.service.get_daily_sentiment(trade_date="20260114")

        self.assertEqual(result["summary"]["limit_up_count"], 2)
        self.assertEqual(result["summary"]["broken_limit_count"], 1)
        self.assertEqual(result["summary"]["max_board"], 3)
        self.assertEqual(result["top_concepts"][0]["name"], "机器人")

    def test_theme_ladder_groups_limit_up_stocks_by_concept(self):
        result = self.service.get_theme_ladder(trade_date="20260114")

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["themes"][0]["concept_name"], "机器人")
        self.assertEqual(result["themes"][0]["core_stocks"][0]["ts_code"], "000001.SZ")

    def test_break_reseal_analysis_splits_resealed_and_failed(self):
        result = self.service.get_break_reseal_analysis(trade_date="20260114")

        self.assertEqual(result["summary"]["resealed_count"], 1)
        self.assertEqual(result["summary"]["failed_break_count"], 1)
        self.assertEqual(result["failed"][0]["reason"], "题材催化")

    def test_hot_money_review_matches_limit_up_stock(self):
        result = self.service.get_hot_money_review(trade_date="20260114")

        self.assertEqual(result["summary"]["top_limit_up_count"], 1)
        self.assertEqual(result["records"][0]["hot_money_count"], 1)
        self.assertEqual(result["active_hot_money"][0]["hm_name"], "测试游资")

    def test_trend_analysis_returns_sentiment_concept_and_lifecycle_trends(self):
        result = self.service.get_trend_analysis(start_date="20260114", end_date="20260115", top_n=10)

        self.assertEqual(result["summary"]["trade_day_count"], 2)
        self.assertEqual(len(result["sentiment_series"]), 2)
        self.assertEqual(result["sentiment_series"][1]["changes"]["limit_up_count"], 1)
        self.assertEqual(result["concept_trends"][0]["concept_name"], "机器人")
        lifecycle_by_code = {item["ts_code"]: item for item in result["stock_lifecycles"]}
        self.assertEqual(lifecycle_by_code["000001.SZ"]["lifecycle_stage"], "二板确认")


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

    @patch("scheduled_tasks.stock_data_query_tasks.dc_board_rps.get_open_trade_dates")
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

    @patch("scheduled_tasks.stock_data_query_tasks.dc_board_rps.cache")
    @patch("scheduled_tasks.stock_data_query_tasks.dc_board_rps._fetch_dc_daily_trade_date")
    @patch("scheduled_tasks.stock_data_query_tasks.dc_board_rps._get_period_start_trade_dates")
    @patch("scheduled_tasks.stock_data_query_tasks.dc_board_rps._get_board_map_by_date")
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

    @patch("scheduled_tasks.stock_data_query_tasks.dc_board_rps.cache")
    @patch("scheduled_tasks.stock_data_query_tasks.dc_board_rps._fetch_dc_daily_trade_date")
    @patch("scheduled_tasks.stock_data_query_tasks.dc_board_rps._get_period_start_trade_dates")
    @patch("scheduled_tasks.stock_data_query_tasks.dc_board_rps._get_recent_trade_dates")
    @patch("scheduled_tasks.stock_data_query_tasks.dc_board_rps._get_board_map_by_date")
    @patch("scheduled_tasks.stock_data_query_tasks.dc_board_rps._get_latest_trade_date")
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

    @patch("scheduled_tasks.stock_data_query_tasks.dc_board_member_rps.cache")
    @patch("scheduled_tasks.stock_data_query_tasks.dc_board_member_rps._fetch_stock_daily_trade_date")
    @patch("scheduled_tasks.stock_data_query_tasks.dc_board_member_rps._get_period_start_trade_dates")
    @patch("scheduled_tasks.stock_data_query_tasks.dc_board_member_rps._fetch_dc_board_name")
    @patch("scheduled_tasks.stock_data_query_tasks.dc_board_member_rps._fetch_dc_board_members")
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

    @patch("scheduled_tasks.stock_data_query_tasks.major_index_rps.cache")
    @patch.dict(
        "scheduled_tasks.stock_data_query_tasks.major_index_rps.DOMESTIC_LARGE_CAP_INDEXES",
        {"000001.SH": "上证综指", "399001.SZ": "深证成指"},
        clear=True,
    )
    @patch.dict(
        "scheduled_tasks.stock_data_query_tasks.major_index_rps.GLOBAL_LARGE_CAP_INDEXES",
        {"SPX": "标普500指数", "IXIC": "纳斯达克指数"},
        clear=True,
    )
    @patch("scheduled_tasks.stock_data_query_tasks.major_index_rps.call_tushare")
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

    @patch("scheduled_tasks.stock_data_query_tasks.major_index_rps.cache")
    @patch.dict(
        "scheduled_tasks.stock_data_query_tasks.major_index_rps.DOMESTIC_LARGE_CAP_INDEXES",
        {"000001.SH": "上证综指"},
        clear=True,
    )
    @patch.dict(
        "scheduled_tasks.stock_data_query_tasks.major_index_rps.GLOBAL_LARGE_CAP_INDEXES",
        {"SPX": "标普500指数"},
        clear=True,
    )
    @patch("scheduled_tasks.stock_data_query_tasks.major_index_rps.call_tushare")
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
