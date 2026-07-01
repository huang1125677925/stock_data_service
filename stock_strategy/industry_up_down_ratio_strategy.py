#!/usr/bin/env python3
"""
行业涨跌比例策略模块

功能：
- 基于 Tushare `dc_index` 获取东方财富板块每日快照
- 统计指定日期范围内每个板块的上涨家数、下跌家数与总家数
- 计算上涨比例与下跌比例

参数：
- start_date(str): 开始日期，格式 YYYY-MM-DD；默认近 90 天
- end_date(str): 结束日期，格式 YYYY-MM-DD；默认当天
- idx_type(str): 东方财富板块类型，默认行业板块
- level(str): 东财行业层级，仅 idx_type=行业板块 时生效

返回值：
- List[Dict]: 每个交易日每个板块的涨跌比例结果

异常：
- 无。内部异常会记录日志，并在对外方法中返回 `None` 或空结果。
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from django.core.cache import cache

from common.tushare_industry import get_open_trade_dates
from common.tushare_proxy import call_tushare

logger = logging.getLogger(__name__)

DC_INDUSTRY_LEVELS = {"东财一级行业", "东财二级行业", "东财三级行业"}


class IndustryUpDownRatioStrategy:
    """行业涨跌比例策略类。

    功能：
    - 计算指定时间范围内每个东方财富板块的上涨比例与下跌比例。

    参数：
    - 通过方法入参传递。

    返回值：
    - 列表结构，便于 API 直接返回。

    异常：
    - 无。内部异常由方法自行记录并处理。
    """

    def __init__(self):
        """初始化行业涨跌比例策略。

        参数：
        - 无。

        返回值：
        - 无。

        异常：
        - 无。
        """
        self.cache_timeout = getattr(settings, "STOCK_CACHE_TIMEOUT", 3600 * 12)

    def _get_default_dates(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> Tuple[str, str]:
        """补齐默认日期区间。

        参数：
        - start_date (Optional[str]): 开始日期，格式 YYYY-MM-DD。
        - end_date (Optional[str]): 结束日期，格式 YYYY-MM-DD。

        返回值：
        - Tuple[str, str]: 标准化后的开始、结束日期。

        异常：
        - 无。
        """
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        return start_date, end_date

    def _normalize_trade_date(self, date_str: Optional[str]) -> str:
        """将日期转换为 YYYYMMDD 格式。

        参数：
        - date_str (Optional[str]): 输入日期，支持 YYYY-MM-DD 或 YYYYMMDD。

        返回值：
        - str: 标准化后的 YYYYMMDD 字符串；空值返回空字符串。

        异常：
        - 无。
        """
        value = str(date_str or "").strip()
        if not value:
            return ""
        return value.replace("-", "")

    def _display_trade_date(self, trade_date: str) -> str:
        """将交易日格式化为接口展示格式。

        参数：
        - trade_date (str): 交易日，格式 YYYYMMDD 或 YYYY-MM-DD。

        返回值：
        - str: 格式化后的 YYYY-MM-DD 字符串。

        异常：
        - 无。
        """
        normalized = self._normalize_trade_date(trade_date)
        if len(normalized) == 8:
            return f"{normalized[:4]}-{normalized[4:6]}-{normalized[6:]}"
        return str(trade_date or "")

    def _get_trade_dates(self, start_date: str, end_date: str) -> List[str]:
        """获取指定日期区间内的实际交易日。

        参数：
        - start_date (str): 开始日期，格式 YYYY-MM-DD 或 YYYYMMDD。
        - end_date (str): 结束日期，格式 YYYY-MM-DD 或 YYYYMMDD。

        返回值：
        - List[str]: 交易日列表，格式 YYYYMMDD。

        异常：
        - 无。内部异常时返回空列表。
        """
        try:
            return get_open_trade_dates(
                self._normalize_trade_date(start_date),
                self._normalize_trade_date(end_date),
            )
        except Exception as exc:
            logger.warning("获取交易日历失败: %s", exc)
            return []

    def _fetch_dc_index_rows(
        self,
        trade_date: str,
        idx_type: str,
        level: Optional[str],
    ) -> List[Dict]:
        """拉取指定交易日的东方财富板块涨跌快照。

        参数：
        - trade_date (str): 交易日期，格式 YYYYMMDD。
        - idx_type (str): 东方财富板块类型。
        - level (Optional[str]): 东财行业层级，仅行业板块时生效。

        返回值：
        - List[Dict]: 过滤后的板块记录列表；失败时返回空列表。

        异常：
        - 无。内部异常会记录日志并返回空列表。
        """
        resp = call_tushare(
            "dc_index",
            params={"trade_date": trade_date, "idx_type": idx_type},
            fields="ts_code,trade_date,name,idx_type,level,up_num,down_num",
            use_query=False,
        )
        if not isinstance(resp, dict) or resp.get("code") != 200:
            logger.warning(
                "Tushare dc_index 调用失败: trade_date=%s idx_type=%s message=%s",
                trade_date,
                idx_type,
                resp.get("message") if isinstance(resp, dict) else resp,
            )
            return []

        data = resp.get("data", {})
        records = data.get("records", []) if isinstance(data, dict) else []
        filtered_rows: List[Dict] = []
        for item in records:
            if not isinstance(item, dict):
                continue
            if level and str(item.get("level") or "").strip() != level:
                continue
            code = str(item.get("ts_code") or "").strip()
            name = str(item.get("name") or "").strip()
            if not code or not name:
                continue
            filtered_rows.append(item)
        return filtered_rows

    def get_industry_up_down_ratio(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        idx_type: str = "行业板块",
        level: Optional[str] = None,
    ) -> Optional[List[Dict]]:
        """计算行业涨跌比例。

        参数：
        - start_date (Optional[str]): 开始日期，格式 YYYY-MM-DD。
        - end_date (Optional[str]): 结束日期，格式 YYYY-MM-DD。
        - idx_type (str): 东方财富板块类型，支持行业板块、概念板块、地域板块。
        - level (Optional[str]): 东财行业层级，仅 `idx_type=行业板块` 时生效。

        返回值：
        - Optional[List[Dict]]: 每日每板块的涨跌比例结果列表；失败返回 `None`。

        异常：
        - 无。内部异常会记录日志并返回 `None`。
        """
        try:
            effective_idx_type = str(idx_type or "行业板块").strip() or "行业板块"
            effective_level = level if effective_idx_type == "行业板块" else None
            if effective_level and effective_level not in DC_INDUSTRY_LEVELS:
                raise ValueError("level参数错误，仅支持：东财一级行业、东财二级行业、东财三级行业")

            start_date, end_date = self._get_default_dates(start_date, end_date)
            cache_key = (
                "industry_up_down_ratio_dc_v1_"
                f"{start_date}_{end_date}_{effective_idx_type}_{effective_level or 'all-level'}"
            )
            try:
                cached = cache.get(cache_key)
                if cached is not None and isinstance(cached, list):
                    logger.info("从缓存获取行业涨跌比例数据")
                    return cached
            except Exception as exc:
                logger.warning("读取行业涨跌比例缓存失败，将直接计算: %s", exc)

            trade_dates = self._get_trade_dates(start_date, end_date)
            if not trade_dates:
                logger.warning("指定区间内未获取到有效交易日")
                return []

            results: List[Dict] = []
            for trade_date in trade_dates:
                rows = self._fetch_dc_index_rows(
                    trade_date=trade_date,
                    idx_type=effective_idx_type,
                    level=effective_level,
                )
                if not rows:
                    continue

                for item in rows:
                    up_num = int(float(item.get("up_num") or 0))
                    down_num = int(float(item.get("down_num") or 0))
                    total_count = up_num + down_num
                    up_ratio = round(up_num / total_count, 4) if total_count > 0 else 0
                    down_ratio = round(down_num / total_count, 4) if total_count > 0 else 0
                    results.append(
                        {
                            "date": self._display_trade_date(trade_date),
                            "sector_code": str(item.get("ts_code") or "").strip(),
                            "sector_name": str(item.get("name") or "").strip(),
                            "idx_type": str(item.get("idx_type") or effective_idx_type).strip(),
                            "level": str(item.get("level") or "").strip(),
                            "up_count": up_num,
                            "down_count": down_num,
                            "total_count": total_count,
                            "up_ratio": up_ratio,
                            "down_ratio": down_ratio,
                        }
                    )

            results.sort(key=lambda item: (item["date"], item["sector_code"]))
            try:
                cache.set(cache_key, results, self.cache_timeout)
            except Exception as exc:
                logger.warning("写入行业涨跌比例缓存失败: %s", exc)

            logger.info(
                "行业涨跌比例计算完成: idx_type=%s level=%s trade_dates=%s result_rows=%s",
                effective_idx_type,
                effective_level or "",
                len(trade_dates),
                len(results),
            )
            return results
        except Exception as exc:
            logger.error("计算行业涨跌比例失败: %s", exc)
            return None


industry_up_down_ratio_strategy = IndustryUpDownRatioStrategy()
