#!/usr/bin/env python3
"""
行业成交额占比分位数策略

计算每个行业每天成交额占总成交额的比例，然后计算这个行业成交额比例在所有行业比例中的分位数
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from industry_stock_data.models import IndustrySector, IndustrySectorDaily
from industry_stock_data.services import industry_sector_service

logger = logging.getLogger(__name__)

class IndustryTurnoverStrategy:
    """行业成交额占比分位数策略类"""
    
    def __init__(self):
        self.cache_timeout = getattr(settings, 'STOCK_CACHE_TIMEOUT', 300)  # 缓存5分钟
        
    def calculate_turnover_ratio(self, start_date: str = None, end_date: str = None) -> Optional[pd.DataFrame]:
        """
        计算每个行业每天成交额占总成交额的比例
        
        Args:
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            
        Returns:
            包含行业成交额占比的DataFrame
        """
        try:
            # 设置默认日期范围（如果未指定）
            if not start_date:
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
                
            # 转换日期格式为akshare接受的格式
            start_date_ak = start_date.replace('-', '')
            end_date_ak = end_date.replace('-', '')
            
            # 获取所有行业板块
            sectors = industry_sector_service.get_industry_sectors()
            if not sectors:
                logger.error("获取行业板块列表失败")
                return None
            
            # 创建行业代码到名称的映射
            sector_map = {sector['code']: sector['name'] for sector in sectors}
            
            # 从数据库中获取指定日期范围内的所有行业日频数据
            from industry_stock_data.models import IndustrySectorDaily, IndustrySector
            from django.db.models import F
            
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            # 直接从数据库获取所有行业在指定日期范围内的数据
            daily_data_queryset = IndustrySectorDaily.objects.filter(
                date__gte=start_date_obj,
                date__lte=end_date_obj
            ).select_related('sector')
            
            # 转换为列表
            all_sectors_data = [item.to_dict() for item in daily_data_queryset]
            
            if not all_sectors_data:
                logger.error("获取行业板块日频数据失败")
                return None
                
            # 转换为DataFrame
            df = pd.DataFrame(all_sectors_data)
            
            # 确保日期列是日期类型
            df['date'] = pd.to_datetime(df['date'])
            
            # 按日期分组，计算每天的总成交额
            daily_total = df.groupby('date')['total_amount'].sum().reset_index()
            daily_total.rename(columns={'total_amount': 'daily_total_amount'}, inplace=True)
            
            # 合并回原始DataFrame
            df = pd.merge(df, daily_total, on='date')
            
            # 计算每个行业每天成交额占比
            df['turnover_ratio'] = df['total_amount'] / df['daily_total_amount']
            
            return df
            
        except Exception as e:
            logger.error(f"计算行业成交额占比失败: {str(e)}")
            return None
    
    def calculate_turnover_ratio_percentile(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        计算行业成交额占比的分位数
        
        Args:
            df: 包含行业成交额占比的DataFrame
            
        Returns:
            包含行业成交额占比分位数的DataFrame
        """
        try:
            if df is None or df.empty:
                return None
                
            # 按日期分组，计算每个行业在当天的成交额占比分位数
            result_data = []
            
            # 获取所有唯一日期
            dates = df['date'].unique()
            
            for date in dates:
                # 获取当天数据
                day_data = df[df['date'] == date]
                
                # 计算当天所有行业成交额占比的分位数
                day_data['turnover_ratio_percentile'] = (day_data['turnover_ratio'].rank(pct=True) * 100).astype(int)
                
                # 添加到结果列表
                result_data.append(day_data)
            
            # 合并所有日期的数据
            result_df = pd.concat(result_data)
            
            # 选择需要的列
            result_df = result_df[['date', 'sector_code', 'sector_name', 'total_amount', 
                                  'daily_total_amount', 'turnover_ratio', 'turnover_ratio_percentile']]
            
            return result_df
            
        except Exception as e:
            logger.error(f"计算行业成交额占比分位数失败: {str(e)}")
            return None
    
    def get_industry_turnover_percentile(self, start_date: str = None, end_date: str = None) -> Optional[List[Dict]]:
        """
        获取指定日期范围内所有行业的日成交额占比分位数
        
        Args:
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            
        Returns:
            行业成交额占比分位数数据列表
        """
        cache_key = f'industry_turnover_percentile_{start_date}_{end_date}'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存获取行业成交额占比分位数数据")
            return cached_data
        
        try:
            # 计算行业成交额占比
            turnover_ratio_df = self.calculate_turnover_ratio(start_date, end_date)
            if turnover_ratio_df is None:
                return None
                
            # 计算行业成交额占比分位数
            percentile_df = self.calculate_turnover_ratio_percentile(turnover_ratio_df)
            if percentile_df is None:
                return None
                
            # 转换为字典列表
            percentile_df['date'] = percentile_df['date'].dt.strftime('%Y-%m-%d')
            result = percentile_df.to_dict('records')
            
            # 缓存数据
            cache.set(cache_key, result, self.cache_timeout)
            
            return result
            
        except Exception as e:
            logger.error(f"获取行业成交额占比分位数数据失败: {str(e)}")
            return None

# 创建策略实例
industry_turnover_strategy = IndustryTurnoverStrategy()