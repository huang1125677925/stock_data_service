#!/usr/bin/env python3
"""
行业成交额百分位策略

功能：
- 参考东方财富板块链路，基于 `dc_index` 获取目标板块清单
- 基于 `dc_daily` 获取板块成交额快照
- 计算每日板块成交额、占目标板块总成交额比例、成交额百分位

参数：
- start_date(str): 开始日期，格式 YYYY-MM-DD，默认近 90 天
- end_date(str): 结束日期，格式 YYYY-MM-DD，默认当天
- idx_type(str): 东方财富板块类型，支持行业板块、概念板块、地域板块
- level(str): 东财行业层级，仅在 idx_type=行业板块 时生效

返回值：
- List[Dict]: 每个交易日每个板块的成交额统计结果

事件：
- 参数标准化
- 交易日回退解析
- 调用 `dc_index`、`dc_daily`
- 聚合成交额比例与百分位并缓存
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
from django.conf import settings
from django.core.cache import cache

from common.tushare_industry import get_open_trade_dates
from common.tushare_proxy import call_tushare

logger = logging.getLogger(__name__)

DC_INDUSTRY_LEVELS = {"东财一级行业", "东财二级行业", "东财三级行业"}


class IndustryTurnoverStrategy:
    """行业成交额百分位策略类。

    功能：
    - 基于东方财富板块快照计算成交额统计结果。

    参数：
    - 通过方法入参传递。

    返回值：
    - 列表结构，便于 API 直接返回。

    事件：
    - `get_industry_turnover_percentile` 执行核心计算并缓存。
    """

    def __init__(self):
        """初始化行业成交额百分位策略。

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

    def _get_recent_trade_dates(self, end_date: str, max_count: int = 5) -> List[str]:
        """获取截止指定日期向前最近若干个开市日。

        参数：
        - end_date (str): 截止日期，格式 YYYYMMDD。
        - max_count (int): 需要返回的最近开市日数量，默认 5。

        返回值：
        - List[str]: 按日期从近到远排序的开市日列表。

        异常：
        - 无。内部异常时返回空列表。
        """
        if max_count <= 0:
            return []

        try:
            end_dt = datetime.strptime(end_date, "%Y%m%d")
        except ValueError:
            return []

        window_days = max(max_count * 7, 14)
        for _ in range(6):
            start_dt = end_dt - timedelta(days=window_days)
            try:
                trade_dates = get_open_trade_dates(
                    start_dt.strftime("%Y%m%d"),
                    end_date,
                )
            except Exception as exc:
                logger.warning("获取最近交易日失败: %s", exc)
                return []
            if trade_dates:
                return sorted(trade_dates, reverse=True)[:max_count]
            window_days *= 2
        return []

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
        """拉取指定交易日的东方财富板块清单。

        参数：
        - trade_date (str): 交易日期，格式 YYYYMMDD。
        - idx_type (str): 东方财富板块类型。
        - level (Optional[str]): 东财行业层级，仅行业板块时生效。

        返回值：
        - List[Dict]: 过滤后的板块记录列表；失败时返回空列表。

        异常：
        - 无。内部异常会记录日志并返回空列表。
        """
        params = {"trade_date": trade_date, "idx_type": idx_type}
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

    def _build_board_map(self, rows: List[Dict]) -> Dict[str, Dict[str, str]]:
        """将板块列表转换为板块映射。

        参数：
        - rows (List[Dict]): `dc_index` 原始板块记录。

        返回值：
        - Dict[str, Dict[str, str]]: 板块代码到板块元数据的映射。

        异常：
        - 无。
        """
        board_map: Dict[str, Dict[str, str]] = {}
        for item in rows:
            code = str(item.get("ts_code") or "").strip()
            if not code:
                continue
            board_map[code] = {
                "sector_name": str(item.get("name") or "").strip(),
                "idx_type": str(item.get("idx_type") or "").strip(),
                "level": str(item.get("level") or "").strip(),
            }
        return board_map

    def _fetch_dc_daily_trade_date(self, trade_date: str, idx_type: str) -> pd.DataFrame:
        """按单个交易日获取东方财富板块成交额快照。

        参数：
        - trade_date (str): 交易日期，格式 YYYYMMDD。
        - idx_type (str): 东方财富板块类型。

        返回值：
        - pd.DataFrame: 包含 `ts_code`、`trade_date`、`amount` 的数据框。

        异常：
        - 无。内部异常时返回空数据框。
        """
        resp = call_tushare(
            "dc_daily",
            params={"trade_date": trade_date, "idx_type": idx_type},
            fields="ts_code,trade_date,amount",
            use_query=False,
        )
        empty_df = pd.DataFrame(columns=["ts_code", "trade_date", "amount"])
        if not isinstance(resp, dict) or resp.get("code") != 200:
            logger.warning(
                "Tushare dc_daily 调用失败: trade_date=%s idx_type=%s message=%s",
                trade_date,
                idx_type,
                resp.get("message") if isinstance(resp, dict) else resp,
            )
            return empty_df

        data = resp.get("data", {})
        records = data.get("records", []) if isinstance(data, dict) else []
        if not records:
            return empty_df

        daily_df = pd.DataFrame.from_records(records)
        if daily_df.empty:
            return empty_df

        daily_df["ts_code"] = daily_df["ts_code"].astype(str).str.strip()
        daily_df["trade_date"] = daily_df["trade_date"].astype(str).map(self._normalize_trade_date)
        daily_df["amount"] = pd.to_numeric(daily_df["amount"], errors="coerce").fillna(0.0)
        return daily_df.dropna(subset=["ts_code", "trade_date"])

    def _resolve_latest_available_trade_date(
        self,
        preferred_date: str,
        idx_type: str,
        level: Optional[str],
        max_fallback_count: int = 5,
    ) -> Tuple[Optional[str], Dict[str, Dict[str, str]]]:
        """解析实际可用的截止交易日与目标板块集合。

        参数：
        - preferred_date (str): 优先使用的截止日期，格式 YYYYMMDD。
        - idx_type (str): 东方财富板块类型。
        - level (Optional[str]): 东财行业层级，仅行业板块时生效。
        - max_fallback_count (int): 最多向前回退检查的开市日数量。

        返回值：
        - Tuple[Optional[str], Dict[str, Dict[str, str]]]:
          第一个值为实际可用交易日，第二个值为命中的板块映射。

        异常：
        - 无。内部异常场景通过空结果返回。
        """
        candidate_dates = self._get_recent_trade_dates(preferred_date, max_count=max_fallback_count)
        if not candidate_dates:
            candidate_dates = [preferred_date]

        for candidate_date in candidate_dates:
            board_rows = self._fetch_dc_index_rows(candidate_date, idx_type=idx_type, level=level)
            if not board_rows:
                continue

            board_map = self._build_board_map(board_rows)
            if not board_map:
                continue

            daily_df = self._fetch_dc_daily_trade_date(candidate_date, idx_type=idx_type)
            if daily_df.empty:
                continue

            available_codes = set(daily_df["ts_code"].astype(str))
            matched_board_map = {
                code: meta
                for code, meta in board_map.items()
                if code in available_codes
            }
            if not matched_board_map:
                continue
            return candidate_date, matched_board_map
        return None, {}

    def _build_turnover_frame(
        self,
        trade_dates: List[str],
        board_map: Dict[str, Dict[str, str]],
        idx_type: str,
    ) -> pd.DataFrame:
        """按交易日构建板块成交额明细数据框。

        参数：
        - trade_dates (List[str]): 待统计的交易日列表，格式 YYYYMMDD。
        - board_map (Dict[str, Dict[str, str]]): 目标板块映射。
        - idx_type (str): 东方财富板块类型。

        返回值：
        - pd.DataFrame: 包含日期、板块、成交额等字段的数据框。

        异常：
        - 无。内部异常日期会记录日志并跳过。
        """
        rows: List[Dict] = []
        target_codes = set(board_map.keys())
        for trade_date in trade_dates:
            daily_df = self._fetch_dc_daily_trade_date(trade_date, idx_type=idx_type)
            if daily_df.empty:
                logger.info("dc_daily 返回空数据，跳过该交易日: %s", trade_date)
                continue

            matched_df = daily_df[daily_df["ts_code"].isin(target_codes)].copy()
            if matched_df.empty:
                continue

            matched_df["sector_code"] = matched_df["ts_code"]
            matched_df["sector_name"] = matched_df["sector_code"].map(
                lambda code: board_map.get(code, {}).get("sector_name", "")
            )
            matched_df["idx_type"] = matched_df["sector_code"].map(
                lambda code: board_map.get(code, {}).get("idx_type", "")
            )
            matched_df["level"] = matched_df["sector_code"].map(
                lambda code: board_map.get(code, {}).get("level", "")
            )
            rows.extend(
                matched_df[
                    ["trade_date", "sector_code", "sector_name", "idx_type", "level", "amount"]
                ].to_dict("records")
            )

        if not rows:
            return pd.DataFrame(
                columns=["trade_date", "sector_code", "sector_name", "idx_type", "level", "amount"]
            )

        result_df = pd.DataFrame(rows)
        result_df["amount"] = pd.to_numeric(result_df["amount"], errors="coerce").fillna(0.0)
        return result_df

    def _calculate_amount_metrics(self, detail_df: pd.DataFrame) -> pd.DataFrame:
        """计算成交额占比与百分位。

        参数：
        - detail_df (pd.DataFrame): 板块成交额明细数据。

        返回值：
        - pd.DataFrame: 新增 `daily_total_amount`、`amount_ratio`、`amount_percentile` 的结果数据框。

        异常：
        - 无。
        """
        if detail_df.empty:
            return detail_df

        result_df = detail_df.copy()
        daily_total_df = (
            result_df.groupby("trade_date")["amount"]
            .sum()
            .reset_index()
            .rename(columns={"amount": "daily_total_amount"})
        )
        result_df = result_df.merge(daily_total_df, on="trade_date", how="left")
        result_df["amount_ratio"] = result_df.apply(
            lambda row: (row["amount"] / row["daily_total_amount"]) if row["daily_total_amount"] else 0.0,
            axis=1,
        )
        result_df["amount_percentile"] = (
            result_df.groupby("trade_date")["amount_ratio"]
            .rank(method="average", pct=True)
            .mul(100)
            .round()
            .astype(int)
        )
        result_df["date"] = result_df["trade_date"].map(self._display_trade_date)
        result_df["amount"] = result_df["amount"].round(2)
        result_df["daily_total_amount"] = result_df["daily_total_amount"].round(2)
        result_df["amount_ratio"] = result_df["amount_ratio"].round(6)
        return result_df[
            [
                "date",
                "sector_code",
                "sector_name",
                "idx_type",
                "level",
                "amount",
                "daily_total_amount",
                "amount_ratio",
                "amount_percentile",
            ]
        ].sort_values(["date", "sector_code"])

    def get_industry_turnover_percentile(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        idx_type: str = "行业板块",
        level: Optional[str] = None,
    ) -> Optional[List[Dict]]:
        """获取板块成交额百分位数据。

        功能：
        - 在指定日期范围内，返回目标板块每日成交额、占总额比例与成交额百分位。

        参数：
        - start_date (Optional[str]): 开始日期，格式 YYYY-MM-DD。
        - end_date (Optional[str]): 结束日期，格式 YYYY-MM-DD。
        - idx_type (str): 东方财富板块类型，默认行业板块。
        - level (Optional[str]): 东财行业层级，仅 `idx_type=行业板块` 时生效。

        返回值：
        - Optional[List[Dict]]: 结果列表；失败返回 `None`。

        异常：
        - ValueError: 当 level 参数非法时抛出异常。
        """
        effective_idx_type = str(idx_type or "行业板块").strip() or "行业板块"
        effective_level = level if effective_idx_type == "行业板块" else None
        if effective_level and effective_level not in DC_INDUSTRY_LEVELS:
            raise ValueError("level参数错误，仅支持：东财一级行业、东财二级行业、东财三级行业")

        start_date, end_date = self._get_default_dates(start_date, end_date)
        cache_key = (
            "industry_turnover_percentile_dc_v2_"
            f"{start_date}_{end_date}_{effective_idx_type}_{effective_level or 'all-level'}"
        )

        try:
            cached = cache.get(cache_key)
            if cached is not None and isinstance(cached, list):
                logger.info("从缓存获取板块成交额百分位数据")
                return cached
        except Exception as exc:
            logger.warning("读取板块成交额百分位缓存失败，将直接计算: %s", exc)

        try:
            preferred_end_trade_date = self._normalize_trade_date(end_date)
            actual_end_trade_date, board_map = self._resolve_latest_available_trade_date(
                preferred_end_trade_date,
                idx_type=effective_idx_type,
                level=effective_level,
            )
            if not actual_end_trade_date or not board_map:
                logger.warning(
                    "未解析到可用的东财板块成交额数据: end_date=%s idx_type=%s level=%s",
                    end_date,
                    effective_idx_type,
                    effective_level or "",
                )
                return []

            trade_dates = self._get_trade_dates(start_date, actual_end_trade_date)
            if not trade_dates:
                logger.warning("指定区间内未获取到有效交易日")
                return []

            detail_df = self._build_turnover_frame(
                trade_dates=trade_dates,
                board_map=board_map,
                idx_type=effective_idx_type,
            )
            if detail_df.empty:
                logger.warning("未构建出可用的板块成交额明细数据")
                return []

            result_df = self._calculate_amount_metrics(detail_df)
            result = result_df.to_dict("records")
            try:
                cache.set(cache_key, result, self.cache_timeout)
            except Exception as exc:
                logger.warning("写入板块成交额百分位缓存失败: %s", exc)
            return result
        except Exception as exc:
            logger.error("获取板块成交额百分位数据失败: %s", exc)
            return None


industry_turnover_strategy = IndustryTurnoverStrategy()
