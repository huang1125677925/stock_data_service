import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from django.core.cache import cache

from common.tushare_proxy import call_tushare
from common.tushare_industry import (
    get_latest_trade_date as get_latest_open_trade_date,
    get_open_trade_dates,
)


def _ensure_date_str(date: Optional[str]) -> str:
    """
    功能：将传入日期标准化为 YYYYMMDD 字符串，未传时默认返回今天日期。

    Args:
        date: 原始日期字符串，支持 YYYYMMDD 或 YYYY-MM-DD；为空时使用当前系统日期。

    Returns:
        str: 标准化后的 YYYYMMDD 格式日期字符串。

    Raises:
        无。函数内部不会主动抛出异常。
    """
    if date:
        return date.replace('-', '')
    return datetime.now().strftime('%Y%m%d')


def _get_latest_trade_date(token: Optional[str] = None) -> Optional[str]:
    """
    功能：获取截至当前日期最近一个开市日。

    Args:
        token: Tushare Token，可选，优先覆盖环境变量中的配置。

    Returns:
        Optional[str]: 最近开市日，格式为 YYYYMMDD；若无法获取则返回 None。

    Raises:
        无。函数内部异常时统一返回 None。
    """
    try:
        return get_latest_open_trade_date(token=token)
    except Exception:
        return None


def _get_recent_trade_dates(
    end_date: str,
    token: Optional[str] = None,
    max_count: int = 5,
) -> List[str]:
    """
    功能：获取截止指定日期向前最近若干个开市日，用于可用行情日期回退。

    Args:
        end_date: 截止日期，格式为 YYYYMMDD。
        token: Tushare Token，可选，优先覆盖环境变量中的配置。
        max_count: 需要返回的最近开市日数量，默认 5。

    Returns:
        List[str]: 按日期从近到远排序的开市日列表；无法获取时返回空列表。

    Raises:
        无。函数内部异常时统一返回空列表。
    """
    if max_count <= 0:
        return []

    try:
        end_dt = datetime.strptime(end_date, '%Y%m%d')
    except ValueError:
        return []

    window_days = max(max_count * 7, 14)
    for _ in range(6):
        start_dt = end_dt - timedelta(days=window_days)
        trade_dates = get_open_trade_dates(
            start_dt.strftime('%Y%m%d'),
            end_date,
            token=token,
        )
        if trade_dates:
            return sorted(trade_dates, reverse=True)[:max_count]
        window_days *= 2
    return []


def _resolve_latest_available_board_trade_date(
    preferred_date: str,
    idx_type: Optional[str],
    level: Optional[str],
    token: Optional[str],
    max_fallback_count: int = 5,
) -> Tuple[Optional[str], Dict[str, Dict[str, str]], List[str]]:
    """
    功能：解析 `index-rps` 应使用的实际截止交易日，并在最新开市日无板块行情时回退到最近可用交易日。

    Args:
        preferred_date: 优先使用的截止日期，格式为 YYYYMMDD。
        idx_type: 板块类型，如概念板块、行业板块、地域板块。
        level: 东财行业层级，仅在行业板块场景下生效。
        token: Tushare Token，可选，优先覆盖环境变量中的配置。
        max_fallback_count: 最多向前回退检查的开市日数量，默认 5。

    Returns:
        Tuple[Optional[str], Dict[str, Dict[str, str]], List[str]]:
        - 第一个返回值：实际可用的截止交易日；未命中时返回 None。
        - 第二个返回值：该交易日对应的板块映射。
        - 第三个返回值：回退过程中的提示信息列表。

    Raises:
        无。函数内部不会主动抛出异常，异常场景通过空结果返回。
    """
    warnings: List[str] = []
    candidate_dates = _get_recent_trade_dates(preferred_date, token=token, max_count=max_fallback_count)
    if not candidate_dates:
        candidate_dates = [preferred_date]

    for candidate_date in candidate_dates:
        board_map = _get_board_map_by_date(candidate_date, token, idx_type=idx_type, level=level)
        if not board_map:
            continue

        daily_df = _fetch_dc_daily_trade_date(candidate_date, idx_type=idx_type, token=token)
        if daily_df.empty:
            continue

        available_codes = set(daily_df['ts_code'].astype(str))
        matched_board_map = {
            code: meta
            for code, meta in board_map.items()
            if code in available_codes
        }
        if not matched_board_map:
            continue

        if candidate_date != preferred_date:
            warnings.append(
                f'dc_daily在{preferred_date}无可用数据，已自动回退至最近可用交易日{candidate_date}'
            )
        return candidate_date, matched_board_map, warnings

    return None, {}, warnings
