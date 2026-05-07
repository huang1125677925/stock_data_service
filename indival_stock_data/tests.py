from django.test import TestCase
from unittest.mock import patch, MagicMock
import pandas as pd
from django.core.cache import cache
from .services import individual_stock_service
from .models import IndividualStock


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
