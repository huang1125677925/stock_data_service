import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd
from django.core.cache import cache

from common.tushare_proxy import call_tushare
from stock_strategy.data_tasks.dc_board_rps import (
    _ensure_date_str,
    _get_latest_trade_date,
    _get_recent_trade_dates,
)

logger = logging.getLogger(__name__)


DEFAULT_PERIODS = [5, 20, 60]
DEFAULT_INDUSTRY_MAPPING = "default"


def _apply_rps(values: pd.Series) -> pd.Series:
    ranks = values.rank(ascending=False, method="min")
    total = len(values)
    return ((1.0 - ranks / total) * 100.0).round(2)


def _fetch_stock_basic_by_status(
    list_status: str,
    token: Optional[str],
    exchange: Optional[str],
    market: str = "主板",
) -> pd.DataFrame:
    columns = ["ts_code", "symbol", "name", "industry", "market", "list_date", "delist_date", "list_status"]
    params = {"list_status": list_status, "market": market}
    if exchange:
        params["exchange"] = exchange

    resp = call_tushare(
        "stock_basic",
        params=params,
        token=token,
        fields="ts_code,symbol,name,industry,market,list_date,delist_date,list_status",
        use_query=False,
    )
    if resp.get("code") != 200:
        return pd.DataFrame(columns=columns)

    records = (resp.get("data") or {}).get("records") or []
    if not records:
        return pd.DataFrame(columns=columns)

    out = pd.DataFrame.from_records(records)
    if out.empty:
        return pd.DataFrame(columns=columns)

    for column in columns:
        if column not in out.columns:
            out[column] = ""
        out[column] = out[column].fillna("").astype(str).str.strip()
    return out[columns]


def _fetch_stock_basic_all_statuses(
    token: Optional[str],
    exchange: Optional[str],
    market: str = "主板",
) -> pd.DataFrame:
    cache_key = f"potential_stock:stock_basic:v1:{exchange or ''}:{market}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    frames = [
        _fetch_stock_basic_by_status(status, token=token, exchange=exchange, market=market)
        for status in ["L", "P", "D"]
    ]
    valid_frames = [frame for frame in frames if frame is not None and not frame.empty]
    if not valid_frames:
        empty_df = pd.DataFrame(
            columns=["ts_code", "symbol", "name", "industry", "market", "list_date", "delist_date", "list_status"]
        )
        cache.set(cache_key, empty_df, 43200)
        return empty_df

    merged_df = pd.concat(valid_frames, ignore_index=True)
    merged_df = merged_df.drop_duplicates(subset=["ts_code"], keep="first").reset_index(drop=True)
    cache.set(cache_key, merged_df, 43200)
    return merged_df


def _filter_stock_universe_by_trade_date(stock_basic_df: pd.DataFrame, trade_date: str) -> pd.DataFrame:
    columns = ["ts_code", "symbol", "name", "industry", "market", "list_date", "delist_date", "list_status"]
    if stock_basic_df is None or stock_basic_df.empty:
        return pd.DataFrame(columns=columns)

    out = stock_basic_df.copy()
    normalized_trade_date = str(trade_date)
    out["list_date"] = out["list_date"].fillna("").astype(str).str.replace("-", "", regex=False)
    out["delist_date"] = out["delist_date"].fillna("").astype(str).str.replace("-", "", regex=False)

    listed_mask = out["list_date"].ne("") & (out["list_date"] <= normalized_trade_date)
    not_delisted_mask = out["delist_date"].eq("") | (out["delist_date"] >= normalized_trade_date)
    out = out[listed_mask & not_delisted_mask].copy()
    if out.empty:
        return out
    return out.drop_duplicates(subset=["ts_code"]).reset_index(drop=True)


