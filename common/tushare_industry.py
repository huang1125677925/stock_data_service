from __future__ import annotations

import concurrent.futures
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from .tushare_proxy import call_tushare


def _safe_records(resp: Any) -> List[Dict[str, Any]]:
    if not isinstance(resp, dict):
        return []
    data = resp.get("data") or {}
    records = data.get("records") or []
    if not isinstance(records, list):
        return []
    return [item for item in records if isinstance(item, dict)]


def _yyyymmdd(date_str: str) -> str:
    if "-" in date_str:
        return date_str.replace("-", "")
    return date_str


def normalize_sector_name(name: Optional[str]) -> str:
    value = str(name or "").strip().lower()
    if not value:
        return ""
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]", "", value)


def get_latest_completed_report_period(
    report_type: str = "annual",
    *,
    today: Optional[date] = None,
) -> str:
    current = today or datetime.now().date()

    if report_type == "annual":
        year = current.year - 1 if (current.month, current.day) >= (5, 1) else current.year - 2
        return f"{year}1231"
    if report_type == "semi_annual":
        year = current.year if (current.month, current.day) >= (9, 1) else current.year - 1
        return f"{year}0630"
    if report_type == "q1":
        year = current.year if (current.month, current.day) >= (5, 1) else current.year - 1
        return f"{year}0331"
    if report_type == "q3":
        year = current.year if (current.month, current.day) >= (11, 1) else current.year - 1
        return f"{year}0930"
    raise ValueError(f"unsupported report_type: {report_type}")


def build_report_periods(
    report_type: str = "annual",
    *,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    years: int = 8,
    today: Optional[date] = None,
) -> List[str]:
    suffix_map = {
        "annual": ["1231"],
        "semi_annual": ["0630"],
        "q1": ["0331"],
        "q3": ["0930"],
        "quarterly": ["0331", "0930"],
    }
    suffixes = suffix_map.get(report_type, ["1231"])
    current = today or datetime.now().date()
    latest_by_suffix = {
        suffix: get_latest_completed_report_period(
            {
                "1231": "annual",
                "0630": "semi_annual",
                "0331": "q1",
                "0930": "q3",
            }[suffix],
            today=current,
        )
        for suffix in suffixes
    }

    normalized_start = _yyyymmdd(start_date) if start_date else None
    normalized_end = _yyyymmdd(end_date) if end_date else None

    if normalized_start and normalized_end and len(normalized_start) == 8 and len(normalized_end) == 8:
        start_year = int(normalized_start[:4])
        end_year = int(normalized_end[:4])
    else:
        start_year = current.year - years + 1
        end_year = current.year

    periods: List[str] = []
    for year in range(start_year, end_year + 1):
        for suffix in suffixes:
            period = f"{year}{suffix}"
            if normalized_start and period < normalized_start:
                continue
            if normalized_end and period > normalized_end:
                continue
            if period > latest_by_suffix[suffix]:
                continue
            periods.append(period)
    return sorted(periods)


def get_open_trade_dates(
    start_date: str,
    end_date: str,
    token: Optional[str] = None,
) -> List[str]:
    resp = call_tushare(
        "trade_cal",
        params={
            "exchange": "",
            "start_date": _yyyymmdd(start_date),
            "end_date": _yyyymmdd(end_date),
            "is_open": "1",
        },
        fields="cal_date,is_open",
        token=token,
        use_query=False,
    )
    return sorted(
        [
            str(item.get("cal_date"))
            for item in _safe_records(resp)
            if item.get("cal_date")
        ]
    )


def get_latest_trade_date(token: Optional[str] = None) -> Optional[str]:
    end_dt = datetime.now().date()
    start_dt = end_dt - timedelta(days=20)
    dates = get_open_trade_dates(
        start_dt.strftime("%Y%m%d"),
        end_dt.strftime("%Y%m%d"),
        token=token,
    )
    return dates[-1] if dates else None


def get_sw_l1_sectors(token: Optional[str] = None) -> List[Dict[str, str]]:
    resp = call_tushare(
        "index_classify",
        params={"level": "L1", "src": "SW2021"},
        fields="index_code,industry_name,level",
        token=token,
        use_query=False,
    )
    records = _safe_records(resp)
    return [
        {
            "sector_code": str(item.get("index_code") or "").strip(),
            "sector_name": str(item.get("industry_name") or "").strip(),
        }
        for item in records
        if item.get("index_code") and item.get("industry_name")
    ]


