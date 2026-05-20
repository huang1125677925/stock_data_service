import math
import calendar
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from common.tushare_proxy import call_tushare, call_tushare_pro_bar
from index_data.utils import replace_nan


class SwingAnalysisService:
    """
    波段分析服务
    功能：基于 Tushare 行情数据，对股票或 ETF 生成波段交易所需的趋势、位置、量能和风险数据。
    """

    fields = 'ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount'

    def _safe_float(self, value: Any) -> Optional[float]:
        if value is None or value == '':
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    def _to_stock_ts_code(self, code: str) -> str:
        if '.' in code:
            return code.upper()
        if code.startswith(('6', '9')):
            return f'{code}.SH'
        if code.startswith(('0', '2', '3')):
            return f'{code}.SZ'
        if code.startswith(('4', '8')):
            return f'{code}.BJ'
        return f'{code}.SZ'

    def _normalize_date(self, value: Optional[str], default: datetime) -> str:
        if not value:
            return default.strftime('%Y%m%d')
        normalized = value.replace('-', '')
        if len(normalized) != 8 or not normalized.isdigit():
            raise ValueError('日期参数格式错误，应为 YYYYMMDD 或 YYYY-MM-DD')
        return normalized

    def _recent_open_dates(self, days: int = 15) -> List[str]:
        end_dt = datetime.now().date()
        start_dt = end_dt - timedelta(days=days)
        resp = call_tushare(
            interface='trade_cal',
            params={
                'exchange': '',
                'start_date': start_dt.strftime('%Y%m%d'),
                'end_date': end_dt.strftime('%Y%m%d'),
                'is_open': '1',
            },
            fields='cal_date,is_open',
            use_query=False,
        )
        if resp.get('code') != 200:
            raise RuntimeError(resp.get('error') or resp.get('message') or '获取交易日历失败')
        records = (resp.get('data') or {}).get('records') or []
        return sorted(
            [str(item.get('cal_date')) for item in records if isinstance(item, dict) and item.get('cal_date')],
            reverse=True,
        )

    def _six_months_ago(self) -> datetime.date:
        today = datetime.now().date()
        month = today.month - 6
        year = today.year
        if month <= 0:
            month += 12
            year -= 1
        day = min(today.day, calendar.monthrange(year, month)[1])
        return today.replace(year=year, month=month, day=day)

    def _fetch_records(
        self,
        *,
        target_type: str,
        ts_code: str,
        start_date: str,
        end_date: str,
        adjust: str = '',
    ) -> List[Dict[str, Any]]:
        adjust = (adjust or '').lower()
        if target_type == 'stock':
            if adjust in {'qfq', 'hfq'}:
                resp = call_tushare_pro_bar(
                    params={
                        'ts_code': ts_code,
                        'asset': 'E',
                        'freq': 'D',
                        'adj': adjust,
                        'start_date': start_date,
                        'end_date': end_date,
                    },
                    fields=self.fields,
                )
            else:
                resp = call_tushare(
                    interface='daily',
                    params={'ts_code': ts_code, 'start_date': start_date, 'end_date': end_date},
                    fields=self.fields,
                    use_query=False,
                )
        else:
            resp = call_tushare(
                interface='fund_daily',
                params={'ts_code': ts_code, 'start_date': start_date, 'end_date': end_date},
                fields=self.fields,
                use_query=False,
            )

        if resp.get('code') != 200:
            raise RuntimeError(resp.get('error') or resp.get('message') or 'Tushare 行情数据获取失败')
        records = (resp.get('data') or {}).get('records') or []
        return [item for item in records if isinstance(item, dict)]

    def _fetch_stock_universe(self, universe_limit: int) -> Dict[str, Any]:
        fields = 'trade_date,ts_code,name,close,amount,total_mv,industry,area'
        for trade_date in self._recent_open_dates():
            resp = call_tushare(
                interface='bak_daily',
                params={'trade_date': trade_date},
                fields=fields,
                use_query=False,
            )
            if resp.get('code') != 200:
                raise RuntimeError(resp.get('error') or resp.get('message') or '获取股票候选池失败')
            records = [
                item for item in ((resp.get('data') or {}).get('records') or [])
                if isinstance(item, dict) and item.get('ts_code')
            ]
            if not records:
                continue
            records.sort(key=lambda item: self._safe_float(item.get('amount')) or 0, reverse=True)
            items = []
            for item in records[:universe_limit]:
                ts_code = str(item.get('ts_code'))
                items.append({
                    'target_type': 'stock',
                    'ts_code': ts_code,
                    'code': ts_code.split('.')[0],
                    'name': item.get('name'),
                    'industry': item.get('industry'),
                    'amount': self._safe_float(item.get('amount')),
                    'total_mv': self._safe_float(item.get('total_mv')),
                })
            return {'trade_date': f'{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}', 'items': items}
        return {'trade_date': None, 'items': []}

    def _fetch_latest_fund_daily_codes(self) -> Dict[str, Any]:
        for trade_date in self._recent_open_dates():
            resp = call_tushare(
                interface='fund_daily',
                params={'trade_date': trade_date},
                fields='ts_code,trade_date,amount',
                use_query=False,
            )
            if resp.get('code') != 200:
                raise RuntimeError(resp.get('error') or resp.get('message') or '获取 ETF 最新行情失败')
            records = [
                item for item in ((resp.get('data') or {}).get('records') or [])
                if isinstance(item, dict) and item.get('ts_code')
            ]
            if records:
                amount_map = {str(item.get('ts_code')): self._safe_float(item.get('amount')) for item in records}
                return {
                    'trade_date': f'{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}',
                    'codes': set(amount_map.keys()),
                    'amount_map': amount_map,
                }
        return {'trade_date': None, 'codes': set(), 'amount_map': {}}

    def _fetch_etf_universe(self, universe_limit: int) -> Dict[str, Any]:
        fields = (
            'ts_code,csname,extname,cname,index_code,index_name,setup_date,list_date,'
            'delist_date,list_status,exchange,mgr_name,mgt_fee,etf_type'
        )
        resp = call_tushare(interface='etf_basic', params={}, fields=fields, use_query=False)
        if resp.get('code') != 200:
            raise RuntimeError(resp.get('error') or resp.get('message') or '获取 ETF 基础信息失败')

        latest = self._fetch_latest_fund_daily_codes()
        latest_codes = latest.get('codes') or set()
        amount_map = latest.get('amount_map') or {}
        listed_before = self._six_months_ago()
        records = [
            item for item in ((resp.get('data') or {}).get('records') or [])
            if isinstance(item, dict) and item.get('ts_code')
        ]

        items = []
        for item in records:
            ts_code = str(item.get('ts_code'))
            raw_list_date = str(item.get('list_date') or '')
            if ts_code.endswith('.OF'):
                continue
            if ts_code not in latest_codes:
                continue
            if len(raw_list_date) != 8 or not raw_list_date.isdigit():
                continue
            if datetime.strptime(raw_list_date, '%Y%m%d').date() > listed_before:
                continue
            if item.get('list_status') and item.get('list_status') != 'L':
                continue
            items.append({
                'target_type': 'etf',
                'ts_code': ts_code,
                'code': ts_code,
                'name': item.get('csname') or item.get('extname') or item.get('cname'),
                'index_code': item.get('index_code'),
                'index_name': item.get('index_name'),
                'exchange': item.get('exchange'),
                'list_date': f'{raw_list_date[:4]}-{raw_list_date[4:6]}-{raw_list_date[6:]}',
                'etf_type': item.get('etf_type'),
                'amount': amount_map.get(ts_code),
            })
        items.sort(key=lambda item: item.get('amount') or 0, reverse=True)
        return {'trade_date': latest.get('trade_date'), 'items': items[:universe_limit]}

    def _build_dataframe(self, records: List[Dict[str, Any]]) -> pd.DataFrame:
        df = pd.DataFrame(records)
        if df.empty:
            return df
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d', errors='coerce')
        df = df.dropna(subset=['trade_date']).sort_values('trade_date')
        df = df.drop_duplicates(subset=['trade_date'], keep='last')
        for col in ['open', 'high', 'low', 'close', 'pre_close', 'change', 'pct_chg', 'vol', 'amount']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=['open', 'high', 'low', 'close'])
        return df

    def _linear_regression(self, values: List[float]) -> Optional[Tuple[float, float]]:
        n = len(values)
        if n < 2:
            return None
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        numerator = sum((idx - x_mean) * (value - y_mean) for idx, value in enumerate(values))
        denominator = sum((idx - x_mean) ** 2 for idx in range(n))
        if denominator == 0:
            return None
        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        return slope, intercept

    def _channel_metrics(self, df: pd.DataFrame, channel_window: int) -> Optional[Dict[str, Any]]:
        if len(df) < channel_window:
            return None
        window_df = df.tail(channel_window).copy()
        lows = [float(v) for v in window_df['low'].tolist()]
        highs = [float(v) for v in window_df['high'].tolist()]
        lower_line = self._linear_regression(lows)
        upper_line = self._linear_regression(highs)
        if lower_line is None or upper_line is None:
            return None
        lower_slope, lower_intercept = lower_line
        upper_slope, upper_intercept = upper_line
        latest = window_df.iloc[-1]
        latest_close = float(latest['close'])
        last_x = channel_window - 1
        lower_latest = lower_intercept + lower_slope * last_x
        upper_latest = upper_intercept + upper_slope * last_x
        channel_width = upper_latest - lower_latest
        if latest_close <= 0 or lower_latest <= 0 or channel_width <= 0:
            return None
        distance_to_lower_pct = (latest_close - lower_latest) / latest_close * 100
        channel_position_pct = (latest_close - lower_latest) / channel_width * 100
        lower_slope_pct = lower_slope / latest_close * 100
        upper_slope_pct = upper_slope / latest_close * 100
        return {
            'latest_trade_date': latest['trade_date'].strftime('%Y-%m-%d'),
            'latest_close': round(latest_close, 4),
            'channel_window': channel_window,
            'lower_line_latest': round(lower_latest, 4),
            'upper_line_latest': round(upper_latest, 4),
            'channel_width_pct': round(channel_width / latest_close * 100, 4),
            'distance_to_lower_pct': round(distance_to_lower_pct, 4),
            'channel_position_pct': round(channel_position_pct, 4),
            'lower_slope': round(lower_slope, 6),
            'upper_slope': round(upper_slope, 6),
            'lower_slope_pct_per_day': round(lower_slope_pct, 6),
            'upper_slope_pct_per_day': round(upper_slope_pct, 6),
            'is_channel_up': lower_slope > 0 and upper_slope > 0,
        }

    def _pct_change(self, current: float, previous: Optional[float]) -> Optional[float]:
        if previous is None or previous == 0:
            return None
        return round((current / previous - 1) * 100, 4)

    def _rolling_value(self, series: pd.Series, window: int, kind: str = 'mean') -> Optional[float]:
        if len(series) < window:
            return None
        if kind == 'max':
            return self._safe_float(series.tail(window).max())
        if kind == 'min':
            return self._safe_float(series.tail(window).min())
        return self._safe_float(series.tail(window).mean())

    def _classify_stage(
        self,
        *,
        latest_close: float,
        ma20: Optional[float],
        ma60: Optional[float],
        position_percentile: Optional[float],
        momentum_20d: Optional[float],
        volume_ratio_20: Optional[float],
    ) -> str:
        if ma20 is not None and ma60 is not None and latest_close > ma20 > ma60 and (momentum_20d or 0) > 0:
            return 'uptrend'
        if ma20 is not None and ma60 is not None and latest_close < ma20 < ma60:
            return 'downtrend'
        if position_percentile is not None and position_percentile >= 80 and (volume_ratio_20 or 0) >= 1.2:
            return 'high_zone_with_volume'
        if position_percentile is not None and position_percentile <= 30:
            return 'low_zone_repair'
        return 'range_bound'

    def _build_decision_hint(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        stage = metrics['wave_stage']
        position = metrics.get('position_percentile')
        atr_pct = metrics.get('atr14_pct')
        volume_ratio = metrics.get('volume_ratio_20')

        reasons: List[str] = []
        risk_flags: List[str] = []
        if stage == 'uptrend':
            bias = 'trend_follow'
            reasons.append('收盘价位于 MA20 与 MA60 上方，且 MA20 高于 MA60，趋势结构偏强。')
        elif stage == 'downtrend':
            bias = 'avoid_or_wait'
            risk_flags.append('收盘价位于中期均线下方，波段结构偏弱。')
        elif stage == 'high_zone_with_volume':
            bias = 'watch_breakout_or_exhaustion'
            reasons.append('价格处于区间高位且量能放大，需要观察突破有效性。')
        elif stage == 'low_zone_repair':
            bias = 'watch_reversal'
            reasons.append('价格处于区间低位，适合观察止跌和均线修复。')
        else:
            bias = 'range_trade'
            reasons.append('价格处于区间震荡结构，可关注支撑压力间的波段机会。')

        if position is not None and position > 90:
            risk_flags.append('区间位置超过 90%，追高风险上升。')
        if atr_pct is not None and atr_pct > 5:
            risk_flags.append('ATR 波动率偏高，止损和仓位需要收紧。')
        if volume_ratio is not None and volume_ratio < 0.7:
            risk_flags.append('量能低于近 20 日均量，价格信号确认度偏弱。')

        return {
            'bias': bias,
            'reasons': reasons,
            'risk_flags': risk_flags,
        }

    def analyze(
        self,
        *,
        target_type: str,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = '',
    ) -> Dict[str, Any]:
        target_type = (target_type or '').lower()
        if target_type not in {'stock', 'etf'}:
            raise ValueError('target_type 仅支持 stock 或 etf')
        if not code:
            raise ValueError('code 为必填参数')

        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=240)
        start = self._normalize_date(start_date, start_dt)
        end = self._normalize_date(end_date, end_dt)
        ts_code = self._to_stock_ts_code(code) if target_type == 'stock' else code.upper()

        records = self._fetch_records(
            target_type=target_type,
            ts_code=ts_code,
            start_date=start,
            end_date=end,
            adjust=adjust,
        )
        df = self._build_dataframe(records)
        if df.empty:
            return replace_nan({
                'target_type': target_type,
                'ts_code': ts_code,
                'start_date': f'{start[:4]}-{start[4:6]}-{start[6:]}',
                'end_date': f'{end[:4]}-{end[4:6]}-{end[6:]}',
                'data_points': 0,
                'message': 'Tushare 未返回可分析行情数据',
                'analysis': None,
            })

        close = df['close']
        high = df['high']
        low = df['low']
        latest = df.iloc[-1]
        first = df.iloc[0]
        latest_close = float(latest['close'])

        ma5 = self._rolling_value(close, 5)
        ma10 = self._rolling_value(close, 10)
        ma20 = self._rolling_value(close, 20)
        ma60 = self._rolling_value(close, 60)
        high_idx = high.idxmax()
        low_idx = low.idxmin()
        period_high = float(df.loc[high_idx, 'high'])
        period_low = float(df.loc[low_idx, 'low'])
        price_range = period_high - period_low
        position_percentile = round((latest_close - period_low) / price_range * 100, 2) if price_range > 0 else None

        prev_close = close.shift(1)
        true_range = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        atr14 = self._rolling_value(true_range, 14)
        atr14_pct = round(atr14 / latest_close * 100, 4) if atr14 is not None and latest_close else None

        avg_vol20 = self._rolling_value(df['vol'], 20)
        latest_vol = self._safe_float(latest.get('vol'))
        volume_ratio_20 = round(latest_vol / avg_vol20, 4) if latest_vol is not None and avg_vol20 else None
        support_20d = self._rolling_value(low, 20, 'min')
        resistance_20d = self._rolling_value(high, 20, 'max')
        momentum_5d = self._pct_change(latest_close, self._safe_float(close.iloc[-6]) if len(close) > 5 else None)
        momentum_20d = self._pct_change(latest_close, self._safe_float(close.iloc[-21]) if len(close) > 20 else None)

        metrics = {
            'latest_trade_date': latest['trade_date'].strftime('%Y-%m-%d'),
            'latest_close': round(latest_close, 4),
            'period_return_pct': self._pct_change(latest_close, self._safe_float(first.get('close'))),
            'period_high': round(period_high, 4),
            'period_high_date': df.loc[high_idx, 'trade_date'].strftime('%Y-%m-%d'),
            'period_low': round(period_low, 4),
            'period_low_date': df.loc[low_idx, 'trade_date'].strftime('%Y-%m-%d'),
            'position_percentile': position_percentile,
            'pullback_from_high_pct': self._pct_change(latest_close, period_high),
            'rebound_from_low_pct': self._pct_change(latest_close, period_low),
            'ma': {
                'ma5': round(ma5, 4) if ma5 is not None else None,
                'ma10': round(ma10, 4) if ma10 is not None else None,
                'ma20': round(ma20, 4) if ma20 is not None else None,
                'ma60': round(ma60, 4) if ma60 is not None else None,
            },
            'momentum': {
                'momentum_5d_pct': momentum_5d,
                'momentum_20d_pct': momentum_20d,
            },
            'volatility': {
                'atr14': round(atr14, 4) if atr14 is not None else None,
                'atr14_pct': atr14_pct,
            },
            'volume': {
                'latest_vol': latest_vol,
                'avg_vol20': round(avg_vol20, 4) if avg_vol20 is not None else None,
                'volume_ratio_20': volume_ratio_20,
            },
            'levels': {
                'support_20d': round(support_20d, 4) if support_20d is not None else None,
                'resistance_20d': round(resistance_20d, 4) if resistance_20d is not None else None,
            },
            'wave_stage': self._classify_stage(
                latest_close=latest_close,
                ma20=ma20,
                ma60=ma60,
                position_percentile=position_percentile,
                momentum_20d=momentum_20d,
                volume_ratio_20=volume_ratio_20,
            ),
        }
        metrics['decision_hint'] = self._build_decision_hint(metrics)

        return replace_nan({
            'target_type': target_type,
            'ts_code': ts_code,
            'start_date': f'{start[:4]}-{start[4:6]}-{start[6:]}',
            'end_date': f'{end[:4]}-{end[4:6]}-{end[6:]}',
            'adjust': adjust or None,
            'data_source': 'Tushare',
            'data_interface': 'fund_daily' if target_type == 'etf' else ('pro_bar' if adjust in {'qfq', 'hfq'} else 'daily'),
            'data_points': len(df),
            'analysis': metrics,
            'theory': [
                {
                    'name': '趋势跟随',
                    'basis': '波段交易优先顺着中期趋势操作，MA20 与 MA60 用于识别中短期趋势结构。',
                    'related_fields': ['ma', 'wave_stage'],
                },
                {
                    'name': '支撑压力',
                    'basis': '区间高低点和近 20 日高低点用于判断价格所处位置，以及潜在止盈止损区域。',
                    'related_fields': ['period_high', 'period_low', 'levels', 'position_percentile'],
                },
                {
                    'name': '波动率风控',
                    'basis': 'ATR 衡量近期真实波动幅度，波动越大，波段仓位和止损距离越需要保守。',
                    'related_fields': ['volatility'],
                },
                {
                    'name': '量价确认',
                    'basis': '价格突破或反转需要成交量配合，volume_ratio_20 用于观察当前成交量相对 20 日均量是否放大。',
                    'related_fields': ['volume'],
                },
            ],
        })

    def screen_up_channel_near_lower(
        self,
        *,
        target_type: str = 'etf',
        codes: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = '',
        channel_window: int = 60,
        max_distance_pct: float = 3.0,
        max_channel_position_pct: float = 35.0,
        min_slope_pct: float = 0.0,
        universe_limit: int = 100,
        limit: int = 50,
    ) -> Dict[str, Any]:
        target_type = (target_type or 'etf').lower()
        if target_type not in {'stock', 'etf'}:
            raise ValueError('target_type 仅支持 stock 或 etf')
        channel_window = max(20, min(int(channel_window), 180))
        universe_limit = max(1, min(int(universe_limit), 2000))
        limit = max(1, min(int(limit), 500))
        max_distance_pct = float(max_distance_pct)
        max_channel_position_pct = float(max_channel_position_pct)
        min_slope_pct = float(min_slope_pct)

        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=max(240, channel_window * 4))
        start = self._normalize_date(start_date, start_dt)
        end = self._normalize_date(end_date, end_dt)

        requested_codes = []
        if codes:
            requested_codes = [code.strip() for code in codes.split(',') if code.strip()]

        if requested_codes:
            universe_trade_date = None
            universe = []
            for code in requested_codes:
                ts_code = self._to_stock_ts_code(code) if target_type == 'stock' else code.upper()
                universe.append({
                    'target_type': target_type,
                    'ts_code': ts_code,
                    'code': ts_code.split('.')[0] if target_type == 'stock' else ts_code,
                    'name': None,
                })
        elif target_type == 'stock':
            payload = self._fetch_stock_universe(universe_limit)
            universe_trade_date = payload.get('trade_date')
            universe = payload.get('items') or []
        else:
            payload = self._fetch_etf_universe(universe_limit)
            universe_trade_date = payload.get('trade_date')
            universe = payload.get('items') or []

        matches: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []
        for item in universe:
            ts_code = item['ts_code']
            try:
                records = self._fetch_records(
                    target_type=target_type,
                    ts_code=ts_code,
                    start_date=start,
                    end_date=end,
                    adjust=adjust if target_type == 'stock' else '',
                )
                df = self._build_dataframe(records)
                metrics = self._channel_metrics(df, channel_window)
                if not metrics:
                    skipped.append({'ts_code': ts_code, 'reason': '行情数据不足或通道无法计算'})
                    continue
                if not metrics['is_channel_up']:
                    continue
                if metrics['distance_to_lower_pct'] < 0:
                    continue
                if metrics['distance_to_lower_pct'] > max_distance_pct:
                    continue
                if metrics['channel_position_pct'] > max_channel_position_pct:
                    continue
                if metrics['lower_slope_pct_per_day'] < min_slope_pct:
                    continue
                matches.append({
                    **item,
                    'analysis': metrics,
                    'score': round(
                        max(0, max_distance_pct - metrics['distance_to_lower_pct']) * 2
                        + max(0, max_channel_position_pct - metrics['channel_position_pct']) * 0.2
                        + metrics['lower_slope_pct_per_day'] * 100,
                        4,
                    ),
                })
            except Exception as exc:
                skipped.append({'ts_code': ts_code, 'reason': str(exc)})

        matches.sort(
            key=lambda item: (
                item['analysis']['distance_to_lower_pct'],
                -item['analysis']['lower_slope_pct_per_day'],
            )
        )
        return replace_nan({
            'target_type': target_type,
            'data_source': 'Tushare',
            'universe_trade_date': universe_trade_date,
            'start_date': f'{start[:4]}-{start[4:6]}-{start[6:]}',
            'end_date': f'{end[:4]}-{end[4:6]}-{end[6:]}',
            'filters': {
                'channel_window': channel_window,
                'max_distance_pct': max_distance_pct,
                'max_channel_position_pct': max_channel_position_pct,
                'min_slope_pct': min_slope_pct,
                'universe_limit': universe_limit,
                'limit': limit,
                'adjust': adjust if target_type == 'stock' else None,
                'codes': requested_codes,
            },
            'total': len(matches[:limit]),
            'matched_total': len(matches),
            'scanned_total': len(universe),
            'skipped_total': len(skipped),
            'data': matches[:limit],
            'skipped_sample': skipped[:20],
            'theory': [
                '上升通道由不断抬高的高点与低点构成，代表资金愿意在更高位置承接。',
                '靠近下通道线通常对应趋势内回调区，理论上比追高更便于设置止损。',
                '筛选结果仍需要结合量能、市场环境与个股/ETF 基本面确认，不构成交易建议。',
            ],
            'query_time': datetime.now().isoformat(),
        })


swing_analysis_service = SwingAnalysisService()