def _fetch_daily_basic_by_trade_date(trade_date: str, token: Optional[str]) -> pd.DataFrame:
    columns = ["ts_code", "latest_price", "total_mv", "circ_mv"]
    resp = call_tushare(
        "daily_basic",
        params={"trade_date": trade_date},
        token=token,
        fields="ts_code,close,total_mv,circ_mv",
        use_query=False,
    )
    if resp.get("code") != 200:
        return pd.DataFrame(columns=columns)

    records = (resp.get("data") or {}).get("records") or []
    if not records:
        return pd.DataFrame(columns=columns)

    out = pd.DataFrame.from_records(records)
    if out.empty:
        return pd.DataFrame(columns=columns)

    out["ts_code"] = out["ts_code"].fillna("").astype(str).str.strip()
    out["latest_price"] = pd.to_numeric(out.get("close"), errors="coerce")
    out["total_mv"] = pd.to_numeric(out.get("total_mv"), errors="coerce") * 10000.0
    out["circ_mv"] = pd.to_numeric(out.get("circ_mv"), errors="coerce") * 10000.0
    out = out.dropna(subset=["ts_code"])
    return out[columns].drop_duplicates(subset=["ts_code"])


def _resolve_latest_available_trade_date(
    preferred_date: str,
    stock_basic_df: pd.DataFrame,
    token: Optional[str],
    max_fallback_count: int = 5,
) -> Tuple[Optional[str], pd.DataFrame, pd.DataFrame, List[str]]:
    warnings: List[str] = []
    candidate_dates = _get_recent_trade_dates(preferred_date, token=token, max_count=max_fallback_count)
    if not candidate_dates:
        candidate_dates = [preferred_date]

    for candidate_date in candidate_dates:
        universe_df = _filter_stock_universe_by_trade_date(stock_basic_df, candidate_date)
        if universe_df.empty:
            continue

        daily_basic_df = _fetch_daily_basic_by_trade_date(candidate_date, token=token)
        if daily_basic_df.empty:
            continue

        matched_df = universe_df[universe_df["ts_code"].isin(set(daily_basic_df["ts_code"].astype(str)))].copy()
        if matched_df.empty:
            continue

        if candidate_date != preferred_date:
            warnings.append(
                f"daily_basic在{preferred_date}无可用数据，已自动回退至最近可用交易日{candidate_date}"
            )
        return candidate_date, matched_df.reset_index(drop=True), daily_basic_df, warnings

    return None, pd.DataFrame(), pd.DataFrame(), warnings


def _fetch_daily_ohlcv_by_trade_date(trade_date: str, token: Optional[str]) -> pd.DataFrame:
    """
    功能：按交易日拉取全市场股票 OHLCV 快照，用于突破形态筛选。

    Args:
        trade_date: 交易日，格式 YYYYMMDD。
        token: Tushare Token，可选。

    Returns:
        pandas.DataFrame: 包含 ts_code、trade_date、open、high、low、close、vol、pct_change 的表。
    """
    columns = ["ts_code", "trade_date", "open", "high", "low", "close", "vol", "pct_change"]
    resp = call_tushare(
        "daily",
        params={"trade_date": trade_date},
        token=token,
        fields="ts_code,trade_date,open,high,low,close,vol,pct_chg",
        use_query=False,
    )
    if resp.get("code") != 200:
        return pd.DataFrame(columns=columns)

    records = (resp.get("data") or {}).get("records") or []
    if not records:
        return pd.DataFrame(columns=columns)

    out = pd.DataFrame.from_records(records)
    if out.empty:
        return pd.DataFrame(columns=columns)

    out["ts_code"] = out["ts_code"].fillna("").astype(str).str.strip()
    out["trade_date"] = out["trade_date"].fillna("").astype(str).str.strip()
    for column in ["open", "high", "low", "close", "vol"]:
        out[column] = pd.to_numeric(out.get(column), errors="coerce")
    out["pct_change"] = pd.to_numeric(out.get("pct_chg"), errors="coerce")
    out = out.dropna(subset=["ts_code", "trade_date", "close"])
    return out[columns].drop_duplicates(subset=["ts_code"])


