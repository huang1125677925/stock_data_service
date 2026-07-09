import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from django.core.cache import cache

from common.tushare_proxy import call_tushare
from stock_strategy.data_tasks.dc_board_rps import (
    _apply_rps,
    _ensure_date_str,
    _get_latest_trade_date,
    _get_period_start_trade_dates,
)


def _fetch_dc_board_members(
    trade_date: str,
    board_ts_code: str,
    token: Optional[str],
) -> pd.DataFrame:
    """
    获取指定东财板块在某个交易日的成分股列表。

    Args:
        trade_date: 查询交易日，格式为 YYYYMMDD。
        board_ts_code: 东财板块代码，例如 BK1462.DC。
        token: Tushare Token，可选，优先覆盖环境变量中的配置。

    Returns:
        pandas.DataFrame: 板块成分股数据，至少包含 con_code、name、trade_date、ts_code 列；
        当接口调用失败或无数据时返回空 DataFrame。

    Raises:
        无。函数内部会吞掉接口异常并以空 DataFrame 兜底。
    """
    resp = call_tushare(
        "dc_member",
        params={"trade_date": trade_date, "ts_code": board_ts_code},
        token=token,
        fields="trade_date,ts_code,con_code,name",
        use_query=False,
    )
    if resp.get("code") != 200:
        return pd.DataFrame(columns=["trade_date", "ts_code", "con_code", "name"])

    records = (resp.get("data") or {}).get("records") or []
    if not records:
        return pd.DataFrame(columns=["trade_date", "ts_code", "con_code", "name"])

    out = pd.DataFrame.from_records(records)
    if out.empty:
        return pd.DataFrame(columns=["trade_date", "ts_code", "con_code", "name"])

    return out


def _fetch_dc_board_members_with_fallback(
    trade_date: str,
    board_ts_code: str,
    token: Optional[str],
    max_lookback: int = 7,
) -> Tuple[pd.DataFrame, str]:
    """
    获取板块成分股列表，若指定交易日无数据则按自然日逐日回退。

    当查询日恰逢周末、节假日或数据尚未更新时，dc_member 会返回空结果；此时
    依次回退到前一天重新查询，直到取到数据或达到最大回退次数。

    Args:
        trade_date: 起始查询交易日，格式为 YYYYMMDD。
        board_ts_code: 东财板块代码，例如 BK0732.DC。
        token: Tushare Token，可选，优先覆盖环境变量中的配置。
        max_lookback: 最大回退次数（按自然日回退），默认 7。

    Returns:
        Tuple[pandas.DataFrame, str]: 成分股 DataFrame 与实际命中的交易日；
        当回退耗尽仍无数据时，返回空 DataFrame 与最后一次尝试的日期。

    Raises:
        无。函数内部会吞掉接口异常并以空 DataFrame 兜底。
    """
    current_date = trade_date
    last_date = trade_date
    # 首次查询 + 最多 max_lookback 次回退
    for _ in range(max_lookback + 1):
        members_df = _fetch_dc_board_members(current_date, board_ts_code=board_ts_code, token=token)
        last_date = current_date
        if not members_df.empty:
            return members_df, current_date
        try:
            prev_dt = datetime.strptime(current_date, "%Y%m%d") - timedelta(days=1)
        except ValueError:
            break
        current_date = prev_dt.strftime("%Y%m%d")

    return pd.DataFrame(columns=["trade_date", "ts_code", "con_code", "name"]), last_date


def _fetch_dc_board_name(
    trade_date: str,
    board_ts_code: str,
    token: Optional[str],
) -> str:
    """
    获取指定东财板块在某个交易日对应的板块名称。

    Args:
        trade_date: 查询交易日，格式为 YYYYMMDD。
        board_ts_code: 东财板块代码，例如 BK1462.DC。
        token: Tushare Token，可选，优先覆盖环境变量中的配置。

    Returns:
        str: 板块名称；未命中时返回空字符串。

    Raises:
        无。函数内部会吞掉接口异常并返回空字符串。
    """
    resp = call_tushare(
        "dc_index",
        params={"trade_date": trade_date, "ts_code": board_ts_code},
        token=token,
        fields="ts_code,name,trade_date",
        use_query=False,
    )
    if resp.get("code") != 200:
        return ""

    records = (resp.get("data") or {}).get("records") or []
    if not records:
        return ""

    return str(records[0].get("name") or "").strip()


