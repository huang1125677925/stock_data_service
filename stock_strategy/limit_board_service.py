from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from common.tushare_proxy import call_tushare

logger = logging.getLogger(__name__)

# 东方财富板块成分本地快照，供行业映射复用（与 industry_ma_breadth_strategy 共用同一份文件）
DC_BOARD_SNAPSHOT_FILE = (
    Path(__file__).resolve().parent.parent / "data" / "dc_board_members_snapshot.json"
)

# industry-trend-strength 接口支持的行业映射方式。
# default 使用 limit_list_d 的 industry 字段（按交易日动态）；
# 其余 5 种基于本地东方财富板块成分快照（静态成分，全区间一致）。
INDUSTRY_MAPPING_MODES: Dict[str, Dict[str, str]] = {
    "default": {"idx_type": "", "level": "", "label": "默认行业映射(limit_list_d)"},
    "dc_concept": {"idx_type": "概念板块", "level": "", "label": "东财概念板块"},
    "dc_region": {"idx_type": "地域板块", "level": "", "label": "东财地域板块"},
    "dc_l1": {"idx_type": "行业板块", "level": "东财一级行业", "label": "东财一级行业板块"},
    "dc_l2": {"idx_type": "行业板块", "level": "东财二级行业", "label": "东财二级行业板块"},
    "dc_l3": {"idx_type": "行业板块", "level": "东财三级行业", "label": "东财三级行业板块"},
}

DEFAULT_INDUSTRY_MAPPING = "default"


