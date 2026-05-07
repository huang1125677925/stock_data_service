"""
基于 Tushare index_basic + index_daily 合成指数情绪分（0–100，50 为中性）。
仅作交易参考，不构成投资建议。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


def _f(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _sort_by_date(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(records, key=lambda r: str(r.get("trade_date") or ""))


def _mean(xs: List[float]) -> Optional[float]:
    if not xs:
        return None
    return sum(xs) / len(xs)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _score_from_momentum(mean5: Optional[float], mean20: Optional[float]) -> float:
    if mean5 is None or mean20 is None:
        return 50.0
    diff = mean5 - mean20
    return _clamp(50.0 + 12.5 * diff, 0.0, 100.0)


def _score_from_trend(close: Optional[float], ma20: Optional[float]) -> float:
    if close is None or ma20 is None or ma20 == 0:
        return 50.0
    bias_pct = (close - ma20) / ma20 * 100.0
    return _clamp(50.0 + 2.0 * bias_pct, 0.0, 100.0)


def _score_from_today_pct(pct: Optional[float]) -> float:
    if pct is None:
        return 50.0
    return _clamp(50.0 + 5.0 * pct, 0.0, 100.0)


def _score_intraday(
    close: Optional[float],
    high: Optional[float],
    low: Optional[float],
) -> float:
    if close is None or high is None or low is None:
        return 50.0
    rng = high - low
    if rng <= 0:
        return 50.0
    strength = (close - low) / rng
    return _clamp(strength * 100.0, 0.0, 100.0)


def _sentiment_level(score: float) -> str:
    if score < 25:
        return "极度悲观"
    if score < 40:
        return "偏空"
    if score < 45:
        return "略偏空"
    if score <= 55:
        return "中性"
    if score <= 65:
        return "略偏多"
    if score <= 75:
        return "偏多"
    return "极度乐观"


def _trading_hint(score: float) -> str:
    if score < 40:
        return "情绪偏弱，宜谨慎控仓、注意下行风险"
    if score <= 60:
        return "情绪中性，可结合自有策略与风控执行"
    return "情绪偏强，注意追高风险与波动放大"


def compute_sentiment_from_series(
    rows: List[Dict[str, Any]],
    *,
    index_meta: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    根据已按日期升序的日线记录计算情绪。至少需要约 21 个交易日。
    返回 (payload, error_message)。
    """
    if len(rows) < 21:
        return None, f"有效交易日不足（当前 {len(rows)}，建议至少 21 日以计算 MA20）"

    last = rows[-1]
    trade_date = str(last.get("trade_date") or "")
    closes = [_f(r.get("close")) for r in rows]
    pcts = [_f(r.get("pct_chg")) for r in rows]

    if closes[-1] is None:
        return None, "最新一日缺少收盘价 close"

    last5 = pcts[-5:]
    last20 = pcts[-20:]
    if any(x is None for x in last5) or any(x is None for x in last20):
        return None, "涨跌幅 pct_chg 存在缺失，无法计算动量"

    mean5 = _mean([float(x) for x in last5])
    mean20 = _mean([float(x) for x in last20])
    ma20_slice = closes[-20:]
    if any(x is None for x in ma20_slice):
        return None, "收盘价序列存在缺失，无法计算 MA20"
    ma20 = sum(ma20_slice) / 20.0  # type: ignore

    c = _f(last.get("close"))
    h = _f(last.get("high"))
    l = _f(last.get("low"))
    pct1 = _f(last.get("pct_chg"))

    s_mom = _score_from_momentum(mean5, mean20)
    s_tr = _score_from_trend(c, ma20)
    s_td = _score_from_today_pct(pct1)
    s_intra = _score_intraday(c, h, l)

    w_mom, w_tr, w_td, w_intra = 0.25, 0.35, 0.25, 0.15
    sentiment = w_mom * s_mom + w_tr * s_tr + w_td * s_td + w_intra * s_intra
    sentiment = _clamp(sentiment, 0.0, 100.0)

    streak = 0
    for i in range(len(rows) - 1, -1, -1):
        pc = _f(rows[i].get("pct_chg"))
        if pc is None:
            break
        sign = 1 if pc > 0 else (-1 if pc < 0 else 0)
        if sign == 0:
            break
        if streak == 0:
            streak = sign
        elif (streak > 0 and sign > 0) or (streak < 0 and sign < 0):
            streak += sign
        else:
            break

    meta = index_meta or {}
    payload: Dict[str, Any] = {
        "ts_code": meta.get("ts_code") or last.get("ts_code"),
        "index_name": meta.get("name"),
        "market": meta.get("market"),
        "category": meta.get("category"),
        "fullname": meta.get("fullname"),
        "as_of_trade_date": trade_date,
        "sentiment_score": round(sentiment, 2),
        "sentiment_level": _sentiment_level(sentiment),
        "trading_reference": {
            "hint": _trading_hint(sentiment),
            "risk_note": "本指标由 index_daily 行情统计合成，仅供参考，不构成投资建议。",
        },
        "components": {
            "momentum_score": round(s_mom, 2),
            "trend_ma20_score": round(s_tr, 2),
            "today_pct_chg_score": round(s_td, 2),
            "intraday_close_in_range_score": round(s_intra, 2),
            "weights": {
                "momentum": w_mom,
                "trend_ma20": w_tr,
                "today_pct_chg": w_td,
                "intraday_strength": w_intra,
            },
            "mean_pct_chg_5d": round(mean5, 4) if mean5 is not None else None,
            "mean_pct_chg_20d": round(mean20, 4) if mean20 is not None else None,
            "ma20": round(ma20, 4) if ma20 is not None else None,
            "latest_pct_chg": pct1,
            "consecutive_same_direction_days": streak,
        },
        "methodology": (
            "情绪分=0.25×短期动量分+0.35×相对MA20趋势分+0.25×当日涨跌幅分+0.15×当日收盘在振幅位置分；"
            "各项均映射到0–100后加权，50为中性。"
        ),
    }
    return payload, None


def prepare_daily_rows(
    records: List[Dict[str, Any]],
    *,
    as_of_trade_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    rows = _sort_by_date([r for r in records if r.get("trade_date")])
    if as_of_trade_date:
        rows = [r for r in rows if str(r.get("trade_date") or "") <= as_of_trade_date]
    return rows


def default_lookback_dates(
    calendar_days: int = 300,
) -> Tuple[str, str]:
    end = datetime.now().date()
    start = end - timedelta(days=int(calendar_days))
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")
