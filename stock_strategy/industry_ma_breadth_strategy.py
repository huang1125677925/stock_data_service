#!/usr/bin/env python3
"""
行业MA市场宽度策略模块

功能：
- 计算指定日期范围内，每个行业内“收盘价高于其N日移动平均线(MA)”的股票占比（市场宽度）
- 行情数据仅通过 Tushare `daily` 获取
- 面向扩展设计，支持窗口大小、行业板块筛选等参数化

参数：
- start_date(str): 开始日期，YYYY-MM-DD；默认取过去90天
- end_date(str): 结束日期，YYYY-MM-DD；默认取当天
- ma_window(int): 移动平均窗口（交易日），默认20
- sector_codes(List[str]): 行业板块代码列表；为空时计算所有板块

返回值：
- List[Dict]: 每日每行业的宽度数据列表，包含日期、板块代码/名称、当日高于MA的股票数量、可计算MA的股票数量、宽度比例

事件：
- 参数校验与默认化
- 从 Tushare 读取个股日频数据
- 计算个股MA并聚合到行业维度
- 缓存结果以提升性能
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

import pandas as pd
from django.core.cache import cache
from django.conf import settings
from common.tushare_proxy import call_tushare
from common.tushare_industry import get_open_trade_dates, get_sw_l1_members, get_sw_l1_sectors

logger = logging.getLogger(__name__)


class IndustryMABreadthStrategy:
    """行业MA市场宽度策略类
    
    功能：提供“行业内收盘价高于N日均线占比”的计算能力
    参数：通过方法入参传递
    返回值：列表结构，便于API直接返回
    事件：
    - get_industry_ma_breadth: 执行核心计算并缓存
    """

    def __init__(self):
        # 缓存超时时间，默认5分钟，可通过settings.STOCK_CACHE_TIMEOUT覆盖
        self.cache_timeout = getattr(settings, 'STOCK_CACHE_TIMEOUT', 3600 * 12)

    def _get_default_dates(self, start_date: Optional[str], end_date: Optional[str]) -> (str, str):
        """内部工具：提供默认日期范围
        
        Args:
            start_date: 开始日期字符串
            end_date: 结束日期字符串
        Returns:
            (start_date, end_date) 字符串元组
        """
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        return start_date, end_date

    def _get_target_sectors(self, sector_codes: Optional[List[str]]) -> List[Dict]:
        """内部工具：获取目标行业板块列表
        
        Args:
            sector_codes: 指定板块代码列表
        Returns:
            板块字典列表 [{'code','name',...}]
        """
        try:
            all_sectors = get_sw_l1_sectors()
            sectors = [
                {"code": item["sector_code"], "name": item["sector_name"]}
                for item in all_sectors
                if item.get("sector_code") and item.get("sector_name")
            ]
            if sector_codes:
                sector_keys = {str(item).strip() for item in sector_codes if str(item).strip()}
                sectors = [
                    item for item in sectors
                    if item["code"] in sector_keys or item["name"] in sector_keys
                ]
            return sectors
        except Exception as e:
            logger.error(f"获取行业板块列表失败: {str(e)}")
            return []

    def _daily_rows_from_tushare(self, extended_start_dt, end_dt) -> List[Dict]:
        tus_records: List[Dict] = []
        trade_dates = get_open_trade_dates(
            extended_start_dt.strftime("%Y%m%d"),
            end_dt.strftime("%Y%m%d"),
        )
        for trade_date in trade_dates:
            resp = call_tushare(
                "daily",
                params={"trade_date": trade_date},
                fields="ts_code,trade_date,close",
            )
            if isinstance(resp, dict) and resp.get("code") == 200:
                data = resp.get("data", {})
                recs = data.get("records", []) if isinstance(data, dict) else []
                if recs:
                    tus_records.extend(item for item in recs if isinstance(item, dict))
            else:
                logger.warning(
                    "Tushare daily 调用失败或为空: date=%s, message=%s",
                    trade_date,
                    resp.get("message") if isinstance(resp, dict) else resp,
                )
        return tus_records

    def get_industry_ma_breadth(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ma_window: int = 20,
        sector_codes: Optional[List[str]] = None,
    ) -> Optional[List[Dict]]:
        """计算行业MA市场宽度
        
        功能：在指定日期范围内，计算每个行业“收盘价高于MA_N”的股票占比
        Args:
            start_date: 开始日期，YYYY-MM-DD
            end_date: 结束日期，YYYY-MM-DD
            ma_window: 移动平均窗口大小（交易日）
            sector_codes: 行业板块代码列表（可选）
        Returns:
            每日每行业的宽度结果列表；失败返回None
        事件：
            - 参数默认化与校验
            - 从 Tushare 读取个股日频数据
            - 逐个股票计算滚动均线并比较收盘价
            - 聚合到行业维度并缓存
        """
        try:
            # 基本参数校验与默认化
            if ma_window <= 1:
                ma_window = 2
            start_date, end_date = self._get_default_dates(start_date, end_date)

            # 缓存键
            cache_key = f"industry_ma_breadth_{start_date}_{end_date}_{ma_window}_{','.join(sector_codes) if sector_codes else 'all'}"
            try:
                cached = cache.get(cache_key)
                if cached is not None and isinstance(cached, list):
                    logger.info("从缓存获取行业MA市场宽度数据")
                    return cached
            except Exception as e:
                logger.warning("读取行业MA市场宽度缓存失败，将直接计算: %s", e)

            # 解析日期对象并扩展窗口起始（为计算MA需要向前取 ma_window-1 天）
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
            extended_start_dt = start_dt - timedelta(days=ma_window * 2)

            # 获取目标板块及成分映射
            sectors = self._get_target_sectors(sector_codes)
            if not sectors:
                logger.warning("未获取到行业板块数据")
                return []
            member_records = get_sw_l1_members()
            if not member_records:
                logger.warning("未获取到申万一级行业成分股数据")
                return []
            sector_code_set = {item["code"] for item in sectors}
            stocks_df = pd.DataFrame(
                [
                    {
                        "stock_id": item["ts_code"],
                        "code": item["ts_code"].split(".")[0],
                        "sector_code": item["sector_code"],
                        "sector_name": item["sector_name"],
                    }
                    for item in member_records
                    if item.get("sector_code") in sector_code_set and item.get("ts_code")
                ]
            )

            if stocks_df.empty:
                logger.warning("申万一级行业成分股为空")
                return []
            map_cols = stocks_df[["stock_id", "code", "sector_code", "sector_name"]].drop_duplicates()

            tus_records = self._daily_rows_from_tushare(extended_start_dt, end_dt)
            if not tus_records:
                logger.warning("Tushare daily 未返回可用个股日线数据，请检查 TUSHARE_TOKEN 或日期范围")
                return []

            ts_df = pd.DataFrame(tus_records)
            if (
                "ts_code" not in ts_df.columns
                or "trade_date" not in ts_df.columns
                or "close" not in ts_df.columns
            ):
                logger.warning("Tushare 返回数据缺少必要字段(ts_code, trade_date, close)")
                return []

            ts_df["code"] = ts_df["ts_code"].astype(str).str.split(".").str[0]
            ts_df["date"] = pd.to_datetime(ts_df["trade_date"])
            ts_df["close_price"] = pd.to_numeric(ts_df["close"], errors="coerce")
            daily_df: pd.DataFrame = ts_df.merge(map_cols, on="code", how="inner")
            daily_df = daily_df[
                ["stock_id", "date", "close_price", "sector_code", "sector_name"]
            ]
            logger.info(
                "行业MA宽度：使用 Tushare daily %s 条（行业成分股数=%s）",
                len(daily_df),
                len(map_cols),
            )

            if daily_df.empty:
                logger.warning("合并行业成分后日线为空")
                return []

            # 分股票计算滚动MA
            daily_df = daily_df.sort_values(['stock_id', 'date'])
            daily_df['ma_close'] = (
                daily_df.groupby('stock_id')['close_price']
                .transform(lambda s: s.rolling(window=ma_window, min_periods=ma_window).mean())
            )

            # 标记收盘价是否高于MA
            daily_df['above_ma'] = (daily_df['close_price'] > daily_df['ma_close'])

            # 仅聚合目标日期范围（start_date ~ end_date），排除前置扩展段
            mask_range = (daily_df['date'] >= pd.to_datetime(start_dt)) & (daily_df['date'] <= pd.to_datetime(end_dt))
            range_df = daily_df.loc[mask_range].copy()

            # 统计每日每行业的数量与比例
            # eligible_count: 当日能计算MA（ma_close非空）的股票数量
            agg_df = (
                range_df.groupby(['date', 'sector_code', 'sector_name'])
                .agg(
                    count_above_ma=('above_ma', lambda x: int(x.fillna(False).sum())),
                    eligible_count=('ma_close', lambda x: int(x.notna().sum()))
                )
                .reset_index()
            )
            # 计算比例
            agg_df['breadth_ratio'] = agg_df.apply(
                lambda r: (r['count_above_ma'] / r['eligible_count']) if r['eligible_count'] > 0 else 0,
                axis=1
            )

            # 整理输出
            agg_df['date'] = agg_df['date'].dt.strftime('%Y-%m-%d')
            agg_df['breadth_ratio'] = agg_df['breadth_ratio'].round(4)

            result = agg_df.sort_values(["date", "sector_code"]).to_dict("records")

            try:
                cache.set(cache_key, result, self.cache_timeout)
            except Exception as e:
                logger.warning("写入行业MA市场宽度缓存失败: %s", e)
            return result
        except Exception as e:
            logger.error(f"计算行业MA市场宽度失败: {str(e)}")
            return None


# 创建策略实例，供视图层调用
industry_ma_breadth_strategy = IndustryMABreadthStrategy()
