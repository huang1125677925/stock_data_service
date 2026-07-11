import json
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from django.core.cache import cache

from common.tushare_proxy import call_tushare
from stock_strategy.data_tasks.dc_board_rps import (
    _apply_rps,
    _ensure_date_str,
    _get_latest_trade_date,
    _get_period_start_trade_dates,
    _get_recent_trade_dates,
)

logger = logging.getLogger(__name__)

# 行业映射配置（从limit_board_service移植）
DC_BOARD_SNAPSHOT_FILE = (
    Path(__file__).resolve().parent.parent.parent / "data" / "dc_board_members_snapshot.json"
)

INDUSTRY_MAPPING_MODES: Dict[str, Dict[str, str]] = {
    "default": {"idx_type": "", "level": "", "label": "默认行业映射(stock_basic)"},
    "dc_concept": {"idx_type": "概念板块", "level": "", "label": "东财概念板块"},
    "dc_region": {"idx_type": "地域板块", "level": "", "label": "东财地域板块"},
    "dc_l1": {"idx_type": "行业板块", "level": "东财一级行业", "label": "东财一级行业板块"},
    "dc_l2": {"idx_type": "行业板块", "level": "东财二级行业", "label": "东财二级行业板块"},
    "dc_l3": {"idx_type": "行业板块", "level": "东财三级行业", "label": "东财三级行业板块"},
}

DEFAULT_INDUSTRY_MAPPING = "default"

_board_snapshot_cache: Optional[List[Dict]] = None


def _fetch_stock_basic_by_status(
    list_status: str,
    token: Optional[str],
    exchange: Optional[str] = None,
    market: Optional[str] = None,
) -> pd.DataFrame:
    """
    功能：按上市状态拉取股票基础信息列表。

    Args:
        list_status: 股票上市状态，支持 L（上市）、P（暂停上市）、D（退市）。
        token: Tushare Token，可选，优先覆盖环境变量中的配置。
        exchange: 交易所筛选，可选，例如 SSE、SZSE、BSE。
        market: 市场类型筛选，可选，例如 主板、创业板、科创板、北交所。

    Returns:
        pandas.DataFrame: 股票基础信息表，至少包含 ts_code、symbol、name、industry、market、
        list_date、delist_date、list_status 列；接口失败时返回空 DataFrame。

    Raises:
        无。函数内部通过空 DataFrame 兜底接口异常或空结果。
    """
    params = {"list_status": list_status}
    if exchange:
        params["exchange"] = exchange
    if market:
        params["market"] = market

    resp = call_tushare(
        "stock_basic",
        params=params,
        token=token,
        fields="ts_code,symbol,name,industry,market,list_date,delist_date,list_status",
        use_query=False,
    )
    if resp.get("code") != 200:
        return pd.DataFrame(
            columns=[
                "ts_code",
                "symbol",
                "name",
                "industry",
                "market",
                "list_date",
                "delist_date",
                "list_status",
            ]
        )

    records = (resp.get("data") or {}).get("records") or []
    if not records:
        return pd.DataFrame(
            columns=[
                "ts_code",
                "symbol",
                "name",
                "industry",
                "market",
                "list_date",
                "delist_date",
                "list_status",
            ]
        )

    out = pd.DataFrame.from_records(records)
    if out.empty:
        return pd.DataFrame(
            columns=[
                "ts_code",
                "symbol",
                "name",
                "industry",
                "market",
                "list_date",
                "delist_date",
                "list_status",
            ]
        )

    for column in ["ts_code", "symbol", "name", "industry", "market", "list_date", "delist_date", "list_status"]:
        if column not in out.columns:
            out[column] = ""
        out[column] = out[column].fillna("").astype(str).str.strip()

    return out[
        [
            "ts_code",
            "symbol",
            "name",
            "industry",
            "market",
            "list_date",
            "delist_date",
            "list_status",
        ]
    ]