DC_INDUSTRY_LEVELS = {'东财一级行业', '东财二级行业', '东财三级行业'}


def _get_board_map_by_date(
    trade_date: str,
    token: Optional[str],
    idx_type: Optional[str] = None,
    level: Optional[str] = None,
) -> Dict[str, Dict[str, str]]:
    """获取指定交易日的板块代码到名称映射。"""
    params = {'trade_date': trade_date}
    if idx_type:
        params['idx_type'] = idx_type
    resp = call_tushare(
        'dc_index',
        params=params,
        token=token,
        fields='ts_code,name,trade_date,level',
        use_query=False,
    )
    if resp.get('code') != 200:
        return {}
    records = (resp.get('data') or {}).get('records') or []
    mapping = {}
    for r in records:
        if level and str(r.get('level') or '').strip() != level:
            continue
        code = r.get('ts_code')
        name = r.get('name')
        if code:
            mapping[code] = {
                'name': name or '',
                'level': str(r.get('level') or '').strip(),
            }
    return mapping


def _fetch_dc_daily_trade_date(trade_date: str, idx_type: Optional[str], token: Optional[str]) -> pd.DataFrame:
    """按单个交易日获取 dc_daily 数据，仅保留计算 RPS 需要的字段。"""
    params = {'trade_date': trade_date}
    if idx_type:
        params['idx_type'] = idx_type
    resp = call_tushare(
        'dc_daily',
        params=params,
        token=token,
        fields='ts_code,trade_date,close,pct_change',
        use_query=False,
    )
    if resp.get('code') != 200:
        return pd.DataFrame(columns=['ts_code', 'trade_date', 'close', 'pct_change'])

    records = (resp.get('data') or {}).get('records') or []
    if not records:
        return pd.DataFrame(columns=['ts_code', 'trade_date', 'close', 'pct_change'])

    out = pd.DataFrame.from_records(records)
    if out.empty:
        return pd.DataFrame(columns=['ts_code', 'trade_date', 'close', 'pct_change'])

    out['trade_date'] = out['trade_date'].astype(str)
    out['close'] = pd.to_numeric(out['close'], errors='coerce')
    out['pct_change'] = pd.to_numeric(out.get('pct_change'), errors='coerce')
    return out.dropna(subset=['ts_code', 'trade_date', 'close'])


def _get_period_start_trade_date(end_date: str, period: int, token: Optional[str] = None) -> str:
    """
    根据截止交易日和回看交易日数量，计算对应的起始交易日。

    Args:
        end_date: 截止交易日，格式 YYYYMMDD。
        period: 回看交易日数量，例如 5、20、60、120、250。
        token: Tushare Token。

    Returns:
        str: 起始交易日，格式 YYYYMMDD。

    Raises:
        ValueError: 当 period 非正整数时抛出。
        RuntimeError: 当交易日历数据不足以覆盖目标周期时抛出。
    """
    if period <= 0:
        raise ValueError('period 必须大于 0')

    end_dt = datetime.strptime(end_date, '%Y%m%d')
    window_days = max(period * 2 + 10, 30)

    for _ in range(6):
        start_dt = end_dt - timedelta(days=window_days)
        trade_dates = get_open_trade_dates(
            start_dt.strftime('%Y%m%d'),
            end_date,
            token=token,
        )
        if len(trade_dates) >= period + 1:
            return trade_dates[-(period + 1)]
        window_days *= 2

    raise RuntimeError(f'交易日历数据不足，无法计算 {period} 个交易日回看区间')


