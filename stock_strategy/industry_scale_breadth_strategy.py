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
            每行业的规模宽度指标列表；无板块时返回空列表；未捕获异常时返回 None
        事件：
            - 从数据库读取IndustrySector与IndividualStock
            - 计算行业总市值与行业公司数量
            - 计算市场总市值与市场总公司数量
            - 计算指标并缓存
        """
        try:
            # 缓存键
            cache_key = f"industry_scale_breadth_{','.join(sector_codes) if sector_codes else 'all'}"
            try:
                cached = cache.get(cache_key)
                if cached is not None and isinstance(cached, list):
                    logger.info("从缓存获取行业规模宽度数据")
                    return cached
            except Exception as e:
                logger.warning(f"读取行业规模宽度缓存失败，将直接计算: {e}")

            # 获取行业板块（可筛选）
            if sector_codes:
                sectors = list(IndustrySector.objects.filter(code__in=sector_codes).values('code', 'name', 'total_market_value'))
            else:
                sectors = list(IndustrySector.objects.all().values('code', 'name', 'total_market_value'))

            if not sectors:
                logger.warning("未获取到行业板块数据")
                return []

            # 市场总市值（来自所有行业板块，不受 sector_codes 筛选影响）
            all_sector_values = IndustrySector.objects.all().values("total_market_value")
            market_total_value = 0
            for v in all_sector_values:
                raw = v.get("total_market_value")
                if raw is None:
                    continue
                try:
                    market_total_value += int(raw)
                except (TypeError, ValueError):
                    market_total_value += int(float(raw))

            stock_total = IndividualStock.objects.count()
            if stock_total > 0:
                industry_counts: Dict[str, int] = {}
                for row in IndividualStock.objects.values('industry').annotate(cnt=Count('id')):
                    key = (row['industry'] or '').strip()
                    if key:
                        industry_counts[key] = int(row['cnt'])
                market_total_company_count = stock_total
                use_board_counts = False
            else:
                cons_rows = IndustrySector.objects.all().values('name', 'rise_count', 'fall_count')
                sector_cons_by_name: Dict[str, int] = {}
                for r in cons_rows:
                    n = (r['name'] or '').strip()
                    c = int(r['rise_count'] or 0) + int(r['fall_count'] or 0)
                    sector_cons_by_name[n] = c
                market_total_company_count = sum(sector_cons_by_name.values())
                if market_total_company_count <= 0:
                    logger.warning(
                        "个股表无数据且板块涨跌家数合计为0，公司数量占比按0处理（建议同步个股或板块行情）"
                    )
                    market_total_company_count = 1
                use_board_counts = True

            # 计算每行业的指标
            results: List[Dict] = []
            for sector in sectors:
                name = (sector['name'] or '').strip()
                code = sector['code']
                _mv = sector.get("total_market_value")
                try:
                    industry_total_value = (
                        int(_mv) if _mv is not None else 0
                    )
                except (TypeError, ValueError):
                    industry_total_value = int(float(_mv)) if _mv is not None else 0
                if use_board_counts:
                    industry_company_count = sector_cons_by_name.get(
                        name,
                        int(sector.get('rise_count') or 0) + int(sector.get('fall_count') or 0),
                    )
                else:
                    industry_company_count = int(industry_counts.get(name, 0))

                market_cap_ratio = (industry_total_value / market_total_value) if market_total_value > 0 else 0
                company_ratio = (
                    (industry_company_count / market_total_company_count)
                    if market_total_company_count > 0
                    else 0
                )
                scale_breadth = round(market_cap_ratio * company_ratio, 6)

                results.append({
                    'sector_code': code,
                    'sector_name': name or sector.get('name') or '',
                    'industry_total_market_value': float(industry_total_value),
                    'market_total_market_value': float(market_total_value),
                    'industry_company_count': int(industry_company_count),
                    'market_total_company_count': int(market_total_company_count),
                    'market_cap_ratio': round(market_cap_ratio, 6),
                    'company_ratio': round(company_ratio, 6),
                    'scale_breadth': scale_breadth,
                })

            # 排序：按指标降序
            results.sort(key=lambda x: x['scale_breadth'], reverse=True)

            try:
                cache.set(cache_key, results, self.cache_timeout)
            except Exception as e:
                logger.warning(f"写入行业规模宽度缓存失败: {e}")
            return results
        except Exception as e:
            logger.error(f"计算行业规模宽度失败: {str(e)}")
            return None


# 创建策略实例，供视图层调用
industry_scale_breadth_strategy = IndustryScaleBreadthStrategy()