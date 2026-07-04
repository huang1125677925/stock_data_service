from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
from django.core.cache import cache

from common.tushare_proxy import call_tushare


DOMESTIC_LARGE_CAP_INDEXES = {
    '000001.SH': '上证综指',
    '000005.SH': '上证商业类',
    '000006.SH': '上证地产类',
    '000016.SH': '上证50',
    '000300.SH': '沪深300',
    '000905.SH': '中证500',
    '399001.SZ': '深证成指',
    '399005.SZ': '中小板指',
    '399006.SZ': '创业板指',
    '399016.SZ': '深证创新',
    '399300.SZ': '沪深300(深)',
    '399905.SZ': '中证500(深)',
}

GLOBAL_LARGE_CAP_INDEXES = {
    'XIN9': '富时中国A50指数',
    'HSI': '恒生指数',
    'HKTECH': '恒生科技指数',
    'HKAH': '恒生AH股H指数',
    'DJI': '道琼斯工业指数',
    'SPX': '标普500指数',
    'IXIC': '纳斯达克指数',
    'FTSE': '富时100指数',
    'FCHI': '法国CAC40指数',
    'GDAXI': '德国DAX指数',
    'N225': '日经225指数',
    'KS11': '韩国综合指数',
    'AS51': '澳大利亚标普200指数',
    'SENSEX': '印度孟买SENSEX指数',
    'IBOVESPA': '巴西IBOVESPA指数',
    'RTS': '俄罗斯RTS指数',
    'TWII': '台湾加权指数',
    'CKLSE': '马来西亚指数',
    'SPTSX': '加拿大S&P/TSX指数',
    'CSX5P': 'STOXX欧洲50指数',
    'RUT': '罗素2000指数',
}


def _ensure_date_str(date: Optional[str]) -> str:
    """
    功能：将传入日期标准化为 `YYYYMMDD` 字符串，未传时使用当前系统日期。

    Args:
        date: 原始日期字符串，支持 `YYYYMMDD` 或 `YYYY-MM-DD`；为空时使用当前系统日期。

    Returns:
        str: 标准化后的 `YYYYMMDD` 日期字符串。

    Raises:
        无。函数内部不会主动抛出异常。
    """
    if date:
        return str(date).replace('-', '')
    return datetime.now().strftime('%Y%m%d')


def _build_history_start_date(end_date: str, max_period: int) -> str:
    """
    功能：根据截止日期和最大回看周期，估算历史行情的开始日期。

    Args:
        end_date: 截止日期，格式为 `YYYYMMDD`。
        max_period: 最大回看交易日周期。

    Returns:
        str: 建议拉取历史行情的开始日期，格式为 `YYYYMMDD`。

    Raises:
        ValueError: 当 `end_date` 不是合法日期时抛出异常。
    """
    end_dt = datetime.strptime(end_date, '%Y%m%d')
    lookback_days = max(max_period * 3, 365)
    return (end_dt - timedelta(days=lookback_days)).strftime('%Y%m%d')


def _extract_records(resp: Dict) -> List[Dict]:
    """
    功能：从 Tushare 统一响应中提取记录列表。

    Args:
        resp: `call_tushare` 返回的统一响应字典。

    Returns:
        List[Dict]: 记录列表；当响应失败或无数据时返回空列表。

    Raises:
        无。函数内部不会主动抛出异常。
    """
    if resp.get('code') != 200:
        return []
    return (resp.get('data') or {}).get('records') or []


