#!/usr/bin/env python3
"""
Django股票数据服务
基于akshare库获取股票数据
"""

import logging
import json
from typing import Dict, List, Optional
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from django.db import models
from .models import StockInfo, StockRealtime, MarketSummary, IndustrySector, IndustrySectorDaily
from common.validators import validate_stock_symbol

logger = logging.getLogger(__name__)

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
                    circulating_market_cap=stock.get('circulation_market_cap', 0),
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

# 行业板块数据服务类
class IndustrySectorService:
    """行业板块数据服务类"""
    
    def __init__(self):
        self.cache_timeout = getattr(settings, 'STOCK_CACHE_TIMEOUT', 300)  # 缓存5分钟
        self.request_timeout = getattr(settings, 'STOCK_REQUEST_TIMEOUT', 30)
        self.max_retries = getattr(settings, 'STOCK_MAX_RETRIES', 3)
        
        logger.info(f"行业板块数据服务初始化: cache_timeout={self.cache_timeout}s")
    
    def get_industry_sectors(self) -> Optional[List[Dict]]:
        """获取所有行业板块列表
        
        Returns:
            行业板块列表
        """
        cache_key = 'industry_sectors_list'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info("从缓存获取行业板块列表")
            return cached_data
        
        try:
            # 尝试从数据库获取
            sectors = list(IndustrySector.objects.all().values())
            if sectors:
                # 转换为字典列表
                result = []
                for sector in sectors:
                    result.append({
                        'code': sector['code'],
                        'name': sector['name'],
                        'description': sector['description'],
                        'created_at': sector['created_at'].isoformat() if isinstance(sector['created_at'], datetime) else sector['created_at'],
                        'updated_at': sector['updated_at'].isoformat() if isinstance(sector['updated_at'], datetime) else sector['updated_at']
                    })
                
                # 缓存数据
                cache.set(cache_key, result, self.cache_timeout)
                logger.info(f"从数据库获取{len(result)}个行业板块")
                return result
            
            # 数据库没有数据，从akshare获取
            logger.info("数据库无行业板块数据，从akshare获取")
            df = ak.stock_board_industry_name_em()
            
            if df is None or df.empty:
                logger.warning("获取行业板块数据为空")
                return None
            
            # 转换数据格式
            sectors = []
            for _, row in df.iterrows():
                sector_data = {
                    'code': str(row['板块代码']),
                    'name': str(row['板块名称']),
                    'description': None,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                sectors.append(sector_data)
                
                # 保存到数据库
                IndustrySector.objects.update_or_create(
                    code=sector_data['code'],
                    defaults={
                        'name': sector_data['name'],
                        'description': sector_data['description']
                    }
                )
            
            # 缓存数据
            cache.set(cache_key, sectors, self.cache_timeout)
            logger.info(f"获取{len(sectors)}个行业板块数据并保存到数据库")
            
            return sectors
            
        except Exception as e:
            logger.error(f"获取行业板块列表失败: {str(e)}")
            return None
    
    def get_industry_sector_daily(self, sector_code: str, start_date: str = None, end_date: str = None) -> Optional[List[Dict]]:
        """获取行业板块日频数据
        
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
        
        cache_key = f'industry_sector_daily_{sector_code}_{start_date}_{end_date}'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存获取行业板块{sector_code}日频数据")
            return cached_data
        
        try:
            # 尝试从数据库获取
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
                
                # 缓存数据
                cache.set(cache_key, result, self.cache_timeout)
                logger.info(f"从数据库获取行业板块{sector_code}的{len(result)}条日频数据")
                return result
            
            # 数据库没有数据，从akshare获取
            logger.info(f"数据库无行业板块{sector_code}日频数据，从akshare获取")
            df = ak.stock_board_industry_hist_em(
                symbol=sector_code,
                start_date=start_date,
                end_date=end_date,
                period="日k",
                adjust=""
            )
            
            if df is None or df.empty:
                logger.warning(f"获取行业板块{sector_code}日频数据为空")
                return None
            
            # 转换数据格式
            daily_list = []
            for _, row in df.iterrows():
                date_str = str(row['日期'])
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                # 检查数据是否已存在
                exists = IndustrySectorDaily.objects.filter(sector=sector, date=date_obj).exists()
                if exists:
                    continue
                
                # 创建日频数据对象
                daily_data = IndustrySectorDaily(
                    sector=sector,
                    date=date_obj,
                    open_price=float(row['开盘']),
                    close_price=float(row['收盘']),
                    high_price=float(row['最高']),
                    low_price=float(row['最低']),
                    change_percent=float(row['涨跌幅']),
                    change_amount=float(row['涨跌额']),
                    total_volume=int(row['成交量']),
                    total_amount=float(row['成交额']),
                    amplitude=float(row['振幅']) if '振幅' in row and pd.notna(row['振幅']) else None,
                    turnover_rate=float(row['换手率']) if '换手率' in row and pd.notna(row['换手率']) else None,
                    # 以下字段需要从其他接口获取或计算
                    rising_stocks=0,
                    falling_stocks=0,
                    flat_stocks=0,
                    total_market_cap=None
                )
                
                # 保存到数据库
                daily_data.save()
                
                # 添加到结果列表
                daily_list.append(daily_data.to_dict())
            
            # 如果没有新增数据，则从数据库获取
            if not daily_list:
                daily_data = IndustrySectorDaily.objects.filter(
                    sector=sector,
                    date__gte=start_date_obj,
                    date__lte=end_date_obj
                ).order_by('-date')
                
                daily_list = [item.to_dict() for item in daily_data]
            
            # 缓存数据
            cache.set(cache_key, daily_list, self.cache_timeout)
            logger.info(f"获取行业板块{sector_code}的{len(daily_list)}条日频数据并保存到数据库")
            
            return daily_list
            
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
        cache_key = f'industry_sector_constituents_{sector_code}'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存获取行业板块{sector_code}成分股")
            return cached_data
        
        try:
            # 从akshare获取
            logger.info(f"从akshare获取行业板块{sector_code}成分股")
            df = ak.stock_board_industry_cons_em(symbol=sector_code)
            
            if df is None or df.empty:
                logger.warning(f"获取行业板块{sector_code}成分股为空")
                return None
            
            # 转换数据格式
            constituents = []
            for _, row in df.iterrows():
                constituent = {
                    'code': str(row['代码']),
                    'name': str(row['名称']),
                    'latest_price': float(row['最新价']) if pd.notna(row['最新价']) else 0.0,
                    'change_percent': float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0.0,
                    'change_amount': float(row['涨跌额']) if pd.notna(row['涨跌额']) else 0.0,
                    'volume': float(row['成交量']) if pd.notna(row['成交量']) else 0.0,
                    'amount': float(row['成交额']) if pd.notna(row['成交额']) else 0.0,
                    'amplitude': float(row['振幅']) if pd.notna(row['振幅']) else 0.0,
                    'high': float(row['最高']) if pd.notna(row['最高']) else 0.0,
                    'low': float(row['最低']) if pd.notna(row['最低']) else 0.0,
                    'open_price': float(row['今开']) if pd.notna(row['今开']) else 0.0,
                    'close_price': float(row['昨收']) if pd.notna(row['昨收']) else 0.0,
                    'turnover_rate': float(row['换手率']) if pd.notna(row['换手率']) else 0.0,
                    'pe_ratio': float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else 0.0,
                    'pb_ratio': float(row['市净率']) if pd.notna(row['市净率']) else 0.0
                }
                constituents.append(constituent)
            
            # 缓存数据
            cache.set(cache_key, constituents, self.cache_timeout)
            logger.info(f"获取行业板块{sector_code}的{len(constituents)}只成分股")
            
            return constituents
            
        except Exception as e:
            logger.error(f"获取行业板块{sector_code}成分股失败: {str(e)}")
            return None

# 全局服务实例
stock_service = StockDataService()
industry_sector_service = IndustrySectorService()