#!/usr/bin/env python3
"""
Django股票数据服务
基于akshare库获取股票数据
"""

import logging
import json
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from django.db import models
from .models import StockInfo, StockRealtime, MarketSummary, IndustrySector, IndustrySectorDaily, IndustrySectorFundFlow
from common.validators import validate_stock_symbol
from indival_stock_data.models import IndividualStock


logger = logging.getLogger(__name__)
DC_INDUSTRY_LEVELS = {"东财一级行业", "东财二级行业", "东财三级行业"}
DC_CONTENT_TYPE_MAP = {
    "行业板块": "行业",
    "概念板块": "概念",
    "地域板块": "地域",
}

class StockDataService:
    """股票数据服务类"""
    
    def __init__(self):
        self.cache_timeout = getattr(settings, 'STOCK_CACHE_TIMEOUT', 300)  # 缓存5分钟
        self.request_timeout = getattr(settings, 'STOCK_REQUEST_TIMEOUT', 30)
        self.max_retries = getattr(settings, 'STOCK_MAX_RETRIES', 3)
        
        logger.info(f"股票数据服务初始化: cache_timeout={self.cache_timeout}s")
    
    def get_realtime_stocks(self, market='sh') -> Optional[List[Dict]]:
        """
        获取实时股票数据
        
        Args:
            market: 市场代码 ('sh', 'sz', 'all')
        
        Returns:
            股票数据列表
        """
        cache_key = f'realtime_stocks_{market}'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存获取{market}市场实时数据")
            return cached_data
        
        try:
            # 尝试从数据库获取最新数据
            db_stocks = self._get_stocks_from_db(market)
            if db_stocks:
                # 缓存数据库获取的数据
                cache.set(cache_key, db_stocks, self.cache_timeout)
                logger.info(f"从数据库获取{market}市场{len(db_stocks)}只股票数据")
                return db_stocks
            
            # 数据库没有数据，从akshare获取
            logger.info(f"数据库无{market}市场数据，从akshare获取")
            if market == 'sh':
                df = ak.stock_zh_a_spot_em()
                # 过滤上证股票（代码以60开头）
                df = df[df['代码'].str.startswith('60')]
            elif market == 'sz':
                df = ak.stock_zh_a_spot_em()
                # 过滤深证股票（代码以00或30开头）
                df = df[df['代码'].str.startswith(('00', '30'))]
            else:
                df = ak.stock_zh_a_spot_em()
            
            if df is None or df.empty:
                logger.warning(f"获取{market}市场数据为空")
                return None
            
            # 转换数据格式
            stocks = []
            for _, row in df.iterrows():
                stock_data = {
                    'code': str(row['代码']),
                    'name': str(row['名称']),
                    'latest_price': float(row['最新价']) if pd.notna(row['最新价']) else 0.0,
                    'change_percent': float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0.0,
                    'change_amount': float(row['涨跌额']) if pd.notna(row['涨跌额']) else 0.0,
                    'volume': int(row['成交量']) if pd.notna(row['成交量']) else 0,
                    'amount': float(row['成交额']) if pd.notna(row['成交额']) else 0.0,
                    'amplitude': float(row['振幅']) if pd.notna(row['振幅']) else 0.0,
                    'high': float(row['最高']) if pd.notna(row['最高']) else 0.0,
                    'low': float(row['最低']) if pd.notna(row['最低']) else 0.0,
                    'open_price': float(row['今开']) if pd.notna(row['今开']) else 0.0,
                    'close_price': float(row['昨收']) if pd.notna(row['昨收']) else 0.0,
                    'volume_ratio': float(row['量比']) if pd.notna(row['量比']) else 0.0,
                    'turnover_rate': float(row['换手率']) if pd.notna(row['换手率']) else 0.0,
                    'pe_ratio': float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else 0.0,
                    'pb_ratio': float(row['市净率']) if pd.notna(row['市净率']) else 0.0,
                    'total_market_cap': float(row['总市值']) if pd.notna(row['总市值']) else 0.0,
                    'circulation_market_cap': float(row['流通市值']) if pd.notna(row['流通市值']) else 0.0,
                    'timestamp': datetime.now().isoformat()
                }
                stocks.append(stock_data)
            
            # 将数据保存到数据库
            self._save_stocks_to_db(stocks)
            
            # 缓存数据
            cache.set(cache_key, stocks, self.cache_timeout)
            logger.info(f"获取{market}市场{len(stocks)}只股票数据并保存到数据库")
            
            return stocks
            
        except Exception as e:
            logger.error(f"获取{market}市场实时数据失败: {str(e)}")
            return None
    
    def get_stock_detail(self, stock_code: str) -> Optional[Dict]:
        """
        获取股票详细信息
        
        Args:
            stock_code: 股票代码
        
        Returns:
            股票详细信息
        """
        if not validate_stock_symbol(stock_code):
            logger.warning(f"无效的股票代码: {stock_code}")
            return None
        
        cache_key = f'stock_detail_{stock_code}'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存获取股票{stock_code}详细信息")
            return cached_data
        
        try:
            # 获取股票基本信息
            info_df = ak.stock_individual_info_em(symbol=stock_code)
            
            if info_df is None or info_df.empty:
                logger.warning(f"无法获取股票{stock_code}的基本信息")
                return None
            
            # 转换为字典
            info_dict = {}
            for _, row in info_df.iterrows():
                item = str(row['item']).strip()
                value = str(row['value']).strip()
                info_dict[item] = value
            
            # 获取实时行情
            realtime_stocks = self.get_realtime_stocks('all')
            realtime_data = None
            
            if realtime_stocks:
                for stock in realtime_stocks:
                    if stock['code'] == stock_code:
                        realtime_data = stock
                        break
            
            # 构建详细信息
            detail = {
                'code': stock_code,
                'name': info_dict.get('股票简称', ''),
                'industry': info_dict.get('行业', ''),
                'list_date': info_dict.get('上市时间', ''),
                'total_shares': self._safe_float(info_dict.get('总股本', '0')),
                'circulating_shares': self._safe_float(info_dict.get('流通股', '0')),
                'realtime': realtime_data,
                'timestamp': datetime.now().isoformat()
            }
            
            # 缓存数据
            cache.set(cache_key, detail, self.cache_timeout)
            
            return detail
            
        except Exception as e:
            logger.error(f"获取股票{stock_code}详细信息失败: {str(e)}")
            return None
    
    def filter_stocks(self, filters: Dict) -> Optional[List[Dict]]:
        """
        根据条件过滤股票
        
        Args:
            filters: 过滤条件字典
        
        Returns:
            过滤后的股票列表
        """
        try:
            # 获取所有股票数据
            all_stocks = self.get_realtime_stocks('all')
            if not all_stocks:
                return None
            
            filtered_stocks = all_stocks
            
            # 应用过滤条件
            if 'market' in filters:
                market = filters['market']
                if market == 'sh':
                    filtered_stocks = [s for s in filtered_stocks if s['code'].startswith('60')]
                elif market == 'sz':
                    filtered_stocks = [s for s in filtered_stocks if s['code'].startswith(('00', '30'))]
            
            if 'min_price' in filters:
                min_price = float(filters['min_price'])
                filtered_stocks = [s for s in filtered_stocks if s['latest_price'] >= min_price]
            
            if 'max_price' in filters:
                max_price = float(filters['max_price'])
                filtered_stocks = [s for s in filtered_stocks if s['latest_price'] <= max_price]
            
            if 'min_change' in filters:
                min_change = float(filters['min_change'])
                filtered_stocks = [s for s in filtered_stocks if s['change_percent'] >= min_change]
            
            if 'max_change' in filters:
                max_change = float(filters['max_change'])
                filtered_stocks = [s for s in filtered_stocks if s['change_percent'] <= max_change]
            
            if 'min_volume' in filters:
                min_volume = int(filters['min_volume'])
                filtered_stocks = [s for s in filtered_stocks if s['volume'] >= min_volume]
            
            # 排序
            sort_by = filters.get('sort_by', 'change_percent')
            reverse = filters.get('order', 'desc') == 'desc'
            
            if sort_by in ['latest_price', 'change_percent', 'change_amount', 'volume', 'amount']:
                filtered_stocks.sort(key=lambda x: x[sort_by], reverse=reverse)
            
            # 分页
            limit = int(filters.get('limit', 100))
            offset = int(filters.get('offset', 0))
            
            return filtered_stocks[offset:offset + limit]
            
        except Exception as e:
            logger.error(f"过滤股票失败: {str(e)}")
            return None
    
    def get_market_summary(self) -> Optional[Dict]:
        """
        获取市场概况
        
        Returns:
            市场概况数据
        """
        cache_key = 'market_summary'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info("从缓存获取市场概况")
            return cached_data
        
        try:
            # 获取所有股票数据
            all_stocks = self.get_realtime_stocks('all')
            if not all_stocks:
                return None
            
            # 计算市场统计
            total_count = len(all_stocks)
            up_count = len([s for s in all_stocks if s['change_percent'] > 0])
            down_count = len([s for s in all_stocks if s['change_percent'] < 0])
            flat_count = total_count - up_count - down_count
            
            # 计算平均值
            avg_change = sum(s['change_percent'] for s in all_stocks) / total_count if total_count > 0 else 0
            total_volume = sum(s['volume'] for s in all_stocks)
            total_amount = sum(s['amount'] for s in all_stocks)
            
            # 找出涨跌幅前10
            top_gainers = sorted(all_stocks, key=lambda x: x['change_percent'], reverse=True)[:10]
            top_losers = sorted(all_stocks, key=lambda x: x['change_percent'])[:10]
            
            summary = {
                'total_count': total_count,
                'up_count': up_count,
                'down_count': down_count,
                'flat_count': flat_count,
                'up_ratio': round(up_count / total_count * 100, 2) if total_count > 0 else 0,
                'avg_change': round(avg_change, 2),
                'total_volume': total_volume,
                'total_amount': total_amount,
                'top_gainers': top_gainers,
                'top_losers': top_losers,
                'timestamp': datetime.now().isoformat()
            }
            
            # 缓存数据
            cache.set(cache_key, summary, self.cache_timeout)
            
            return summary
            
        except Exception as e:
            logger.error(f"获取市场概况失败: {str(e)}")
            return None
    
    def _get_stocks_from_db(self, market='sh') -> Optional[List[Dict]]:
        """
        从数据库获取最新股票数据
        
        Args:
            market: 市场代码 ('sh', 'sz', 'all')
            
        Returns:
            股票数据列表，如果没有数据则返回None
        """
        try:
            # 获取最新的数据时间
            latest_record = StockRealtime.objects.order_by('-timestamp').first()
            if not latest_record:
                logger.info("数据库中没有股票实时数据")
                return None
                
            # 获取最近10分钟内的数据，确保数据新鲜度
            time_threshold = datetime.now() - timedelta(minutes=10)
            if latest_record.timestamp < time_threshold:
                logger.info("数据库中的股票数据已过期")
                return None
                
            # 根据市场过滤
            queryset = StockRealtime.objects.filter(timestamp=latest_record.timestamp)
            if market == 'sh':
                queryset = queryset.filter(code__startswith='60')
            elif market == 'sz':
                queryset = queryset.filter(models.Q(code__startswith='00') | models.Q(code__startswith='30'))
                
            # 如果没有数据，返回None
            if not queryset.exists():
                logger.info(f"数据库中没有{market}市场的股票数据")
                return None
                
            # 转换为字典列表
            stocks = [stock.to_dict() for stock in queryset]
            logger.info(f"从数据库获取到{len(stocks)}条{market}市场股票数据")
            return stocks
            
        except Exception as e:
            logger.error(f"从数据库获取股票数据失败: {str(e)}")
            return None
    
    def _save_stocks_to_db(self, stocks: List[Dict]) -> None:
        """
        将股票数据保存到数据库
        
        Args:
            stocks: 股票数据列表
        """
        if not stocks:
            return
            
        try:
            # 批量创建对象
            stock_objects = []
            for stock in stocks:
                stock_obj = StockRealtime(
                    code=stock['code'],
                    name=stock['name'],
                    latest_price=stock['latest_price'],
                    change_percent=stock['change_percent'],
                    change_amount=stock['change_amount'],
                    volume=stock['volume'],
                    amount=stock['amount'],
                    amplitude=stock['amplitude'],
                    high=stock['high'],
                    low=stock['low'],
                    open_price=stock['open_price'],
                    close_price=stock['close_price'],
                    turnover_rate=stock['turnover_rate'],
                    pe_ratio=stock['pe_ratio'],
                    pb_ratio=stock['pb_ratio'],
                    market_cap=stock.get('total_market_cap', 0),
                    circulation_market_cap=stock.get('circulation_market_cap', 0),
                )
                stock_objects.append(stock_obj)
                
            # 批量保存
            if stock_objects:
                StockRealtime.objects.bulk_create(stock_objects)
                logger.info(f"成功保存{len(stock_objects)}条股票数据到数据库")
                
        except Exception as e:
            logger.error(f"保存股票数据到数据库失败: {str(e)}")
    
    def _safe_float(self, value: str) -> float:
        """
        安全转换为浮点数
        
        Args:
            value: 字符串值
        
        Returns:
            浮点数
        """
        try:
            return float(str(value).replace(',', '').replace('万', '0000').replace('亿', '00000000'))
        except (ValueError, AttributeError):
            return 0.0

    def get_hot_stocks(self, limit: int = 10) -> Optional[List[Dict]]:
        """
        获取热门股票（按成交额排序）
        
        Args:
            limit: 返回数量限制
            
        Returns:
            热门股票列表
        """
        cache_key = f'hot_stocks_{limit}'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存获取热门股票数据")
            return cached_data
        
        try:
            # 获取所有股票数据
            all_stocks = self.get_realtime_stocks('all')
            if not all_stocks:
                return None
            
            # 按成交额排序
            hot_stocks = sorted(all_stocks, key=lambda x: x['amount'], reverse=True)[:limit]
            
            # 缓存数据
            cache.set(cache_key, hot_stocks, self.cache_timeout)
            
            return hot_stocks
            
        except Exception as e:
            logger.error(f"获取热门股票失败: {str(e)}")
            return None
    
    def get_low_turnover_stocks(self, limit: int = 10) -> Optional[List[Dict]]:
        """
        获取低换手率股票
        
        Args:
            limit: 返回数量限制
            
        Returns:
            低换手率股票列表
        """
        cache_key = f'low_turnover_stocks_{limit}'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存获取低换手率股票数据")
            return cached_data
        
        try:
            # 获取所有股票数据
            all_stocks = self.get_realtime_stocks('all')
            if not all_stocks:
                return None
            
            # 过滤掉换手率为0的股票（可能是停牌）
            valid_stocks = [s for s in all_stocks if s['turnover_rate'] > 0]
            
            # 按换手率排序（从低到高）
            low_turnover_stocks = sorted(valid_stocks, key=lambda x: x['turnover_rate'])[:limit]
            
            # 缓存数据
            cache.set(cache_key, low_turnover_stocks, self.cache_timeout)
            
            return low_turnover_stocks
            
        except Exception as e:
            logger.error(f"获取低换手率股票失败: {str(e)}")
            return None
    
    def get_stock_type(self, stock_code: str) -> Optional[Dict]:
        """
        获取股票类型信息
        
        Args:
            stock_code: 股票代码
            
        Returns:
            股票类型信息
        """
        if not validate_stock_symbol(stock_code):
            logger.warning(f"无效的股票代码: {stock_code}")
            return None
        
        cache_key = f'stock_type_{stock_code}'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存获取股票{stock_code}类型信息")
            return cached_data
        
        try:
            # 从数据库获取
            stock_info = StockInfo.objects.filter(code=stock_code).first()
            if stock_info:
                type_info = stock_info.to_dict()
                cache.set(cache_key, type_info, self.cache_timeout)
                return type_info
            
            # 从akshare获取
            info_df = ak.stock_individual_info_em(symbol=stock_code)
            
            if info_df is None or info_df.empty:
                logger.warning(f"无法获取股票{stock_code}的类型信息")
                return None
            
            # 创建字典映射
            info_dict = {}
            for _, row in info_df.iterrows():
                item = str(row['item']).strip()
                value = str(row['value']).strip()
                info_dict[item] = value
            
            # 构建类型信息
            type_info = {
                'code': stock_code,
                'name': info_dict.get('股票简称', ''),
                'industry': info_dict.get('行业', ''),
                'list_date': info_dict.get('上市时间', ''),
                'total_shares': self._safe_float(info_dict.get('总股本', '0')),
                'circulating_shares': self._safe_float(info_dict.get('流通股', '0')),
                'timestamp': datetime.now().isoformat()
            }
            
            # 保存到数据库
            try:
                StockInfo.objects.update_or_create(
                    code=stock_code,
                    defaults={
                        'name': type_info['name'],
                        'industry': type_info['industry'],
                        'total_shares': type_info['total_shares'],
                        'circulating_shares': type_info['circulating_shares'],
                        'list_date': datetime.strptime(type_info['list_date'], '%Y%m%d').date() if type_info['list_date'] else None
                    }
                )
            except Exception as db_error:
                logger.error(f"保存股票{stock_code}类型信息到数据库失败: {str(db_error)}")
            
            # 缓存数据
            cache.set(cache_key, type_info, self.cache_timeout)
            
            return type_info
            
        except Exception as e:
            logger.error(f"获取股票{stock_code}类型信息失败: {str(e)}")
            return None
    
    def get_stock_value_em(self, stock_code: str) -> Optional[Dict]:
        """
        获取股票估值数据
        
        Args:
            stock_code: 股票代码
            
        Returns:
            股票估值数据
        """
        if not validate_stock_symbol(stock_code):
            logger.warning(f"无效的股票代码: {stock_code}")
            return None
        
        cache_key = f'stock_value_em_{stock_code}'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存获取股票{stock_code}估值数据")
            return cached_data
        
        try:
            # 从akshare获取
            value_df = ak.stock_value_em(symbol=stock_code)
            
            if value_df is None or value_df.empty:
                logger.warning(f"无法获取股票{stock_code}的估值数据")
                return None
            
            # 转换为字典
            value_data = json.loads(value_df.to_json(orient="records", force_ascii=False))
            
            # 添加时间戳
            result = {
                'code': stock_code,
                'data': value_data,
                'timestamp': datetime.now().isoformat()
            }
            
            # 缓存数据
            cache.set(cache_key, result, self.cache_timeout)
            
            return result
            
        except Exception as e:
            logger.error(f"获取股票{stock_code}估值数据失败: {str(e)}")
            return None
    
    def get_stock_individual_fund_flow(self, stock_code: str) -> Optional[Dict]:
        """
        获取股票资金流向数据
        
        Args:
            stock_code: 股票代码
            
        Returns:
            股票资金流向数据
        """
        if not validate_stock_symbol(stock_code):
            logger.warning(f"无效的股票代码: {stock_code}")
            return None
        
        cache_key = f'stock_fund_flow_{stock_code}'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存获取股票{stock_code}资金流向数据")
            return cached_data
        
        try:
            # 从akshare获取
            flow_df = ak.stock_individual_fund_flow(stock=stock_code)
            
            if flow_df is None or flow_df.empty:
                logger.warning(f"无法获取股票{stock_code}的资金流向数据")
                return None
            
            # 转换为字典
            flow_data = json.loads(flow_df.to_json(orient="records", force_ascii=False))
            
            # 添加时间戳
            result = {
                'code': stock_code,
                'data': flow_data,
                'timestamp': datetime.now().isoformat()
            }
            
            # 缓存数据
            cache.set(cache_key, result, self.cache_timeout)
            
            return result
            
        except Exception as e:
            logger.error(f"获取股票{stock_code}资金流向数据失败: {str(e)}")
            return None
    
    def get_stock_history(self, stock_code: str, period: str = 'daily', start_date: str = None, end_date: str = None) -> Optional[Dict]:
        """
        获取股票历史数据
        
        Args:
            stock_code: 股票代码
            period: 周期 ('daily', 'weekly', 'monthly')
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            股票历史数据
        """
        if not validate_stock_symbol(stock_code):
            logger.warning(f"无效的股票代码: {stock_code}")
            return None
        
        # 处理日期参数
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        cache_key = f'stock_history_{stock_code}_{period}_{start_date}_{end_date}'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存获取股票{stock_code}历史数据")
            return cached_data
        
        try:
            # 从akshare获取
            history_df = ak.stock_zh_a_hist(symbol=stock_code, period=period, start_date=start_date, end_date=end_date)
            
            if history_df is None or history_df.empty:
                logger.warning(f"无法获取股票{stock_code}的历史数据")
                return None
            
            # 转换为字典
            history_data = json.loads(history_df.to_json(orient="records", force_ascii=False))
            
            # 添加时间戳
            result = {
                'code': stock_code,
                'period': period,
                'start_date': start_date,
                'end_date': end_date,
                'data': history_data,
                'timestamp': datetime.now().isoformat()
            }
            
            # 缓存数据
            cache.set(cache_key, result, self.cache_timeout)
            
            return result
            
        except Exception as e:
            logger.error(f"获取股票{stock_code}历史数据失败: {str(e)}")
            return None
    
    def get_stock_account_statistics(self) -> Optional[List[Dict]]:
        """
        获取股票账户统计数据
        
        Returns:
            股票账户统计数据
        """
        cache_key = 'stock_account_statistics'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info("从缓存获取股票账户统计数据")
            return cached_data
        
        try:
            # 从akshare获取
            stats_df = ak.stock_account_statistics_em()
            
            if stats_df is None or stats_df.empty:
                logger.warning("无法获取股票账户统计数据")
                return None
            
            # 转换日期格式
            stats_df['date'] = pd.to_datetime(stats_df['数据日期']).dt.strftime('%Y-%m')
            
            # 转换为字典
            stats_data = json.loads(stats_df.to_json(orient="records", force_ascii=False))
            
            # 缓存数据
            cache.set(cache_key, stats_data, self.cache_timeout)
            
            return stats_data
            
        except Exception as e:
            logger.error(f"获取股票账户统计数据失败: {str(e)}")
            return None
    
    def save_stock_account_statistics(self, data: List[Dict]) -> bool:
        """
        保存股票账户统计数据
        
        Args:
            data: 股票账户统计数据
            
        Returns:
            是否保存成功
        """
        if not data:
            return False
            
        try:
            # 保存到缓存
            cache.set('stock_account_statistics', data, self.cache_timeout)
            return True
            
        except Exception as e:
            logger.error(f"保存股票账户统计数据失败: {str(e)}")
            return False
    
    def get_stock_market_activity(self) -> Optional[List[Dict]]:
        """
        获取股票市场活跃度数据
        
        Returns:
            股票市场活跃度数据
        """
        cache_key = 'stock_market_activity'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info("从缓存获取股票市场活跃度数据")
            return cached_data
        
        try:
            # 从akshare获取
            activity_df = ak.stock_market_activity_legu()
            
            if activity_df is None or activity_df.empty:
                logger.warning("无法获取股票市场活跃度数据")
                return None
            
            # 转换日期格式
            activity_df['date'] = pd.to_datetime(activity_df['数据日期']).dt.strftime('%Y-%m')
            
            # 转换为字典
            activity_data = json.loads(activity_df.to_json(orient="records", force_ascii=False))
            
            # 缓存数据
            cache.set(cache_key, activity_data, self.cache_timeout)
            
            return activity_data
            
        except Exception as e:
            logger.error(f"获取股票市场活跃度数据失败: {str(e)}")
            return None
    
    def save_stock_market_activity(self, data: List[Dict]) -> bool:
        """
        保存股票市场活跃度数据
        
        Args:
            data: 股票市场活跃度数据
            
        Returns:
            是否保存成功
        """
        if not data:
            return False
            
        try:
            # 保存到缓存
            cache.set('stock_market_activity', data, self.cache_timeout)
            return True
            
        except Exception as e:
            logger.error(f"保存股票市场活跃度数据失败: {str(e)}")
            return False
    
    def get_stock_types_batch(self, stock_codes: List[str]) -> Optional[List[Dict]]:
        """
        批量获取股票类型信息
        
        Args:
            stock_codes: 股票代码列表
            
        Returns:
            股票类型信息列表
        """
        if not stock_codes:
            return None
            
        try:
            result = []
            for code in stock_codes:
                type_info = self.get_stock_type(code)
                if type_info:
                    result.append(type_info)
            
            return result if result else None
            
        except Exception as e:
            logger.error(f"批量获取股票类型信息失败: {str(e)}")
            return None
    
    def get_all_industries(self) -> Optional[List[Dict]]:
        """
        获取所有行业分类
        
        Returns:
            行业分类列表
        """
        cache_key = 'all_industries'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info("从缓存获取行业分类数据")
            return cached_data
        
        try:
            # 从数据库获取所有行业
            industries = StockInfo.objects.values('industry').distinct()
            industry_list = []
            
            for industry_dict in industries:
                industry = industry_dict['industry']
                if not industry:
                    continue
                    
                # 获取该行业的股票数量
                count = StockInfo.objects.filter(industry=industry).count()
                
                # 获取该行业的前10只股票
                stocks = StockInfo.objects.filter(industry=industry)[:10]
                stock_list = [stock.to_dict() for stock in stocks]
                
                industry_list.append({
                    'industry': industry,
                    'count': count,
                    'stocks': stock_list
                })
            
            # 如果数据库中没有足够的行业数据，从akshare获取
            if len(industry_list) < 10:
                # 获取所有股票数据
                all_stocks = self.get_realtime_stocks('all')
                if all_stocks:
                    # 遍历所有股票，获取行业信息
                    for stock in all_stocks:
                        code = stock['code']
                        # 获取股票类型信息（包含行业）
                        self.get_stock_type(code)
                    
                    # 重新从数据库获取行业信息
                    industries = StockInfo.objects.values('industry').distinct()
                    industry_list = []
                    
                    for industry_dict in industries:
                        industry = industry_dict['industry']
                        if not industry:
                            continue
                            
                        # 获取该行业的股票数量
                        count = StockInfo.objects.filter(industry=industry).count()
                        
                        # 获取该行业的前10只股票
                        stocks = StockInfo.objects.filter(industry=industry)[:10]
                        stock_list = [stock.to_dict() for stock in stocks]
                        
                        industry_list.append({
                            'industry': industry,
                            'count': count,
                            'stocks': stock_list
                        })
            
            # 按股票数量排序
            industry_list.sort(key=lambda x: x['count'], reverse=True)
            
            # 缓存数据
            cache.set(cache_key, industry_list, self.cache_timeout)
            
            return industry_list
            
        except Exception as e:
            logger.error(f"获取行业分类失败: {str(e)}")
            return None

    def get_stock_type_info(self, stock_code: str) -> Optional[Dict]:
        """
        获取股票类型信息
        
        Args:
            stock_code: 股票代码
            
        Returns:
            股票类型信息
        """
        # 直接调用 get_stock_type 方法，保持功能一致性
        return self.get_stock_type(stock_code)

