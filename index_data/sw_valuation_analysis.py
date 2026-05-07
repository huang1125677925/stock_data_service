"""申万行业估值分析：与 sw-valuation-analysis 接口一致的业务逻辑（无 HTTP）。"""

from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Set

from common.tushare_proxy import call_tushare

from .utils import replace_nan


@dataclass
class SwValuationAnalysisOutcome:
    """与 success_response / error_response 的 code、message、data 对齐。"""

    code: int
    message: str
    data: Optional[Dict[str, Any]] = None


def run_sw_valuation_analysis(
    start_date: str,
    end_date: str,
    *,
    level: Optional[str] = None,
    index_codes_str: Optional[str] = None,
) -> SwValuationAnalysisOutcome:
    """
    按 level 或 index_codes 拉取 sw_daily，计算窗口内 PE/PB 历史分位数及最新一日指标。

    参数与 GET /django/api/index/sw-valuation-analysis/ 的 Query 一致。
    """
    if not start_date or not end_date:
        return SwValuationAnalysisOutcome(400, "缺少必要参数: start_date, end_date")

    if not (index_codes_str or level):
        return SwValuationAnalysisOutcome(400, "必须提供 level 或 index_codes 其中之一")

    valid_codes: Set[str]
    if index_codes_str:
        valid_codes = {c.strip() for c in index_codes_str.split(",") if c.strip()}
    else:
        resp_classify = call_tushare(
            "index_classify", params={"level": level, "src": "SW2021"}, use_query=False
        )
        if resp_classify.get("code") != 200:
            return SwValuationAnalysisOutcome(
                500,
                f"获取行业分类失败: {resp_classify.get('message')}",
            )
        classify_data = resp_classify.get("data", {}).get("records", [])
        valid_codes = {item["index_code"] for item in classify_data if item.get("index_code")}

    if not valid_codes:
        return SwValuationAnalysisOutcome(
            200,
            "该Level下无行业数据",
            {"interface": "sw_valuation_analysis", "count": 0, "records": []},
        )

    try:
        start_dt = datetime.strptime(start_date, "%Y%m%d")
        end_dt = datetime.strptime(end_date, "%Y%m%d")
        days_diff = (end_dt - start_dt).days + 1
    except ValueError:
        return SwValuationAnalysisOutcome(400, "日期格式错误，应为YYYYMMDD")

    all_records: list = []

    def fetch_daily_data(date_str: str) -> list:
        resp = call_tushare("sw_daily", params={"trade_date": date_str}, use_query=False)
        if resp.get("code") == 200:
            records = resp.get("data", {}).get("records", [])
            return [r for r in records if r.get("ts_code") in valid_codes]
        return []

    def fetch_code_data(ts_code: str) -> list:
        resp = call_tushare(
            "sw_daily",
            params={"ts_code": ts_code, "start_date": start_date, "end_date": end_date},
            use_query=False,
        )
        if resp.get("code") == 200:
            return resp.get("data", {}).get("records", [])
        return []

    max_workers = 8

    if days_diff < len(valid_codes):
        date_list = []
        current_dt = start_dt
        while current_dt <= end_dt:
            date_list.append(current_dt.strftime("%Y%m%d"))
            current_dt += timedelta(days=1)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch_daily_data, d): d for d in date_list}
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        all_records.extend(result)
                except Exception:
                    pass
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch_code_data, code): code for code in valid_codes}
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        all_records.extend(result)
                except Exception:
                    pass

    grouped_data: Dict[str, list] = {}
    for record in all_records:
        code = record.get("ts_code")
        if code:
            grouped_data.setdefault(code, []).append(record)

    final_records = []
    for code, records in grouped_data.items():
        if not records:
            continue
        records.sort(key=lambda x: x.get("trade_date", ""))
        latest_record = records[-1]

        pe_values = [r.get("pe") for r in records if r.get("pe") is not None]
        current_pe = latest_record.get("pe")
        if current_pe is not None and pe_values:
            count_le = sum(1 for v in pe_values if v <= current_pe)
            latest_record["pe_percentile"] = round((count_le / len(pe_values)) * 100, 2)
        else:
            latest_record["pe_percentile"] = None

        pb_values = [r.get("pb") for r in records if r.get("pb") is not None]
        current_pb = latest_record.get("pb")
        if current_pb is not None and pb_values:
            count_le = sum(1 for v in pb_values if v <= current_pb)
            latest_record["pb_percentile"] = round((count_le / len(pb_values)) * 100, 2)
        else:
            latest_record["pb_percentile"] = None

        final_records.append(latest_record)

    final_records = replace_nan(final_records)
    final_records.sort(key=lambda x: x.get("ts_code", ""))

    result_data = {
        "interface": "sw_valuation_analysis",
        "count": len(final_records),
        "records": final_records,
    }
    return SwValuationAnalysisOutcome(200, "查询申万行业估值分析成功", result_data)