def _build_ohlcv_history(
    trade_dates: List[str],
    stock_codes: List[str],
    token: Optional[str],
) -> pd.DataFrame:
    """
    功能：批量构建股票 OHLCV 历史行情。

    Args:
        trade_dates: 交易日列表，格式 YYYYMMDD。
        stock_codes: 股票代码列表。
        token: Tushare Token，可选。

    Returns:
        pandas.DataFrame: 多日 OHLCV 行情，按 ts_code/trade_date 升序排列。
    """
    stock_code_set = set(stock_codes)
    frames: List[pd.DataFrame] = []
    for trade_date in sorted(set(trade_dates)):
        daily_df = _fetch_daily_ohlcv_by_trade_date(trade_date, token=token)
        if daily_df.empty:
            continue
        filtered_df = daily_df[daily_df["ts_code"].isin(stock_code_set)].copy()
        if not filtered_df.empty:
            frames.append(filtered_df)

    if not frames:
        return pd.DataFrame(columns=["ts_code", "trade_date", "open", "high", "low", "close", "vol", "pct_change"])

    out = pd.concat(frames, ignore_index=True)
    return out.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)


def _safe_float(value) -> Optional[float]:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return round(numeric, 4) if pd.notna(numeric) else None


def _score_candidate(row: pd.Series) -> Tuple[int, List[str]]:
    score = 0
    tags: List[str] = []

    if bool(row.get("is_breakout")):
        score += 25
        tags.append("突破前高")
    if bool(row.get("volume_confirmed")):
        score += 18
        tags.append("放量确认")
    if bool(row.get("ma_aligned")):
        score += 18
        tags.append("均线多头")
    if bool(row.get("base_depth_ok")):
        score += 12
        tags.append("平台回撤可控")
    if bool(row.get("not_overextended")):
        score += 10
        tags.append("未明显乖离")

    rps_20 = _safe_float(row.get("RPS_20")) or 0.0
    rps_60 = _safe_float(row.get("RPS_60")) or 0.0
    rps_today = _safe_float(row.get("RPS_today")) or 0.0
    if rps_20 >= 90 or rps_60 >= 90:
        score += 12
        tags.append("RPS极强")
    elif rps_20 >= 80 or rps_60 >= 80:
        score += 8
        tags.append("RPS强势")
    if rps_today >= 80:
        score += 5
        tags.append("当日强势")

    return min(score, 100), tags