class IndustryStatsService:
    """
    行业统计数据服务类
    基于IndividualStock模型数据进行行业维度的统计分析
    """
    
    def __init__(self):
        self.cache_timeout = getattr(settings, 'STOCK_CACHE_TIMEOUT', 300)  # 缓存5分钟
        logger.info("行业统计数据服务初始化")
    
    def get_industry_statistics(self, industry_name: str = None) -> Optional[Dict]:
        """
        获取行业统计数据
        
        Args:
            industry_name: 行业名称，如果为None则返回所有行业统计
        
        Returns:
            行业统计数据字典
        """
        cache_key = f'industry_stats_{industry_name or "all"}'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存获取行业统计数据: {industry_name or '全部行业'}")
            return cached_data
        
        try:
            from indival_stock_data.models import IndividualStock
            from django.db.models import Avg, Sum, Count, Max, Min
            from datetime import datetime, date
            
            # 构建查询集
            queryset = IndividualStock.objects.all()
            if industry_name:
                queryset = queryset.filter(industry=industry_name)
            
            # 过滤掉没有行业信息的股票
            queryset = queryset.filter(industry__isnull=False).exclude(industry='')
            
            if not queryset.exists():
                logger.warning(f"没有找到行业数据: {industry_name}")
                return None
            
            # 按行业分组统计
            industry_stats = queryset.values('industry').annotate(
                # 股票数量
                stock_count=Count('id'),
                
                # 市值统计（总数）
                total_market_cap_sum=Sum('total_market_cap'),
                circulating_market_cap_sum=Sum('circulating_market_cap'),
                
                # 价格统计（平均值）
                avg_latest_price=Avg('latest_price'),
                avg_change_percent=Avg('change_percent'),
                avg_change_amount=Avg('change_amount'),
                
                # 成交量成交额统计（总数）
                total_volume=Sum('volume'),
                total_amount=Sum('amount'),
                
                # 比率统计（平均值）
                avg_amplitude=Avg('amplitude'),
                avg_turnover_rate=Avg('turnover_rate'),
                avg_pe_ratio=Avg('pe_ratio'),
                avg_pb_ratio=Avg('pb_ratio'),
                avg_volume_ratio=Avg('volume_ratio'),
                avg_price_change_speed=Avg('price_change_speed'),
                avg_change_5min=Avg('change_5min'),
                avg_change_60d=Avg('change_60d'),
                avg_change_ytd=Avg('change_ytd'),
                
                # 价格区间统计
                max_high=Max('high'),
                min_low=Min('low'),
                avg_open_price=Avg('open_price'),
                avg_close_price=Avg('close_price'),
                
                # 股本统计（总数）
                total_shares_sum=Sum('total_shares'),
                circulating_shares_sum=Sum('circulating_shares'),
            ).order_by('-total_market_cap_sum')
            
            # 计算平均上市年数
            current_date = date.today()
            for stat in industry_stats:
                industry_stocks = queryset.filter(industry=stat['industry'])
                
                # 计算平均上市年数
                listed_stocks = industry_stocks.filter(list_date__isnull=False)
                if listed_stocks.exists():
                    total_years = 0
                    count = 0
                    for stock in listed_stocks:
                        if stock.list_date:
                            years = (current_date - stock.list_date).days / 365.25
                            total_years += years
                            count += 1
                    stat['avg_listing_years'] = round(total_years / count, 2) if count > 0 else 0
                else:
                    stat['avg_listing_years'] = 0
                
                # 格式化数值
                stat['total_market_cap_sum'] = float(stat['total_market_cap_sum']) if stat['total_market_cap_sum'] else 0
                stat['circulating_market_cap_sum'] = float(stat['circulating_market_cap_sum']) if stat['circulating_market_cap_sum'] else 0
                stat['avg_latest_price'] = round(float(stat['avg_latest_price']), 3) if stat['avg_latest_price'] else 0
                stat['avg_change_percent'] = round(float(stat['avg_change_percent']), 3) if stat['avg_change_percent'] else 0
                stat['avg_change_amount'] = round(float(stat['avg_change_amount']), 3) if stat['avg_change_amount'] else 0
                stat['total_volume'] = stat['total_volume'] if stat['total_volume'] else 0
                stat['total_amount'] = float(stat['total_amount']) if stat['total_amount'] else 0
                stat['avg_amplitude'] = round(float(stat['avg_amplitude']), 3) if stat['avg_amplitude'] else 0
                stat['avg_turnover_rate'] = round(float(stat['avg_turnover_rate']), 3) if stat['avg_turnover_rate'] else 0
                stat['avg_pe_ratio'] = round(float(stat['avg_pe_ratio']), 3) if stat['avg_pe_ratio'] else 0
                stat['avg_pb_ratio'] = round(float(stat['avg_pb_ratio']), 3) if stat['avg_pb_ratio'] else 0
                stat['avg_volume_ratio'] = round(float(stat['avg_volume_ratio']), 3) if stat['avg_volume_ratio'] else 0
                stat['avg_price_change_speed'] = round(float(stat['avg_price_change_speed']), 3) if stat['avg_price_change_speed'] else 0
                stat['avg_change_5min'] = round(float(stat['avg_change_5min']), 3) if stat['avg_change_5min'] else 0
                stat['avg_change_60d'] = round(float(stat['avg_change_60d']), 3) if stat['avg_change_60d'] else 0
                stat['avg_change_ytd'] = round(float(stat['avg_change_ytd']), 3) if stat['avg_change_ytd'] else 0
                stat['max_high'] = float(stat['max_high']) if stat['max_high'] else 0
                stat['min_low'] = float(stat['min_low']) if stat['min_low'] else 0
                stat['avg_open_price'] = round(float(stat['avg_open_price']), 3) if stat['avg_open_price'] else 0
                stat['avg_close_price'] = round(float(stat['avg_close_price']), 3) if stat['avg_close_price'] else 0
                stat['total_shares_sum'] = stat['total_shares_sum'] if stat['total_shares_sum'] else 0
                stat['circulating_shares_sum'] = stat['circulating_shares_sum'] if stat['circulating_shares_sum'] else 0
            
            result = {
                'industries': list(industry_stats),
                'total_industries': len(industry_stats),
                'timestamp': datetime.now().isoformat()
            }
            
            # # 如果查询特定行业，只返回该行业数据
            # if industry_name and industry_stats:
            #     result = {
            #         'industry': list(industry_stats),
            #         'timestamp': datetime.now().isoformat()
            #     }
            
            # 缓存数据
            cache.set(cache_key, result, self.cache_timeout)
            logger.info(f"获取行业统计数据成功: {industry_name or '全部行业'}")
            
            return result
            
        except Exception as e:
            logger.error(f"获取行业统计数据失败: {str(e)}")
            return None
    
    def get_industry_ranking(self, sort_by: str = 'total_market_cap_sum', order: str = 'desc', limit: int = 20) -> Optional[List[Dict]]:
        """
        获取行业排名数据
        
        Args:
            sort_by: 排序字段
            order: 排序方向 ('asc', 'desc')
            limit: 返回数量限制
        
        Returns:
            行业排名列表
        """
        cache_key = f'industry_ranking_{sort_by}_{order}_{limit}'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存获取行业排名数据")
            return cached_data
        
        try:
            # 获取所有行业统计数据
            all_stats = self.get_industry_statistics()
            if not all_stats or 'industries' not in all_stats:
                return None
            
            industries = all_stats['industries']
            
            # 验证排序字段
            valid_sort_fields = [
                'stock_count', 'total_market_cap_sum', 'circulating_market_cap_sum',
                'avg_latest_price', 'avg_change_percent', 'total_volume', 'total_amount',
                'avg_amplitude', 'avg_turnover_rate', 'avg_pe_ratio', 'avg_pb_ratio',
                'avg_listing_years'
            ]
            
            if sort_by not in valid_sort_fields:
                sort_by = 'total_market_cap_sum'
            
            # 排序
            reverse = order == 'desc'
            industries.sort(key=lambda x: x.get(sort_by, 0) or 0, reverse=reverse)
            
            # 添加排名
            for i, industry in enumerate(industries[:limit], 1):
                industry['rank'] = i
            
            result = industries[:limit]
            
            # 缓存数据
            cache.set(cache_key, result, self.cache_timeout)
            logger.info(f"获取行业排名数据成功，排序字段: {sort_by}")
            
            return result
            
        except Exception as e:
            logger.error(f"获取行业排名数据失败: {str(e)}")
            return None
    
    def get_industry_comparison(self, industries: List[str]) -> Optional[Dict]:
        """
        获取多个行业对比数据
        
        Args:
            industries: 行业名称列表
        
        Returns:
            行业对比数据
        """
        if not industries or len(industries) < 2:
            logger.warning("行业对比需要至少2个行业")
            return None
        
        cache_key = f'industry_comparison_{"_".join(sorted(industries))}'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存获取行业对比数据")
            return cached_data
        
        try:
            comparison_data = []
            
            for industry in industries:
                industry_stat = self.get_industry_statistics(industry)
                if industry_stat and 'industry' in industry_stat:
                    comparison_data.append(industry_stat['industry'])
            
            if not comparison_data:
                logger.warning("没有找到有效的行业对比数据")
                return None
            
            result = {
                'industries': comparison_data,
                'comparison_count': len(comparison_data),
                'timestamp': datetime.now().isoformat()
            }
            
            # 缓存数据
            cache.set(cache_key, result, self.cache_timeout)
            logger.info(f"获取行业对比数据成功，对比行业数: {len(comparison_data)}")
            
            return result
            
        except Exception as e:
            logger.error(f"获取行业对比数据失败: {str(e)}")
            return None