def _get_period_start_trade_dates(end_date: str, periods: List[int], token: Optional[str] = None) -> Dict[int, str]:
    """
    根据截止交易日和多个回看交易日数量，批量计算各周期的起始交易日。

    Args:
        end_date: 截止交易日，格式 YYYYMMDD。
        periods: 回看交易日数量列表，例如 [5, 20, 60, 120, 250]。
        token: Tushare Token。

    Returns:
        Dict[int, str]: 各周期对应的起始交易日映射，键为周期，值为 YYYYMMDD 格式日期。

    Raises:
        ValueError: 当 periods 为空，或存在非正整数周期时抛出。
        RuntimeError: 当交易日历数据不足以覆盖最大周期时抛出。
    """
    if not periods:
        raise ValueError('periods 不能为空')

    invalid_periods = [period for period in periods if period <= 0]
    if invalid_periods:
        raise ValueError('period 必须大于 0')

    unique_periods = sorted(set(periods))
    max_period = unique_periods[-1]
    end_dt = datetime.strptime(end_date, '%Y%m%d')
    window_days = max(max_period * 2 + 10, 30)

    for _ in range(6):
        start_dt = end_dt - timedelta(days=window_days)
        trade_dates = get_open_trade_dates(
            start_dt.strftime('%Y%m%d'),
            end_date,
            token=token,
        )
        if len(trade_dates) >= max_period + 1:
            return {
                period: trade_dates[-(period + 1)]
                for period in unique_periods
            }
        window_days *= 2

    raise RuntimeError(f'交易日历数据不足，无法计算最大周期 {max_period} 个交易日回看区间')


def _build_close_snapshot_map(
    trade_dates: List[str],
    idx_type: Optional[str],
    token: Optional[str],
    board_codes: List[str],
) -> Dict[str, pd.DataFrame]:
    """
    按交易日批量拉取板块日快照，并构建 trade_date -> snapshot DataFrame 映射。

    Args:
        trade_dates: 需要拉取的交易日列表，格式 YYYYMMDD。
        idx_type: 板块类型。
        token: Tushare Token。
        board_codes: 当前结果集对应的板块代码列表。

    Returns:
        Dict[str, pd.DataFrame]: 键为交易日，值为以 ts_code 为索引，包含 close/pct_change 的 DataFrame。
    """
    snapshot_map: Dict[str, pd.DataFrame] = {}
    board_code_set = set(board_codes)

    for trade_date in sorted(set(trade_dates)):
        daily_df = _fetch_dc_daily_trade_date(trade_date, idx_type=idx_type, token=token)
        if daily_df.empty:
            continue
        filtered_df = daily_df[daily_df['ts_code'].isin(board_code_set)].copy()
        if filtered_df.empty:
            continue
        if 'pct_change' not in filtered_df.columns:
            filtered_df['pct_change'] = pd.NA
        snapshot_map[trade_date] = filtered_df.drop_duplicates(subset=['ts_code']).set_index('ts_code')[
            ['close', 'pct_change']
        ]

    return snapshot_map


def _apply_rps(values: pd.Series) -> pd.Series:
    """计算 RPS = (1 - rank/total) * 100。"""
    ranks = values.rank(ascending=False, method='min')
    total = len(values)
    return ((1.0 - ranks / total) * 100.0).round(2)


