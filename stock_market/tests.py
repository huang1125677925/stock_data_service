from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient


class StockMarketFundFlowTrendViewTests(TestCase):
    """
    大盘资金流趋势接口测试。

    功能：验证区间趋势接口的成功响应、区间变化摘要计算和参数校验逻辑。
    参数：
        无。
    返回值：无，使用断言校验接口输出。
    事件：通过 Django 测试客户端发起接口请求。
    """

    def setUp(self):
        """
        初始化测试客户端。

        参数:
            无。

        返回值:
            无。

        异常情况:
            无。
        """
        self.client = APIClient()
        self.url = '/django/api/market/fund-flow/trend/'

    @patch('stock_market.views.call_tushare')
    def test_fund_flow_trend_returns_range_records_and_summary(self, mock_call_tushare):
        """
        验证区间趋势接口返回升序记录和变化摘要。

        参数:
            mock_call_tushare (Mock): 被 patch 的 Tushare 调用函数。

        返回值:
            无。

        异常情况:
            AssertionError: 当接口返回结构或计算结果不符合预期时抛出异常。
        """
        mock_call_tushare.return_value = {
            'code': 200,
            'message': 'success',
            'data': {
                'interface': 'moneyflow_mkt_dc',
                'count': 2,
                'records': [
                    {
                        'trade_date': '20260630',
                        'close_sh': 3450.0,
                        'pct_change_sh': 1.2,
                        'close_sz': 10200.0,
                        'pct_change_sz': 1.5,
                        'net_amount': 150000000.0,
                        'net_amount_rate': 2.1,
                        'buy_elg_amount': 30000000.0,
                        'buy_elg_amount_rate': 0.8,
                        'buy_lg_amount': 20000000.0,
                        'buy_lg_amount_rate': 0.5,
                        'buy_md_amount': -10000000.0,
                        'buy_md_amount_rate': -0.3,
                        'buy_sm_amount': -5000000.0,
                        'buy_sm_amount_rate': -0.1,
                    },
                    {
                        'trade_date': '20260627',
                        'close_sh': 3400.0,
                        'pct_change_sh': 0.5,
                        'close_sz': 10000.0,
                        'pct_change_sz': 0.8,
                        'net_amount': 100000000.0,
                        'net_amount_rate': 1.1,
                        'buy_elg_amount': 25000000.0,
                        'buy_elg_amount_rate': 0.6,
                        'buy_lg_amount': 18000000.0,
                        'buy_lg_amount_rate': 0.4,
                        'buy_md_amount': -8000000.0,
                        'buy_md_amount_rate': -0.2,
                        'buy_sm_amount': -4000000.0,
                        'buy_sm_amount_rate': -0.1,
                    },
                ],
            },
        }

        response = self.client.get(self.url, {'start_date': '2026-06-27', 'end_date': '2026-06-30'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['data']['interface'], 'moneyflow_mkt_dc')
        self.assertEqual(response.data['data']['count'], 2)
        self.assertEqual(response.data['data']['records'][0]['trade_date'], '20260627')
        self.assertEqual(response.data['data']['records'][1]['net_amount_change'], 50000000.0)
        self.assertEqual(response.data['data']['records'][1]['close_sh_change'], 50.0)
        self.assertEqual(response.data['data']['summary']['net_amount_change'], 50000000.0)
        self.assertEqual(response.data['data']['summary']['shanghai_close_change'], 50.0)
        self.assertEqual(response.data['data']['summary']['shenzhen_close_change'], 200.0)

    def test_fund_flow_trend_rejects_invalid_date_range(self):
        """
        验证开始日期晚于结束日期时返回参数错误。

        参数:
            无。

        返回值:
            无。

        异常情况:
            AssertionError: 当接口没有按预期返回错误响应时抛出异常。
        """
        response = self.client.get(self.url, {'start_date': '2026-06-30', 'end_date': '2026-06-27'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 400)
        self.assertIn('开始日期不能晚于结束日期', response.data['message'])
