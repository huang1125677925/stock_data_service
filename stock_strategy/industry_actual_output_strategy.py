#!/usr/bin/env python3
"""
行业实际产出规模估算策略模块

功能：
- 计算行业实际产出规模（估算）≈ 前N大企业营业总收入之和 / 行业集中度（CRn）
- 其中行业集中度CRn定义为：该行业前N名企业市场份额（以营业总收入计）的加总（0-1小数），即 CRn = Σ(Top N 企业营业收入 / 行业总营业收入)
- 通过 Tushare 申万一级行业成分股与财务接口获取数据。
- 支持按行业板块代码筛选、选择Top N与报告期（可选），并对结果进行缓存。

参数：
- sector_codes(List[str], 可选): 行业板块代码列表；为空时计算所有板块。
- top_n(int, 默认3): 前N大企业数。
- report_date(str, 可选): 报告期（YYYYMMDD）；为空时使用最近一个已完整披露的年报期。

返回值：
- List[Dict]: 每行业的实际产出规模估算数据列表，包含：
  - sector_code/sector_name: 行业板块信息
  - top_n: 计算所用前N企业数
  - report_date: 报告期（若提供）
  - top_n_revenue_sum: 前N企业营业总收入之和（元）
  - crn_ratio: 行业集中度CRn（0-1）
  - estimated_industry_output: 行业实际产出规模估算值（元）
  - industry_total_revenue: 行业总营业收入
  - company_count_with_reports: 参与计算、具有报告数据的公司数量

事件：
- 参数校验
- 从 Tushare 读取申万一级行业成分股与财务数据
- 聚合计算Top N收入与CRn，给出估算值
- 结果缓存
"""

import logging
import math
from typing import Dict, List, Optional

from django.conf import settings
from django.core.cache import cache

from common.tushare_industry import (
    fetch_financial_vip_period,
    get_latest_completed_report_period,
    get_sw_l1_members,
    get_sw_l1_sectors,
)

logger = logging.getLogger(__name__)