def compute_board_rps(
    periods: List[int],
    idx_type: Optional[str] = '概念板块',
    trade_date: Optional[str] = None,
    level: Optional[str] = None,
    token: Optional[str] = None,
) -> Tuple[Optional[pd.DataFrame], List[str]]:
    """
    功能：使用 Tushare `dc_index` 和 `dc_daily` 计算东方财富板块的多周期 RPS 排名。

    Args:
        periods: 周期列表（单位：交易日），例如 [5, 20, 60]。
        idx_type: 板块类型（`dc_daily` 的 `idx_type` 参数），如概念板块、行业板块、地域板块。
        trade_date: 计算截止交易日，格式为 YYYYMMDD；为空时自动解析最近可用交易日。
        level: 东财行业层级，仅在 `idx_type=行业板块` 时使用。
        token: 传递给 Tushare 的 Token，可选。

    Returns:
        Tuple[Optional[pandas.DataFrame], List[str]]:
        - 第一个返回值：结果 DataFrame，包含 `ts_code`、`name`、`pct_change`、`RPS_today`
          以及各周期的 `return_{p}` 与 `RPS_{p}` 列；失败时返回 None。
        - 第二个返回值：错误与提示信息列表。

    Raises:
        无。函数内部捕获异常并通过 `errors` 返回错误信息。
    """
    errors: List[str] = []
    normalized_periods = [int(period) for period in periods]
    if not normalized_periods:
        errors.append('periods 不能为空')
        return None, errors

    effective_level = level if idx_type == '行业板块' else None
    if effective_level and effective_level not in DC_INDUSTRY_LEVELS:
        errors.append(f'level参数错误，仅支持: {", ".join(sorted(DC_INDUSTRY_LEVELS))}')
        return None, errors

    # 确定截止交易日
    end_date = _ensure_date_str(trade_date)
    if trade_date is None:
        latest = _get_latest_trade_date(token)
        if latest:
            end_date = latest

    # 获取板块映射，并在未显式指定 trade_date 时回退到最近可用行情交易日。
    if trade_date is None:
        resolved_end_date, board_map, fallback_warnings = _resolve_latest_available_board_trade_date(
            end_date,
            idx_type=idx_type,
            level=effective_level,
            token=token,
        )
        errors.extend(fallback_warnings)
        if not resolved_end_date or not board_map:
            errors.append('未获取到板块列表或 trade_date 无数据')
            return None, errors
        end_date = resolved_end_date
    else:
        board_map = _get_board_map_by_date(end_date, token, idx_type=idx_type, level=effective_level)
        if not board_map:
            errors.append('未获取到板块列表或 trade_date 无数据')
            return None, errors

    cache_key = (
        f'board_rps:v2:{end_date}:{idx_type or ""}:{effective_level or ""}:'
        f'{",".join(map(str, normalized_periods))}'
    )
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    result_df = pd.DataFrame({
        'ts_code': list(board_map.keys()),
        'name': [board_map[k]['name'] for k in board_map.keys()],
        'level': [board_map[k]['level'] for k in board_map.keys()],
    })

    try:
        period_start_dates = _get_period_start_trade_dates(end_date, normalized_periods, token=token)
    except Exception as e:
        errors.append(f'计算交易日起始区间失败: {str(e)}')
        return None, errors

    snapshot_dates = [end_date] + list(period_start_dates.values())
    daily_snapshot_map = _build_close_snapshot_map(
        trade_dates=snapshot_dates,
        idx_type=idx_type,
        token=token,
        board_codes=list(board_map.keys()),
    )
    if end_date not in daily_snapshot_map:
        errors.append(f'dc_daily返回空数据: trade_date={end_date}')
        return None, errors

    end_snapshot = daily_snapshot_map[end_date]
    result_df['close_end'] = result_df['ts_code'].map(end_snapshot['close'])
    result_df['pct_change'] = result_df['ts_code'].map(end_snapshot['pct_change'])
    result_df['RPS_today'] = _apply_rps(result_df['pct_change'].fillna(-999))

    for p in normalized_periods:
        try:
            start_date = period_start_dates[p]
            start_snapshot = daily_snapshot_map.get(start_date)
            if start_snapshot is None or start_snapshot.empty:
                errors.append(f'dc_daily返回空数据: period={p}, trade_date={start_date}')
                continue

            result_df[f'close_{p}'] = result_df['ts_code'].map(start_snapshot['close'])
            result_df[f'return_{p}'] = (
                (result_df['close_end'] / result_df[f'close_{p}'] - 1.0) * 100.0
            )
            result_df[f'RPS_{p}'] = _apply_rps(result_df[f'return_{p}'].fillna(-999))
        except Exception as e:
            errors.append(f'计算周期{p}失败: {str(e)}')

    drop_columns = ['close_end'] + [f'close_{p}' for p in normalized_periods if f'close_{p}' in result_df.columns]
    result_df = result_df.drop(columns=drop_columns, errors='ignore')
    result_df.attrs['trade_date'] = end_date

    # 排序：优先第一个周期，其次其他周期之和
    sort_cols = [f'RPS_{normalized_periods[0]}'] if normalized_periods else []
    if sort_cols:
        try:
            result_df = result_df.sort_values(by=sort_cols, ascending=False)
        except Exception:
            pass

    result = (result_df, errors)
    cache.set(cache_key, result, 900)
    return result

if __name__ == '__main__':
    # 测试：计算5日、20日、60日RPS，截止20240930
    df, errors = compute_board_rps(periods=[5, 20, 60], idx_type='行业板块')
    if errors:
        print('错误:', errors)
    else:
        print(df)