def _fetch_stock_daily_trade_date(
    trade_date: str,
    stock_codes: List[str],
    token: Optional[str],
) -> pd.DataFrame:
    """
    按交易日拉取指定股票集合的日线快照，仅保留 RPS 计算需要的字段。

    Args:
        trade_date: 查询交易日，格式为 YYYYMMDD。
        stock_codes: 股票代码列表，支持多个 Tushare ts_code。
        token: Tushare Token，可选，优先覆盖环境变量中的配置。

    Returns:
        pandas.DataFrame: 股票日线快照，包含 ts_code、trade_date、close、pct_change 列；
        当接口调用失败或无数据时返回空 DataFrame。

    Raises:
        无。函数内部会吞掉接口异常并以空 DataFrame 兜底。
    """
    if not stock_codes:
        return pd.DataFrame(columns=["ts_code", "trade_date", "close", "pct_change"])

    resp = call_tushare(
        "daily",
        params={"trade_date": trade_date, "ts_code": ",".join(stock_codes)},
        token=token,
        fields="ts_code,trade_date,close,pct_chg",
        use_query=False,
    )
    if resp.get("code") != 200:
        return pd.DataFrame(columns=["ts_code", "trade_date", "close", "pct_change"])

    records = (resp.get("data") or {}).get("records") or []
    if not records:
        return pd.DataFrame(columns=["ts_code", "trade_date", "close", "pct_change"])

    out = pd.DataFrame.from_records(records)
    if out.empty:
        return pd.DataFrame(columns=["ts_code", "trade_date", "close", "pct_change"])

    out["trade_date"] = out["trade_date"].astype(str)
    out["close"] = pd.to_numeric(out.get("close"), errors="coerce")
    out["pct_change"] = pd.to_numeric(out.get("pct_chg"), errors="coerce")
    out = out.dropna(subset=["ts_code", "trade_date", "close"])
    return out[["ts_code", "trade_date", "close", "pct_change"]]


def _build_stock_snapshot_map(
    trade_dates: List[str],
    stock_codes: List[str],
    token: Optional[str],
) -> Dict[str, pd.DataFrame]:
    """
    批量构造成分股在多个交易日的收盘价快照映射。

    Args:
        trade_dates: 需要抓取的交易日列表，格式为 YYYYMMDD。
        stock_codes: 成分股代码列表。
        token: Tushare Token，可选，优先覆盖环境变量中的配置。

    Returns:
        Dict[str, pandas.DataFrame]: 键为交易日，值为以 ts_code 为索引、包含 close/pct_change
        列的 DataFrame；若某天无数据则不会出现在映射中。

    Raises:
        无。函数内部会跳过无数据交易日。
    """
    snapshot_map: Dict[str, pd.DataFrame] = {}

    for trade_date in sorted(set(trade_dates)):
        daily_df = _fetch_stock_daily_trade_date(trade_date, stock_codes=stock_codes, token=token)
        if daily_df.empty:
            continue
        snapshot_map[trade_date] = daily_df.drop_duplicates(subset=["ts_code"]).set_index("ts_code")[
            ["close", "pct_change"]
        ]

    return snapshot_map


def _fetch_stock_market_map(token: Optional[str]) -> Dict[str, str]:
    """
    获取全市场上市股票的市场类型映射，仅调用一次 stock_basic 接口。

    Args:
        token: Tushare Token，可选，优先覆盖环境变量中的配置。

    Returns:
        Dict[str, str]: 键为 ts_code，值为市场类型（如 主板、创业板、科创板、北交所）；
        接口失败或无数据时返回空字典。

    Raises:
        无。函数内部会吞掉接口异常并以空字典兜底。
    """
    resp = call_tushare(
        "stock_basic",
        params={"list_status": "L"},
        token=token,
        fields="ts_code,market",
        use_query=False,
    )
    if resp.get("code") != 200:
        return {}

    records = (resp.get("data") or {}).get("records") or []
    if not records:
        return {}

    market_map: Dict[str, str] = {}
    for record in records:
        ts_code = str(record.get("ts_code") or "").strip()
        if not ts_code:
            continue
        market_map[ts_code] = str(record.get("market") or "").strip()

    return market_map