def _normalize_history_frame(records: List[Dict], pct_field: str) -> pd.DataFrame:
    """
    功能：将指数历史记录标准化为统一 DataFrame 结构，便于后续计算收益率和 RPS。

    Args:
        records: Tushare 返回的历史记录列表。
        pct_field: 原始涨跌幅字段名，如 `pct_change` 或 `pct_chg`。

    Returns:
        pandas.DataFrame: 统一后的行情数据，包含 `ts_code`、`trade_date`、`close`、`pct_change` 四列。

    Raises:
        无。函数内部不会主动抛出异常。
    """
    if not records:
        return pd.DataFrame(columns=['ts_code', 'trade_date', 'close', 'pct_change'])

    frame = pd.DataFrame.from_records(records)
    if frame.empty:
        return pd.DataFrame(columns=['ts_code', 'trade_date', 'close', 'pct_change'])

    if pct_field not in frame.columns:
        frame[pct_field] = pd.NA

    frame['trade_date'] = frame['trade_date'].astype(str)
    frame['close'] = pd.to_numeric(frame.get('close'), errors='coerce')
    frame['pct_change'] = pd.to_numeric(frame.get(pct_field), errors='coerce')
    frame = frame[['ts_code', 'trade_date', 'close', 'pct_change']].dropna(subset=['ts_code', 'trade_date', 'close'])
    frame = frame.sort_values('trade_date').drop_duplicates(subset=['trade_date'], keep='last')
    return frame.reset_index(drop=True)


def _fetch_domestic_index_history(
    ts_code: str,
    start_date: str,
    end_date: str,
    token: Optional[str],
) -> pd.DataFrame:
    """
    功能：通过 Tushare `index_daily` 拉取单个国内大盘指数的历史行情。

    Args:
        ts_code: 国内指数 TS 代码。
        start_date: 历史行情开始日期，格式为 `YYYYMMDD`。
        end_date: 历史行情结束日期，格式为 `YYYYMMDD`。
        token: Tushare Token，可选，优先覆盖环境变量中的配置。

    Returns:
        pandas.DataFrame: 指数历史行情，标准化为统一字段结构。

    Raises:
        无。接口异常场景由空 DataFrame 表示。
    """
    resp = call_tushare(
        'index_daily',
        params={'ts_code': ts_code, 'start_date': start_date, 'end_date': end_date},
        token=token,
        fields='ts_code,trade_date,close,pct_chg',
        use_query=False,
    )
    return _normalize_history_frame(_extract_records(resp), pct_field='pct_chg')


def _fetch_global_index_history(
    ts_code: str,
    start_date: str,
    end_date: str,
    token: Optional[str],
) -> pd.DataFrame:
    """
    功能：通过 Tushare `index_global` 拉取单个国际大盘指数的历史行情。

    Args:
        ts_code: 国际指数 TS 代码。
        start_date: 历史行情开始日期，格式为 `YYYYMMDD`。
        end_date: 历史行情结束日期，格式为 `YYYYMMDD`。
        token: Tushare Token，可选，优先覆盖环境变量中的配置。

    Returns:
        pandas.DataFrame: 指数历史行情，标准化为统一字段结构。

    Raises:
        无。接口异常场景由空 DataFrame 表示。
    """
    resp = call_tushare(
        'index_global',
        params={'ts_code': ts_code, 'start_date': start_date, 'end_date': end_date},
        token=token,
        fields='ts_code,trade_date,close,pct_chg',
        use_query=False,
    )
    return _normalize_history_frame(_extract_records(resp), pct_field='pct_chg')


def _build_index_metrics(history_df: pd.DataFrame, periods: List[int], anchor_date: str) -> Optional[Dict[str, object]]:
    """
    功能：基于单个指数的历史行情，提取截至目标日期最近可用交易日的收益率与涨跌幅指标。

    Args:
        history_df: 单个指数的历史行情 DataFrame。
        periods: 回看交易日周期列表。
        anchor_date: 目标截止日期，格式为 `YYYYMMDD`。

    Returns:
        Optional[Dict[str, object]]: 指标字典；当目标日期前无可用数据时返回 `None`。

    Raises:
        无。函数内部不会主动抛出异常。
    """
    available_history = history_df[history_df['trade_date'] <= anchor_date].copy()
    if available_history.empty:
        return None

    available_history = available_history.sort_values('trade_date').reset_index(drop=True)
    end_row = available_history.iloc[-1]
    metrics: Dict[str, object] = {
        'trade_date': str(end_row['trade_date']),
        'pct_change': end_row['pct_change'],
    }

    for period in periods:
        if len(available_history) < period + 1:
            metrics[f'return_{period}'] = pd.NA
            continue
        start_row = available_history.iloc[-(period + 1)]
        metrics[f'return_{period}'] = ((end_row['close'] / start_row['close']) - 1.0) * 100.0

    return metrics


