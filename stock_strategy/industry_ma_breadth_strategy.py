#!/usr/bin/env python3
"""
行业 MA 市场宽度策略模块

功能：
- 基于交易日历获取区间交易日
- 基于东方财富行业板块 `dc_index` 获取最新交易日的板块列表
- 基于 `dc_member` 获取最新交易日的行业成分映射
- 基于 `stk_factor_pro` 获取股票技术指标快照，计算指定日期范围内的行业 MA 宽度

参数：
- start_date(str): 开始日期，YYYY-MM-DD；默认取过去 90 天
- end_date(str): 结束日期，YYYY-MM-DD；默认取当天
- ma_window(int): 移动平均窗口（交易日），默认 20
- idx_type(str): 东方财富板块类型，默认行业板块
- level(str): 东财行业层级，仅 idx_type=行业板块 时生效

返回值：
- List[Dict]: 每日每行业的宽度数据列表，包含日期、板块代码/名称、当日高于 MA 的股票数量、可计算 MA 的股票数量、宽度比例

事件：
- 参数校验与默认化
- 调用 Tushare `dc_index`、`dc_member`、`stk_factor_pro`
- 聚合行业宽度结果并写入缓存
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd
from django.conf import settings
from django.core.cache import cache

from common.tushare_industry import get_open_trade_dates
from common.tushare_proxy import call_tushare

logger = logging.getLogger(__name__)

SUPPORTED_PRECOMPUTED_WINDOWS = {5, 10, 20, 30, 60, 90, 250}
DC_INDUSTRY_LEVELS = {"东财一级行业", "东财二级行业", "东财三级行业"}


class IndustryMABreadthStrategy:
    """行业 MA 市场宽度策略类。

    功能：
    - 提供“行业内收盘价高于 N 日均线占比”的计算能力。

    参数：
    - 通过方法入参传递。

    返回值：
    - 列表结构，便于 API 直接返回。

    事件：
    - `get_industry_ma_breadth` 执行核心计算并缓存。
    """

    def __init__(self):
        """初始化行业 MA 市场宽度策略。

        参数：
        - 无。

        返回值：
        - 无。

        异常：
        - 无。
        """
        self.cache_timeout = getattr(settings, "STOCK_CACHE_TIMEOUT", 3600 * 12)

    def _get_default_dates(self, start_date: Optional[str], end_date: Optional[str]) -> Tuple[str, str]:
        """提供默认日期范围。

        参数：
        - start_date (Optional[str]): 开始日期字符串。
        - end_date (Optional[str]): 结束日期字符串。

        返回值：
        - Tuple[str, str]: 标准化后的开始日期与结束日期，格式为 YYYY-MM-DD。

        异常：
        - 无。
        """
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        return start_date, end_date

    def _normalize_trade_date(self, date_str: str) -> str:
        """标准化交易日格式。

        参数：
        - date_str (str): 输入日期，支持 YYYY-MM-DD 或 YYYYMMDD。

        返回值：
        - str: 去掉分隔符后的 YYYYMMDD 字符串；空值返回空字符串。

        异常：
        - 无。
        """
        value = str(date_str or "").strip()
        if not value:
            return ""
        return value.replace("-", "")

    def _display_trade_date(self, trade_date: str) -> str:
        """将交易日转换为接口展示格式。

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

    def _fetch_dc_index_rows(
        self,
        trade_date: str,
        idx_type: Optional[str] = None,
    ) -> List[Dict]:
        """拉取指定交易日的东方财富板块列表。

        参数：
        - trade_date (str): 交易日期，格式 YYYYMMDD。
        - idx_type (Optional[str]): 东方财富板块类型，例如行业板块、概念板块、地域板块。

        返回值：
        - List[Dict]: `dc_index` 记录列表；失败时返回空列表。

        异常：
        - 无。内部异常会记录日志并返回空列表。
        """
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
                "Tushare dc_index 调用失败: trade_date=%s message=%s",
                trade_date,
                resp.get("message") if isinstance(resp, dict) else resp,
            )
            return []
        data = resp.get("data", {})
        records = data.get("records", []) if isinstance(data, dict) else []
        return [item for item in records if isinstance(item, dict)]

    def _fetch_dc_member_rows(self, trade_date: str, sector_codes: List[str]) -> List[Dict]:
        """拉取指定交易日、目标板块集合的成分映射。

        参数：
        - trade_date (str): 交易日期，格式 YYYYMMDD。
        - sector_codes (List[str]): 目标板块代码列表。

        返回值：
        - List[Dict]: `dc_member` 记录列表；失败时返回空列表。

        异常：
        - 无。内部异常会记录日志并返回空列表。
        """
        member_records: List[Dict] = []
        for sector_code in sector_codes:
            resp = call_tushare(
                "dc_member",
                params={"trade_date": trade_date, "ts_code": sector_code},
                fields="trade_date,ts_code,con_code,name",
                use_query=False,
            )
            if not isinstance(resp, dict) or resp.get("code") != 200:
                logger.warning(
                    "Tushare dc_member 调用失败: trade_date=%s sector_code=%s message=%s",
                    trade_date,
                    sector_code,
                    resp.get("message") if isinstance(resp, dict) else resp,
                )
                continue
            data = resp.get("data", {})
            records = data.get("records", []) if isinstance(data, dict) else []
            member_records.extend(item for item in records if isinstance(item, dict))
        return member_records

    def _get_trade_dates(self, start_date: str, end_date: str) -> List[str]:
        """获取指定自然日期区间内的实际交易日列表。

        参数：
        - start_date (str): 开始日期，格式 YYYY-MM-DD。
        - end_date (str): 结束日期，格式 YYYY-MM-DD。

        返回值：
        - List[str]: 交易日列表，格式 YYYYMMDD。

        异常：
        - 无。交易日历获取失败时返回空列表。
        """
        try:
            return get_open_trade_dates(
                self._normalize_trade_date(start_date),
                self._normalize_trade_date(end_date),
            )
        except Exception as exc:
            logger.warning("获取交易日历失败: %s", exc)
            return []

    def _resolve_target_sectors(
        self,
        latest_sector_df: pd.DataFrame,
        level: Optional[str] = None,
    ) -> pd.DataFrame:
        """解析目标行业板块列表。

        参数：
        - latest_sector_df (pd.DataFrame): 最新交易日行业板块数据，需包含 `sector_code`、`sector_name`。
        - level (Optional[str]): 东财行业层级，仅行业板块时生效。

        返回值：
        - pd.DataFrame: 过滤后的目标行业板块列表。

        异常：
        - 无。
        """
        if latest_sector_df.empty:
            return latest_sector_df

        filtered_df = latest_sector_df.copy()
        if level and "level" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["level"].astype(str).str.strip() == level].copy()

        return filtered_df

    def _fetch_factor_rows(
        self,
        trade_dates: List[str],
        fields: str,
        target_codes: Set[str],
    ) -> List[Dict]:
        """按交易日拉取股票技术指标快照。

        参数：
        - trade_dates (List[str]): 待请求的交易日列表，格式 YYYYMMDD。
        - fields (str): `stk_factor_pro` 请求字段列表。
        - target_codes (Set[str]): 目标股票代码集合，用于在本地过滤记录。

        返回值：
        - List[Dict]: 满足目标股票范围的因子记录列表。

        异常：
        - 无。内部异常会记录日志并跳过异常日期。
        """
        factor_records: List[Dict] = []
        for trade_date in trade_dates:
            resp = call_tushare(
                "stk_factor_pro",
                params={"trade_date": trade_date},
                fields=fields,
                use_query=False,
            )
            if not isinstance(resp, dict) or resp.get("code") != 200:
                logger.warning(
                    "Tushare stk_factor_pro 调用失败: trade_date=%s message=%s",
                    trade_date,
                    resp.get("message") if isinstance(resp, dict) else resp,
                )
                continue

            data = resp.get("data", {})
            records = data.get("records", []) if isinstance(data, dict) else []
            if not records:
                continue

            filtered_records = [
                item
                for item in records
                if isinstance(item, dict) and str(item.get("ts_code") or "").strip() in target_codes
            ]
            factor_records.extend(filtered_records)

        return factor_records

    def _build_supported_window_frame(
        self,
        factor_records: List[Dict],
        ma_window: int,
        output_trade_dates: Set[str],
    ) -> pd.DataFrame:
        """基于预计算均线字段构建行情数据框。

        参数：
        - factor_records (List[Dict]): `stk_factor_pro` 返回的原始记录。
        - ma_window (int): 均线窗口。
        - output_trade_dates (Set[str]): 需要输出的交易日集合。

        返回值：
        - pd.DataFrame: 包含 `stock_id`、`trade_date`、`close_price`、`ma_close` 的数据框。

        异常：
        - 无。
        """
        ma_field = f"ma_bfq_{ma_window}"
        factor_df = pd.DataFrame(factor_records)
        if factor_df.empty or ma_field not in factor_df.columns:
            return pd.DataFrame()

        factor_df["stock_id"] = factor_df["ts_code"].astype(str).str.strip()
        factor_df["trade_date"] = factor_df["trade_date"].astype(str).map(self._normalize_trade_date)
        factor_df["close_price"] = pd.to_numeric(factor_df["close"], errors="coerce")
        factor_df["ma_close"] = pd.to_numeric(factor_df[ma_field], errors="coerce")
        factor_df = factor_df[factor_df["trade_date"].isin(output_trade_dates)].copy()
        return factor_df[["stock_id", "trade_date", "close_price", "ma_close"]]

    def _build_rolling_window_frame(
        self,
        factor_records: List[Dict],
        ma_window: int,
        output_trade_dates: Set[str],
    ) -> pd.DataFrame:
        """基于收盘价本地滚动计算任意窗口均线。

        参数：
        - factor_records (List[Dict]): `stk_factor_pro` 返回的原始记录。
        - ma_window (int): 均线窗口。
        - output_trade_dates (Set[str]): 需要输出的交易日集合。

        返回值：
        - pd.DataFrame: 包含 `stock_id`、`trade_date`、`close_price`、`ma_close` 的数据框。

        异常：
        - 无。
        """
        factor_df = pd.DataFrame(factor_records)
        if factor_df.empty:
            return pd.DataFrame()

        factor_df["stock_id"] = factor_df["ts_code"].astype(str).str.strip()
        factor_df["trade_date"] = factor_df["trade_date"].astype(str).map(self._normalize_trade_date)
        factor_df["close_price"] = pd.to_numeric(factor_df["close"], errors="coerce")
        factor_df["trade_dt"] = pd.to_datetime(factor_df["trade_date"], format="%Y%m%d", errors="coerce")
        factor_df = factor_df.dropna(subset=["trade_dt"]).sort_values(["stock_id", "trade_dt"])
        factor_df["ma_close"] = (
            factor_df.groupby("stock_id")["close_price"]
            .transform(lambda series: series.rolling(window=ma_window, min_periods=ma_window).mean())
        )
        factor_df = factor_df[factor_df["trade_date"].isin(output_trade_dates)].copy()
        return factor_df[["stock_id", "trade_date", "close_price", "ma_close"]]

    def get_industry_ma_breadth(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ma_window: int = 20,
        idx_type: str = "行业板块",
        level: Optional[str] = None,
    ) -> Optional[List[Dict]]:
        """计算行业 MA 市场宽度。

        功能：
        - 在指定日期范围内，计算每个行业“收盘价高于 MA_N”的股票占比。

        参数：
        - start_date (Optional[str]): 开始日期，格式 YYYY-MM-DD。
        - end_date (Optional[str]): 结束日期，格式 YYYY-MM-DD。
        - ma_window (int): 移动平均窗口大小（交易日）。
        - idx_type (str): 东方财富板块类型，支持行业板块、概念板块、地域板块。
        - level (Optional[str]): 东财行业层级，仅 `idx_type=行业板块` 时生效。

        返回值：
        - Optional[List[Dict]]: 每日每行业的宽度结果列表；失败返回 `None`。

        异常：
        - 无。内部异常会记录日志并返回 `None`。
        """
        try:
            if ma_window <= 1:
                ma_window = 2
            effective_idx_type = str(idx_type or "行业板块").strip() or "行业板块"
            effective_level = level if effective_idx_type == "行业板块" else None
            if effective_level and effective_level not in DC_INDUSTRY_LEVELS:
                raise ValueError("level参数错误，仅支持：东财一级行业、东财二级行业、东财三级行业")

            start_date, end_date = self._get_default_dates(start_date, end_date)
            cache_key = (
                "industry_ma_breadth_dc_v2_"
                f"{start_date}_{end_date}_{ma_window}_{effective_idx_type}_{effective_level or 'all-level'}_"
                "all"
            )
            try:
                cached = cache.get(cache_key)
                if cached is not None and isinstance(cached, list):
                    logger.info("从缓存获取行业 MA 市场宽度数据")
                    return cached
            except Exception as exc:
                logger.warning("读取行业 MA 市场宽度缓存失败，将直接计算: %s", exc)

            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            use_precomputed_ma = ma_window in SUPPORTED_PRECOMPUTED_WINDOWS
            extended_start_dt = start_dt if use_precomputed_ma else start_dt - timedelta(days=ma_window * 2)

            output_trade_dates = self._get_trade_dates(start_date, end_date)
            if not output_trade_dates:
                logger.warning("指定区间内未获取到有效交易日")
                return []
            all_trade_dates = (
                output_trade_dates
                if use_precomputed_ma
                else self._get_trade_dates(extended_start_dt.strftime("%Y-%m-%d"), end_date)
            )
            if not all_trade_dates:
                logger.warning("未获取到计算均线所需的交易日")
                return []

            latest_trade_date = output_trade_dates[-1]
            dc_index_rows = self._fetch_dc_index_rows(
                latest_trade_date,
                idx_type=effective_idx_type,
            )
            if not dc_index_rows:
                logger.warning("未获取到东方财富行业板块数据")
                return []

            index_df = pd.DataFrame(dc_index_rows)
            if index_df.empty or not {"ts_code", "trade_date", "name"}.issubset(index_df.columns):
                logger.warning("dc_index 返回数据缺少必要字段(ts_code, trade_date, name)")
                return []

            index_df["trade_date"] = index_df["trade_date"].astype(str).map(self._normalize_trade_date)
            index_df["sector_code"] = index_df["ts_code"].astype(str).str.strip()
            index_df["sector_name"] = index_df["name"].astype(str).str.strip()
            if "level" in index_df.columns:
                index_df["level"] = index_df["level"].astype(str).str.strip()
            else:
                index_df["level"] = ""
            latest_sector_df = (
                index_df[index_df["trade_date"] == latest_trade_date][["sector_code", "sector_name", "level"]]
                .drop_duplicates()
                .reset_index(drop=True)
            )
            target_sector_df = self._resolve_target_sectors(
                latest_sector_df,
                level=effective_level,
            )
            if target_sector_df.empty:
                logger.warning("未匹配到目标行业板块")
                return []

            target_sector_codes = set(target_sector_df["sector_code"].tolist())
            dc_member_rows = self._fetch_dc_member_rows(
                latest_trade_date,
                sorted(target_sector_codes),
            )
            if not dc_member_rows:
                logger.warning("未获取到东方财富行业板块成分数据")
                return []

            member_df = pd.DataFrame(dc_member_rows)
            if member_df.empty or not {"ts_code", "con_code"}.issubset(member_df.columns):
                logger.warning("dc_member 返回数据缺少必要字段(ts_code, con_code)")
                return []

            member_df["sector_code"] = member_df["ts_code"].astype(str).str.strip()
            member_df["stock_id"] = member_df["con_code"].astype(str).str.strip()
            member_df = member_df[member_df["sector_code"].isin(target_sector_codes)].copy()
            member_df = member_df.merge(target_sector_df, on="sector_code", how="left")
            member_df = member_df[["stock_id", "sector_code", "sector_name"]].drop_duplicates()
            if member_df.empty:
                logger.warning("目标行业板块成分股为空")
                return []

            target_codes = set(member_df["stock_id"].tolist())
            factor_request_dates = output_trade_dates if use_precomputed_ma else all_trade_dates
            factor_fields = (
                f"ts_code,trade_date,close,ma_bfq_{ma_window}"
                if use_precomputed_ma
                else "ts_code,trade_date,close"
            )
            factor_rows = self._fetch_factor_rows(factor_request_dates, factor_fields, target_codes)
            if not factor_rows:
                logger.warning("stk_factor_pro 未返回可用技术指标数据")
                return []

            if use_precomputed_ma:
                factor_df = self._build_supported_window_frame(
                    factor_rows,
                    ma_window,
                    set(output_trade_dates),
                )
            else:
                factor_df = self._build_rolling_window_frame(
                    factor_rows,
                    ma_window,
                    set(output_trade_dates),
                )

            if factor_df.empty:
                logger.warning("未构建出可用的股票 MA 数据")
                return []

            factor_df = factor_df.merge(member_df, on="stock_id", how="inner")
            if factor_df.empty:
                logger.warning("技术指标数据与行业成分映射合并后为空")
                return []

            factor_df["above_ma"] = factor_df["close_price"] > factor_df["ma_close"]
            agg_df = (
                factor_df.groupby(["trade_date", "sector_code", "sector_name"])
                .agg(
                    count_above_ma=("above_ma", lambda values: int(values.fillna(False).sum())),
                    eligible_count=("ma_close", lambda values: int(values.notna().sum())),
                )
                .reset_index()
            )
            agg_df["breadth_ratio"] = agg_df.apply(
                lambda row: (row["count_above_ma"] / row["eligible_count"]) if row["eligible_count"] > 0 else 0,
                axis=1,
            )
            agg_df["date"] = agg_df["trade_date"].map(self._display_trade_date)
            agg_df["breadth_ratio"] = agg_df["breadth_ratio"].round(4)

            result = agg_df[
                ["date", "sector_code", "sector_name", "count_above_ma", "eligible_count", "breadth_ratio"]
            ].sort_values(["date", "sector_code"]).to_dict("records")

            try:
                cache.set(cache_key, result, self.cache_timeout)
            except Exception as exc:
                logger.warning("写入行业 MA 市场宽度缓存失败: %s", exc)

            logger.info(
                "行业 MA 宽度计算完成: idx_type=%s level=%s sectors=%s factor_trade_dates=%s result_rows=%s",
                effective_idx_type,
                effective_level or "",
                len(target_sector_df),
                len(factor_request_dates),
                len(result),
            )
            return result
        except ValueError:
            raise
        except Exception as exc:
            logger.error("计算行业 MA 市场宽度失败: %s", exc)
            return None


industry_ma_breadth_strategy = IndustryMABreadthStrategy()