def resolve_sw_l1_sector_code(
    sector_name: Optional[str],
    sectors: Optional[List[Dict[str, str]]] = None,
    token: Optional[str] = None,
) -> Optional[str]:
    target_name = str(sector_name or "").strip()
    if not target_name:
        return None

    sector_rows = sectors if sectors is not None else get_sw_l1_sectors(token=token)
    exact_map = {
        str(item.get("sector_name") or "").strip(): str(item.get("sector_code") or "").strip()
        for item in sector_rows
        if item.get("sector_name") and item.get("sector_code")
    }
    if target_name in exact_map:
        return exact_map[target_name]

    normalized_target = normalize_sector_name(target_name)
    if not normalized_target:
        return None

    normalized_matches = {
        str(item.get("sector_code") or "").strip()
        for item in sector_rows
        if normalize_sector_name(item.get("sector_name")) == normalized_target
        and item.get("sector_code")
    }
    if len(normalized_matches) == 1:
        return next(iter(normalized_matches))

    fuzzy_matches = {
        str(item.get("sector_code") or "").strip()
        for item in sector_rows
        if item.get("sector_name")
        and item.get("sector_code")
        and (
            normalized_target in normalize_sector_name(item.get("sector_name"))
            or normalize_sector_name(item.get("sector_name")) in normalized_target
        )
    }
    if len(fuzzy_matches) == 1:
        return next(iter(fuzzy_matches))

    return None


def get_sw_l1_members(token: Optional[str] = None) -> List[Dict[str, str]]:
    sectors = get_sw_l1_sectors(token=token)
    if not sectors:
        return []

    def fetch_one(sector: Dict[str, str]) -> List[Dict[str, str]]:
        resp = call_tushare(
            "index_member_all",
            params={"l1_code": sector["sector_code"], "is_new": "Y"},
            fields="l1_code,l1_name,ts_code,name,is_new",
            token=token,
            use_query=False,
        )
        return [
            {
                "sector_code": sector["sector_code"],
                "sector_name": sector["sector_name"],
                "ts_code": str(item.get("ts_code") or "").strip(),
                "name": str(item.get("name") or "").strip(),
            }
            for item in _safe_records(resp)
            if item.get("ts_code")
        ]

    members: List[Dict[str, str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(fetch_one, sector) for sector in sectors]
        for future in concurrent.futures.as_completed(futures):
            try:
                members.extend(future.result())
            except Exception:
                continue
    return members


def fetch_sw_daily_by_codes(
    ts_codes: List[str],
    start_date: str,
    end_date: str,
    *,
    fields: str,
    token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if not ts_codes:
        return []

    def fetch_one(ts_code: str) -> List[Dict[str, Any]]:
        resp = call_tushare(
            "sw_daily",
            params={
                "ts_code": ts_code,
                "start_date": _yyyymmdd(start_date),
                "end_date": _yyyymmdd(end_date),
            },
            fields=fields,
            token=token,
            use_query=False,
        )
        return _safe_records(resp)

    records: List[Dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(fetch_one, code) for code in ts_codes]
        for future in concurrent.futures.as_completed(futures):
            try:
                records.extend(future.result())
            except Exception:
                continue
    return records


def fetch_bak_daily_snapshot(
    trade_date: Optional[str] = None,
    *,
    fields: str = "ts_code,name,industry,total_mv",
    token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    actual_trade_date = trade_date or get_latest_trade_date(token=token)
    if not actual_trade_date:
        return []
    resp = call_tushare(
        "bak_daily",
        params={"trade_date": actual_trade_date},
        fields=fields,
        token=token,
        use_query=False,
    )
    return _safe_records(resp)


def fetch_financial_vip_period(
    interface: str,
    period: str,
    *,
    fields: str,
    token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    resp = call_tushare(
        interface,
        params={"period": period},
        fields=fields,
        token=token,
        use_query=False,
    )
    return _safe_records(resp)
