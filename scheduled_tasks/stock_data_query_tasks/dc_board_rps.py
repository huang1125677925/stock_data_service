import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict

from common.tushare_proxy import call_tushare


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


def _chunk_date_ranges(start_date: str, end_date: str, chunk_days: int = 4) -> List[Tuple[str, str]]:
    """将区间拆分为小块，避免 dc_daily 单次返回超过 2000 条。"""
    start = datetime.strptime(start_date, '%Y%m%d')
    end = datetime.strptime(end_date, '%Y%m%d')
    chunks = []
    cur = start
    while cur <= end:
        nxt = cur + timedelta(days=chunk_days - 1)
        if nxt > end:
            nxt = end
        chunks.append((cur.strftime('%Y%m%d'), nxt.strftime('%Y%m%d')))
        cur = nxt + timedelta(days=1)
    return chunks


def _get_board_map_by_date(trade_date: str, token: Optional[str]) -> Dict[str, str]:
    """获取指定交易日的概念板块代码到名称映射。"""
    params = {'trade_date': trade_date}
    resp = call_tushare('dc_index', params=params, token=token, fields='ts_code,name,trade_date', use_query=False)
    if resp.get('code') != 200:
        return {}
    records = (resp.get('data') or {}).get('records') or []
    mapping = {}
    for r in records:
        code = r.get('ts_code')
        name = r.get('name')
        if code:
            mapping[code] = name or ''
    return mapping


def _fetch_dc_daily_range(start_date: str, end_date: str, idx_type: Optional[str], token: Optional[str]) -> pd.DataFrame:
    """按日期区间分块获取 dc_daily 数据，仅保留 ts_code/trade_date/close。"""
    frames = []
    for s, e in _chunk_date_ranges(start_date, end_date, chunk_days=4):
        params = {'start_date': s, 'end_date': e}
        if idx_type:
            params['idx_type'] = idx_type
        resp = call_tushare('dc_daily', params=params, token=token, fields='ts_code,trade_date,close', use_query=False)
        if resp.get('code') != 200:
            # 忽略单块错误，继续获取其他块
            continue
        records = (resp.get('data') or {}).get('records') or []
        if not records:
            continue
        df = pd.DataFrame.from_records(records)
        if not df.empty:
            frames.append(df)
    if frames:
        out = pd.concat(frames, ignore_index=True)
        # 确保类型正确
        out['trade_date'] = out['trade_date'].astype(str)
        out['close'] = pd.to_numeric(out['close'], errors='coerce')
        return out.dropna(subset=['ts_code', 'trade_date', 'close'])
    return pd.DataFrame(columns=['ts_code', 'trade_date', 'close'])


def _compute_period_return(df: pd.DataFrame, end_date: str) -> pd.DataFrame:
    """基于 close 计算区间收益：return_pct = (last/first - 1) * 100。"""
    if df.empty:
        return pd.DataFrame(columns=['ts_code', 'return_pct'])
    # 按 ts_code, trade_date 排序
    df = df.sort_values(['ts_code', 'trade_date'])
    # 选择每个 ts_code 的首尾有效收盘
    first_close = df.groupby('ts_code')['close'].first()
    last_close = df.groupby('ts_code')['close'].last()
    ret = (last_close / first_close - 1.0) * 100.0
    out = ret.reset_index()
    out.columns = ['ts_code', 'return_pct']
    return out


def _apply_rps(values: pd.Series) -> pd.Series:
    """计算 RPS = (1 - rank/total) * 100。"""
    ranks = values.rank(ascending=False, method='min')
    total = len(values)
    return ((1.0 - ranks / total) * 100.0).round(2)


def compute_board_rps(
    periods: List[int],
    idx_type: Optional[str] = '概念板块',
    trade_date: Optional[str] = None,
    token: Optional[str] = None,
) -> Tuple[Optional[pd.DataFrame], List[str]]:
    """
    使用 Tushare dc_index/dc_daily 计算东方财富板块的 RPS 排名。

    Args:
        periods: 周期列表（单位：自然日），例如 [5, 20, 60]
        idx_type: 板块类型（dc_daily 的 idx_type 参数），如：概念板块、行业板块、地域板块
        trade_date: 计算截止交易日（YYYYMMDD），为空时自动获取最新交易日
        token: 传递给 Tushare 的 token

    Returns:
        (df, errors): df 包含 ts_code、name 及各周期的 return_{p} 与 RPS_{p} 列；errors 为错误信息列表
    """
    errors: List[str] = []

    # 确定截止交易日
    end_date = _ensure_date_str(trade_date)
    if trade_date is None:
        latest = _get_latest_trade_date(token)
        if latest:
            end_date = latest

    # 获取板块映射
    board_map = _get_board_map_by_date(end_date, token)
    if not board_map:
        errors.append('未获取到板块列表或 trade_date 无数据')
        return None, errors

    result_df = pd.DataFrame({'ts_code': list(board_map.keys()), 'name': [board_map[k] for k in board_map.keys()]})

    for p in periods:
        try:
            start_dt = datetime.strptime(end_date, '%Y%m%d') - timedelta(days=p)
            start_date = start_dt.strftime('%Y%m%d')
            # 获取区间内的日线数据
            daily_df = _fetch_dc_daily_range(start_date, end_date, idx_type=idx_type, token=token)
            if daily_df.empty:
                errors.append(f'dc_daily返回空数据: period={p}, {start_date}-{end_date}')
                # 继续其他周期
                continue
            # 仅保留当前板块集合的数据
            daily_df = daily_df[daily_df['ts_code'].isin(board_map.keys())]
            # 计算区间收益
            rets = _compute_period_return(daily_df, end_date)
            # 合并到结果
            result_df = result_df.merge(rets, on='ts_code', how='left', suffixes=(None, None))
            # 列重命名 return_pct -> return_{p}
            result_df.rename(columns={'return_pct': f'return_{p}'}, inplace=True)
            # 计算RPS
            result_df[f'RPS_{p}'] = _apply_rps(result_df[f'return_{p}'].fillna(-999))
        except Exception as e:
            errors.append(f'计算周期{p}失败: {str(e)}')

    # 排序：优先第一个周期，其次其他周期之和
    sort_cols = [f'RPS_{periods[0]}'] if periods else []
    if sort_cols:
        try:
            result_df = result_df.sort_values(by=sort_cols, ascending=False)
        except Exception:
            pass

    return result_df, errors