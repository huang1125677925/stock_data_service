#!/usr/bin/env python3
"""
行业实际产出规模估算策略模块

功能：
- 计算行业实际产出规模（估算）≈ 前N大企业营业总收入之和 / 行业集中度（CRn）
- 其中行业集中度CRn定义为：该行业前N名企业市场份额（以营业总收入计）的加总（0-1小数），即 CRn = Σ(Top N 企业营业收入 / 行业总营业收入)
- 当CRn以数据库数据计算时，估算值等于行业总营业收入（用于验证与一致性）。
- 仅从数据库获取数据（IndividualStock、PerformanceReport、IndustrySector），符合工作空间规则。
- 支持按行业板块代码筛选、选择Top N与报告期（可选），并对结果进行缓存。

参数：
- sector_codes(List[str], 可选): 行业板块代码列表；为空时计算所有板块。
- top_n(int, 默认3): 前N大企业数。
- report_date(str, 可选): 报告期（YYYYMMDD）；为空时使用每只股票的最新业绩快报（优先announcement_date，其次report_date）。

返回值：
- List[Dict]: 每行业的实际产出规模估算数据列表，包含：
  - sector_code/sector_name: 行业板块信息
  - top_n: 计算所用前N企业数
  - report_date: 报告期（若提供）
  - top_n_revenue_sum: 前N企业营业总收入之和（元）
  - crn_ratio: 行业集中度CRn（0-1）
  - estimated_industry_output: 行业实际产出规模估算值（元）
  - industry_total_revenue: 行业总营业收入（以数据库可得数据计算）
  - company_count_with_reports: 参与计算、具有报告数据的公司数量

事件：
- 参数校验
- 从数据库读取行业板块、个股与业绩快报数据
- 聚合计算Top N收入与CRn，给出估算值
- 结果缓存
"""

import logging
from typing import Dict, List, Optional

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, OuterRef, Subquery

from industry_stock_data.models import IndustrySector
from indival_stock_data.models import IndividualStock
from indival_stock_data.models import PerformanceReport

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
            report_date: 报告期（YYYYMMDD，可选）；为空时使用最新业绩快报。
        Returns:
            每行业的实际产出规模估算数据列表；若无数据返回None。
        事件：
            - 读取IndustrySector、IndividualStock、PerformanceReport数据
            - 对每行业聚合计算Top N收入之和、行业总收入与CRn
            - 计算估算值，并进行缓存
        """
        try:
            # 参数校验
            if top_n <= 0:
                logger.warning("top_n必须为正整数")
                return None

            # 构造缓存键
            cache_key = f"industry_actual_output_{','.join(sector_codes) if sector_codes else 'all'}_n{top_n}_{report_date or 'latest'}"
            cached = cache.get(cache_key)
            if cached:
                logger.info("从缓存获取行业实际产出规模估算数据")
                return cached

            # 获取行业板块（可筛选）
            if sector_codes:
                sectors = list(IndustrySector.objects.filter(code__in=sector_codes).values('code', 'name'))
            else:
                sectors = list(IndustrySector.objects.all().values('code', 'name'))

            if not sectors:
                logger.warning("未获取到行业板块数据")
                return None

            results: List[Dict] = []

            # 遍历每个行业板块计算
            for sector in sectors:
                sector_code = sector['code']
                sector_name = sector['name']

                # 按行业名称选择股票（基于IndividualStock.industry与IndustrySector.name的匹配）
                stocks_qs = IndividualStock.objects.filter(industry=sector_name)

                # 为每只股票注入其（指定报告期或最新）营业总收入
                if report_date:
                    # 指定报告期：取该期报告的营业总收入（若无则为None）
                    revenue_subq = PerformanceReport.objects.filter(
                        stock=OuterRef('pk'),
                        report_date=report_date
                    ).order_by('-announcement_date', '-updated_at').values('operating_revenue')[:1]
                else:
                    # 最新报告：优先按announcement_date降序，其次report_date，再次updated_at
                    revenue_subq = PerformanceReport.objects.filter(
                        stock=OuterRef('pk')
                    ).order_by('-announcement_date', '-report_date', '-updated_at').values('operating_revenue')[:1]

                stocks_with_rev = stocks_qs.annotate(latest_operating_revenue=Subquery(revenue_subq))\
                                        .values_list('latest_operating_revenue', flat=True)

                # 收集有效收入（去除None与非正值）
                revenues = [float(rv) for rv in stocks_with_rev if rv is not None and float(rv) > 0]

                company_count_with_reports = len(revenues)
                if company_count_with_reports == 0:
                    # 若该行业无可用收入数据，则跳过或填充0结果
                    results.append({
                        'sector_code': sector_code,
                        'sector_name': sector_name,
                        'top_n': top_n,
                        'report_date': report_date,
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
                    'report_date': report_date,
                    'top_n_revenue_sum': round(float(top_n_revenue_sum), 2),
                    'crn_ratio': round(float(crn_ratio), 6),
                    'estimated_industry_output': round(float(estimated_output), 2),
                    'industry_total_revenue': round(float(industry_total_revenue), 2),
                    'company_count_with_reports': int(company_count_with_reports),
                })

            # 排序：按估算产出规模降序
            results.sort(key=lambda x: x['estimated_industry_output'], reverse=True)

            # 缓存结果
            cache.set(cache_key, results, self.cache_timeout)
            return results
        except Exception as e:
            logger.error(f"计算行业实际产出规模估算失败: {str(e)}")
            return None


# 创建策略实例，供视图层调用
industry_actual_output_strategy = IndustryActualOutputStrategy()