def _fetch_stock_basic_all_statuses(
    token: Optional[str],
    exchange: Optional[str] = None,
    market: Optional[str] = None,
) -> pd.DataFrame:
    """
    功能：汇总上市、暂停上市和退市股票的基础信息，用于构建历史股票池。

    Args:
        token: Tushare Token，可选，优先覆盖环境变量中的配置。
        exchange: 交易所筛选，可选，例如 SSE、SZSE、BSE。
        market: 市场类型筛选，可选，例如 主板、创业板、科创板、北交所。

    Returns:
        pandas.DataFrame: 合并后的股票基础信息表，按 ts_code 去重；若全部状态均无数据则返回空 DataFrame。

    Raises:
        无。函数内部通过缓存和空 DataFrame 兜底。
    """
    cache_key = f"stock_rps:stock_basic:v1:{exchange or ''}:{market or ''}"
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
            columns=[
                "ts_code",
                "symbol",
                "name",
                "industry",
                "market",
                "list_date",
                "delist_date",
                "list_status",
            ]
        )
        cache.set(cache_key, empty_df, 43200)
        return empty_df

    merged_df = pd.concat(valid_frames, ignore_index=True)
    merged_df = merged_df.drop_duplicates(subset=["ts_code"], keep="first").reset_index(drop=True)
    cache.set(cache_key, merged_df, 43200)
    return merged_df


def _filter_stock_universe_by_trade_date(stock_basic_df: pd.DataFrame, trade_date: str) -> pd.DataFrame:
    """
    功能：根据目标交易日过滤股票池，仅保留在该日已上市且未退市的股票。

    Args:
        stock_basic_df: 股票基础信息表。
        trade_date: 目标交易日，格式为 YYYYMMDD。

    Returns:
        pandas.DataFrame: 过滤后的股票池，至少包含 ts_code、symbol、name、industry、market、
        list_date、delist_date、list_status 列；无符合条件时返回空 DataFrame。

    Raises:
        无。函数内部不会主动抛出异常。
    """
    if stock_basic_df is None or stock_basic_df.empty:
        return pd.DataFrame(
            columns=[
                "ts_code",
                "symbol",
                "name",
                "industry",
                "market",
                "list_date",
                "delist_date",
                "list_status",
            ]
        )

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


