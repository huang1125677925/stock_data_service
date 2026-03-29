#!/usr/bin/env python3
"""
行业MA市场宽度策略模块

功能：
- 计算指定日期范围内，每个行业内“收盘价高于其N日移动平均线(MA)”的股票占比（市场宽度）
- 仅从数据库获取数据，遵循工作空间API规范
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
- 从数据库读取行业与个股日频数据
- 计算个股MA并聚合到行业维度
- 缓存结果以提升性能
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

import pandas as pd
from django.core.cache import cache
from django.conf import settings
from django.db.models.functions import Trim

from industry_stock_data.models import IndustrySector
from indival_stock_data.models import IndividualStock, IndividualStockDaily
from industry_stock_data.services import industry_sector_service
from common.tushare_proxy import call_tushare

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
            if sector_codes:
                # 直接从数据库过滤指定板块
                sectors = list(IndustrySector.objects.filter(code__in=sector_codes).values('code', 'name'))
            else:
                # 复用服务层获取所有板块（服务内部已用数据库数据）
                sectors = industry_sector_service.get_industry_sectors()
                if sectors is None:
                    sectors = []
                else:
                    sectors = [{'code': s['code'], 'name': s['name']} for s in sectors]
            return sectors
        except Exception as e:
            logger.error(f"获取行业板块列表失败: {str(e)}")
            return []

    def _daily_rows_from_db(
        self,
        stock_ids: List[int],
        extended_start_dt,
        end_dt,
    ) -> List[Dict]:
        if not stock_ids:
            return []
        rows = list(
            IndividualStockDaily.objects.filter(
                stock_id__in=stock_ids,
                date__gte=extended_start_dt,
                date__lte=end_dt,
            ).values("stock_id", "date", "close_price")
        )
        return rows

    def _daily_rows_from_tushare(self, extended_start_dt, end_dt) -> List[Dict]:
        tus_records: List[Dict] = []
        cur_dt = extended_start_dt
        while cur_dt <= end_dt:
            trade_date = cur_dt.strftime("%Y%m%d")
            resp = call_tushare("daily", params={"trade_date": trade_date})
            if isinstance(resp, dict) and resp.get("code") == 200:
                data = resp.get("data", {})
                recs = data.get("records", []) if isinstance(data, dict) else []
                if recs:
                    tus_records.extend(recs)
            else:
                logger.warning(
                    "Tushare daily 调用失败或为空: date=%s, message=%s",
                    trade_date,
                    resp.get("message") if isinstance(resp, dict) else resp,
                )
            cur_dt += timedelta(days=1)
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
            - 从数据库读取个股日频数据
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

            # 获取目标板块及映射
            sectors = self._get_target_sectors(sector_codes)
            if not sectors:
                logger.warning("未获取到行业板块数据")
                return []
            sector_name_set = {
                (s["name"] or "").strip()
                for s in sectors
                if (s.get("name") or "").strip()
            }
            if not sector_name_set:
                logger.warning("行业板块名称为空")
                return []

            # 与板块名称对齐：对 industry 做 TRIM 再匹配，避免空格导致零命中
            stocks_qs = (
                IndividualStock.objects.annotate(_ind_trim=Trim("industry"))
                .filter(_ind_trim__in=sector_name_set)
                .values("id", "code", "name", "industry")
            )
            if not stocks_qs.exists():
                logger.warning("无成分股数据（industry 与板块名称未对齐或个股表为空）")
                return []
            stocks_df = pd.DataFrame(list(stocks_qs))
            industry_to_code = {(s["name"] or "").strip(): s["code"] for s in sectors}
            ind_key = stocks_df["industry"].fillna("").astype(str).str.strip()
            stocks_df["sector_code"] = ind_key.map(industry_to_code)
            stocks_df["sector_name"] = ind_key
            if stocks_df["sector_code"].isna().any():
                stocks_df = stocks_df.dropna(subset=["sector_code"])

            stock_ids = [int(x) for x in stocks_df["id"].tolist()]
            if not stock_ids:
                logger.warning("成分股行业字段无法映射到板块代码")
                return []
            map_cols = stocks_df[["id", "code", "sector_code", "sector_name"]].rename(
                columns={"id": "stock_id"}
            )

            # 优先使用已入库的日频数据（MCP/任务环境常无法直连 Tushare）
            db_rows = self._daily_rows_from_db(stock_ids, extended_start_dt, end_dt)
            daily_df: pd.DataFrame
            if db_rows:
                ts_df = pd.DataFrame(db_rows)
                ts_df["date"] = pd.to_datetime(ts_df["date"])
                ts_df["close_price"] = pd.to_numeric(ts_df["close_price"], errors="coerce")
                daily_df = ts_df.merge(map_cols, on="stock_id", how="inner")
                daily_df = daily_df[
                    ["stock_id", "date", "close_price", "sector_code", "sector_name"]
                ]
                logger.info(
                    "行业MA宽度：使用库内个股日线 %s 条（股票数=%s）",
                    len(daily_df),
                    len(stock_ids),
                )
            else:
                tus_records = self._daily_rows_from_tushare(extended_start_dt, end_dt)
                if not tus_records:
                    logger.warning("库内无个股日线且 Tushare 未返回数据，请同步 individual_stock_daily 或配置 TUSHARE_TOKEN")
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
                daily_df = ts_df.merge(map_cols, on="code", how="inner")
                daily_df = daily_df[
                    ["stock_id", "date", "close_price", "sector_code", "sector_name"]
                ]

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