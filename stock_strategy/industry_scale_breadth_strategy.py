#!/usr/bin/env python3
"""
行业规模宽度策略模块

功能：
- 计算行业规模宽度指标 = (行业总市值 / 市场总市值) × (行业公司数量 / 市场总公司数量)
- 仅从数据库获取数据（IndustrySector、IndividualStock），符合工作空间规则
- 支持按行业板块代码筛选，具备可扩展性与缓存

参数：
- sector_codes(List[str]): 行业板块代码列表，可选；为空时计算所有板块

返回值：
- List[Dict]: 每行业的规模宽度数据列表，包含板块代码/名称、行业总市值、市场总市值、行业公司数量、市场总公司数量、两个比例以及最终指标

事件：
- 参数校验
- 从数据库读取行业板块及个股信息
- 统一计算行业与市场的总市值与公司数量
- 缓存结果
"""

import logging
from typing import Dict, List, Optional
from django.core.cache import cache
from django.conf import settings
from django.db.models import Count

from industry_stock_data.models import IndustrySector
from indival_stock_data.models import IndividualStock

logger = logging.getLogger(__name__)


class IndustryScaleBreadthStrategy:
    """行业规模宽度策略类
    
    功能：提供行业规模宽度指标的计算能力
    参数：通过方法入参传递
    返回值：列表结构，便于API直接返回
    事件：
    - get_industry_scale_breadth: 执行核心计算并缓存
    """

    def __init__(self):
        # 缓存超时时间，默认5分钟，可通过settings.STOCK_CACHE_TIMEOUT覆盖
        self.cache_timeout = getattr(settings, 'STOCK_CACHE_TIMEOUT', 300)

    def get_industry_scale_breadth(
        self,
        sector_codes: Optional[List[str]] = None,
    ) -> Optional[List[Dict]]:
        """计算行业规模宽度指标
        
        功能：按照公式 (行业总市值 / 市场总市值) × (行业公司数量 / 市场总公司数量)
        Args:
            sector_codes: 行业板块代码列表（可选）；为空时计算所有板块
        Returns:
            每行业的规模宽度指标列表；失败返回None
        事件：
            - 从数据库读取IndustrySector与IndividualStock
            - 计算行业总市值与行业公司数量
            - 计算市场总市值与市场总公司数量
            - 计算指标并缓存
        """
        try:
            # 缓存键
            cache_key = f"industry_scale_breadth_{','.join(sector_codes) if sector_codes else 'all'}"
            cached = cache.get(cache_key)
            if cached:
                logger.info("从缓存获取行业规模宽度数据")
                return cached

            # 获取行业板块（可筛选）
            if sector_codes:
                sectors = list(IndustrySector.objects.filter(code__in=sector_codes).values('code', 'name', 'total_market_value'))
            else:
                sectors = list(IndustrySector.objects.all().values('code', 'name', 'total_market_value'))

            if not sectors:
                logger.warning("未获取到行业板块数据")
                return None

            # 市场总市值（来自所有行业板块）
            # 过滤None与非正值，保证计算稳定
            market_total_value = sum([s['total_market_value'] for s in sectors if s.get('total_market_value')])
            # 市场总市值（来自所有行业板块，不受sector_codes筛选影响）
            # 过滤None与非正值，保证计算稳定
            all_sector_values = IndustrySector.objects.all().values('total_market_value')
            market_total_value = sum([v['total_market_value'] for v in all_sector_values if v.get('total_market_value')])
            if market_total_value is None:
                market_total_value = 0

            # 市场总公司数量（来自所有个股表）
            market_total_company_count = IndividualStock.objects.count()
            if market_total_company_count == 0:
                logger.warning("市场总公司数量为0")
                return None

            # 预聚合：按行业名称统计公司数量（一次查询）
            industry_counts = dict(
                IndividualStock.objects.values('industry').annotate(cnt=Count('id')).values_list('industry', 'cnt')
            )

            # 计算每行业的指标
            results: List[Dict] = []
            for sector in sectors:
                name = sector['name']
                code = sector['code']
                industry_total_value = sector.get('total_market_value') or 0
                industry_company_count = int(industry_counts.get(name, 0))

                market_cap_ratio = (industry_total_value / market_total_value) if market_total_value > 0 else 0
                company_ratio = (industry_company_count / market_total_company_count) if market_total_company_count > 0 else 0
                scale_breadth = round(market_cap_ratio * company_ratio, 6)

                results.append({
                    'sector_code': code,
                    'sector_name': name,
                    'industry_total_market_value': float(industry_total_value),
                    'market_total_market_value': float(market_total_value),
                    'industry_company_count': industry_company_count,
                    'market_total_company_count': int(market_total_company_count),
                    'market_cap_ratio': round(market_cap_ratio, 6),
                    'company_ratio': round(company_ratio, 6),
                    'scale_breadth': scale_breadth,
                })

            # 排序：按指标降序
            results.sort(key=lambda x: x['scale_breadth'], reverse=True)

            # 缓存结果
            cache.set(cache_key, results, self.cache_timeout)
            return results
        except Exception as e:
            logger.error(f"计算行业规模宽度失败: {str(e)}")
            return None


# 创建策略实例，供视图层调用
industry_scale_breadth_strategy = IndustryScaleBreadthStrategy()