def compute_dc_board_member_rps(
    periods: List[int],
    board_ts_code: str = "BK1462.DC",
    trade_date: Optional[str] = None,
    token: Optional[str] = None,
) -> Tuple[Optional[pd.DataFrame], Dict[str, object], List[str]]:
    """
    计算指定东财板块成分股的多周期 RPS 排名。

    Args:
        periods: 回看交易日周期列表，例如 [5, 20, 60]。
        board_ts_code: 东财板块代码，默认 BK1462.DC。
        trade_date: 截止交易日，格式为 YYYYMMDD；为空时自动取最新交易日。
        token: Tushare Token，可选，优先覆盖环境变量中的配置。

    Returns:
        Tuple[Optional[pandas.DataFrame], Dict[str, object], List[str]]:
        - 第一个返回值：结果 DataFrame，包含 ts_code、name、pct_change、RPS_today、return_{p}、RPS_{p} 等列；
          当无法完成计算时返回 None。
        - 第二个返回值：元信息字典，包含 board_ts_code、board_name、trade_date、member_count。
        - 第三个返回值：错误信息列表，记录非致命告警或失败原因。

    Raises:
        无。函数内部捕获大部分异常，并通过 errors 返回错误信息。
    """
    errors: List[str] = []
    normalized_periods = [int(period) for period in periods]
    meta: Dict[str, object] = {
        "board_ts_code": board_ts_code,
        "board_name": "",
        "trade_date": "",
        "member_count": 0,
    }

    if not normalized_periods:
        errors.append("periods 不能为空")
        return None, meta, errors

    if any(period <= 0 for period in normalized_periods):
        errors.append("period 必须大于 0")
        return None, meta, errors

    end_date = _ensure_date_str(trade_date)
    if trade_date is None:
        latest = _get_latest_trade_date(token)
        if latest:
            end_date = latest

    meta["trade_date"] = end_date

    cache_key = f"dc_board_member_rps:v1:{board_ts_code}:{end_date}:{','.join(map(str, normalized_periods))}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    members_df, resolved_date = _fetch_dc_board_members_with_fallback(
        end_date, board_ts_code=board_ts_code, token=token
    )
    if members_df.empty:
        errors.append("未获取到板块成分股列表或 trade_date 无数据")
        return None, meta, errors

    # 回退命中的交易日可能早于请求日期，后续计算与元信息统一使用命中日期
    if resolved_date != end_date:
        errors.append(f"请求交易日 {end_date} 无数据，已回退至 {resolved_date}")
        end_date = resolved_date
        meta["trade_date"] = end_date

    board_name = _fetch_dc_board_name(end_date, board_ts_code=board_ts_code, token=token)
    meta["board_name"] = board_name or board_ts_code

    members_df = members_df.drop_duplicates(subset=["con_code"]).copy()
    result_df = members_df[["con_code", "name"]].rename(columns={"con_code": "ts_code"})
    stock_codes = result_df["ts_code"].dropna().astype(str).tolist()
    meta["member_count"] = len(stock_codes)

    if not stock_codes:
        errors.append("板块成分股为空")
        return None, meta, errors

    try:
        period_start_dates = _get_period_start_trade_dates(end_date, normalized_periods, token=token)
    except Exception as exc:
        errors.append(f"计算交易日起始区间失败: {str(exc)}")
        return None, meta, errors

    snapshot_dates = [end_date] + list(period_start_dates.values())
    daily_snapshot_map = _build_stock_snapshot_map(snapshot_dates, stock_codes=stock_codes, token=token)
    if end_date not in daily_snapshot_map:
        errors.append(f"daily返回空数据: trade_date={end_date}")
        return None, meta, errors

    market_map = _fetch_stock_market_map(token)
    result_df["market"] = result_df["ts_code"].map(market_map).fillna("")

    end_snapshot = daily_snapshot_map[end_date]
    result_df["close_end"] = result_df["ts_code"].map(end_snapshot["close"])
    result_df["close"] = result_df["close_end"]
    result_df["pct_change"] = result_df["ts_code"].map(end_snapshot["pct_change"])
    result_df["RPS_today"] = _apply_rps(result_df["pct_change"].fillna(-999))

    for period in normalized_periods:
        start_date = period_start_dates[period]
        start_snapshot = daily_snapshot_map.get(start_date)
        if start_snapshot is None or start_snapshot.empty:
            errors.append(f"daily返回空数据: period={period}, trade_date={start_date}")
            continue

        result_df[f"close_{period}"] = result_df["ts_code"].map(start_snapshot["close"])
        result_df[f"return_{period}"] = (result_df["close_end"] / result_df[f"close_{period}"] - 1.0) * 100.0
        result_df[f"RPS_{period}"] = _apply_rps(result_df[f"return_{period}"].fillna(-999))

    drop_columns = ["close_end"] + [f"close_{period}" for period in normalized_periods]
    result_df = result_df.drop(columns=drop_columns, errors="ignore")

    try:
        result_df = result_df.sort_values(by=[f"RPS_{normalized_periods[0]}"], ascending=False, na_position="last")
    except Exception:
        pass

    result = (result_df.reset_index(drop=True), meta, errors)
    cache.set(cache_key, result, 900)
    return result