def _apply_rps(values: pd.Series) -> pd.Series:
    """
    功能：根据横向排名计算 RPS 指标。

    Args:
        values: 用于排名的数值序列。

    Returns:
        pandas.Series: 对应的 RPS 结果，取值范围约为 `0-100`。

    Raises:
        无。函数内部不会主动抛出异常。
    """
    ranks = values.rank(ascending=False, method='min')
    total = len(values)
    return ((1.0 - ranks / total) * 100.0).round(2)


def compute_major_index_rps(
    periods: List[int],
    trade_date: Optional[str] = None,
    token: Optional[str] = None,
) -> Tuple[Optional[pd.DataFrame], List[str]]:
    """
    功能：综合国内与国际大盘指数行情，计算多周期 RPS 强度排名。

    Args:
        periods: 回看交易日周期列表，例如 `[5, 20, 60, 120, 250]`。
        trade_date: 目标截止日期，格式为 `YYYYMMDD`；为空时默认使用当前系统日期。
        token: Tushare Token，可选，优先覆盖环境变量中的配置。

    Returns:
        Tuple[Optional[pandas.DataFrame], List[str]]:
        - 第一个返回值：结果 DataFrame，包含指数代码、名称、市场、最新可用交易日、当天涨跌幅、
          `RPS_today` 以及各周期的 `return_{period}` 和 `RPS_{period}`；失败时返回 `None`。
        - 第二个返回值：错误与提示信息列表。

    Raises:
        无。函数内部捕获异常并通过错误列表返回。
    """
    errors: List[str] = []

    try:
        normalized_periods = sorted({int(period) for period in periods})
    except (TypeError, ValueError):
        return None, ['periods 参数格式错误，应为整数列表']

    if not normalized_periods:
        return None, ['periods 不能为空']
    if any(period <= 0 for period in normalized_periods):
        return None, ['period 必须大于 0']

    anchor_date = _ensure_date_str(trade_date)
    start_date = _build_history_start_date(anchor_date, max(normalized_periods))
    cache_key = f'major_index_rps:v1:{anchor_date}:{",".join(map(str, normalized_periods))}'
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    rows: List[Dict[str, object]] = []
    index_groups = [
        ('国内', 'index_daily', DOMESTIC_LARGE_CAP_INDEXES, _fetch_domestic_index_history),
        ('国际', 'index_global', GLOBAL_LARGE_CAP_INDEXES, _fetch_global_index_history),
    ]

    for market, source, index_mapping, fetcher in index_groups:
        for ts_code, name in index_mapping.items():
            try:
                history_df = fetcher(ts_code, start_date, anchor_date, token)
            except Exception as exc:
                errors.append(f'{ts_code}({name}) 拉取历史行情失败: {str(exc)}')
                continue

            metrics = _build_index_metrics(history_df, normalized_periods, anchor_date)
            if metrics is None:
                errors.append(f'{ts_code}({name}) 在 {anchor_date} 之前无可用行情数据')
                continue

            rows.append(
                {
                    'ts_code': ts_code,
                    'name': name,
                    'market': market,
                    'source': source,
                    **metrics,
                }
            )

    if not rows:
        errors.append('未获取到任何国内或国际大盘指数的可用行情数据')
        return None, errors

    result_df = pd.DataFrame(rows)
    result_df['pct_change'] = pd.to_numeric(result_df['pct_change'], errors='coerce')
    result_df['RPS_today'] = _apply_rps(result_df['pct_change'].fillna(-999))

    for period in normalized_periods:
        return_column = f'return_{period}'
        result_df[return_column] = pd.to_numeric(result_df.get(return_column), errors='coerce')
        result_df[f'RPS_{period}'] = _apply_rps(result_df[return_column].fillna(-999))

    result_df.attrs['trade_date'] = anchor_date
    result_df = result_df.sort_values(by=[f'RPS_{normalized_periods[0]}', 'RPS_today'], ascending=False)
    result = (result_df.reset_index(drop=True), errors)
    cache.set(cache_key, result, 900)
    return result
