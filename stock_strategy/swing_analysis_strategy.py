import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

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


swing_analysis_service = SwingAnalysisService()