class IndustryActualOutputStrategy:
    """行业实际产出规模估算策略类
    
    功能：依据“前N大企业营收总和 / 行业集中度CRn”公式估算行业实际产出规模。
    参数：通过方法入参传递（sector_codes、top_n、report_date）
    返回值：列表结构，便于视图层API直接返回
    事件：
    - get_industry_actual_output: 执行核心估算并缓存
    """

    def __init__(self):
        # 缓存超时时间，默认5分钟，可通过settings.STOCK_CACHE_TIMEOUT覆盖
        self.cache_timeout = getattr(settings, 'STOCK_CACHE_TIMEOUT', 300)

    def _sanitize_result_item(self, item: Dict) -> Dict:
        sanitized = dict(item)
        for key in (
            'top_n_revenue_sum',
            'crn_ratio',
            'estimated_industry_output',
            'industry_total_revenue',
        ):
            value = sanitized.get(key)
            if isinstance(value, float) and not math.isfinite(value):
                sanitized[key] = 0.0
        return sanitized

    def get_industry_actual_output(
        self,
        sector_codes: Optional[List[str]] = None,
        top_n: int = 3,
        report_date: Optional[str] = None,
    ) -> Optional[List[Dict]]:
        """计算行业实际产出规模估算值
        
        功能：按照公式 估算值 ≈ 前N企业营业总收入之和 / CRn，其中 CRn = Top N 企业营业收入之和 / 行业总营业收入。
        Args:
            sector_codes: 行业板块代码列表（可选）；为空时计算所有板块。
            top_n: 前N大企业数量（默认为3）。
            report_date: 报告期（YYYYMMDD，可选）；为空时使用最近一个已完整披露的年报期。
        Returns:
            每行业的实际产出规模估算数据列表；若无数据返回None。
        事件：
            - 读取 Tushare 申万一级行业成分股与财务数据
            - 对每行业聚合计算Top N收入之和、行业总收入与CRn
            - 计算估算值，并进行缓存
        """
        try:
            # 参数校验
            if top_n <= 0:
                logger.warning("top_n必须为正整数")
                return None

            # 构造缓存键
            cache_key = f"industry_actual_output_sw_l1_members_v2_{','.join(sector_codes) if sector_codes else 'all'}_n{top_n}_{report_date or 'latest'}"
            cached = cache.get(cache_key)
            if cached:
                logger.info("从缓存获取行业实际产出规模估算数据")
                return [self._sanitize_result_item(item) for item in cached]

            sector_rows = get_sw_l1_sectors()
            sector_by_code = {
                item["sector_code"]: item["sector_name"]
                for item in sector_rows
                if item.get("sector_code") and item.get("sector_name")
            }
            if not sector_by_code:
                logger.warning("未获取到申万一级行业列表")
                return None

            target_sector_codes = set(sector_by_code.keys())
            if sector_codes:
                sector_key_set = {str(code).strip() for code in sector_codes if str(code).strip()}
                target_sector_codes = {
                    code for code, name in sector_by_code.items()
                    if code in sector_key_set or name in sector_key_set
                }

            if not target_sector_codes:
                logger.warning("未匹配到目标申万一级行业")
                return []

            member_records = get_sw_l1_members()
            if not member_records:
                logger.warning("未获取到申万一级行业成分股")
                return None

            sector_members: Dict[str, Dict[str, object]] = {}
            for item in member_records:
                sector_code = str(item.get("sector_code") or "").strip()
                ts_code = str(item.get("ts_code") or "").strip()
                if not sector_code or not ts_code or sector_code not in target_sector_codes:
                    continue
                sector_members.setdefault(
                    sector_code,
                    {
                        "sector_name": sector_by_code.get(sector_code) or item.get("sector_name") or "",
                        "ts_codes": set(),
                    },
                )
                sector_members[sector_code]["ts_codes"].add(ts_code)

            if not sector_members:
                logger.warning("目标申万一级行业成分股为空")
                return []

            actual_period = report_date or get_latest_completed_report_period("annual")
            income_records = fetch_financial_vip_period(
                "income_vip",
                actual_period,
                fields="ts_code,end_date,total_revenue",
            )
            if not income_records:
                logger.warning("Tushare income_vip 未返回数据: period=%s", actual_period)
                return None

            revenue_by_stock: Dict[str, float] = {}
            for item in income_records:
                ts_code = str(item.get("ts_code") or "").strip()
                revenue = item.get("total_revenue")
                try:
                    revenue_val = float(revenue)
                except (TypeError, ValueError):
                    continue
                if not math.isfinite(revenue_val) or revenue_val <= 0:
                    continue
                revenue_by_stock[ts_code] = revenue_val

            results: List[Dict] = []

            for sector_code, sector_info in sector_members.items():
                sector_name = str(sector_info["sector_name"])
                ts_codes = sector_info["ts_codes"]
                revenues = [
                    revenue_by_stock[ts_code]
                    for ts_code in ts_codes
                    if ts_code in revenue_by_stock
                ]

                company_count_with_reports = len(revenues)
                if company_count_with_reports == 0:
                    results.append({
                        'sector_code': sector_code,
                        'sector_name': sector_name,
                        'top_n': top_n,
                        'report_date': actual_period,
                        'top_n_revenue_sum': 0.0,
                        'crn_ratio': 0.0,
                        'estimated_industry_output': 0.0,
                        'industry_total_revenue': 0.0,
                        'company_count_with_reports': 0,
                    })
                    continue

                # 行业总营业收入
                industry_total_revenue = sum(revenues)

                # 前N企业营业收入之和
                revenues_sorted = sorted(revenues, reverse=True)
                top_n_revenue_sum = sum(revenues_sorted[:min(top_n, len(revenues_sorted))])

                # 行业集中度CRn（Top N市场份额加总，0-1）
                crn_ratio = (top_n_revenue_sum / industry_total_revenue) if industry_total_revenue > 0 else 0.0

                # 估算行业实际产出规模（单位：元）
                estimated_output = (top_n_revenue_sum / crn_ratio) if crn_ratio > 0 else 0.0

                results.append({
                    'sector_code': sector_code,
                    'sector_name': sector_name,
                    'top_n': top_n,
                    'report_date': actual_period,
                    'top_n_revenue_sum': round(float(top_n_revenue_sum), 2),
                    'crn_ratio': round(float(crn_ratio), 6),
                    'estimated_industry_output': round(float(estimated_output), 2),
                    'industry_total_revenue': round(float(industry_total_revenue), 2),
                    'company_count_with_reports': int(company_count_with_reports),
                })

            # 排序：按估算产出规模降序
            results.sort(key=lambda x: x['estimated_industry_output'], reverse=True)

            # 缓存结果
            sanitized_results = [self._sanitize_result_item(item) for item in results]
            cache.set(cache_key, sanitized_results, self.cache_timeout)
            return sanitized_results
        except Exception as e:
            logger.error(f"计算行业实际产出规模估算失败: {str(e)}")
            return None


# 创建策略实例，供视图层调用
industry_actual_output_strategy = IndustryActualOutputStrategy()
