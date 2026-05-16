#!/usr/bin/env python3
"""
行业规模宽度策略模块

功能：
- 计算行业规模宽度指标 = (行业总市值 / 市场总市值) × (行业公司数量 / 市场总公司数量)
- 通过 Tushare `bak_daily` 获取行业与市值快照
- 支持按行业板块代码筛选，具备可扩展性与缓存

参数：
- sector_codes(List[str]): 行业板块代码列表，可选；为空时计算所有板块

返回值：
- List[Dict]: 每行业的规模宽度数据列表，包含板块代码/名称、行业总市值、市场总市值、行业公司数量、市场总公司数量、两个比例以及最终指标

事件：
- 参数校验
- 从 Tushare 读取行业与市值快照
- 统一计算行业与市场的总市值与公司数量
- 缓存结果
"""

import logging
from typing import Dict, List, Optional
from django.core.cache import cache
from django.conf import settings

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
            - 从 Tushare `bak_daily` 读取行业与市值快照
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

            from common.tushare_industry import (
                fetch_bak_daily_snapshot,
                get_sw_l1_sectors,
                resolve_sw_l1_sector_code,
            )

            snapshot = fetch_bak_daily_snapshot(fields="ts_code,industry,total_mv")
            if not snapshot:
                logger.warning("未获取到 Tushare bak_daily 快照")
                return []
            sector_rows = get_sw_l1_sectors()
            sector_code_map = {
                item["sector_name"]: item["sector_code"]
                for item in sector_rows
                if item.get("sector_name") and item.get("sector_code")
            }

            industry_stats: Dict[str, Dict[str, float]] = {}
            market_total_value = 0.0
            market_total_company_count = 0

            for row in snapshot:
                industry_name = str(row.get("industry") or "").strip()
                total_mv = row.get("total_mv")
                if not industry_name or total_mv in (None, ""):
                    continue
                try:
                    mv = float(total_mv)
                except (TypeError, ValueError):
                    continue
                market_total_value += mv
                market_total_company_count += 1
                stats = industry_stats.setdefault(
                    industry_name,
                    {"industry_total_value": 0.0, "industry_company_count": 0},
                )
                stats["industry_total_value"] += mv
                stats["industry_company_count"] += 1

            if market_total_company_count <= 0 or market_total_value <= 0:
                logger.warning("Tushare 快照未生成有效市值统计")
                return []

            # 计算每行业的指标
            results: List[Dict] = []
            target_names = sorted(industry_stats.keys())
            if sector_codes:
                sector_code_set = set(sector_codes)
                target_names = [
                    name for name in target_names
                    if name in sector_code_set or sector_code_map.get(name) in sector_code_set
                ]

            for name in target_names:
                code = resolve_sw_l1_sector_code(name, sectors=sector_rows)
                industry_total_value = float(industry_stats[name]["industry_total_value"])
                industry_company_count = int(industry_stats[name]["industry_company_count"])

                market_cap_ratio = (industry_total_value / market_total_value) if market_total_value > 0 else 0
                company_ratio = (
                    (industry_company_count / market_total_company_count)
                    if market_total_company_count > 0
                    else 0
                )
                scale_breadth = round(market_cap_ratio * company_ratio, 6)

                results.append({
                    'sector_code': code,
                    'sector_name': name,
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