def _fetch_daily_snapshot_by_trade_date(trade_date: str, token: Optional[str]) -> pd.DataFrame:
    """
    功能：按单个交易日拉取全市场股票日线快照，并保留 RPS 计算所需字段。

    Args:
        trade_date: 查询交易日，格式为 YYYYMMDD。
        token: Tushare Token，可选，优先覆盖环境变量中的配置。

    Returns:
        pandas.DataFrame: 股票日线快照，包含 ts_code、trade_date、close、pct_change 列；
        接口失败或无数据时返回空 DataFrame。

    Raises:
        无。函数内部通过空 DataFrame 兜底。
    """
    resp = call_tushare(
        "daily",
        params={"trade_date": trade_date},
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
    功能：批量构建多个交易日的股票收盘价快照映射。

    Args:
        trade_dates: 需要抓取的交易日列表，格式为 YYYYMMDD。
        stock_codes: 股票代码列表，用于过滤快照范围。
        token: Tushare Token，可选，优先覆盖环境变量中的配置。

    Returns:
        Dict[str, pandas.DataFrame]: 键为交易日，值为以 ts_code 为索引、包含 close 和 pct_change
        列的 DataFrame；当某日无数据时该日期不会出现在结果中。

    Raises:
        无。函数内部会跳过无数据交易日。
    """
    snapshot_map: Dict[str, pd.DataFrame] = {}
    stock_code_set = set(stock_codes)

    for trade_date in sorted(set(trade_dates)):
        daily_df = _fetch_daily_snapshot_by_trade_date(trade_date, token=token)
        if daily_df.empty:
            continue

        filtered_df = daily_df[daily_df["ts_code"].isin(stock_code_set)].copy()
        if filtered_df.empty:
            continue

        snapshot_map[trade_date] = filtered_df.drop_duplicates(subset=["ts_code"]).set_index("ts_code")[
            ["close", "pct_change"]
        ]

    return snapshot_map


def _fetch_daily_basic_by_trade_date(trade_date: str, token: Optional[str]) -> pd.DataFrame:
    """
    功能：按单个交易日拉取全市场每日指标快照，提取最新股价与市值信息。

    Args:
        trade_date: 查询交易日，格式为 YYYYMMDD。
        token: Tushare Token，可选，优先覆盖环境变量中的配置。

    Returns:
        pandas.DataFrame: 每日指标快照，包含 ts_code、close、total_mv、circ_mv 列；
        接口失败或无数据时返回空 DataFrame。total_mv、circ_mv 单位为元
        （Tushare 原始单位为万元，此处已换算）。

    Raises:
        无。函数内部通过空 DataFrame 兜底。
    """
    empty_columns = ["ts_code", "close", "total_mv", "circ_mv"]
    resp = call_tushare(
        "daily_basic",
        params={"trade_date": trade_date},
        token=token,
        fields="ts_code,close,total_mv,circ_mv",
        use_query=False,
    )
    if resp.get("code") != 200:
        return pd.DataFrame(columns=empty_columns)

    records = (resp.get("data") or {}).get("records") or []
    if not records:
        return pd.DataFrame(columns=empty_columns)

    out = pd.DataFrame.from_records(records)
    if out.empty:
        return pd.DataFrame(columns=empty_columns)

    out["ts_code"] = out["ts_code"].astype(str)
    out["close"] = pd.to_numeric(out.get("close"), errors="coerce")
    # Tushare daily_basic 的 total_mv、circ_mv 单位为万元，换算为元
    out["total_mv"] = pd.to_numeric(out.get("total_mv"), errors="coerce") * 10000.0
    out["circ_mv"] = pd.to_numeric(out.get("circ_mv"), errors="coerce") * 10000.0
    out = out.dropna(subset=["ts_code"])
    return out[["ts_code", "close", "total_mv", "circ_mv"]].drop_duplicates(subset=["ts_code"])


def _resolve_latest_available_stock_trade_date(
    preferred_date: str,
    stock_basic_df: pd.DataFrame,
    token: Optional[str],
    max_fallback_count: int = 5,
) -> Tuple[Optional[str], pd.DataFrame, List[str]]:
    """
    功能：在最新开市日无股票日线快照时，自动回退到最近可用交易日。

    Args:
        preferred_date: 优先使用的截止交易日，格式为 YYYYMMDD。
        stock_basic_df: 全量股票基础信息表。
        token: Tushare Token，可选，优先覆盖环境变量中的配置。
        max_fallback_count: 最多向前回退检查的开市日数量，默认 5。

    Returns:
        Tuple[Optional[str], pandas.DataFrame, List[str]]:
        - 第一个返回值：最终可用的交易日；没有可用日期时返回 None。
        - 第二个返回值：该交易日对应的有效股票池。
        - 第三个返回值：回退过程中的提示信息列表。

    Raises:
        无。函数内部不会主动抛出异常。
    """
    warnings: List[str] = []
    candidate_dates = _get_recent_trade_dates(preferred_date, token=token, max_count=max_fallback_count)
    if not candidate_dates:
        candidate_dates = [preferred_date]

    for candidate_date in candidate_dates:
        universe_df = _filter_stock_universe_by_trade_date(stock_basic_df, candidate_date)
        if universe_df.empty:
            continue

        daily_df = _fetch_daily_snapshot_by_trade_date(candidate_date, token=token)
        if daily_df.empty:
            continue

        available_codes = set(daily_df["ts_code"].astype(str))
        matched_universe_df = universe_df[universe_df["ts_code"].isin(available_codes)].copy()
        if matched_universe_df.empty:
            continue

        if candidate_date != preferred_date:
            warnings.append(
                f"daily在{preferred_date}无可用数据，已自动回退至最近可用交易日{candidate_date}"
            )
        return candidate_date, matched_universe_df.reset_index(drop=True), warnings

    return None, pd.DataFrame(), warnings


def _normalize_industry_mapping(industry_mapping: Optional[str]) -> str:
    """
    校验并归一化行业映射方式参数。

    参数：
    - industry_mapping (Optional[str]): 请求传入的映射方式，空值回退为默认映射。

    返回值：
    - str: `INDUSTRY_MAPPING_MODES` 中的合法键。

    异常：
    - ValueError: 传入的映射方式不在支持范围内时抛出。
    """
    mode = str(industry_mapping or "").strip() or DEFAULT_INDUSTRY_MAPPING
    if mode not in INDUSTRY_MAPPING_MODES:
        supported = ", ".join(INDUSTRY_MAPPING_MODES.keys())
        raise ValueError(f"industry_mapping 非法，仅支持: {supported}")
    return mode


def _load_board_snapshot() -> List[Dict]:
    """
    加载本地东方财富板块成分快照（进程内缓存）。

    返回值：
    - List[Dict]: 快照中的板块列表；文件缺失或解析失败时返回空列表。

    异常：
    - 无。内部异常会记录日志并返回空列表。
    """
    global _board_snapshot_cache
    if _board_snapshot_cache is not None:
        return _board_snapshot_cache
    boards: List[Dict] = []
    try:
        if DC_BOARD_SNAPSHOT_FILE.exists():
            with DC_BOARD_SNAPSHOT_FILE.open("r", encoding="utf-8") as file_obj:
                payload = json.load(file_obj)
            raw_boards = payload.get("boards", []) if isinstance(payload, dict) else []
            boards = [item for item in raw_boards if isinstance(item, dict)]
        else:
            logger.warning("本地板块成分快照不存在: %s", DC_BOARD_SNAPSHOT_FILE)
    except Exception as exc:
        logger.warning("读取本地板块成分快照失败: %s", exc)
        boards = []
    _board_snapshot_cache = boards
    return boards


def _build_snapshot_industry_index(idx_type: str, level: str) -> Dict[str, List[str]]:
    """
    基于本地板块成分快照构建 `股票代码 -> 所属板块名称列表` 的索引。

    参数：
    - idx_type (str): 东方财富板块类型（如 `行业板块`、`概念板块`、`地域板块`）。
    - level (str): 东财行业层级，仅 `行业板块` 需要（`东财一/二/三级行业`）；其它类型传空串。

    返回值：
    - Dict[str, List[str]]: 以股票代码为键、所属板块名称去重列表为值的映射。
      概念板块为多对多，一只个股可能对应多个板块名称。

    异常：
    - 无。
    """
    index: Dict[str, List[str]] = {}
    for board in _load_board_snapshot():
        if str(board.get("idx_type") or "").strip() != idx_type:
            continue
        if level and str(board.get("level") or "").strip() != level:
            continue
        sector_name = str(board.get("sector_name") or "").strip()
        if not sector_name:
            continue
        for member in board.get("members") or []:
            code = str(member or "").strip()
            if not code:
                continue
            names = index.setdefault(code, [])
            if sector_name not in names:
                names.append(sector_name)
    return index


def compute_stock_rps(
    periods: List[int],
    trade_date: Optional[str] = None,
    token: Optional[str] = None,
    exchange: Optional[str] = None,
    market: Optional[str] = None,
    industry_mapping: str = DEFAULT_INDUSTRY_MAPPING,
) -> Tuple[Optional[pd.DataFrame], List[str]]:
    """
    功能：使用 Tushare `stock_basic` 和 `daily` 计算股票多周期 RPS 排名。

    Args:
        periods: 回看交易日周期列表，例如 [5, 20, 60]。
        trade_date: 截止交易日，格式为 YYYYMMDD；为空时自动使用最近可用交易日。
        token: Tushare Token，可选，优先覆盖环境变量中的配置。
        exchange: 交易所筛选，可选，例如 SSE、SZSE、BSE。
        market: 市场类型筛选，可选，例如 主板、创业板、科创板、北交所。
        industry_mapping: 行业映射方式，取值见 `INDUSTRY_MAPPING_MODES`，默认 `default`。
          - `default`: 使用 `stock_basic` 的 `industry` 字段（默认）。
          - `dc_concept` / `dc_region` / `dc_l1` / `dc_l2` / `dc_l3`: 基于本地东方财富板块成分快照映射。

    Returns:
        Tuple[Optional[pandas.DataFrame], List[str]]:
        - 第一个返回值：结果 DataFrame，包含 ts_code、symbol、name、industry（或industries列表）、market、
          pct_change、RPS_today、return_{p}、RPS_{p}、latest_price（最新股价）、total_mv（总市值，元）、
          circ_mv（流通市值，元）等列；失败时返回 None。
        - 第二个返回值：错误或提示信息列表。

    Raises:
        无。函数内部统一捕获大部分异常并通过 errors 返回错误信息。
    """
    errors: List[str] = []
    normalized_periods = [int(period) for period in periods]
    if not normalized_periods:
        errors.append("periods 不能为空")
        return None, errors

    if any(period <= 0 for period in normalized_periods):
        errors.append("period 必须大于 0")
        return None, errors

    # 归一化并验证行业映射方式
    mapping_mode = _normalize_industry_mapping(industry_mapping)
    mapping_meta = INDUSTRY_MAPPING_MODES[mapping_mode]
    use_snapshot = mapping_mode != DEFAULT_INDUSTRY_MAPPING

    preferred_end_date = _ensure_date_str(trade_date)
    if trade_date is None:
        latest = _get_latest_trade_date(token)
        if latest:
            preferred_end_date = latest

    stock_basic_df = _fetch_stock_basic_all_statuses(token=token, exchange=exchange, market=market)
    if stock_basic_df.empty:
        errors.append("未获取到股票基础信息")
        return None, errors

    if trade_date is None:
        resolved_end_date, universe_df, fallback_warnings = _resolve_latest_available_stock_trade_date(
            preferred_end_date,
            stock_basic_df=stock_basic_df,
            token=token,
        )
        errors.extend(fallback_warnings)
        if not resolved_end_date or universe_df.empty:
            errors.append("未获取到可用于计算RPS的股票日线数据")
            return None, errors
        end_date = resolved_end_date
    else:
        end_date = preferred_end_date
        universe_df = _filter_stock_universe_by_trade_date(stock_basic_df, end_date)
        if universe_df.empty:
            errors.append("目标交易日无可用股票池")
            return None, errors

    cache_key = (
        f"stock_rps:v2:{end_date}:{exchange or ''}:{market or ''}:{mapping_mode}:"
        f"{','.join(map(str, normalized_periods))}"
    )
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    try:
        period_start_dates = _get_period_start_trade_dates(end_date, normalized_periods, token=token)
    except Exception as exc:
        errors.append(f"计算交易日起始区间失败: {str(exc)}")
        return None, errors

    stock_codes = universe_df["ts_code"].dropna().astype(str).tolist()
    snapshot_dates = [end_date] + list(period_start_dates.values())
    snapshot_map = _build_stock_snapshot_map(snapshot_dates, stock_codes=stock_codes, token=token)
    if end_date not in snapshot_map:
        errors.append(f"daily返回空数据: trade_date={end_date}")
        return None, errors

    end_snapshot = snapshot_map[end_date]
    result_df = universe_df[universe_df["ts_code"].isin(end_snapshot.index)].copy()
    if result_df.empty:
        errors.append("目标交易日无可用股票行情")
        return None, errors

    result_df["trade_date"] = end_date
    result_df["close_end"] = result_df["ts_code"].map(end_snapshot["close"])
    result_df["pct_change"] = result_df["ts_code"].map(end_snapshot["pct_change"])
    result_df["RPS_today"] = _apply_rps(result_df["pct_change"].fillna(-999))

    # 应用行业映射
    if use_snapshot:
        # 使用东方财富板块成分快照
        snapshot_index = _build_snapshot_industry_index(
            idx_type=mapping_meta["idx_type"],
            level=mapping_meta["level"],
        )
        # 对于多对多映射（如概念板块），保留列表形式
        result_df["industries"] = result_df["ts_code"].map(
            lambda code: snapshot_index.get(str(code), [])
        )
        # 同时保留单个industry字段（取第一个，或空字符串）
        result_df["industry"] = result_df["industries"].apply(
            lambda lst: lst[0] if lst else ""
        )
    # else: 使用默认的 stock_basic.industry 字段，已包含在 universe_df 中

    for period in normalized_periods:
        start_date = period_start_dates[period]
        start_snapshot = snapshot_map.get(start_date)
        if start_snapshot is None or start_snapshot.empty:
            errors.append(f"daily返回空数据: period={period}, trade_date={start_date}")
            continue

        result_df[f"close_{period}"] = result_df["ts_code"].map(start_snapshot["close"])
        result_df[f"return_{period}"] = (result_df["close_end"] / result_df[f"close_{period}"] - 1.0) * 100.0
        result_df[f"RPS_{period}"] = _apply_rps(result_df[f"return_{period}"].fillna(-999))

    # 合并最新股价与市值信息（total_mv 总市值、circ_mv 流通市值，单位元）
    daily_basic_df = _fetch_daily_basic_by_trade_date(end_date, token=token)
    if daily_basic_df is not None and not daily_basic_df.empty:
        basic_indexed = daily_basic_df.set_index("ts_code")
        result_df["latest_price"] = result_df["ts_code"].map(basic_indexed["close"])
        result_df["total_mv"] = result_df["ts_code"].map(basic_indexed["total_mv"])
        result_df["circ_mv"] = result_df["ts_code"].map(basic_indexed["circ_mv"])
    else:
        errors.append(f"daily_basic返回空数据: trade_date={end_date}，市值与最新价字段为空")
        result_df["latest_price"] = pd.NA
        result_df["total_mv"] = pd.NA
        result_df["circ_mv"] = pd.NA

    # 最新股价缺失时回退使用截止日收盘价
    result_df["latest_price"] = result_df["latest_price"].fillna(result_df["close_end"])

    drop_columns = ["close_end"] + [f"close_{period}" for period in normalized_periods]
    result_df = result_df.drop(columns=drop_columns, errors="ignore")
    result_df.attrs["trade_date"] = end_date

    try:
        result_df = result_df.sort_values(by=[f"RPS_{normalized_periods[0]}"], ascending=False, na_position="last")
    except Exception:
        pass

    result = (result_df.reset_index(drop=True), errors)
    cache.set(cache_key, result, 900)
    return result