class LimitBoardDataService:
    """
    涨停打板组合数据服务。

    该服务只做 Tushare 多接口聚合和轻量统计，不写库；HTTP 层负责参数校验和响应包装。
    """

    # limit_list_ths `status` 字段中需要统计的涨停状态类型
    LIMIT_STATUS_TYPES: Tuple[str, ...] = ("T字板", "一字板", "换手板")

    # limit_list_ths 显式请求字段。
    # Tushare 默认仅返回“默认显示（Y）”字段，first_lu_time、rise_rate 等标记为 N 的字段
    # 需通过 fields 显式声明才会返回，否则响应中缺失这些列。
    LIMIT_LIST_THS_FIELDS: str = (
        "trade_date,ts_code,name,price,pct_chg,open_num,lu_desc,limit_type,tag,status,"
        "first_lu_time,last_lu_time,first_ld_time,last_ld_time,limit_order,limit_amount,"
        "turnover_rate,free_float,lu_limit_order,limit_up_suc_rate,turnover,"
        "rise_rate,sum_float,market_type"
    )

    def __init__(self, fetcher: Callable[..., Dict[str, Any]] = call_tushare):
        self.fetcher = fetcher

    def get_daily_sentiment(self, trade_date: str, token: Optional[str] = None) -> Dict[str, Any]:
        limit_up = self._fetch_records("limit_list_d", {"trade_date": trade_date, "limit_type": "U"}, token=token)
        limit_down = self._fetch_records("limit_list_d", {"trade_date": trade_date, "limit_type": "D"}, token=token)
        broken = self._fetch_records("limit_list_d", {"trade_date": trade_date, "limit_type": "Z"}, token=token)
        ladder = self._fetch_records("limit_step", {"trade_date": trade_date}, token=token)
        concepts = self._fetch_records("limit_cpt_list", {"trade_date": trade_date}, token=token)

        board_distribution = self._count_by_number(ladder, "nums")
        if not board_distribution:
            board_distribution = self._count_by_number(limit_up, "limit_times")

        max_board = max(board_distribution.keys(), default=0)
        limit_attempts = len(limit_up) + len(broken)
        broken_rate = self._safe_round(len(broken) / limit_attempts * 100 if limit_attempts else 0)
        sealed_rate = self._safe_round(len(limit_up) / limit_attempts * 100 if limit_attempts else 0)
        one_board_count = board_distribution.get(1, 0) or max(len(limit_up) - sum(v for k, v in board_distribution.items() if k >= 2), 0)
        second_board_or_above = sum(v for k, v in board_distribution.items() if k >= 2)
        high_board_count = sum(v for k, v in board_distribution.items() if k >= 3)

        sentiment_score = self._calc_sentiment_score(
            limit_up_count=len(limit_up),
            limit_down_count=len(limit_down),
            broken_rate=broken_rate,
            max_board=max_board,
            high_board_count=high_board_count,
        )
        phase = self._sentiment_phase(sentiment_score, len(limit_down), broken_rate, max_board)

        top_concepts = sorted(
            concepts,
            key=lambda item: (
                self._safe_int(item.get("rank"), 9999),
                -self._safe_float(item.get("up_nums")),
                -self._safe_float(item.get("pct_chg")),
            ),
        )[:20]

        return {
            "trade_date": trade_date,
            "summary": {
                "limit_up_count": len(limit_up),
                "limit_down_count": len(limit_down),
                "broken_limit_count": len(broken),
                "limit_attempt_count": limit_attempts,
                "sealed_rate": sealed_rate,
                "broken_rate": broken_rate,
                "max_board": max_board,
                "one_board_count": one_board_count,
                "second_board_or_above_count": second_board_or_above,
                "high_board_count": high_board_count,
                "sentiment_score": sentiment_score,
                "phase": phase["phase"],
                "phase_label": phase["label"],
                "conclusion": phase["conclusion"],
            },
            "board_distribution": [
                {"board": board, "count": count}
                for board, count in sorted(board_distribution.items(), reverse=True)
            ],
            "top_concepts": top_concepts,
            "source_counts": {
                "limit_list_d_up": len(limit_up),
                "limit_list_d_down": len(limit_down),
                "limit_list_d_broken": len(broken),
                "limit_step": len(ladder),
                "limit_cpt_list": len(concepts),
            },
            "query_time": datetime.now().isoformat(),
        }

    def get_enhanced_auction_candidates(
        self,
        trade_date: str,
        token: Optional[str] = None,
        top_n: int = 10,
        auction_max_retries: int = 6,
        auction_base_wait: int = 2,
    ) -> Dict[str, Any]:
        from .auction_selection_strategy import auction_selection_strategy_service

        base_result = auction_selection_strategy_service.get_strategy_result(
            trade_date=trade_date,
            top_n=max(top_n, 1),
            token=token,
            auction_max_retries=auction_max_retries,
            auction_base_wait=auction_base_wait,
        )

        ths_records = self._fetch_records("limit_list_ths", {"trade_date": trade_date}, token=token, required=False)
        kpl_records = self._fetch_records("kpl_list", {"trade_date": trade_date}, token=token, required=False)
        dc_hot_records = self._fetch_records("dc_hot", {"trade_date": trade_date, "market": "A股市场"}, token=token, required=False)
        ths_hot_records = self._fetch_records("ths_hot", {"trade_date": trade_date, "market": "热股"}, token=token, required=False)

        ths_map = self._first_by_code(ths_records)
        kpl_map = self._first_by_code(kpl_records)
        dc_hot_map = self._first_by_code(dc_hot_records)
        ths_hot_map = self._first_by_code(ths_hot_records)

        candidates = []
        for item in base_result.get("candidates", []):
            code = item.get("code") or item.get("ts_code")
            ths = ths_map.get(code, {})
            kpl = kpl_map.get(code, {})
            dc_hot = dc_hot_map.get(code, {})
            ths_hot = ths_hot_map.get(code, {})
            hot_score = self._calc_hot_score(dc_hot, ths_hot)
            enhanced_score = self._safe_round(self._safe_float(item.get("score")) + hot_score, 1)

            candidates.append({
                **item,
                "enhanced_score": enhanced_score,
                "hot_score": hot_score,
                "reason": ths.get("lu_desc") or kpl.get("theme") or "",
                "tags": self._merge_tags(ths.get("tag"), kpl.get("theme"), kpl.get("status")),
                "ths_status": ths.get("status"),
                "kpl_status": kpl.get("status"),
                "dc_hot": dc_hot,
                "ths_hot": ths_hot,
                "raw_sources": {
                    "limit_list_ths": ths,
                    "kpl_list": kpl,
                },
            })

        candidates.sort(key=lambda item: item.get("enhanced_score", item.get("score", 0)), reverse=True)

        return {
            **base_result,
            "top_candidates": candidates[:top_n],
            "candidates": candidates,
            "statistics": {
                **base_result.get("statistics", {}),
                "enhanced_selected_count": len(candidates),
                "ths_matched_count": sum(1 for item in candidates if item["raw_sources"]["limit_list_ths"]),
                "kpl_matched_count": sum(1 for item in candidates if item["raw_sources"]["kpl_list"]),
                "dc_hot_matched_count": sum(1 for item in candidates if item["dc_hot"]),
                "ths_hot_matched_count": sum(1 for item in candidates if item["ths_hot"]),
            },
            "params": {
                **base_result.get("params", {}),
                "top_n": top_n,
                "enhance_sources": ["limit_list_ths", "kpl_list", "dc_hot", "ths_hot"],
            },
        }

    def get_theme_ladder(self, trade_date: str, token: Optional[str] = None, top_n: int = 20) -> Dict[str, Any]:
        kpl_list = self._fetch_records("kpl_list", {"trade_date": trade_date, "tag": "涨停"}, token=token, required=False)
        concepts = self._fetch_records("kpl_concept", {"trade_date": trade_date}, token=token, required=False)
        concept_members = self._fetch_records("kpl_concept_cons", {"trade_date": trade_date}, token=token, required=False)
        strongest_concepts = self._fetch_records("limit_cpt_list", {"trade_date": trade_date}, token=token, required=False)
        limit_step = self._fetch_records("limit_step", {"trade_date": trade_date}, token=token, required=False)

        stock_ladder = {item.get("ts_code"): self._safe_int(item.get("nums")) for item in limit_step}
        stock_pool = self._first_by_code(kpl_list)
        concept_meta = {item.get("ts_code"): item for item in concepts if item.get("ts_code")}
        strongest_by_name = {item.get("name"): item for item in strongest_concepts if item.get("name")}

        grouped: Dict[str, Dict[str, Any]] = {}
        for member in concept_members:
            concept_code = member.get("ts_code")
            stock_code = member.get("con_code")
            stock = stock_pool.get(stock_code)
            if not concept_code or not stock_code or not stock:
                continue

            meta = concept_meta.get(concept_code, {})
            name = meta.get("name") or member.get("name") or concept_code
            bucket = grouped.setdefault(
                concept_code,
                {
                    "concept_code": concept_code,
                    "concept_name": name,
                    "limit_up_count": 0,
                    "max_board": 0,
                    "core_stocks": [],
                    "strongest_concept": strongest_by_name.get(name, {}),
                },
            )
            board = stock_ladder.get(stock_code) or self._parse_status_board(stock.get("status"))
            bucket["limit_up_count"] += 1
            bucket["max_board"] = max(bucket["max_board"], board)
            bucket["core_stocks"].append({
                "ts_code": stock_code,
                "name": stock.get("name") or member.get("con_name"),
                "board": board,
                "status": stock.get("status"),
                "theme": stock.get("theme"),
                "raw": stock,
            })

        if not grouped and strongest_concepts:
            for item in strongest_concepts:
                grouped[item.get("ts_code") or item.get("name")] = {
                    "concept_code": item.get("ts_code"),
                    "concept_name": item.get("name"),
                    "limit_up_count": self._safe_int(item.get("up_nums")),
                    "max_board": self._parse_up_stat(item.get("up_stat")),
                    "core_stocks": [],
                    "strongest_concept": item,
                }

        themes = list(grouped.values())
        for theme in themes:
            theme["core_stocks"].sort(key=lambda item: item.get("board", 0), reverse=True)
            theme["core_stocks"] = theme["core_stocks"][:10]
            theme["heat_score"] = self._safe_round(
                theme["limit_up_count"] * 2 + theme["max_board"] * 3 + self._safe_float(theme["strongest_concept"].get("pct_chg"))
            )

        themes.sort(key=lambda item: (item["heat_score"], item["limit_up_count"], item["max_board"]), reverse=True)

        return {
            "trade_date": trade_date,
            "total": len(themes),
            "themes": themes[:top_n],
            "source_counts": {
                "kpl_list": len(kpl_list),
                "kpl_concept": len(concepts),
                "kpl_concept_cons": len(concept_members),
                "limit_cpt_list": len(strongest_concepts),
                "limit_step": len(limit_step),
            },
            "query_time": datetime.now().isoformat(),
        }

    def get_break_reseal_analysis(self, trade_date: str, token: Optional[str] = None, top_n: int = 50) -> Dict[str, Any]:
        limit_up = self._fetch_records("limit_list_d", {"trade_date": trade_date, "limit_type": "U"}, token=token, required=False)
        broken = self._fetch_records("limit_list_d", {"trade_date": trade_date, "limit_type": "Z"}, token=token, required=False)
        ths_broken = self._fetch_records("limit_list_ths", {"trade_date": trade_date, "limit_type": "炸板池"}, token=token, required=False)
        ths_map = self._first_by_code(ths_broken)

        resealed = []
        for item in limit_up:
            open_times = self._safe_int(item.get("open_times"))
            if open_times <= 0:
                continue
            code = item.get("ts_code")
            resealed.append(self._build_break_item(item, "resealed", ths_map.get(code, {})))

        failed = [
            self._build_break_item(item, "failed", ths_map.get(item.get("ts_code"), {}))
            for item in broken
        ]

        resealed.sort(key=lambda item: (item["open_times"], item["break_strength_score"]), reverse=True)
        failed.sort(key=lambda item: (item["open_times"], item["amount"]), reverse=True)

        total_attempts = len(limit_up) + len(broken)
        return {
            "trade_date": trade_date,
            "summary": {
                "limit_up_count": len(limit_up),
                "resealed_count": len(resealed),
                "failed_break_count": len(failed),
                "break_attempt_count": len(resealed) + len(failed),
                "failed_break_rate": self._safe_round(len(failed) / total_attempts * 100 if total_attempts else 0),
                "reseal_rate_after_break": self._safe_round(len(resealed) / (len(resealed) + len(failed)) * 100 if (len(resealed) + len(failed)) else 0),
            },
            "resealed": resealed[:top_n],
            "failed": failed[:top_n],
            "source_counts": {
                "limit_list_d_up": len(limit_up),
                "limit_list_d_broken": len(broken),
                "limit_list_ths_broken": len(ths_broken),
            },
            "query_time": datetime.now().isoformat(),
        }

    def get_hot_money_review(self, trade_date: str, token: Optional[str] = None, top_n: int = 100) -> Dict[str, Any]:
        top_list = self._fetch_records("top_list", {"trade_date": trade_date}, token=token, required=False)
        hm_detail = self._fetch_records("hm_detail", {"trade_date": trade_date}, token=token, required=False)
        limit_up = self._fetch_records("limit_list_d", {"trade_date": trade_date, "limit_type": "U"}, token=token, required=False)
        broken = self._fetch_records("limit_list_d", {"trade_date": trade_date, "limit_type": "Z"}, token=token, required=False)

        limit_up_map = self._first_by_code(limit_up)
        broken_map = self._first_by_code(broken)
        hm_by_stock: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        hm_counter: Counter[str] = Counter()
        hm_net_buy: Counter[str] = Counter()

        for item in hm_detail:
            code = item.get("ts_code")
            if code:
                hm_by_stock[code].append(item)
            hm_name = item.get("hm_name") or item.get("name")
            if hm_name:
                hm_counter[hm_name] += 1
                hm_net_buy[hm_name] += self._safe_float(item.get("net_amount") or item.get("net_buy") or item.get("buy_amount")) - self._safe_float(item.get("sell_amount"))

        review_records = []
        for item in top_list:
            code = item.get("ts_code")
            board_status = "limit_up" if code in limit_up_map else "broken" if code in broken_map else "other"
            review_records.append({
                "ts_code": code,
                "name": item.get("name"),
                "board_status": board_status,
                "top_list": item,
                "limit_record": limit_up_map.get(code) or broken_map.get(code) or {},
                "hot_money_records": hm_by_stock.get(code, []),
                "hot_money_count": len(hm_by_stock.get(code, [])),
            })

        review_records.sort(key=lambda item: (item["board_status"] == "limit_up", item["hot_money_count"]), reverse=True)
        active_hot_money = [
            {
                "hm_name": name,
                "appear_count": count,
                "estimated_net_buy": self._safe_round(hm_net_buy[name], 2),
            }
            for name, count in hm_counter.most_common(30)
        ]

        return {
            "trade_date": trade_date,
            "summary": {
                "top_list_count": len(top_list),
                "hot_money_detail_count": len(hm_detail),
                "top_limit_up_count": sum(1 for item in review_records if item["board_status"] == "limit_up"),
                "top_broken_count": sum(1 for item in review_records if item["board_status"] == "broken"),
                "active_hot_money_count": len(active_hot_money),
            },
            "active_hot_money": active_hot_money,
            "records": review_records[:top_n],
            "source_counts": {
                "top_list": len(top_list),
                "hm_detail": len(hm_detail),
                "limit_list_d_up": len(limit_up),
                "limit_list_d_broken": len(broken),
            },
            "query_time": datetime.now().isoformat(),
        }

    def get_trend_analysis(
        self,
        start_date: str,
        end_date: str,
        token: Optional[str] = None,
        top_n: int = 20,
    ) -> Dict[str, Any]:
        """
        获取涨停打板趋势分析。

        时间维度覆盖三类变化：
        - 情绪变化：涨停、跌停、炸板、封板率、连板高度、情绪分。
        - 题材变化：强势题材在区间内的上榜天数、热度峰值、排名变化。
        - 个股生命周期：股票在区间内涨停/炸板/连板演进。
        """
        self._validate_date_range(start_date, end_date)

        limit_up = self._fetch_records("limit_list_d", {"start_date": start_date, "end_date": end_date, "limit_type": "U"}, token=token, required=False)
        limit_down = self._fetch_records("limit_list_d", {"start_date": start_date, "end_date": end_date, "limit_type": "D"}, token=token, required=False)
        broken = self._fetch_records("limit_list_d", {"start_date": start_date, "end_date": end_date, "limit_type": "Z"}, token=token, required=False)
        ladder = self._fetch_records("limit_step", {"start_date": start_date, "end_date": end_date}, token=token, required=False)
        concepts = self._fetch_records("limit_cpt_list", {"start_date": start_date, "end_date": end_date}, token=token, required=False)

        up_by_date = self._group_by_date(limit_up)
        down_by_date = self._group_by_date(limit_down)
        broken_by_date = self._group_by_date(broken)
        ladder_by_date = self._group_by_date(ladder)
        concepts_by_date = self._group_by_date(concepts)
        trade_dates = sorted(set(up_by_date) | set(down_by_date) | set(broken_by_date) | set(ladder_by_date) | set(concepts_by_date))

        sentiment_series = []
        prev_point: Optional[Dict[str, Any]] = None
        for trade_date in trade_dates:
            up_records = up_by_date.get(trade_date, [])
            down_records = down_by_date.get(trade_date, [])
            broken_records = broken_by_date.get(trade_date, [])
            ladder_records = ladder_by_date.get(trade_date, [])

            board_distribution = self._count_by_number(ladder_records, "nums")
            if not board_distribution:
                board_distribution = self._count_by_number(up_records, "limit_times")
            max_board = max(board_distribution.keys(), default=0)
            limit_attempts = len(up_records) + len(broken_records)
            broken_rate = self._safe_round(len(broken_records) / limit_attempts * 100 if limit_attempts else 0)
            sealed_rate = self._safe_round(len(up_records) / limit_attempts * 100 if limit_attempts else 0)
            high_board_count = sum(v for k, v in board_distribution.items() if k >= 3)
            sentiment_score = self._calc_sentiment_score(
                limit_up_count=len(up_records),
                limit_down_count=len(down_records),
                broken_rate=broken_rate,
                max_board=max_board,
                high_board_count=high_board_count,
            )
            phase = self._sentiment_phase(sentiment_score, len(down_records), broken_rate, max_board)
            point = {
                "trade_date": trade_date,
                "limit_up_count": len(up_records),
                "limit_down_count": len(down_records),
                "broken_limit_count": len(broken_records),
                "limit_attempt_count": limit_attempts,
                "sealed_rate": sealed_rate,
                "broken_rate": broken_rate,
                "max_board": max_board,
                "high_board_count": high_board_count,
                "sentiment_score": sentiment_score,
                "phase": phase["phase"],
                "phase_label": phase["label"],
                "board_distribution": [
                    {"board": board, "count": count}
                    for board, count in sorted(board_distribution.items(), reverse=True)
                ],
                "top_concepts": sorted(
                    concepts_by_date.get(trade_date, []),
                    key=lambda item: self._safe_int(item.get("rank"), 9999),
                )[:10],
            }
            if prev_point:
                point["changes"] = {
                    "limit_up_count": point["limit_up_count"] - prev_point["limit_up_count"],
                    "broken_limit_count": point["broken_limit_count"] - prev_point["broken_limit_count"],
                    "max_board": point["max_board"] - prev_point["max_board"],
                    "sentiment_score": self._safe_round(point["sentiment_score"] - prev_point["sentiment_score"], 1),
                }
            else:
                point["changes"] = {
                    "limit_up_count": 0,
                    "broken_limit_count": 0,
                    "max_board": 0,
                    "sentiment_score": 0,
                }
            sentiment_series.append(point)
            prev_point = point

        concept_trends = self._build_concept_trends(concepts, top_n=top_n)
        stock_lifecycles = self._build_stock_lifecycles(limit_up=limit_up, broken=broken, ladder=ladder, top_n=top_n)
        phase_counter = Counter(item["phase"] for item in sentiment_series)

        return {
            "start_date": start_date,
            "end_date": end_date,
            "trade_dates": trade_dates,
            "summary": {
                "trade_day_count": len(trade_dates),
                "avg_limit_up_count": self._safe_round(sum(item["limit_up_count"] for item in sentiment_series) / len(sentiment_series) if sentiment_series else 0),
                "avg_broken_rate": self._safe_round(sum(item["broken_rate"] for item in sentiment_series) / len(sentiment_series) if sentiment_series else 0),
                "max_board_peak": max((item["max_board"] for item in sentiment_series), default=0),
                "sentiment_score_start": sentiment_series[0]["sentiment_score"] if sentiment_series else 0,
                "sentiment_score_end": sentiment_series[-1]["sentiment_score"] if sentiment_series else 0,
                "sentiment_score_change": self._safe_round(
                    (sentiment_series[-1]["sentiment_score"] - sentiment_series[0]["sentiment_score"]) if len(sentiment_series) >= 2 else 0,
                    1,
                ),
                "phase_distribution": dict(phase_counter),
                "dominant_phase": phase_counter.most_common(1)[0][0] if phase_counter else "",
            },
            "sentiment_series": sentiment_series,
            "concept_trends": concept_trends,
            "stock_lifecycles": stock_lifecycles,
            "source_counts": {
                "limit_list_d_up": len(limit_up),
                "limit_list_d_down": len(limit_down),
                "limit_list_d_broken": len(broken),
                "limit_step": len(ladder),
                "limit_cpt_list": len(concepts),
            },
            "query_time": datetime.now().isoformat(),
        }

    def get_industry_trend_strength(
        self,
        start_date: str,
        end_date: str,
        token: Optional[str] = None,
        industry_mapping: str = DEFAULT_INDUSTRY_MAPPING,
    ) -> Dict[str, Any]:
        """
        获取行业维度的涨停趋势强度分析。

        功能：
        - 以 `limit_list_ths(limit_type=涨停池)` 在指定时间区间内的同花顺涨停池数据为基础，
          按 `industry_mapping` 指定的映射方式获取每只涨停股所属行业。
        - 剔除 ST/退市类股票，以及无法归类到具体行业（未知行业）的个股，二者均不计入统计范围。
        - 结果以交易日为 key，每个交易日返回整体、行业、个股三个维度：
          - 整体：该日（过滤后）涨停总数（按去重个股计）与涉及行业数量。
          - 行业：该日涨停股细分到各个行业，以及每个行业的涨停数量与涨停状态统计
            （`T字板`、`一字板`、`换手板`）。
          - 个股：每个行业内的涨停股列表，每只个股包含 `limit_list_ths` 中该日的全部原始字段
            （并补充所属行业 `industry`）。

        行业映射方式（`industry_mapping`）：
        - `default`：从 `limit_list_d(limit_type=U)` 的 `industry` 字段按交易日动态映射（默认）。
        - `dc_concept` / `dc_region` / `dc_l1` / `dc_l2` / `dc_l3`：基于本地东方财富板块成分
          快照（概念板块 / 地域板块 / 东财一/二/三级行业板块）映射，成分为静态快照，全区间一致。
          其中 `dc_concept` 为多对多映射，同一只涨停股可同时归入多个概念板块，因此整体/汇总的
          涨停总数按去重个股计，各行业的涨停数量则按成分归属分别计入。

        参数：
        - start_date (str): 开始日期，格式 `YYYYMMDD`。
        - end_date (str): 结束日期，格式 `YYYYMMDD`。
        - token (str，可选): Tushare Token，用于覆盖默认环境变量。
        - industry_mapping (str): 行业映射方式，取值见 `INDUSTRY_MAPPING_MODES`，默认 `default`。

        返回值：
        - Dict[str, Any]: 包含查询区间、汇总信息、按交易日为 key 的三维明细、源数据统计和查询时间。

        异常：
        - ValueError: 日期格式非法、开始日期晚于结束日期、查询区间超限、或映射方式非法时抛出。
        - RuntimeError: Tushare 接口调用失败时抛出。
        """
        self._validate_date_range(start_date, end_date)
        mapping_mode = self._normalize_industry_mapping(industry_mapping)
        mapping_meta = INDUSTRY_MAPPING_MODES[mapping_mode]
        use_snapshot = mapping_mode != DEFAULT_INDUSTRY_MAPPING

        ths_records = self._fetch_records(
            "limit_list_ths",
            {"start_date": start_date, "end_date": end_date, "limit_type": "涨停池"},
            token=token,
            fields=self.LIMIT_LIST_THS_FIELDS,
            required=False,
        )

        # 构建行业解析器：default 走 limit_list_d 动态映射，其余走本地板块成分快照。
        limit_up_d: List[Dict[str, Any]] = []
        industry_map: Dict[Tuple[str, str], str] = {}
        snapshot_index: Dict[str, List[str]] = {}
        if use_snapshot:
            snapshot_index = self._build_snapshot_industry_index(
                idx_type=mapping_meta["idx_type"],
                level=mapping_meta["level"],
            )
        else:
            limit_up_d = self._fetch_records(
                "limit_list_d",
                {"start_date": start_date, "end_date": end_date, "limit_type": "U"},
                token=token,
                required=False,
            )
            industry_map = self._build_industry_map(limit_up_d)

        def resolve_industries(trade_date: str, code: Any, record: Dict[str, Any]) -> List[str]:
            if use_snapshot:
                return list(snapshot_index.get(str(code or ""), []))
            mapped_industry = industry_map.get((trade_date, code))
            industry = mapped_industry or str(record.get("industry") or "").strip()
            return [industry] if industry else []

        data: Dict[str, Any] = {}
        industry_matched_count = 0
        counted_limit_up_count = 0
        excluded_st_count = 0
        excluded_unknown_industry_count = 0
        grouped = self._group_by_date(ths_records)
        for trade_date in sorted(grouped.keys()):
            day_records = grouped[trade_date]
            industry_stocks: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            day_unique_codes: set = set()
            for record in day_records:
                # 剔除 ST 股票，不计入统计范围
                if self._is_st_stock(record.get("name")):
                    excluded_st_count += 1
                    continue
                code = record.get("ts_code")
                industries = resolve_industries(trade_date, code, record)
                # 剔除无法归类到具体行业（未知行业）的个股，不计入统计范围
                if not industries:
                    excluded_unknown_industry_count += 1
                    continue
                industry_matched_count += 1
                day_unique_codes.add(code)
                # 多对多映射（如概念板块）下同一只个股会归入多个行业分组
                for industry in industries:
                    industry_stocks[industry].append({**record, "industry": industry})

            # 该交易日经过滤后无有效涨停个股则跳过
            if not industry_stocks:
                continue

            # 整体涨停总数按去重个股计（概念多对多时避免重复计数）
            day_limit_up_count = len(day_unique_codes)
            counted_limit_up_count += day_limit_up_count
            industries = sorted(
                (
                    {
                        "industry": name,
                        "limit_up_count": len(stocks),
                        "status_counts": self._count_limit_status(stocks),
                    }
                    for name, stocks in industry_stocks.items()
                ),
                key=lambda item: (-item["limit_up_count"], item["industry"]),
            )
            data[trade_date] = {
                "trade_date": trade_date,
                "overall": {
                    "limit_up_count": day_limit_up_count,
                    "industry_count": len(industry_stocks),
                },
                "industries": industries,
                "stocks": dict(industry_stocks),
            }

        trade_dates = sorted(data.keys())

        industry_range_totals: Dict[str, Dict[str, Any]] = {}
        for trade_date in trade_dates:
            for entry in data[trade_date]["industries"]:
                name = entry["industry"]
                agg = industry_range_totals.setdefault(
                    name,
                    {"industry": name, "total_limit_up_count": 0, "trade_day_count": 0},
                )
                agg["total_limit_up_count"] += entry["limit_up_count"]
                agg["trade_day_count"] += 1

        top_industries = sorted(
            (
                {
                    **agg,
                    "avg_daily_limit_up_count": self._safe_round(
                        agg["total_limit_up_count"] / agg["trade_day_count"] if agg["trade_day_count"] else 0
                    ),
                }
                for agg in industry_range_totals.values()
            ),
            key=lambda item: (-item["total_limit_up_count"], item["industry"]),
        )[:20]

        return {
            "start_date": start_date,
            "end_date": end_date,
            "summary": {
                "trade_day_count": len(trade_dates),
                "industry_count": len(industry_range_totals),
                "total_limit_up_count": counted_limit_up_count,
                "industry_matched_count": industry_matched_count,
                "excluded_st_count": excluded_st_count,
                "excluded_unknown_industry_count": excluded_unknown_industry_count,
                "industry_mapping": mapping_mode,
                "industry_mapping_label": mapping_meta["label"],
                "top_industries": top_industries,
            },
            "data": data,
            "source_counts": {
                "limit_list_ths": len(ths_records),
                "limit_list_d_up": len(limit_up_d),
                "dc_board_snapshot_stocks": len(snapshot_index),
            },
            "query_time": datetime.now().isoformat(),
        }

    def _fetch_records(
        self,
        interface: str,
        params: Dict[str, Any],
        token: Optional[str] = None,
        fields: Optional[str] = None,
        required: bool = True,
    ) -> List[Dict[str, Any]]:
        resp = self.fetcher(interface, params=params, fields=fields, token=token, use_query=False)
        if resp.get("code") != 200:
            if required:
                raise RuntimeError(resp.get("message") or f"Tushare {interface} 调用失败")
            return []
        data = resp.get("data") or {}
        return data.get("records") or []

    @staticmethod
    def _group_by_date(records: Iterable[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for item in records:
            trade_date = str(item.get("trade_date") or "")
            if trade_date:
                grouped[trade_date].append(item)
        return dict(grouped)

    @staticmethod
    def _is_st_stock(name: Any) -> bool:
        """
        判断股票名称是否为 ST/退市类股票。

        参数：
        - name (Any): 股票名称，通常来自 `limit_list_ths` 的 `name` 字段。

        返回值：
        - bool: 名称中包含 `ST`（含 `*ST`、`SST`、`S*ST` 等）或 `退` 时返回 True。

        异常：
        - 无。
        """
        text = str(name or "").upper()
        return "ST" in text or "退" in text

    @staticmethod
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

    @classmethod
    def _load_board_snapshot(cls) -> List[Dict[str, Any]]:
        """
        加载本地东方财富板块成分快照（进程内缓存）。

        参数：
        - 无。

        返回值：
        - List[Dict[str, Any]]: 快照中的板块列表；文件缺失或解析失败时返回空列表。

        异常：
        - 无。内部异常会记录日志并返回空列表。
        """
        cached = getattr(cls, "_board_snapshot_cache", None)
        if cached is not None:
            return cached
        boards: List[Dict[str, Any]] = []
        try:
            if DC_BOARD_SNAPSHOT_FILE.exists():
                with DC_BOARD_SNAPSHOT_FILE.open("r", encoding="utf-8") as file_obj:
                    payload = json.load(file_obj)
                raw_boards = payload.get("boards", []) if isinstance(payload, dict) else []
                boards = [item for item in raw_boards if isinstance(item, dict)]
            else:
                logger.warning("本地板块成分快照不存在: %s", DC_BOARD_SNAPSHOT_FILE)
        except Exception as exc:  # noqa: BLE001
            logger.warning("读取本地板块成分快照失败: %s", exc)
            boards = []
        cls._board_snapshot_cache = boards
        return boards

    @classmethod
    def _build_snapshot_industry_index(cls, idx_type: str, level: str) -> Dict[str, List[str]]:
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
        for board in cls._load_board_snapshot():
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

    @classmethod
    def _count_limit_status(cls, stocks: Iterable[Dict[str, Any]]) -> Dict[str, int]:
        """
        统计一组涨停股在 `LIMIT_STATUS_TYPES` 各涨停状态下的数量。

        参数：
        - stocks (Iterable[Dict[str, Any]]): 涨停个股记录集合，取每条记录的 `status` 字段。

        返回值：
        - Dict[str, int]: 以涨停状态（`T字板`、`一字板`、`换手板`）为键、对应数量为值的字典，
          未出现的状态计数为 0。

        异常：
        - 无。
        """
        counts: Dict[str, int] = {status: 0 for status in cls.LIMIT_STATUS_TYPES}
        for item in stocks:
            status = str(item.get("status") or "").strip()
            if status in counts:
                counts[status] += 1
        return counts

    @staticmethod
    def _build_industry_map(
        records: Iterable[Dict[str, Any]]
    ) -> Dict[Tuple[str, str], str]:
        """
        基于 `limit_list_d` 记录构建 `(交易日, 股票代码) -> 行业` 的映射。

        参数：
        - records (Iterable[Dict[str, Any]]): `limit_list_d(limit_type=U)` 返回的原始记录集合。

        返回值：
        - Dict[Tuple[str, str], str]: 以 `(trade_date, ts_code)` 为键、所属行业为值的映射。
          缺失交易日或股票代码的记录会被忽略，缺失行业的记录不写入映射。

        异常：
        - 无。
        """
        mapping: Dict[Tuple[str, str], str] = {}
        for item in records:
            trade_date = str(item.get("trade_date") or "")
            code = item.get("ts_code")
            if not trade_date or not code:
                continue
            industry = str(item.get("industry") or "").strip()
            if industry:
                mapping[(trade_date, code)] = industry
        return mapping

    @classmethod
    def _build_concept_trends(cls, concepts: Iterable[Dict[str, Any]], top_n: int) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}
        for item in concepts:
            key = item.get("ts_code") or item.get("name")
            if not key:
                continue
            bucket = grouped.setdefault(
                key,
                {
                    "concept_code": item.get("ts_code"),
                    "concept_name": item.get("name"),
                    "active_days": 0,
                    "first_date": None,
                    "last_date": None,
                    "peak_rank": 9999,
                    "max_up_nums": 0,
                    "max_cons_nums": 0,
                    "max_board": 0,
                    "avg_pct_chg": 0.0,
                    "heat_score": 0.0,
                    "series": [],
                },
            )
            trade_date = str(item.get("trade_date") or "")
            rank = cls._safe_int(item.get("rank"), 9999)
            up_nums = cls._safe_int(item.get("up_nums"))
            cons_nums = cls._safe_int(item.get("cons_nums"))
            pct_chg = cls._safe_float(item.get("pct_chg"))
            max_board = cls._parse_up_stat(item.get("up_stat"))
            bucket["active_days"] += 1
            bucket["first_date"] = min(bucket["first_date"], trade_date) if bucket["first_date"] else trade_date
            bucket["last_date"] = max(bucket["last_date"], trade_date) if bucket["last_date"] else trade_date
            bucket["peak_rank"] = min(bucket["peak_rank"], rank)
            bucket["max_up_nums"] = max(bucket["max_up_nums"], up_nums)
            bucket["max_cons_nums"] = max(bucket["max_cons_nums"], cons_nums)
            bucket["max_board"] = max(bucket["max_board"], max_board)
            bucket["series"].append({
                "trade_date": trade_date,
                "rank": rank,
                "up_nums": up_nums,
                "cons_nums": cons_nums,
                "pct_chg": pct_chg,
                "up_stat": item.get("up_stat"),
                "raw": item,
            })

        trends = []
        for bucket in grouped.values():
            bucket["series"].sort(key=lambda item: item["trade_date"])
            pct_values = [item["pct_chg"] for item in bucket["series"]]
            bucket["avg_pct_chg"] = cls._safe_round(sum(pct_values) / len(pct_values) if pct_values else 0)
            bucket["heat_score"] = cls._safe_round(
                bucket["active_days"] * 4
                + bucket["max_up_nums"] * 1.5
                + bucket["max_cons_nums"] * 2
                + bucket["max_board"] * 3
                + max(0, 30 - bucket["peak_rank"]),
                1,
            )
            bucket["rank_change"] = cls._safe_int(bucket["series"][-1]["rank"], 9999) - cls._safe_int(bucket["series"][0]["rank"], 9999) if len(bucket["series"]) >= 2 else 0
            trends.append(bucket)

        trends.sort(key=lambda item: (item["heat_score"], item["active_days"], item["max_up_nums"]), reverse=True)
        return trends[:top_n]

    @classmethod
    def _build_stock_lifecycles(
        cls,
        limit_up: Iterable[Dict[str, Any]],
        broken: Iterable[Dict[str, Any]],
        ladder: Iterable[Dict[str, Any]],
        top_n: int,
    ) -> List[Dict[str, Any]]:
        ladder_by_date_code = {
            (str(item.get("trade_date") or ""), item.get("ts_code")): cls._safe_int(item.get("nums"))
            for item in ladder
            if item.get("trade_date") and item.get("ts_code")
        }
        grouped: Dict[str, Dict[str, Any]] = {}

        for item in limit_up:
            code = item.get("ts_code")
            if not code:
                continue
            trade_date = str(item.get("trade_date") or "")
            board = ladder_by_date_code.get((trade_date, code)) or cls._safe_int(item.get("limit_times"), 1)
            bucket = grouped.setdefault(
                code,
                {
                    "ts_code": code,
                    "name": item.get("name"),
                    "industry": item.get("industry"),
                    "first_limit_date": trade_date,
                    "last_limit_date": trade_date,
                    "limit_up_days": 0,
                    "broken_days": 0,
                    "max_board": 0,
                    "current_status": "limit_up",
                    "lifecycle_stage": "",
                    "events": [],
                },
            )
            bucket["name"] = bucket.get("name") or item.get("name")
            bucket["industry"] = bucket.get("industry") or item.get("industry")
            bucket["first_limit_date"] = min(bucket["first_limit_date"], trade_date)
            bucket["last_limit_date"] = max(bucket["last_limit_date"], trade_date)
            bucket["limit_up_days"] += 1
            bucket["max_board"] = max(bucket["max_board"], board)
            bucket["current_status"] = "limit_up"
            bucket["events"].append({
                "trade_date": trade_date,
                "event": "limit_up",
                "board": board,
                "open_times": cls._safe_int(item.get("open_times")),
                "first_time": item.get("first_time"),
                "last_time": item.get("last_time"),
                "raw": item,
            })

        for item in broken:
            code = item.get("ts_code")
            if not code:
                continue
            trade_date = str(item.get("trade_date") or "")
            bucket = grouped.setdefault(
                code,
                {
                    "ts_code": code,
                    "name": item.get("name"),
                    "industry": item.get("industry"),
                    "first_limit_date": "",
                    "last_limit_date": "",
                    "limit_up_days": 0,
                    "broken_days": 0,
                    "max_board": 0,
                    "current_status": "broken",
                    "lifecycle_stage": "",
                    "events": [],
                },
            )
            bucket["name"] = bucket.get("name") or item.get("name")
            bucket["industry"] = bucket.get("industry") or item.get("industry")
            bucket["broken_days"] += 1
            bucket["current_status"] = "broken"
            bucket["events"].append({
                "trade_date": trade_date,
                "event": "broken",
                "board": cls._safe_int(item.get("limit_times")),
                "open_times": cls._safe_int(item.get("open_times")),
                "first_time": item.get("first_time"),
                "last_time": item.get("last_time"),
                "raw": item,
            })

        lifecycles = []
        for bucket in grouped.values():
            bucket["events"].sort(key=lambda item: item["trade_date"])
            if bucket["events"]:
                bucket["current_status"] = bucket["events"][-1]["event"]
            bucket["lifecycle_stage"] = cls._stock_lifecycle_stage(
                max_board=bucket["max_board"],
                limit_up_days=bucket["limit_up_days"],
                broken_days=bucket["broken_days"],
                current_status=bucket["current_status"],
            )
            bucket["strength_score"] = cls._safe_round(
                bucket["limit_up_days"] * 8 + bucket["max_board"] * 12 - bucket["broken_days"] * 6,
                1,
            )
            lifecycles.append(bucket)

        lifecycles.sort(key=lambda item: (item["strength_score"], item["max_board"], item["limit_up_days"]), reverse=True)
        return lifecycles[:top_n]

    @staticmethod
    def _stock_lifecycle_stage(max_board: int, limit_up_days: int, broken_days: int, current_status: str) -> str:
        if current_status == "broken":
            return "断板/炸板"
        if max_board >= 5:
            return "高位龙头"
        if max_board >= 3:
            return "主升连板"
        if max_board == 2 or limit_up_days >= 2:
            return "二板确认"
        if broken_days > 0:
            return "试错回封"
        return "首板启动"

    @staticmethod
    def _validate_date_range(start_date: str, end_date: str, max_calendar_days: int = 90) -> None:
        if not start_date or len(start_date) != 8 or not start_date.isdigit():
            raise ValueError("start_date 为必填参数，格式为 YYYYMMDD")
        if not end_date or len(end_date) != 8 or not end_date.isdigit():
            raise ValueError("end_date 为必填参数，格式为 YYYYMMDD")

        start = datetime.strptime(start_date, "%Y%m%d")
        end = datetime.strptime(end_date, "%Y%m%d")
        if start > end:
            raise ValueError("start_date 不能晚于 end_date")
        if end - start > timedelta(days=max_calendar_days):
            raise ValueError(f"查询区间不能超过 {max_calendar_days} 个自然日")

    @staticmethod
    def _first_by_code(records: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        result = {}
        for item in records:
            code = item.get("ts_code") or item.get("code")
            if code and code not in result:
                result[code] = item
        return result

    @staticmethod
    def _count_by_number(records: Iterable[Dict[str, Any]], field: str) -> Dict[int, int]:
        counter: Counter[int] = Counter()
        for item in records:
            value = LimitBoardDataService._safe_int(item.get(field))
            if value > 0:
                counter[value] += 1
        return dict(counter)

    @staticmethod
    def _build_break_item(item: Dict[str, Any], status: str, ths_item: Dict[str, Any]) -> Dict[str, Any]:
        amount = LimitBoardDataService._safe_float(item.get("amount"))
        fd_amount = LimitBoardDataService._safe_float(item.get("fd_amount"))
        seal_ratio = fd_amount / amount * 100 if amount > 0 else 0
        open_times = LimitBoardDataService._safe_int(item.get("open_times") or ths_item.get("open_num"))
        score = max(0, 100 - open_times * 12 + min(seal_ratio, 50))
        return {
            "ts_code": item.get("ts_code"),
            "name": item.get("name") or ths_item.get("name"),
            "status": status,
            "industry": item.get("industry"),
            "close": item.get("close"),
            "pct_chg": item.get("pct_chg"),
            "amount": amount,
            "fd_amount": fd_amount,
            "seal_ratio_pct": LimitBoardDataService._safe_round(seal_ratio),
            "first_time": item.get("first_time") or ths_item.get("first_lu_time"),
            "last_time": item.get("last_time") or ths_item.get("last_lu_time"),
            "open_times": open_times,
            "limit_times": LimitBoardDataService._safe_int(item.get("limit_times")),
            "reason": ths_item.get("lu_desc") or "",
            "break_strength_score": LimitBoardDataService._safe_round(score, 1),
            "raw_sources": {
                "limit_list_d": item,
                "limit_list_ths": ths_item,
            },
        }

    @staticmethod
    def _calc_sentiment_score(limit_up_count: int, limit_down_count: int, broken_rate: float, max_board: int, high_board_count: int) -> float:
        score = 50
        score += min(limit_up_count, 120) * 0.25
        score += min(max_board, 10) * 3
        score += min(high_board_count, 30) * 0.8
        score -= min(limit_down_count, 80) * 0.35
        score -= min(broken_rate, 80) * 0.45
        return LimitBoardDataService._safe_round(max(0, min(score, 100)), 1)

    @staticmethod
    def _sentiment_phase(score: float, limit_down_count: int, broken_rate: float, max_board: int) -> Dict[str, str]:
        if score >= 75 and max_board >= 4 and broken_rate <= 30:
            return {"phase": "attack", "label": "进攻期", "conclusion": "连板高度和封板质量较好，适合重点观察核心题材与前排。"}
        if score >= 60 and limit_down_count <= 20:
            return {"phase": "repair", "label": "修复期", "conclusion": "情绪处于修复或温和活跃状态，关注换手充分的强势股。"}
        if score >= 45:
            return {"phase": "mixed", "label": "分歧期", "conclusion": "涨停和炸板并存，适合降低预期并观察回封质量。"}
        return {"phase": "defense", "label": "防守期", "conclusion": "亏钱效应或炸板压力较高，不宜盲目接力。"}

    @staticmethod
    def _calc_hot_score(dc_hot: Dict[str, Any], ths_hot: Dict[str, Any]) -> float:
        score = 0.0
        for item in (dc_hot, ths_hot):
            if not item:
                continue
            rank = LimitBoardDataService._safe_int(item.get("rank") or item.get("rank_no"), 9999)
            if rank <= 10:
                score += 2.0
            elif rank <= 30:
                score += 1.2
            elif rank <= 100:
                score += 0.5
        return LimitBoardDataService._safe_round(score, 1)

    @staticmethod
    def _merge_tags(*values: Any) -> List[str]:
        tags: List[str] = []
        for value in values:
            if not value:
                continue
            for part in str(value).replace("、", ",").replace("，", ",").split(","):
                tag = part.strip()
                if tag and tag not in tags:
                    tags.append(tag)
        return tags

    @staticmethod
    def _parse_status_board(value: Any) -> int:
        text = str(value or "")
        digits = "".join(ch for ch in text if ch.isdigit())
        return int(digits) if digits else 1

    @staticmethod
    def _parse_up_stat(value: Any) -> int:
        text = str(value or "")
        if "板" not in text:
            return 0
        before_board = text.split("板", 1)[0]
        digits = ""
        for ch in reversed(before_board):
            if ch.isdigit():
                digits = ch + digits
            elif digits:
                break
        return int(digits) if digits else 0

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            if value is None or value == "":
                return default
            return int(float(value))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_round(value: float, digits: int = 2) -> float:
        return round(float(value), digits)


limit_board_data_service = LimitBoardDataService()