def _compute_shape_metrics(
    history_df: pd.DataFrame,
    lookback_days: int,
    min_breakout_pct: float,
    max_breakout_pct: float,
    min_volume_ratio: float,
    max_base_depth_pct: float,
    max_distance_ma20_pct: float,
) -> pd.DataFrame:
    rows: List[Dict] = []
    if history_df.empty:
        return pd.DataFrame()

    for ts_code, group in history_df.groupby("ts_code"):
        bars = group.sort_values("trade_date").reset_index(drop=True)
        if len(bars) < max(25, min(lookback_days, 60) // 2):
            continue

        latest = bars.iloc[-1]
        previous = bars.iloc[:-1].tail(lookback_days)
        if previous.empty:
            continue

        close_series = bars["close"]
        volume_series = bars["vol"]
        close = float(latest["close"])
        prev_high = float(previous["high"].max())
        base_low = float(previous["low"].min())
        prev_close = float(bars.iloc[-2]["close"]) if len(bars) >= 2 else close

        ma5 = close_series.tail(5).mean()
        ma10 = close_series.tail(10).mean()
        ma20 = close_series.tail(20).mean()
        ma60 = close_series.tail(60).mean() if len(close_series) >= 60 else pd.NA
        ma20_prev = close_series.iloc[:-5].tail(20).mean() if len(close_series) >= 25 else pd.NA

        avg_vol5 = volume_series.iloc[:-1].tail(5).mean()
        avg_vol10 = volume_series.iloc[:-1].tail(10).mean()
        volume_ratio_5 = float(latest["vol"] / avg_vol5) if avg_vol5 and avg_vol5 > 0 else pd.NA
        volume_ratio_10 = float(latest["vol"] / avg_vol10) if avg_vol10 and avg_vol10 > 0 else pd.NA

        breakout_pct = (close / prev_high - 1.0) * 100.0 if prev_high > 0 else pd.NA
        base_depth_pct = (prev_high / base_low - 1.0) * 100.0 if base_low > 0 else pd.NA
        distance_ma20_pct = (close / ma20 - 1.0) * 100.0 if ma20 and ma20 > 0 else pd.NA
        ma20_slope_pct = (ma20 / ma20_prev - 1.0) * 100.0 if pd.notna(ma20_prev) and ma20_prev > 0 else pd.NA

        is_breakout = pd.notna(breakout_pct) and min_breakout_pct <= breakout_pct <= max_breakout_pct
        volume_confirmed = pd.notna(volume_ratio_5) and volume_ratio_5 >= min_volume_ratio
        ma_aligned = bool(ma5 > ma10 > ma20 and close > ma20 and (pd.isna(ma60) or ma20 >= ma60 * 0.98))
        base_depth_ok = pd.notna(base_depth_pct) and base_depth_pct <= max_base_depth_pct
        not_overextended = pd.notna(distance_ma20_pct) and distance_ma20_pct <= max_distance_ma20_pct

        rows.append(
            {
                "ts_code": ts_code,
                "latest_trade_date": str(latest["trade_date"]),
                "latest_close": close,
                "previous_close": prev_close,
                "prev_high": prev_high,
                "base_low": base_low,
                "breakout_pct": breakout_pct,
                "base_depth_pct": base_depth_pct,
                "volume_ratio_5": volume_ratio_5,
                "volume_ratio_10": volume_ratio_10,
                "ma5": ma5,
                "ma10": ma10,
                "ma20": ma20,
                "ma60": ma60,
                "ma20_slope_pct": ma20_slope_pct,
                "distance_ma20_pct": distance_ma20_pct,
                "is_breakout": is_breakout,
                "volume_confirmed": volume_confirmed,
                "ma_aligned": ma_aligned,
                "base_depth_ok": base_depth_ok,
                "not_overextended": not_overextended,
                "is_limit_up_like": _safe_float(latest.get("pct_change")) is not None and float(latest.get("pct_change")) >= 9.5,
            }
        )

    return pd.DataFrame(rows)


def _compute_rps_metrics(history_df: pd.DataFrame, periods: List[int]) -> pd.DataFrame:
    if history_df.empty:
        return pd.DataFrame()

    latest_rows = (
        history_df.sort_values(["ts_code", "trade_date"])
        .groupby("ts_code", as_index=False)
        .tail(1)
        .copy()
    )
    result_df = latest_rows[["ts_code", "trade_date", "close", "pct_change"]].rename(
        columns={
            "trade_date": "trade_date",
            "close": "latest_close",
        }
    )
    result_df["pct_change"] = pd.to_numeric(result_df["pct_change"], errors="coerce")
    result_df["RPS_today"] = _apply_rps(result_df["pct_change"].fillna(-999))

    for period in periods:
        rows: List[Dict] = []
        for ts_code, group in history_df.groupby("ts_code"):
            bars = group.sort_values("trade_date").reset_index(drop=True)
            if len(bars) < period + 1:
                continue
            start_close = pd.to_numeric(bars.iloc[-period - 1]["close"], errors="coerce")
            end_close = pd.to_numeric(bars.iloc[-1]["close"], errors="coerce")
            if pd.isna(start_close) or pd.isna(end_close) or start_close <= 0:
                continue
            rows.append({
                "ts_code": ts_code,
                f"return_{period}": (float(end_close) / float(start_close) - 1.0) * 100.0,
            })

        period_df = pd.DataFrame(rows)
        if period_df.empty:
            result_df[f"return_{period}"] = pd.NA
            result_df[f"RPS_{period}"] = pd.NA
            continue
        period_df[f"RPS_{period}"] = _apply_rps(period_df[f"return_{period}"].fillna(-999))
        result_df = result_df.merge(period_df, on="ts_code", how="left")

    return result_df


def compute_potential_stock_candidates(
    periods: Optional[List[int]] = None,
    trade_date: Optional[str] = None,
    token: Optional[str] = None,
    exchange: Optional[str] = "SSE",
    industry_mapping: str = DEFAULT_INDUSTRY_MAPPING,
    lookback_days: int = 60,
    min_rps_20: float = 80.0,
    min_rps_60: float = 70.0,
    min_volume_ratio: float = 1.3,
    min_breakout_pct: float = 0.0,
    max_breakout_pct: float = 12.0,
    max_base_depth_pct: float = 35.0,
    max_distance_ma20_pct: float = 25.0,
    max_price: float = 30.0,
    max_circ_mv: float = 50000000000.0,
    limit: int = 100,
) -> Tuple[Optional[pd.DataFrame], List[str], Dict]:
    """
    功能：筛选指定交易所主板中接近“突破前高 + 趋势加速”形态的潜力股票。

    Returns:
        Tuple[pandas.DataFrame|None, List[str], Dict]: 候选列表、提示信息、筛选元数据。
    """
    errors: List[str] = []
    normalized_periods = [int(period) for period in (periods or DEFAULT_PERIODS)]
    if 20 not in normalized_periods:
        normalized_periods.append(20)
    if 60 not in normalized_periods:
        normalized_periods.append(60)
    normalized_periods = sorted(set(normalized_periods))

    preferred_end_date = _ensure_date_str(trade_date)
    if trade_date is None:
        latest = _get_latest_trade_date(token)
        if latest:
            preferred_end_date = latest

    cache_key = (
        "potential_stock_candidates:v3:"
        f"{preferred_end_date}:{exchange or ''}:{','.join(map(str, normalized_periods))}:"
        f"{lookback_days}:{min_rps_20}:{min_rps_60}:{min_volume_ratio}:"
        f"{min_breakout_pct}:{max_breakout_pct}:{max_base_depth_pct}:{max_distance_ma20_pct}:"
        f"{max_price}:{max_circ_mv}:{limit}"
    )
    cached = cache.get(cache_key)
    if cached:
        return cached

    stock_basic_df = _fetch_stock_basic_all_statuses(token=token, exchange=exchange, market="主板")
    if stock_basic_df.empty:
        errors.append("未获取到主板股票基础信息")
        return None, errors, {}

    if trade_date is None:
        resolved = _resolve_latest_available_trade_date(
            preferred_end_date,
            stock_basic_df=stock_basic_df,
            token=token,
        )
        end_date, universe_df, daily_basic_df, fallback_warnings = resolved
        errors.extend(fallback_warnings)
        if not end_date or universe_df.empty:
            errors.append("未获取到可用主板股票池")
            return None, errors, {}
    else:
        end_date = preferred_end_date
        universe_df = _filter_stock_universe_by_trade_date(stock_basic_df, end_date)
        if universe_df.empty:
            errors.append("目标交易日无可用主板股票池")
            return None, errors, {}
        daily_basic_df = _fetch_daily_basic_by_trade_date(end_date, token=token)
        if daily_basic_df.empty:
            errors.append(f"daily_basic返回空数据: trade_date={end_date}")
            return None, errors, {}

    prefilter_total = len(universe_df)
    candidate_df = universe_df.merge(daily_basic_df, on="ts_code", how="inner")
    name_series = candidate_df["name"].fillna("").astype(str)
    candidate_df = candidate_df[~name_series.str.contains("ST", case=False, na=False)].copy()
    candidate_df["latest_price"] = pd.to_numeric(candidate_df["latest_price"], errors="coerce")
    candidate_df["circ_mv"] = pd.to_numeric(candidate_df["circ_mv"], errors="coerce")
    candidate_df = candidate_df[
        (candidate_df["latest_price"].notna())
        & (candidate_df["circ_mv"].notna())
        & (candidate_df["latest_price"] <= max_price)
        & (candidate_df["circ_mv"] <= max_circ_mv)
    ].copy()
    prefiltered_total = len(candidate_df)
    if candidate_df.empty:
        errors.append("价格和流通市值预过滤后无候选股票")
        return pd.DataFrame(), errors, {
            "trade_date": end_date,
            "rps_total": prefilter_total,
            "universe_total": prefilter_total,
            "prefiltered_total": 0,
            "scanned_total": 0,
            "history_start_date": "",
            "history_end_date": "",
        }

    required_dates = _get_recent_trade_dates(end_date, token=token, max_count=max(lookback_days + 1, max(normalized_periods) + 1))
    if not required_dates:
        errors.append("未获取到交易日历")
        return None, errors, {}

    stock_codes = candidate_df["ts_code"].dropna().astype(str).tolist()
    history_df = _build_ohlcv_history(required_dates, stock_codes=stock_codes, token=token)
    if history_df.empty:
        errors.append("未获取到主板股票历史行情")
        return None, errors, {}

    rps_df = _compute_rps_metrics(history_df, periods=normalized_periods)
    if rps_df.empty:
        errors.append("未计算出有效RPS指标")
        return None, errors, {}

    metrics_df = _compute_shape_metrics(
        history_df=history_df,
        lookback_days=lookback_days,
        min_breakout_pct=min_breakout_pct,
        max_breakout_pct=max_breakout_pct,
        min_volume_ratio=min_volume_ratio,
        max_base_depth_pct=max_base_depth_pct,
        max_distance_ma20_pct=max_distance_ma20_pct,
    )
    if metrics_df.empty:
        errors.append("未计算出有效形态指标")
        return None, errors, {}

    merged_df = candidate_df.merge(rps_df, on="ts_code", how="inner", suffixes=("", "_rps"))
    merged_df = merged_df.merge(metrics_df, on="ts_code", how="inner", suffixes=("", "_shape"))
    if merged_df.empty:
        errors.append("RPS数据与历史行情未匹配")
        return None, errors, {}

    merged_df["RPS_20"] = pd.to_numeric(merged_df.get("RPS_20"), errors="coerce")
    merged_df["RPS_60"] = pd.to_numeric(merged_df.get("RPS_60"), errors="coerce")

    filtered_df = merged_df[
        (merged_df["is_breakout"])
        & (merged_df["volume_confirmed"])
        & (merged_df["ma_aligned"])
        & (merged_df["base_depth_ok"])
        & (merged_df["not_overextended"])
        & (merged_df["RPS_20"].fillna(0) >= min_rps_20)
        & (merged_df["RPS_60"].fillna(0) >= min_rps_60)
    ].copy()

    if filtered_df.empty:
        filtered_df = merged_df[
            (merged_df["is_breakout"])
            & (merged_df["volume_confirmed"])
            & (merged_df["RPS_20"].fillna(0) >= min_rps_20)
        ].copy()
        if not filtered_df.empty:
            errors.append("严格趋势条件无结果，已放宽为突破+放量+RPS20")

    if filtered_df.empty:
        errors.append("未筛选到符合条件的潜力股票")
        meta = {
            "trade_date": end_date,
            "scanned_total": len(merged_df),
            "rps_total": prefilter_total,
            "universe_total": prefilter_total,
            "prefiltered_total": prefiltered_total,
            "history_start_date": min(required_dates),
            "history_end_date": max(required_dates),
        }
        return filtered_df, errors, meta

    scores = filtered_df.apply(_score_candidate, axis=1)
    filtered_df["setup_score"] = [item[0] for item in scores]
    filtered_df["setup_tags"] = [item[1] for item in scores]
    filtered_df["signal"] = filtered_df["is_limit_up_like"].apply(lambda value: "涨停突破" if value else "放量突破")

    sort_columns = ["setup_score", "RPS_20", "RPS_60", "volume_ratio_5"]
    filtered_df = filtered_df.sort_values(sort_columns, ascending=False, na_position="last").head(limit)

    numeric_columns = [
        "latest_close", "previous_close", "prev_high", "base_low", "breakout_pct", "base_depth_pct",
        "volume_ratio_5", "volume_ratio_10", "ma5", "ma10", "ma20", "ma60", "ma20_slope_pct",
        "distance_ma20_pct",
    ]
    for column in numeric_columns:
        if column in filtered_df.columns:
            filtered_df[column] = filtered_df[column].apply(_safe_float)

    meta = {
        "trade_date": end_date,
        "scanned_total": len(merged_df),
        "rps_total": prefilter_total,
        "universe_total": prefilter_total,
        "prefiltered_total": prefiltered_total,
        "history_start_date": min(required_dates),
        "history_end_date": max(required_dates),
    }
    result = (filtered_df.reset_index(drop=True), errors, meta)
    cache.set(cache_key, result, 900)
    return result
