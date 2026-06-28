from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import RequestFactory, TestCase

from industry_stock_data.services import IndustrySectorService
from industry_stock_data.views import get_industry_fund_flow_data


class IndustrySectorServiceTestCase(TestCase):
    """行业板块服务测试。"""

    def setUp(self):
        """
        初始化测试依赖。

        参数：
            无。

        返回值：
            无。

        异常：
            无。
        """
        cache.clear()
        self.service = IndustrySectorService()

    @patch("common.tushare_proxy.call_tushare")
    @patch("common.tushare_industry.get_open_trade_dates")
    def test_get_industry_fund_flow_data_uses_latest_dc_index_snapshot(
        self,
        mock_get_open_trade_dates,
        mock_call_tushare,
    ):
        """
        验证行业资金流接口基于最新交易日板块快照过滤目标板块。

        参数：
            mock_get_open_trade_dates: 交易日历桩对象。
            mock_call_tushare: Tushare 调用桩对象。

        返回值：
            无。

        异常：
            无。断言失败时由测试框架抛出异常。
        """
        mock_get_open_trade_dates.return_value = ["20260625", "20260626"]

        def side_effect(interface, params=None, fields=None, use_query=False, **kwargs):
            if interface == "dc_index":
                return {
                    "code": 200,
                    "data": {
                        "records": [
                            {
                                "ts_code": "BK1001",
                                "trade_date": "20260626",
                                "name": "半导体",
                                "idx_type": "行业板块",
                                "level": "东财一级行业",
                            },
                            {
                                "ts_code": "BK1002",
                                "trade_date": "20260626",
                                "name": "软件开发",
                                "idx_type": "行业板块",
                                "level": "东财二级行业",
                            },
                        ]
                    },
                }
            if interface == "moneyflow_ind_dc":
                if params["trade_date"] == "20260625":
                    return {
                        "code": 200,
                        "data": {
                            "records": [
                                {
                                    "ts_code": "BK1001",
                                    "trade_date": "20260625",
                                    "name": "半导体",
                                    "net_amount": 10,
                                    "net_amount_rate": 1,
                                    "buy_elg_amount": 20,
                                    "buy_elg_amount_rate": 2,
                                    "buy_lg_amount": 30,
                                    "buy_lg_amount_rate": 3,
                                    "buy_md_amount": -5,
                                    "buy_md_amount_rate": -0.5,
                                    "buy_sm_amount": -8,
                                    "buy_sm_amount_rate": -0.8,
                                },
                                {
                                    "ts_code": "BK9999",
                                    "trade_date": "20260625",
                                    "name": "无关板块",
                                    "net_amount": 999,
                                    "net_amount_rate": 9,
                                    "buy_elg_amount": 0,
                                    "buy_elg_amount_rate": 0,
                                    "buy_lg_amount": 0,
                                    "buy_lg_amount_rate": 0,
                                    "buy_md_amount": 0,
                                    "buy_md_amount_rate": 0,
                                    "buy_sm_amount": 0,
                                    "buy_sm_amount_rate": 0,
                                },
                            ]
                        },
                    }
                return {
                    "code": 200,
                    "data": {
                        "records": [
                            {
                                "ts_code": "BK1001",
                                "trade_date": "20260626",
                                "name": "半导体",
                                "net_amount": 15,
                                "net_amount_rate": 1.5,
                                "buy_elg_amount": 25,
                                "buy_elg_amount_rate": 2.5,
                                "buy_lg_amount": 35,
                                "buy_lg_amount_rate": 3.5,
                                "buy_md_amount": -6,
                                "buy_md_amount_rate": -0.6,
                                "buy_sm_amount": -9,
                                "buy_sm_amount_rate": -0.9,
                            }
                        ]
                    },
                }
            raise AssertionError(f"unexpected interface: {interface}")

        mock_call_tushare.side_effect = side_effect

        result = self.service.get_industry_fund_flow_data(
            start_date="2026-06-25",
            end_date="2026-06-26",
            weekly_flag=False,
            idx_type="行业板块",
            level="东财一级行业",
        )

        self.assertEqual(result["dates"], ["2026-06-25", "2026-06-26"])
        self.assertEqual(result["swCodeNames"], [{"indexCode": "BK1001", "indexName": "半导体"}])
        self.assertEqual(list(result["congestions"].keys()), ["BK1001"])
        self.assertEqual(result["congestions"]["BK1001"][0]["total_net_inflow_amount"], 47.0)
        self.assertEqual(result["congestions"]["BK1001"][1]["total_net_inflow_ratio"], 6.0)

        dc_index_calls = [
            item for item in mock_call_tushare.call_args_list if item.args and item.args[0] == "dc_index"
        ]
        self.assertEqual(len(dc_index_calls), 1)
        self.assertEqual(dc_index_calls[0].kwargs["params"]["trade_date"], "20260626")


class IndustryFundFlowViewTestCase(TestCase):
    """行业资金流接口视图测试。"""

    def setUp(self):
        """
        初始化测试依赖。

        参数：
            无。

        返回值：
            无。

        异常：
            无。
        """
        self.factory = RequestFactory()

    @patch("industry_stock_data.views.industry_sector_service.get_industry_fund_flow_data")
    def test_get_industry_fund_flow_data_returns_400_when_level_invalid(self, mock_get_data: Mock):
        """
        验证非法 level 参数返回 400。

        参数：
            mock_get_data: 服务层桩对象。

        返回值：
            无。

        异常：
            无。断言失败时由测试框架抛出异常。
        """
        mock_get_data.side_effect = ValueError("level参数错误，仅支持：东财一级行业、东财二级行业、东财三级行业")
        request = self.factory.get(
            "/django/api/stock/industry/fund-flow/data/",
            {"idx_type": "行业板块", "level": "非法层级"},
        )

        response = get_industry_fund_flow_data(request)

        self.assertEqual(response.status_code, 400)
        self.assertIn("level参数错误", response.content.decode("utf-8"))
