#!/usr/bin/env python3
"""
行业成交额占比分位数策略

通过 Tushare 申万行业日线 `sw_daily` 计算每个行业每天成交额占总成交额的比例，
再计算这个行业成交额比例在所有行业比例中的分位数。
"""

import logging
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from common.tushare_industry import fetch_sw_daily_by_codes, get_sw_l1_sectors

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
                
            sectors = get_sw_l1_sectors()
            if not sectors:
                logger.error("获取申万一级行业列表失败")
                return None

            ts_codes = [item["sector_code"] for item in sectors if item.get("sector_code")]
            records = fetch_sw_daily_by_codes(
                ts_codes,
                start_date,
                end_date,
                fields="ts_code,trade_date,name,amount",
            )
            if not records:
                logger.error("获取申万行业日线成交额数据失败")
                return None

            df = pd.DataFrame(records)
            if df.empty:
                return None

            df["date"] = pd.to_datetime(df["trade_date"].astype(str))
            df["total_amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
            df["sector_code"] = df["ts_code"].astype(str)
            df["sector_name"] = df["name"].astype(str)

            daily_total = df.groupby("date")["total_amount"].sum().reset_index()
            daily_total.rename(columns={"total_amount": "daily_total_amount"}, inplace=True)
            df = pd.merge(df, daily_total, on="date", how="left")
            df["turnover_ratio"] = df.apply(
                lambda row: (row["total_amount"] / row["daily_total_amount"])
                if row["daily_total_amount"] else 0.0,
                axis=1,
            )
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
            result_df = result_df[
                [
                    'date',
                    'sector_code',
                    'sector_name',
                    'total_amount',
                    'daily_total_amount',
                    'turnover_ratio',
                    'turnover_ratio_percentile',
                ]
            ]
            
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
