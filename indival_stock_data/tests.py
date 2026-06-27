from django.test import TestCase
from unittest.mock import patch, MagicMock
import pandas as pd
from django.core.cache import cache
from .services import individual_stock_service
from .models import IndividualStock
from common.validators import normalize_stock_symbol, validate_stock_symbol


class IndividualStockServiceTest(TestCase):
    """个股数据服务测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 清除缓存
        cache.clear()
        
        # 创建测试数据
        self.test_stock = IndividualStock.objects.create(
            code='000001',
            name='平安银行',
            pe_ratio=10.5,
            pb_ratio=1.2,
            total_market_cap=2000.0,
            circulating_market_cap=1500.0
        )
    
    def tearDown(self):
        """测试后清理"""
        # 清除缓存
        cache.clear()
        
        # 清除测试数据
        IndividualStock.objects.all().delete()
    
    def test_get_stock_list_from_cache(self):
        """测试从缓存获取股票列表"""
        # 准备缓存数据
        test_data = [{'code': '000001', 'name': '平安银行'}]
        cache.set('individual_stock_list', test_data, 300)
        
        # 调用方法
        result = individual_stock_service.get_stock_list()
        
        # 验证结果
        self.assertEqual(result, test_data)
    
    def test_get_stock_list_from_db(self):
        """测试从数据库获取股票列表"""
        # 确保缓存为空
        cache.delete('individual_stock_list')
        
        # 调用方法
        result = individual_stock_service.get_stock_list()
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['code'], '000001')
        self.assertEqual(result[0]['name'], '平安银行')
        
        # 验证缓存是否已设置
        cached_data = cache.get('individual_stock_list')
        self.assertIsNotNone(cached_data)
    
    @patch('akshare.stock_sh_a_spot_em')
    def test_get_stock_list_from_akshare(self, mock_akshare):
        """测试从akshare获取股票列表"""
        # 确保缓存为空
        cache.delete('individual_stock_list')
        
        # 清除数据库数据
        IndividualStock.objects.all().delete()
        
        # 模拟akshare返回数据
        mock_df = pd.DataFrame({
            '代码': ['000001', '000002'],
            '名称': ['平安银行', '万科A'],
            '市盈率-动态': [10.5, 12.3],
            '市净率': [1.2, 1.5],
            '总市值': [2000.0, 3000.0],
            '流通市值': [1500.0, 2500.0]
        })
        mock_akshare.return_value = mock_df
        
        # 调用方法
        result = individual_stock_service.get_stock_list()
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['code'], '000001')
        self.assertEqual(result[0]['name'], '平安银行')
        
        # 验证数据库是否已保存
        self.assertEqual(IndividualStock.objects.count(), 2)
        
        # 验证缓存是否已设置
        cached_data = cache.get('individual_stock_list')
        self.assertIsNotNone(cached_data)
    
    @patch('akshare.stock_sh_a_spot_em')
    def test_get_stock_list_akshare_error(self, mock_akshare):
        """测试akshare获取股票列表失败"""
        # 确保缓存为空
        cache.delete('individual_stock_list')
        
        # 清除数据库数据
        IndividualStock.objects.all().delete()
        
        # 模拟akshare抛出异常
        mock_akshare.side_effect = Exception('测试异常')
        
        # 调用方法
        result = individual_stock_service.get_stock_list()
        
        # 验证结果
        self.assertIsNone(result)

    @patch('indival_stock_data.services.call_tushare')
    @patch('indival_stock_data.services.call_tushare_pro_bar')
    def test_get_stock_history_with_ts_code_uses_pro_bar(self, mock_call_tushare_pro_bar, mock_call_tushare):
        """测试带市场后缀的历史行情查询会走 Tushare pro_bar。"""
        mock_call_tushare_pro_bar.return_value = {
            'code': 200,
            'data': {
                'records': [
                    {
                        'ts_code': '600909.SH',
                        'trade_date': '20250627',
                        'open': 10.0,
                        'high': 10.5,
                        'low': 9.8,
                        'close': 10.2,
                        'pre_close': 9.9,
                        'change': 0.3,
                        'pct_chg': 3.03,
                        'vol': 123456,
                        'amount': 789012.0,
                    }
                ]
            }
        }

        result = individual_stock_service.get_stock_history(
            '600909.SH',
            '20250627',
            '20260627',
            'qfq',
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['stock_code'], '600909')
        self.assertEqual(result[0]['ts_code'], '600909.SH')
        self.assertEqual(result[0]['date'], '2025-06-27')
        mock_call_tushare_pro_bar.assert_called_once_with(
            params={
                'ts_code': '600909.SH',
                'asset': 'E',
                'freq': 'D',
                'adj': 'qfq',
                'start_date': '20250627',
                'end_date': '20260627',
            },
            fields='ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount',
        )
        mock_call_tushare.assert_not_called()


class StockSymbolValidatorTest(TestCase):
    """股票代码校验与规范化测试类"""

    def test_validate_stock_symbol_supports_ts_code_when_enabled(self):
        """测试在显式允许时支持 Tushare ts_code 格式。"""
        self.assertFalse(validate_stock_symbol('600909.SH'))
        self.assertTrue(validate_stock_symbol('600909.SH', allow_market_suffix=True))

    def test_normalize_stock_symbol_supports_multiple_formats(self):
        """测试股票代码规范化支持 plain、前缀式和 ts_code 格式。"""
        self.assertEqual(normalize_stock_symbol('600909', output_format='ts'), '600909.SH')
        self.assertEqual(normalize_stock_symbol('sh600909', output_format='ts'), '600909.SH')
        self.assertEqual(normalize_stock_symbol('600909.SH', output_format='plain'), '600909')


class StockHistoryViewTest(TestCase):
    """股票历史行情接口测试类"""

    @patch('indival_stock_data.views.individual_stock_service.get_stock_history')
    def test_history_endpoint_accepts_ts_code(self, mock_get_stock_history):
        """测试历史行情接口支持带市场后缀的股票代码。"""
        mock_get_stock_history.return_value = []

        response = self.client.get(
            '/django/api/individual_stock/stocks/600909.SH/history/',
            {
                'start_date': '20250627',
                'end_date': '20260627',
                'adjust': 'qfq',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['code'], 200)
        mock_get_stock_history.assert_called_once_with(
            '600909.SH',
            '20250627',
            '20260627',
            'qfq',
            'daily',
        )