# 创建服务实例
industry_stats_service = IndustryStatsService()

class IndustrySectorService:
    """行业板块数据服务类"""
    
    def __init__(self):
        self.cache_timeout = getattr(settings, 'STOCK_CACHE_TIMEOUT', 300)  # 缓存5分钟
        self.request_timeout = getattr(settings, 'STOCK_REQUEST_TIMEOUT', 30)
        self.max_retries = getattr(settings, 'STOCK_MAX_RETRIES', 3)
        
        logger.info(f"行业板块数据服务初始化: cache_timeout={self.cache_timeout}s")

    def _normalize_trade_date(self, date_str: Optional[str]) -> str:
        """
        标准化交易日字符串。

        参数：
            date_str: 输入日期，支持 YYYY-MM-DD 或 YYYYMMDD。

        返回值：
            去掉分隔符后的 YYYYMMDD 字符串；空值时返回空字符串。

        异常：
            无。内部仅做字符串清洗。
        """
        value = str(date_str or "").strip()
        if not value:
            return ""
        return value.replace("-", "")

    def _display_trade_date(self, trade_date: str) -> str:
        """
        将交易日转换为接口展示格式。

        参数：
            trade_date: 交易日，格式 YYYYMMDD 或 YYYY-MM-DD。

        返回值：
            YYYY-MM-DD 格式的日期字符串。

        异常：
            无。无法识别时返回原始字符串。
        """
        normalized = self._normalize_trade_date(trade_date)
        if len(normalized) == 8:
            return f"{normalized[:4]}-{normalized[4:6]}-{normalized[6:8]}"
        return str(trade_date or "")

    def _get_default_fund_flow_dates(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
        weekly_flag: bool,
    ) -> Tuple[str, str]:
        """
        生成行业资金流接口的默认日期范围。

        参数：
            start_date: 开始日期，格式 YYYY-MM-DD。
            end_date: 结束日期，格式 YYYY-MM-DD。
            weekly_flag: 是否按周聚合。

        返回值：
            标准化后的开始日期和结束日期元组，格式均为 YYYY-MM-DD。

        异常：
            无。默认值由当前时间推导。
        """
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            delta = timedelta(weeks=20) if weekly_flag else timedelta(days=30)
            start_date = (datetime.now() - delta).strftime('%Y-%m-%d')
        return start_date, end_date

    def _get_trade_dates(self, start_date: str, end_date: str) -> List[str]:
        """
        获取指定自然日区间内的实际交易日列表。

        参数：
            start_date: 开始日期，格式 YYYY-MM-DD。
            end_date: 结束日期，格式 YYYY-MM-DD。

        返回值：
            交易日列表，格式 YYYYMMDD。

        异常：
            无。底层异常向上抛出，由调用方统一处理。
        """
        from common.tushare_industry import get_open_trade_dates

        return get_open_trade_dates(
            self._normalize_trade_date(start_date),
            self._normalize_trade_date(end_date),
        )

    def _fetch_dc_index_rows(self, trade_date: str, idx_type: Optional[str] = None) -> List[Dict]:
        """
        拉取指定交易日的东方财富板块列表。

        参数：
            trade_date: 交易日，格式 YYYYMMDD。
            idx_type: 东方财富板块类型，例如行业板块、概念板块、地域板块。

        返回值：
            dc_index 记录列表；调用失败时返回空列表。

        异常：
            无。内部异常会记录日志并返回空列表。
        """
        from common.tushare_proxy import call_tushare

        params = {"trade_date": trade_date}
        if idx_type:
            params["idx_type"] = idx_type

        resp = call_tushare(
            "dc_index",
            params=params,
            fields="ts_code,trade_date,name,idx_type,level",
            use_query=False,
        )
        if not isinstance(resp, dict) or resp.get("code") != 200:
            logger.warning(
                "Tushare dc_index 调用失败: trade_date=%s idx_type=%s message=%s",
                trade_date,
                idx_type or "",
                resp.get("message") if isinstance(resp, dict) else resp,
            )
            return []

        data = resp.get("data", {})
        records = data.get("records", []) if isinstance(data, dict) else []
        return [item for item in records if isinstance(item, dict)]

    def _resolve_target_sector_df(
        self,
        trade_date: str,
        idx_type: str,
        level: Optional[str],
    ) -> pd.DataFrame:
        """
        解析目标板块清单。

        参数：
            trade_date: 最新交易日，格式 YYYYMMDD。
            idx_type: 东方财富板块类型。
            level: 东财行业层级，仅行业板块时生效。

        返回值：
            包含 sector_code、sector_name、level 的目标板块数据框。

        异常：
            无。数据缺失时返回空 DataFrame。
        """
        dc_index_rows = self._fetch_dc_index_rows(trade_date, idx_type=idx_type)
        if not dc_index_rows:
            return pd.DataFrame(columns=["sector_code", "sector_name", "level"])

        index_df = pd.DataFrame(dc_index_rows)
        if index_df.empty or not {"ts_code", "trade_date", "name"}.issubset(index_df.columns):
            logger.warning("dc_index 返回数据缺少必要字段(ts_code, trade_date, name)")
            return pd.DataFrame(columns=["sector_code", "sector_name", "level"])

        index_df["trade_date"] = index_df["trade_date"].astype(str).map(self._normalize_trade_date)
        index_df["sector_code"] = index_df["ts_code"].astype(str).str.strip()
        index_df["sector_name"] = index_df["name"].astype(str).str.strip()
        if "level" in index_df.columns:
            index_df["level"] = index_df["level"].astype(str).str.strip()
        else:
            index_df["level"] = ""

        target_sector_df = (
            index_df[index_df["trade_date"] == trade_date][["sector_code", "sector_name", "level"]]
            .drop_duplicates()
            .reset_index(drop=True)
        )
        if level:
            target_sector_df = target_sector_df[target_sector_df["level"] == level].copy()

        return target_sector_df

    def _build_daily_fund_flow_payload(self, item: Dict) -> Dict:
        """
        构建单个交易日的资金流指标对象。

        参数：
            item: moneyflow_ind_dc 返回的单条记录。

        返回值：
            标准化后的资金流指标字典，包含主力及各档净流入金额、占比和合计字段。

        异常：
            无。字段缺失时按 0 处理。
        """
        payload = {
            "main_net_inflow_amount": round(float(item.get("net_amount") or 0), 4),
            "main_net_inflow_ratio": round(float(item.get("net_amount_rate") or 0), 4),
            "super_large_net_inflow_amount": round(float(item.get("buy_elg_amount") or 0), 4),
            "super_large_net_inflow_ratio": round(float(item.get("buy_elg_amount_rate") or 0), 4),
            "large_net_inflow_amount": round(float(item.get("buy_lg_amount") or 0), 4),
            "large_net_inflow_ratio": round(float(item.get("buy_lg_amount_rate") or 0), 4),
            "medium_net_inflow_amount": round(float(item.get("buy_md_amount") or 0), 4),
            "medium_net_inflow_ratio": round(float(item.get("buy_md_amount_rate") or 0), 4),
            "small_net_inflow_amount": round(float(item.get("buy_sm_amount") or 0), 4),
            "small_net_inflow_ratio": round(float(item.get("buy_sm_amount_rate") or 0), 4),
        }
        payload["total_net_inflow_amount"] = round(
            payload["main_net_inflow_amount"]
            + payload["super_large_net_inflow_amount"]
            + payload["large_net_inflow_amount"]
            + payload["medium_net_inflow_amount"]
            + payload["small_net_inflow_amount"],
            4,
        )
        payload["total_net_inflow_ratio"] = round(
            payload["main_net_inflow_ratio"]
            + payload["super_large_net_inflow_ratio"]
            + payload["large_net_inflow_ratio"]
            + payload["medium_net_inflow_ratio"]
            + payload["small_net_inflow_ratio"],
            4,
        )
        return payload

    def _empty_industry_fund_flow_response(self) -> Dict:
        """
        构造空的行业资金流响应体。

        参数：
            无。

        返回值：
            包含空 dates、swCodeNames 和 congestions 的字典。

        异常：
            无。
        """
        return {"dates": [], "swCodeNames": [], "congestions": {}}

    def _build_weekly_fund_flow_payload(
        self,
        trade_dates: List[str],
        sector_codes: List[str],
        per_code_rows: Dict[str, Dict[str, Dict]],
    ) -> Dict:
        """
        按周汇总行业资金流数据。

        参数：
            trade_dates: 交易日列表，格式 YYYYMMDD。
            sector_codes: 目标板块代码列表。
            per_code_rows: 按板块代码和交易日组织的资金流数据。

        返回值：
            接口响应字典，dates 为周序列，congestions 为每周均值序列。

        异常：
            无。缺失周数据时使用空对象占位。
        """
        weekly_dates = sorted({
            datetime.strptime(trade_date, "%Y%m%d").date().strftime("%Y-W%W")
            for trade_date in trade_dates
        })
        weekly_congestions: Dict[str, List[Dict]] = {}
        metric_keys = [
            "main_net_inflow_amount",
            "main_net_inflow_ratio",
            "super_large_net_inflow_amount",
            "super_large_net_inflow_ratio",
            "large_net_inflow_amount",
            "large_net_inflow_ratio",
            "medium_net_inflow_amount",
            "medium_net_inflow_ratio",
            "small_net_inflow_amount",
            "small_net_inflow_ratio",
            "total_net_inflow_amount",
            "total_net_inflow_ratio",
        ]

        for sector_code in sector_codes:
            bucket: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
            count_map: Dict[str, int] = defaultdict(int)
            for trade_date, payload in per_code_rows.get(sector_code, {}).items():
                week_key = datetime.strptime(trade_date, "%Y%m%d").date().strftime("%Y-W%W")
                count_map[week_key] += 1
                for key in metric_keys:
                    bucket[week_key][key] += float(payload.get(key, 0))

            weekly_series: List[Dict] = []
            for week_key in weekly_dates:
                if not count_map.get(week_key):
                    weekly_series.append({})
                    continue
                weekly_series.append(
                    {
                        key: round(bucket[week_key][key] / count_map[week_key], 4)
                        for key in metric_keys
                    }
                )
            weekly_congestions[sector_code] = weekly_series

        return {
            "dates": weekly_dates,
            "congestions": weekly_congestions,
        }
    
    def get_industry_sectors(self) -> Optional[List[Dict]]:
        """获取所有行业板块列表
        
        Returns:
            行业板块列表，仅从数据库获取
        """
        cache_key = 'industry_sectors_list'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info("从缓存获取行业板块列表")
            return cached_data
        
        try:
            # 从数据库获取
            sectors = list(IndustrySector.objects.all().values())
            if sectors:
                # 转换为字典列表
                result = []
                for sector in sectors:
                    result.append({
                        'code': sector['code'],
                        'name': sector['name'],
                        'description': sector['description'],
                        'latest_price': sector.get('latest_price'),
                        'change_amount': sector.get('change_amount'),
                        'change_percent': sector.get('change_percent'),
                        'total_market_value': sector.get('total_market_value'),
                        'turnover_rate': sector.get('turnover_rate'),
                        'rise_count': sector.get('rise_count'),
                        'fall_count': sector.get('fall_count'),
                        'leading_stock': sector.get('leading_stock'),
                        'leading_stock_change_percent': sector.get('leading_stock_change_percent'),
                        'created_at': sector['created_at'].isoformat() if isinstance(sector['created_at'], datetime) else sector['created_at'],
                        'updated_at': sector['updated_at'].isoformat() if isinstance(sector['updated_at'], datetime) else sector['updated_at']
                    })
                
                # 缓存数据
                cache.set(cache_key, result, self.cache_timeout)
                logger.info(f"从数据库获取{len(result)}个行业板块")
                return result
            
            logger.warning("数据库中没有行业板块数据")
            return None
            
        except Exception as e:
            logger.error(f"获取行业板块列表失败: {str(e)}")
            return None
    
    def get_industry_sector_daily(self, sector_code: str, start_date: str = None, end_date: str = None) -> Optional[List[Dict]]:
        """获取行业板块日频数据（仅从数据库查询）
        
        Args:
            sector_code: 行业板块代码
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
        
        Returns:
            行业板块日频数据列表
        """
        if not start_date:
            # 默认获取最近60天数据
            start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')
        
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        
        try:
            # 从数据库获取
            start_date_obj = datetime.strptime(start_date, '%Y%m%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y%m%d').date()
            
            sector = IndustrySector.objects.filter(code=sector_code).first()
            if not sector:
                logger.warning(f"行业板块{sector_code}不存在")
                return None
            
            daily_data = IndustrySectorDaily.objects.filter(
                sector=sector,
                date__gte=start_date_obj,
                date__lte=end_date_obj
            ).order_by('-date')
            
            if daily_data.exists():
                result = [item.to_dict() for item in daily_data]
                logger.info(f"从数据库获取行业板块{sector_code}的{len(result)}条日频数据")
                return result
            
            logger.info(f"数据库无行业板块{sector_code}日频数据")
            return []
            
        except Exception as e:
            logger.error(f"获取行业板块{sector_code}日频数据失败: {str(e)}")
            return None
    
    def get_industry_sector_realtime(self, sector_code: str) -> Optional[Dict]:
        """获取行业板块实时行情
        
        Args:
            sector_code: 行业板块代码
        
        Returns:
            行业板块实时行情
        """
        cache_key = f'industry_sector_realtime_{sector_code}'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存获取行业板块{sector_code}实时行情")
            return cached_data
        
        try:
            # 从akshare获取
            logger.info(f"从akshare获取行业板块{sector_code}实时行情")
            
            # 先获取板块名称
            sector = IndustrySector.objects.filter(code=sector_code).first()
            if not sector:
                # 尝试从API获取板块列表
                self.get_industry_sectors()
                sector = IndustrySector.objects.filter(code=sector_code).first()
                if not sector:
                    logger.warning(f"行业板块{sector_code}不存在")
                    return None
            
            # 获取实时行情
            df = ak.stock_board_industry_spot_em(symbol=sector.name)
            
            if df is None or df.empty:
                logger.warning(f"获取行业板块{sector_code}实时行情为空")
                return None
            
            # 转换为字典
            realtime_data = {}
            for _, row in df.iterrows():
                item = str(row['item']).strip()
                value = row['value']
                realtime_data[item] = value
            
            # 构建结果
            result = {
                'sector_code': sector_code,
                'sector_name': sector.name,
                'latest_price': float(realtime_data.get('最新', 0)),
                'change_percent': float(realtime_data.get('涨跌幅', 0)),
                'change_amount': float(realtime_data.get('涨跌额', 0)),
                'open_price': float(realtime_data.get('开盘', 0)),
                'high_price': float(realtime_data.get('最高', 0)),
                'low_price': float(realtime_data.get('最低', 0)),
                'volume': int(realtime_data.get('成交量', 0)),
                'amount': float(realtime_data.get('成交额', 0)),
                'turnover_rate': float(realtime_data.get('换手率', 0)),
                'amplitude': float(realtime_data.get('振幅', 0)),
                'timestamp': datetime.now().isoformat()
            }
            
            # 缓存数据
            cache.set(cache_key, result, self.cache_timeout)
            
            return result
            
        except Exception as e:
            logger.error(f"获取行业板块{sector_code}实时行情失败: {str(e)}")
            return None
    
    def get_industry_sector_constituents(self, sector_code: str) -> Optional[List[Dict]]:
        """获取行业板块成分股
        
        Args:
            sector_code: 行业板块代码
        
        Returns:
            行业板块成分股列表
        """        
        try:
            # 从数据库获取行业板块信息
            try:
                sector = IndustrySector.objects.get(code=sector_code)
            except IndustrySector.DoesNotExist:
                logger.warning(f"行业板块{sector_code}不存在")
                return None
            
            # 从数据库获取该行业的所有个股

            stocks = IndividualStock.objects.filter(industry=sector.name)
            
            if not stocks.exists():
                logger.warning(f"行业板块{sector_code}({sector.name})没有成分股数据")
                return None
            
            # 转换数据格式
            constituents = []
            for stock in stocks:
                constituent = {
                    'code': stock.code,
                    'name': stock.name,
                    'latest_price': float(stock.latest_price) if stock.latest_price is not None else 0.0,
                    'change_percent': float(stock.change_percent) if stock.change_percent is not None else 0.0,
                    'change_amount': float(stock.change_amount) if stock.change_amount is not None else 0.0,
                    'volume': float(stock.volume) if stock.volume is not None else 0.0,
                    'amount': float(stock.amount) if stock.amount is not None else 0.0,
                    'amplitude': float(stock.amplitude) if stock.amplitude is not None else 0.0,
                    'high': float(stock.high) if stock.high is not None else 0.0,
                    'low': float(stock.low) if stock.low is not None else 0.0,
                    'open_price': float(stock.open_price) if stock.open_price is not None else 0.0,
                    'close_price': float(stock.close_price) if stock.close_price is not None else 0.0,
                    'turnover_rate': float(stock.turnover_rate) if stock.turnover_rate is not None else 0.0,
                    'pe_ratio': float(stock.pe_ratio) if stock.pe_ratio is not None else 0.0,
                    'pb_ratio': float(stock.pb_ratio) if stock.pb_ratio is not None else 0.0
                }
                constituents.append(constituent)
            
            return constituents
            
        except Exception as e:
            logger.error(f"获取行业板块{sector_code}成分股失败: {str(e)}")
            return None

    def get_industry_sector_fund_flow(self, sector_code: str, start_date: str = None, end_date: str = None) -> Optional[List[Dict]]:
        """获取行业板块资金流数据（仅从数据库查询）
        
        Args:
            sector_code: 行业板块代码
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
        
        Returns:
            行业板块资金流数据列表
        """
        if not start_date:
            # 默认获取最近60天数据
            start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')
        
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        
        try:
            # 从数据库获取
            start_date_obj = datetime.strptime(start_date, '%Y%m%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y%m%d').date()
            
            sector = IndustrySector.objects.filter(code=sector_code).first()
            if not sector:
                logger.warning(f"行业板块{sector_code}不存在")
                return None
            
            fund_flow_data = IndustrySectorFundFlow.objects.filter(
                sector=sector,
                date__gte=start_date_obj,
                date__lte=end_date_obj
            ).order_by('-date')
            
            if fund_flow_data.exists():
                result = [item.to_dict() for item in fund_flow_data]
                logger.info(f"从数据库获取行业板块{sector_code}的{len(result)}条资金流数据")
                return result
            
            logger.info(f"数据库无行业板块{sector_code}资金流数据")
            return []
            
        except Exception as e:
            logger.error(f"获取行业板块{sector_code}资金流数据失败: {str(e)}")
            return None

    def get_all_sectors_fund_flow_summary(self, date: str = None) -> Optional[List[Dict]]:
        """获取所有行业板块指定日期的资金流汇总数据
        
        Args:
            date: 日期，格式：YYYYMMDD，默认为最新交易日
        
        Returns:
            所有行业板块资金流汇总数据列表
        """
        if not date:
            date = datetime.now().strftime('%Y%m%d')
        
        try:
            date_obj = datetime.strptime(date, '%Y%m%d').date()
            
            fund_flow_data = IndustrySectorFundFlow.objects.filter(
                date=date_obj
            ).select_related('sector').order_by('-main_net_inflow_amount')
            
            if fund_flow_data.exists():
                result = [item.to_dict() for item in fund_flow_data]
                logger.info(f"获取{date}日{len(result)}个行业板块资金流汇总数据")
                return result
            
            logger.info(f"数据库无{date}日行业板块资金流数据")
            return []
            
        except Exception as e:
            logger.error(f"获取{date}日行业板块资金流汇总数据失败: {str(e)}")
            return None

    def get_fund_flow_ranking(self, date: str = None, sort_by: str = 'main_net_inflow_amount', order: str = 'desc', limit: int = 20) -> Optional[List[Dict]]:
        """获取行业板块资金流排行榜
        
        Args:
            date: 日期，格式：YYYYMMDD，默认为最新交易日
            sort_by: 排序字段，可选值：main_net_inflow_amount, main_net_inflow_ratio, 
                    super_large_net_inflow_amount, large_net_inflow_amount等
            order: 排序方式，'desc'降序，'asc'升序
            limit: 返回数量限制
        
        Returns:
            行业板块资金流排行榜
        """
        if not date:
            date = datetime.now().strftime('%Y%m%d')
        
        try:
            date_obj = datetime.strptime(date, '%Y%m%d').date()
            
            # 构建排序字段
            order_field = f'-{sort_by}' if order == 'desc' else sort_by
            
            fund_flow_data = IndustrySectorFundFlow.objects.filter(
                date=date_obj
            ).select_related('sector').order_by(order_field)[:limit]
            
            if fund_flow_data.exists():
                result = []
                for i, item in enumerate(fund_flow_data, 1):
                    data = item.to_dict()
                    data['rank'] = i
                    result.append(data)
                
                logger.info(f"获取{date}日行业板块资金流排行榜，共{len(result)}条")
                return result
            
            logger.info(f"数据库无{date}日行业板块资金流数据")
            return []
            
        except Exception as e:
            logger.error(f"获取{date}日行业板块资金流排行榜失败: {str(e)}")
            return None

    def get_industry_fund_flow_data(
        self,
        start_date: str = None,
        end_date: str = None,
        weekly_flag: bool = False,
        idx_type: str = "行业板块",
        level: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        获取行业板块资金流向数据。

        参数：
            start_date: 开始日期，格式 YYYY-MM-DD。
            end_date: 结束日期，格式 YYYY-MM-DD。
            weekly_flag: 是否按周汇聚数据，为 True 时返回周均值序列。
            idx_type: 东方财富板块类型，支持行业板块、概念板块、地域板块。
            level: 东财行业层级，仅 idx_type=行业板块 时生效。

        返回值：
            包含 dates、swCodeNames 和 congestions 的字典；失败时返回 None。

        异常：
            ValueError: 当 level 参数不在允许范围内时抛出。
            其他异常：内部记录日志并返回 None。
        """
        try:
            from common.tushare_proxy import call_tushare

            effective_idx_type = str(idx_type or "行业板块").strip() or "行业板块"
            effective_level = level if effective_idx_type == "行业板块" else None
            if effective_level and effective_level not in DC_INDUSTRY_LEVELS:
                raise ValueError("level参数错误，仅支持：东财一级行业、东财二级行业、东财三级行业")

            start_date, end_date = self._get_default_fund_flow_dates(start_date, end_date, weekly_flag)
            cache_key = (
                "industry_fund_flow_dc_v2_"
                f"{start_date}_{end_date}_{int(weekly_flag)}_{effective_idx_type}_{effective_level or 'all-level'}"
            )
            cached_data = cache.get(cache_key)
            if cached_data is not None and isinstance(cached_data, dict):
                logger.info("从缓存获取行业资金流向数据")
                return cached_data

            logger.info(
                "获取行业资金流向数据，日期范围: %s 到 %s，按周汇聚: %s，idx_type: %s，level: %s",
                start_date,
                end_date,
                weekly_flag,
                effective_idx_type,
                effective_level or "",
            )

            trade_dates = self._get_trade_dates(start_date, end_date)
            if not trade_dates:
                return self._empty_industry_fund_flow_response()

            latest_trade_date = trade_dates[-1]
            target_sector_df = self._resolve_target_sector_df(
                trade_date=latest_trade_date,
                idx_type=effective_idx_type,
                level=effective_level,
            )
            if target_sector_df.empty:
                logger.warning(
                    "未匹配到目标板块: latest_trade_date=%s idx_type=%s level=%s",
                    latest_trade_date,
                    effective_idx_type,
                    effective_level or "",
                )
                return self._empty_industry_fund_flow_response()

            sector_codes = sorted(target_sector_df["sector_code"].tolist())
            target_code_set: Set[str] = set(sector_codes)
            code_name_map: Dict[str, str] = {
                str(row["sector_code"]).strip(): str(row["sector_name"]).strip()
                for row in target_sector_df.to_dict("records")
            }
            name_code_map: Dict[str, str] = {
                sector_name: sector_code for sector_code, sector_name in code_name_map.items()
            }
            content_type = DC_CONTENT_TYPE_MAP.get(effective_idx_type, "行业")
            per_code_rows: Dict[str, Dict[str, Dict]] = defaultdict(dict)

            flow_fields = (
                "ts_code,trade_date,name,net_amount,net_amount_rate,"
                "buy_elg_amount,buy_elg_amount_rate,"
                "buy_lg_amount,buy_lg_amount_rate,"
                "buy_md_amount,buy_md_amount_rate,"
                "buy_sm_amount,buy_sm_amount_rate"
            )

            for trade_date in trade_dates:
                flow_resp = call_tushare(
                    "moneyflow_ind_dc",
                    params={"trade_date": trade_date, "content_type": content_type},
                    fields=flow_fields,
                    use_query=False,
                )
                if not isinstance(flow_resp, dict) or flow_resp.get("code") != 200:
                    logger.warning(
                        "Tushare moneyflow_ind_dc 调用失败: trade_date=%s content_type=%s message=%s",
                        trade_date,
                        content_type,
                        flow_resp.get("message") if isinstance(flow_resp, dict) else flow_resp,
                    )
                    continue

                flow_data = flow_resp.get("data", {})
                flow_records = flow_data.get("records", []) if isinstance(flow_data, dict) else []
                for item in flow_records:
                    if not isinstance(item, dict):
                        continue
                    sector_code = str(item.get("ts_code") or "").strip()
                    sector_name = str(item.get("name") or "").strip()
                    if not sector_code and sector_name:
                        sector_code = name_code_map.get(sector_name, "")
                    if not sector_code or sector_code not in target_code_set:
                        continue
                    if sector_name and sector_code not in code_name_map:
                        code_name_map[sector_code] = sector_name
                    per_code_rows[sector_code][trade_date] = self._build_daily_fund_flow_payload(item)

            sw_code_names = [
                {"indexCode": sector_code, "indexName": code_name_map.get(sector_code, "")}
                for sector_code in sector_codes
            ]

            if weekly_flag:
                result = self._build_weekly_fund_flow_payload(
                    trade_dates=trade_dates,
                    sector_codes=sector_codes,
                    per_code_rows=per_code_rows,
                )
                result["swCodeNames"] = sw_code_names
                cache.set(cache_key, result, self.cache_timeout)
                return result

            dates = [self._display_trade_date(trade_date) for trade_date in trade_dates]
            congestions: Dict[str, List[Dict]] = {}
            for sector_code in sector_codes:
                row_map = per_code_rows.get(sector_code, {})
                congestions[sector_code] = [row_map.get(trade_date, {}) for trade_date in trade_dates]

            result = {"dates": dates, "swCodeNames": sw_code_names, "congestions": congestions}
            cache.set(cache_key, result, self.cache_timeout)
            return result

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"获取行业资金流向数据失败: {str(e)}")
            return None
    
    def get_all_sectors_fund_flow_summary(self, date: str = None) -> Optional[List[Dict]]:
        """获取所有行业板块指定日期的资金流汇总数据
        
        Args:
            date: 日期，格式：YYYYMMDD，默认为最新交易日
        
        Returns:
            所有行业板块资金流汇总数据列表
        """
        if not date:
            date = datetime.now().strftime('%Y%m%d')
        
        try:
            date_obj = datetime.strptime(date, '%Y%m%d').date()
            
            fund_flow_data = IndustrySectorFundFlow.objects.filter(
                date=date_obj
            ).select_related('sector').order_by('-main_net_inflow_amount')
            
            if fund_flow_data.exists():
                result = [item.to_dict() for item in fund_flow_data]
                logger.info(f"获取{date}日{len(result)}个行业板块资金流汇总数据")
                return result
            
            logger.info(f"数据库无{date}日行业板块资金流数据")
            return []
            
        except Exception as e:
            logger.error(f"获取{date}日行业板块资金流汇总数据失败: {str(e)}")
            return None

    def get_fund_flow_ranking(self, date: str = None, sort_by: str = 'main_net_inflow_amount', order: str = 'desc', limit: int = 20) -> Optional[List[Dict]]:
        """获取行业板块资金流排行榜
        
        Args:
            date: 日期，格式：YYYYMMDD，默认为最新交易日
            sort_by: 排序字段，可选值：main_net_inflow_amount, main_net_inflow_ratio, 
                    super_large_net_inflow_amount, large_net_inflow_amount等
            order: 排序方式，'desc'降序，'asc'升序
            limit: 返回数量限制
        
        Returns:
            行业板块资金流排行榜
        """
        if not date:
            date = datetime.now().strftime('%Y%m%d')
        
        try:
            date_obj = datetime.strptime(date, '%Y%m%d').date()
            
            # 构建排序字段
            order_field = f'-{sort_by}' if order == 'desc' else sort_by
            
            fund_flow_data = IndustrySectorFundFlow.objects.filter(
                date=date_obj
            ).select_related('sector').order_by(order_field)[:limit]
            
            if fund_flow_data.exists():
                result = []
                for i, item in enumerate(fund_flow_data, 1):
                    data = item.to_dict()
                    data['rank'] = i
                    result.append(data)
                
                logger.info(f"获取{date}日行业板块资金流排行榜，共{len(result)}条")
                return result
            
            logger.info(f"数据库无{date}日行业板块资金流数据")
            return []
            
        except Exception as e:
            logger.error(f"获取{date}日行业板块资金流排行榜失败: {str(e)}")
            return None

# 全局服务实例
stock_service = StockDataService()
industry_sector_service = IndustrySectorService()
