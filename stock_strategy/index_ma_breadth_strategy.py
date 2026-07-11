#!/usr/bin/env python3
"""
指数 MA 市场宽度策略模块

功能：
- 复用行业 MA 市场宽度（industry-ma-breadth）的计算逻辑，将“行业”维度替换为“指数”维度。
- 分析的指数列表与 major-index-rps 接口保持一致（国内+国际大盘指数）。
- 指数成分股通过 Tushare `index_weight` 接口获取（仅国内指数可解析成分股；国际指数无成分股数据将被跳过并记录提示）。
- 基于 `stk_factor_pro` 获取成分股技术指标快照，计算指定日期范围内每个指数
  “收盘价高于 MA_N”的成分股占比（市场宽度）。

参数：
- start_date(str): 开始日期，YYYY-MM-DD；默认取过去 90 天
- end_date(str): 结束日期，YYYY-MM-DD；默认取当天
- ma_window(int): 移动平均窗口（交易日），默认 20
- index_codes(List[str]): 可选，指定要分析的指数代码列表；为空则使用与 major-index-rps 相同的默认指数列表

返回值：
- Tuple[Optional[List[Dict]], List[str]]: 每日每指数的宽度数据列表与提示/错误信息列表

事件：
- 参数校验与默认化
- 调用 Tushare `index_weight`、`stk_factor_pro`
- 聚合指数宽度结果并写入缓存
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd
from django.core.cache import cache

from common.tushare_proxy import call_tushare

from .industry_ma_breadth_strategy import (
    IndustryMABreadthStrategy,
    SUPPORTED_PRECOMPUTED_WINDOWS,
)
from .data_tasks.major_index_rps import (
    DOMESTIC_LARGE_CAP_INDEXES,
    GLOBAL_LARGE_CAP_INDEXES,
)

logger = logging.getLogger(__name__)

# 与 major-index-rps 接口保持一致的默认指数列表（国内+国际）。
DEFAULT_INDEX_MAPPING: Dict[str, str] = {
    **DOMESTIC_LARGE_CAP_INDEXES,
    **GLOBAL_LARGE_CAP_INDEXES,
}

# index_weight 通常按月更新，回溯窗口需覆盖至少一次成分调整，取 45 个自然日。
INDEX_WEIGHT_LOOKBACK_DAYS = 45


class IndexMABreadthStrategy(IndustryMABreadthStrategy):
    """指数 MA 市场宽度策略类。

    功能：
    - 提供“指数成分股内收盘价高于 N 日均线占比”的计算能力。
    - 复用 IndustryMABreadthStrategy 的日期处理、交易日历、因子拉取与均线构建逻辑。

    参数：
    - 通过方法入参传递。

    返回值：
    - 列表结构，便于 API 直接返回。

    事件：
    - `get_index_ma_breadth` 执行核心计算并缓存。
    """

    def _fetch_index_members(
        self,
        index_code: str,
        end_date: str,
    ) -> Tuple[List[str], List[str]]:
        """获取指定指数最新可用交易日的成分股代码列表。

        参数：
        - index_code (str): 指数代码，例如 000300.SH。
        - end_date (str): 截止日期，格式 YYYY-MM-DD。

        返回值：
        - Tuple[List[str], List[str]]: (成分股代码列表, 提示/错误信息列表)。

        异常：
        - 无。内部异常会记录日志并通过错误列表返回。
        """
        errors: List[str] = []
        normalized_index_code = str(index_code or "").strip()
        if not normalized_index_code:
            return [], ["指数代码为空"]

        end_norm = self._normalize_trade_date(end_date)
        try:
            end_dt = datetime.strptime(end_norm, "%Y%m%d").date()
        except ValueError:
            return [], [f"{normalized_index_code} 截止日期格式错误: {end_date}"]

        start_norm = (end_dt - timedelta(days=INDEX_WEIGHT_LOOKBACK_DAYS)).strftime("%Y%m%d")

        resp = call_tushare(
            "index_weight",
            params={
                "index_code": normalized_index_code,
                "start_date": start_norm,
                "end_date": end_norm,
            },
            fields="index_code,con_code,trade_date,weight",
            use_query=False,
        )
        if not isinstance(resp, dict) or resp.get("code") != 200:
            message = resp.get("message") if isinstance(resp, dict) else str(resp)
            errors.append(f"{normalized_index_code} 获取指数成分(index_weight)失败: {message}")
            return [], errors

        data = resp.get("data", {})
        records = data.get("records", []) if isinstance(data, dict) else []
        records = [item for item in records if isinstance(item, dict)]
        if not records:
            errors.append(f"{normalized_index_code} 在最近 {INDEX_WEIGHT_LOOKBACK_DAYS} 天内无 index_weight 成分数据")
            return [], errors

        weight_df = pd.DataFrame(records)
        if "con_code" not in weight_df.columns or "trade_date" not in weight_df.columns:
            errors.append(f"{normalized_index_code} index_weight 返回数据缺少必要字段(con_code, trade_date)")
            return [], errors

        weight_df["trade_date"] = weight_df["trade_date"].astype(str).map(self._normalize_trade_date)
        latest_trade_date = weight_df["trade_date"].max()
        latest_members = weight_df[weight_df["trade_date"] == latest_trade_date]
        con_codes = sorted(
            {
                str(code or "").strip()
                for code in latest_members["con_code"].tolist()
                if str(code or "").strip()
            }
        )
        if not con_codes:
            errors.append(f"{normalized_index_code} 最新成分股列表为空")
        return con_codes, errors

    def _build_index_member_frame(
        self,
        index_mapping: Dict[str, str],
        end_date: str,
    ) -> Tuple[pd.DataFrame, List[str]]:
        """构建指数成分股映射数据框。

        参数：
        - index_mapping (Dict[str, str]): 指数代码到指数名称的映射。
        - end_date (str): 截止日期，格式 YYYY-MM-DD。

        返回值：
        - Tuple[pd.DataFrame, List[str]]: (含 stock_id/index_code/index_name 的数据框, 提示信息列表)。

        异常：
        - 无。
        """
        errors: List[str] = []
        member_rows: List[Dict] = []
        for index_code, index_name in index_mapping.items():
            con_codes, member_errors = self._fetch_index_members(index_code, end_date)
            errors.extend(member_errors)
            for stock_id in con_codes:
                member_rows.append(
                    {
                        "stock_id": stock_id,
                        "index_code": index_code,
                        "index_name": index_name,
                    }
                )
        if not member_rows:
            return pd.DataFrame(columns=["stock_id", "index_code", "index_name"]), errors
        return pd.DataFrame(member_rows).drop_duplicates(), errors

    def get_index_ma_breadth(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ma_window: int = 20,
        index_codes: Optional[List[str]] = None,
    ) -> Tuple[Optional[List[Dict]], List[str]]:
        """计算指数 MA 市场宽度。

        功能：
        - 在指定日期范围内，计算每个指数“收盘价高于 MA_N”的成分股占比。
        - 指数成分股通过 Tushare `index_weight` 获取；均线与占比计算逻辑与
          行业 MA 市场宽度（industry-ma-breadth）保持一致。

        参数：
        - start_date (Optional[str]): 开始日期，格式 YYYY-MM-DD。
        - end_date (Optional[str]): 结束日期，格式 YYYY-MM-DD。
        - ma_window (int): 移动平均窗口大小（交易日）。
        - index_codes (Optional[List[str]]): 指定指数代码列表；为空则使用默认指数列表
          （与 major-index-rps 一致）。

        返回值：
        - Tuple[Optional[List[Dict]], List[str]]: (每日每指数的宽度结果列表, 提示/错误信息列表)；
          计算失败返回 (None, errors)。

        异常：
        - 无。内部异常会记录日志并通过错误列表返回。
        """
        errors: List[str] = []
        try:
            if ma_window <= 1:
                ma_window = 2

            if index_codes:
                index_mapping = {
                    str(code).strip(): DEFAULT_INDEX_MAPPING.get(str(code).strip(), str(code).strip())
                    for code in index_codes
                    if str(code or "").strip()
                }
            else:
                index_mapping = dict(DEFAULT_INDEX_MAPPING)

            if not index_mapping:
                return None, ["未指定有效的指数代码"]

            start_date, end_date = self._get_default_dates(start_date, end_date)
            cache_key = (
                "index_ma_breadth_v1_"
                f"{start_date}_{end_date}_{ma_window}_"
                f"{'-'.join(sorted(index_mapping.keys()))}"
            )
            try:
                cached = cache.get(cache_key)
                if cached is not None and isinstance(cached, tuple):
                    logger.info("从缓存获取指数 MA 市场宽度数据")
                    return cached
            except Exception as exc:
                logger.warning("读取指数 MA 市场宽度缓存失败，将直接计算: %s", exc)

            member_df, member_errors = self._build_index_member_frame(index_mapping, end_date)
            errors.extend(member_errors)
            if member_df.empty:
                errors.append("未获取到任何指数的成分股数据")
                return [], errors

            output_trade_dates = self._get_trade_dates(start_date, end_date)
            if not output_trade_dates:
                errors.append("指定区间内未获取到有效交易日")
                return [], errors

            use_precomputed_ma = ma_window in SUPPORTED_PRECOMPUTED_WINDOWS
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            extended_start_dt = start_dt if use_precomputed_ma else start_dt - timedelta(days=ma_window * 2)
            all_trade_dates = (
                output_trade_dates
                if use_precomputed_ma
                else self._get_trade_dates(extended_start_dt.strftime("%Y-%m-%d"), end_date)
            )
            if not all_trade_dates:
                errors.append("未获取到计算均线所需的交易日")
                return [], errors

            target_codes: Set[str] = set(member_df["stock_id"].tolist())
            factor_request_dates = output_trade_dates if use_precomputed_ma else all_trade_dates
            factor_fields = (
                f"ts_code,trade_date,close,ma_bfq_{ma_window}"
                if use_precomputed_ma
                else "ts_code,trade_date,close"
            )
            factor_rows = self._fetch_factor_rows(factor_request_dates, factor_fields, target_codes)
            if not factor_rows:
                errors.append("stk_factor_pro 未返回可用技术指标数据")
                return [], errors

            output_dates = set(output_trade_dates)
            if use_precomputed_ma:
                factor_df = self._build_supported_window_frame(factor_rows, ma_window, output_dates)
            else:
                factor_df = self._build_rolling_window_frame(factor_rows, ma_window, output_dates)

            if factor_df.empty:
                errors.append("未构建出可用的股票 MA 数据")
                return [], errors

            factor_df = factor_df.merge(member_df, on="stock_id", how="inner")
            if factor_df.empty:
                errors.append("技术指标数据与指数成分映射合并后为空")
                return [], errors

            factor_df["above_ma"] = factor_df["close_price"] > factor_df["ma_close"]
            agg_df = (
                factor_df.groupby(["trade_date", "index_code", "index_name"])
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

            result = (
                agg_df[
                    ["date", "index_code", "index_name", "count_above_ma", "eligible_count", "breadth_ratio"]
                ]
                .sort_values(["date", "index_code"])
                .to_dict("records")
            )

            payload = (result, errors)
            try:
                cache.set(cache_key, payload, self.cache_timeout)
            except Exception as exc:
                logger.warning("写入指数 MA 市场宽度缓存失败: %s", exc)

            logger.info(
                "指数 MA 宽度计算完成: indexes=%s factor_trade_dates=%s result_rows=%s",
                len(index_mapping),
                len(factor_request_dates),
                len(result),
            )
            return payload
        except Exception as exc:
            logger.error("计算指数 MA 市场宽度失败: %s", exc)
            errors.append(f"计算指数 MA 市场宽度失败: {str(exc)}")
            return None, errors


index_ma_breadth_strategy = IndexMABreadthStrategy()
