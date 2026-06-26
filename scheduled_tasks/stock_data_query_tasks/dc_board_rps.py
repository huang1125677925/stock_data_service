import sys
import os
from pathlib import Path
import django

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_data_service.settings')
django.setup()
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from django.core.cache import cache

from common.tushare_proxy import call_tushare
from common.tushare_industry import get_open_trade_dates


def _ensure_date_str(date: Optional[str]) -> str:
    """返回 YYYYMMDD 格式的日期字符串，默认使用今天。"""
    if date:
        return date.replace('-', '')
    return datetime.now().strftime('%Y%m%d')


def _get_latest_trade_date(token: Optional[str] = None) -> Optional[str]:
    """通过 dc_index 获取最新的交易日（取返回记录中的最大 trade_date）。"""
    resp = call_tushare('dc_index', params={}, token=token, fields='ts_code,name,trade_date', use_query=False)
    if resp.get('code') != 200:
        return None
    records = (resp.get('data') or {}).get('records') or []
    if not records:
        return None
    try:
        dates = [r.get('trade_date') for r in records if r.get('trade_date')]
        return max(dates) if dates else None
    except Exception:
        return None
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
    使用 Tushare dc_index/dc_daily 计算东方财富板块的 RPS 排名。

    Args:
        periods: 周期列表（单位：交易日），例如 [5, 20, 60]
        idx_type: 板块类型（dc_daily 的 idx_type 参数），如：概念板块、行业板块、地域板块
        trade_date: 计算截止交易日（YYYYMMDD），为空时自动获取最新交易日
        level: 东财行业层级，仅在 idx_type=行业板块 时使用
        token: 传递给 Tushare 的 token

    Returns:
        (df, errors): df 包含 ts_code、name、pct_change、RPS_today 及各周期的 return_{p} 与 RPS_{p} 列；errors 为错误信息列表
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

    cache_key = (
        f'board_rps:v2:{end_date}:{idx_type or ""}:{effective_level or ""}:'
        f'{",".join(map(str, normalized_periods))}'
    )
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    # 获取板块映射
    board_map = _get_board_map_by_date(end_date, token, idx_type=idx_type, level=effective_level)
    if not board_map:
        errors.append('未获取到板块列表或 trade_date 无数据')
        return None, errors

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
