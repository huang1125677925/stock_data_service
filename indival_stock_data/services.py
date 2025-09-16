#!/usr/bin/env python3
"""
个股数据服务
基于akshare库获取个股数据
"""

import logging
import time
import pandas as pd
import akshare as ak
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from django.db import transaction
from .models import IndividualStock, IndividualStockDaily, IndividualStockRealtime
from common.validators import validate_stock_symbol

logger = logging.getLogger(__name__)


class IndividualStockService:
    """个股数据服务类"""
    
    def __init__(self):
        self.cache_timeout = getattr(settings, 'STOCK_CACHE_TIMEOUT', 300)  # 缓存5分钟
        self.request_timeout = getattr(settings, 'STOCK_REQUEST_TIMEOUT', 30)
        self.max_retries = getattr(settings, 'STOCK_MAX_RETRIES', 3)
        
        logger.info(f"个股数据服务初始化: cache_timeout={self.cache_timeout}s")
    
    def get_stock_list(self) -> Optional[List[Dict]]:
        """
        获取股票列表
        
        Returns:
            股票列表
        """
        cache_key = 'individual_stock_list'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info("从缓存获取股票列表")
            return cached_data
        
        try:
            # 尝试从数据库获取
            stocks = IndividualStock.objects.all()
            if stocks.exists():
                stock_list = [stock.to_dict() for stock in stocks]
                cache.set(cache_key, stock_list, self.cache_timeout)
                logger.info(f"从数据库获取{len(stock_list)}只股票信息")
                return stock_list
            
            # 数据库没有数据，从akshare获取
            logger.info("数据库无股票列表数据，从akshare获取")
            df = ak.stock_sh_a_spot_em()
            
            if df is None or df.empty:
                logger.warning("获取股票列表数据为空")
                return None
            
            # 转换数据格式并保存到数据库
            stock_list = []
            for _, row in df.iterrows():
                code = str(row['代码'])
                name = str(row['名称'])
                
                # 创建或更新股票信息
                stock, created = IndividualStock.objects.update_or_create(
                    code=code,
                    defaults={
                        'name': name,
                        'pe_ratio': float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else None,
                        'pb_ratio': float(row['市净率']) if pd.notna(row['市净率']) else None,
                        'total_market_cap': float(row['总市值']) if pd.notna(row['总市值']) else None,
                        'circulating_market_cap': float(row['流通市值']) if pd.notna(row['流通市值']) else None,
                    }
                )
                
                stock_list.append({
                    'code': code,
                    'name': name,
                    'pe_ratio': float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else None,
                    'pb_ratio': float(row['市净率']) if pd.notna(row['市净率']) else None,
                    'total_market_cap': float(row['总市值']) if pd.notna(row['总市值']) else None,
                    'circulating_market_cap': float(row['流通市值']) if pd.notna(row['流通市值']) else None,
                })
            
            # 缓存数据
            cache.set(cache_key, stock_list, self.cache_timeout)
            logger.info(f"获取{len(stock_list)}只股票信息并保存到数据库")
            
            return stock_list
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {str(e)}")
            return None
    
    def get_stock_realtime(self, stock_code: str = None) -> Optional[Union[Dict, List[Dict]]]:
        """
        获取股票实时行情
        
        Args:
            stock_code: 股票代码，如果为None则获取所有股票的实时行情
        
        Returns:
            股票实时行情数据
        """
        if stock_code and not validate_stock_symbol(stock_code):
            logger.warning(f"无效的股票代码: {stock_code}")
            return None
        
        cache_key = f'individual_stock_realtime_{stock_code if stock_code else "all"}'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存获取股票{stock_code if stock_code else '所有'}实时行情")
            return cached_data
        
        try:
            # 从akshare获取实时行情
            df = ak.stock_sh_a_spot_em()
            
            if df is None or df.empty:
                logger.warning("获取股票实时行情数据为空")
                return None
            
            # 如果指定了股票代码，则过滤数据
            if stock_code:
                df = df[df['代码'] == stock_code]
                if df.empty:
                    logger.warning(f"未找到股票{stock_code}的实时行情")
                    return None
            
            # 转换数据格式并保存到数据库
            realtime_list = []
            with transaction.atomic():
                for _, row in df.iterrows():
                    code = str(row['代码'])
                    name = str(row['名称'])
                    
                    # 获取或创建股票信息
                    stock, created = IndividualStock.objects.get_or_create(
                        code=code,
                        defaults={'name': name}
                    )
                    
                    # 更新股票信息
                    if not created:
                        stock.name = name
                        stock.pe_ratio = float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else None
                        stock.pb_ratio = float(row['市净率']) if pd.notna(row['市净率']) else None
                        stock.total_market_cap = float(row['总市值']) if pd.notna(row['总市值']) else None
                        stock.circulating_market_cap = float(row['流通市值']) if pd.notna(row['流通市值']) else None
                        stock.save()
                    
                    # 创建实时行情
                    realtime = IndividualStockRealtime(
                        stock=stock,
                        latest_price=float(row['最新价']) if pd.notna(row['最新价']) else 0.0,
                        change_percent=float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0.0,
                        change_amount=float(row['涨跌额']) if pd.notna(row['涨跌额']) else 0.0,
                        volume=int(row['成交量']) if pd.notna(row['成交量']) else 0,
                        amount=float(row['成交额']) if pd.notna(row['成交额']) else 0.0,
                        amplitude=float(row['振幅']) if pd.notna(row['振幅']) else None,
                        high=float(row['最高']) if pd.notna(row['最高']) else None,
                        low=float(row['最低']) if pd.notna(row['最低']) else None,
                        open_price=float(row['今开']) if pd.notna(row['今开']) else None,
                        close_price=float(row['昨收']) if pd.notna(row['昨收']) else None,
                        turnover_rate=float(row['换手率']) if pd.notna(row['换手率']) else None
                    )
                    realtime.save()
                    
                    realtime_data = realtime.to_dict()
                    realtime_list.append(realtime_data)
            
            # 缓存数据
            result = realtime_list[0] if stock_code else realtime_list
            cache.set(cache_key, result, self.cache_timeout)
            
            logger.info(f"获取股票{stock_code if stock_code else '所有'}实时行情并保存到数据库")
            return result
            
        except Exception as e:
            logger.error(f"获取股票{stock_code if stock_code else '所有'}实时行情失败: {str(e)}")
            return None
    
    def get_stock_history(self, stock_code: str, start_date: str = None, end_date: str = None, adjust: str = "") -> Optional[List[Dict]]:
        """
        获取股票历史行情数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期，格式：YYYYMMDD，默认为30天前
            end_date: 结束日期，格式：YYYYMMDD，默认为今天
            adjust: 复权类型，""为不复权，"qfq"为前复权，"hfq"为后复权
        
        Returns:
            股票历史行情数据列表
        """
        if not validate_stock_symbol(stock_code):
            logger.warning(f"无效的股票代码: {stock_code}")
            return None
        
        # 设置默认日期
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        
        cache_key = f'individual_stock_history_{stock_code}_{start_date}_{end_date}_{adjust}'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存获取股票{stock_code}历史行情数据")
            return cached_data
        
        try:
            # 获取或创建股票信息
            stock = self._get_or_create_stock(stock_code)
            if not stock:
                logger.warning(f"未找到股票{stock_code}的信息")
                return None
            
            # 尝试从数据库获取历史数据
            start_date_obj = datetime.strptime(start_date, '%Y%m%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y%m%d').date()
            
            db_history = IndividualStockDaily.objects.filter(
                stock=stock,
                date__gte=start_date_obj,
                date__lte=end_date_obj
            ).order_by('date')
            
            # 如果数据库中有完整的历史数据，则直接返回
            if db_history.count() > 0 and (end_date_obj - start_date_obj).days + 1 <= db_history.count() * 1.5:  # 允许有一些交易日的差异
                history_list = [history.to_dict() for history in db_history]
                cache.set(cache_key, history_list, self.cache_timeout)
                logger.info(f"从数据库获取股票{stock_code}历史行情数据")
                return history_list
            
            # 从akshare获取历史数据
            logger.info(f"从akshare获取股票{stock_code}历史行情数据")
            df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start_date, end_date=end_date, adjust=adjust)
            
            if df is None or df.empty:
                logger.warning(f"获取股票{stock_code}历史行情数据为空")
                return None
            
            # 转换数据格式并保存到数据库
            history_list = []
            with transaction.atomic():
                for _, row in df.iterrows():
                    date_str = row['日期']
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    
                    # 创建或更新历史数据
                    history, created = IndividualStockDaily.objects.update_or_create(
                        stock=stock,
                        date=date_obj,
                        defaults={
                            'open_price': float(row['开盘']) if pd.notna(row['开盘']) else 0.0,
                            'close_price': float(row['收盘']) if pd.notna(row['收盘']) else 0.0,
                            'high_price': float(row['最高']) if pd.notna(row['最高']) else 0.0,
                            'low_price': float(row['最低']) if pd.notna(row['最低']) else 0.0,
                            'change_percent': float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0.0,
                            'change_amount': float(row['涨跌额']) if pd.notna(row['涨跌额']) else 0.0,
                            'volume': int(row['成交量']) if pd.notna(row['成交量']) else 0,
                            'amount': float(row['成交额']) if pd.notna(row['成交额']) else 0.0,
                            'amplitude': float(row['振幅']) if pd.notna(row['振幅']) else None,
                            'turnover_rate': float(row['换手率']) if pd.notna(row['换手率']) else None
                        }
                    )
                    
                    history_list.append(history.to_dict())
            
            # 缓存数据
            cache.set(cache_key, history_list, self.cache_timeout)
            logger.info(f"获取股票{stock_code}历史行情数据并保存到数据库")
            
            return history_list
            
        except Exception as e:
            logger.error(f"获取股票{stock_code}历史行情数据失败: {str(e)}")
            return None
    
    def get_stock_info(self, stock_code: str) -> Optional[Dict]:
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
        
        cache_key = f'individual_stock_info_{stock_code}'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存获取股票{stock_code}详细信息")
            return cached_data
        
        try:
            # 尝试从数据库获取
            try:
                stock = IndividualStock.objects.get(code=stock_code)
                stock_info = stock.to_dict()
            except IndividualStock.DoesNotExist:
                # 数据库没有数据，从akshare获取
                logger.info(f"数据库无股票{stock_code}信息，从akshare获取")
                stock = self._get_or_create_stock(stock_code)
                if not stock:
                    logger.warning(f"未找到股票{stock_code}的信息")
                    return None
                stock_info = stock.to_dict()
            
            # 获取最新的实时行情
            try:
                realtime = IndividualStockRealtime.objects.filter(stock=stock).latest('timestamp')
                realtime_info = realtime.to_dict()
            except IndividualStockRealtime.DoesNotExist:
                # 没有实时行情，获取最新的
                realtime_info = self.get_stock_realtime(stock_code)
            
            # 获取最近的历史数据
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
            history = self.get_stock_history(stock_code, start_date, end_date)
            
            # 构建详细信息
            info = {
                **stock_info,
                'realtime': realtime_info,
                'history': history[:7] if history else []
            }
            
            # 缓存数据
            cache.set(cache_key, info, self.cache_timeout)
            
            return info
            
        except Exception as e:
            logger.error(f"获取股票{stock_code}详细信息失败: {str(e)}")
            return None
    
    def update_all_stocks(self) -> Tuple[int, int, int]:
        """
        更新所有股票信息和实时行情
        
        Returns:
            更新的股票数量、新增的股票数量、失败的股票数量
        """
        try:
            # 从akshare获取所有股票列表
            df = ak.stock_sh_a_spot_em()
            
            if df is None or df.empty:
                logger.warning("获取股票列表数据为空")
                return 0, 0, 0
            
            updated_count = 0
            created_count = 0
            failed_count = 0
            
            # 更新股票信息和实时行情
            with transaction.atomic():
                for _, row in df.iterrows():
                    try:
                        code = str(row['代码'])
                        name = str(row['名称'])
                        
                        # 创建或更新股票信息
                        stock, created = IndividualStock.objects.update_or_create(
                            code=code,
                            defaults={
                                'name': name,
                                'pe_ratio': float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else None,
                                'pb_ratio': float(row['市净率']) if pd.notna(row['市净率']) else None,
                                'total_market_cap': float(row['总市值']) if pd.notna(row['总市值']) else None,
                                'circulating_market_cap': float(row['流通市值']) if pd.notna(row['流通市值']) else None,
                            }
                        )
                        
                        # 创建实时行情
                        IndividualStockRealtime.objects.create(
                            stock=stock,
                            latest_price=float(row['最新价']) if pd.notna(row['最新价']) else 0.0,
                            change_percent=float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0.0,
                            change_amount=float(row['涨跌额']) if pd.notna(row['涨跌额']) else 0.0,
                            volume=int(row['成交量']) if pd.notna(row['成交量']) else 0,
                            amount=float(row['成交额']) if pd.notna(row['成交额']) else 0.0,
                            amplitude=float(row['振幅']) if pd.notna(row['振幅']) else None,
                            high=float(row['最高']) if pd.notna(row['最高']) else None,
                            low=float(row['最低']) if pd.notna(row['最低']) else None,
                            open_price=float(row['今开']) if pd.notna(row['今开']) else None,
                            close_price=float(row['昨收']) if pd.notna(row['昨收']) else None,
                            turnover_rate=float(row['换手率']) if pd.notna(row['换手率']) else None
                        )
                        
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                            
                    except Exception as e:
                        logger.error(f"更新股票{code}信息失败: {str(e)}")
                        failed_count += 1
            
            # 清除缓存
            cache.delete('individual_stock_list')
            cache.delete('individual_stock_realtime_all')
            
            logger.info(f"更新所有股票信息完成: 更新{updated_count}只，新增{created_count}只，失败{failed_count}只")
            return updated_count, created_count, failed_count
            
        except Exception as e:
            logger.error(f"更新所有股票信息失败: {str(e)}")
            return 0, 0, 0
    
    def update_stock_history(self, stock_code: str = None, days: int = 30) -> Tuple[int, int]:
        """
        更新股票历史数据
        
        Args:
            stock_code: 股票代码，如果为None则更新所有股票
            days: 更新的天数
        
        Returns:
            更新的股票数量、更新的历史数据数量
        """
        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

            updated_stocks = 0
            updated_history = 0
            
            # 如果指定了股票代码，则只更新该股票
            if stock_code:
                if not validate_stock_symbol(stock_code):
                    logger.warning(f"无效的股票代码: {stock_code}")
                    return 0, 0
                
                # 获取或创建股票信息
                stock = self._get_or_create_stock(stock_code)
                if not stock:
                    logger.warning(f"未找到股票{stock_code}的信息")
                    return 0, 0
                
                # 更新历史数据
                history_count = self._update_stock_history(stock, start_date, end_date)
                if history_count > 0:
                    updated_stocks = 1
                    updated_history = history_count
            else:
                # 更新所有股票的历史数据
                stocks = IndividualStock.objects.all()
                for stock in stocks:
                    print(f"更新股票{stock.code}的历史数据")
                    try:
                        history_count = self._update_stock_history(stock, start_date, end_date)
                        if history_count > 0:
                            updated_stocks += 1
                            updated_history += history_count
                    except Exception as e:
                        logger.error(f"更新股票{stock.code}历史数据失败: {str(e)}")
            
            logger.info(f"更新股票历史数据完成: 更新{updated_stocks}只股票，{updated_history}条历史数据")
            return updated_stocks, updated_history
            
        except Exception as e:
            logger.error(f"更新股票历史数据失败: {str(e)}")
            return 0, 0
    
    def _get_or_create_stock(self, stock_code: str) -> Optional[IndividualStock]:
        """
        获取或创建股票信息
        
        Args:
            stock_code: 股票代码
        
        Returns:
            股票对象
        """
        try:
            # 尝试从数据库获取
            try:
                return IndividualStock.objects.get(code=stock_code)
            except IndividualStock.DoesNotExist:
                pass
            
            # 从akshare获取股票信息
            df = ak.stock_sh_a_spot_em()
            if df is None or df.empty:
                logger.warning("获取股票列表数据为空")
                return None
            
            # 过滤指定股票
            df = df[df['代码'] == stock_code]
            if df.empty:
                logger.warning(f"未找到股票{stock_code}的信息")
                return None
            
            # 创建股票信息
            row = df.iloc[0]
            stock = IndividualStock.objects.create(
                code=stock_code,
                name=str(row['名称']),
                pe_ratio=float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else None,
                pb_ratio=float(row['市净率']) if pd.notna(row['市净率']) else None,
                total_market_cap=float(row['总市值']) if pd.notna(row['总市值']) else None,
                circulating_market_cap=float(row['流通市值']) if pd.notna(row['流通市值']) else None,
            )
            
            return stock
            
        except Exception as e:
            logger.error(f"获取或创建股票{stock_code}信息失败: {str(e)}")
            return None
    
    def _update_stock_history(self, stock: IndividualStock, start_date: str, end_date: str) -> int:
        """
        更新股票历史数据
        
        Args:
            stock: 股票对象
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
        
        Returns:
            更新的历史数据数量
        """
        try:
            time.sleep(1)
            # 从akshare获取历史数据
            df = ak.stock_zh_a_hist(symbol=stock.code, period="daily", start_date=start_date, end_date=end_date, adjust="")
            
            if df is None or df.empty:
                logger.warning(f"获取股票{stock.code}历史行情数据为空")
                return 0
            
            # 更新历史数据
            updated_count = 0
            for _, row in df.iterrows():
                date_str = row['日期'].strftime('%Y-%m-%d')
                # 将字符串日期转换为日期对象
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                # 创建或更新历史数据
                _, created = IndividualStockDaily.objects.update_or_create(
                    stock=stock,
                    date=date_obj,
                    defaults={
                        'open_price': float(row['开盘']) if pd.notna(row['开盘']) else 0.0,
                        'close_price': float(row['收盘']) if pd.notna(row['收盘']) else 0.0,
                        'high_price': float(row['最高']) if pd.notna(row['最高']) else 0.0,
                        'low_price': float(row['最低']) if pd.notna(row['最低']) else 0.0,
                        'change_percent': float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0.0,
                        'change_amount': float(row['涨跌额']) if pd.notna(row['涨跌额']) else 0.0,
                        'volume': int(row['成交量']) if pd.notna(row['成交量']) else 0,
                        'amount': float(row['成交额']) if pd.notna(row['成交额']) else 0.0,
                        'amplitude': float(row['振幅']) if pd.notna(row['振幅']) else None,
                        'turnover_rate': float(row['换手率']) if pd.notna(row['换手率']) else None
                    }
                )
                print(f"更新股票{stock.code}的历史数据，日期：{date_str} {created}")
                updated_count += 1
            
            # 清除缓存
            cache_key = f'individual_stock_history_{stock.code}_{start_date}_{end_date}_'
            cache.delete(cache_key)
            
            return updated_count
            
        except Exception as e:
            logger.error(f"更新股票{stock.code}历史数据失败: {str(e)}")
            return 0


# 创建服务实例
individual_stock_service = IndividualStockService()