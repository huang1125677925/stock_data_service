#!/usr/bin/env python3
"""
行业板块数据抓取任务
定期从akshare获取行业板块数据并存储到数据库
"""

import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

def fetch_industry_sectors():
    """
    获取所有行业板块列表并保存到数据库
    每天执行一次
    """
    logger.info("开始执行行业板块列表获取任务")
    
    try:
        # 导入行业板块服务
        from stock_data.services import industry_sector_service
        
        # 获取行业板块列表
        sectors = industry_sector_service.get_industry_sectors()
        
        if not sectors:
            logger.warning("获取行业板块列表为空")
            return {"status": "warning", "message": "获取行业板块列表为空"}
        
        logger.info(f"成功获取{len(sectors)}个行业板块")
        return {"status": "success", "message": f"成功获取{len(sectors)}个行业板块"}
    except Exception as e:
        logger.error(f"行业板块列表获取任务执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}

def fetch_industry_sector_daily_data():
    """
    获取所有行业板块的日频数据并保存到数据库
    每天收盘后执行一次
    只获取最近120天的数据
    """
    logger.info("开始执行行业板块日频数据获取任务")
    
    try:
        # 导入行业板块服务和模型
        from stock_data.services import industry_sector_service
        from stock_data.models import IndustrySector
        
        # 获取所有行业板块
        sectors = IndustrySector.objects.all()
        
        if not sectors.exists():
            # 如果数据库中没有行业板块数据，先获取行业板块列表
            logger.info("数据库中没有行业板块数据，先获取行业板块列表")
            fetch_industry_sectors()
            sectors = IndustrySector.objects.all()
            
            if not sectors.exists():
                logger.warning("获取行业板块列表失败，无法获取日频数据")
                return {"status": "error", "message": "获取行业板块列表失败，无法获取日频数据"}
        
        # 计算开始日期和结束日期（最近120天）
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=120)).strftime('%Y%m%d')
        
        # 获取每个行业板块的日频数据
        success_count = 0
        error_count = 0
        total_count = sectors.count()
        
        for sector in sectors:
            try:
                logger.info(f"获取行业板块 {sector.code} ({sector.name}) 的日频数据")
                daily_data = industry_sector_service.get_industry_sector_daily(
                    sector_code=sector.code,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if daily_data:
                    logger.info(f"成功获取行业板块 {sector.code} 的 {len(daily_data)} 条日频数据")
                    success_count += 1
                else:
                    logger.warning(f"行业板块 {sector.code} 的日频数据为空")
                    error_count += 1
            except Exception as e:
                logger.error(f"获取行业板块 {sector.code} 的日频数据失败: {str(e)}")
                error_count += 1
        
        logger.info(f"行业板块日频数据获取任务完成，成功: {success_count}，失败: {error_count}，总计: {total_count}")
        return {
            "status": "success" if error_count == 0 else "partial",
            "message": f"行业板块日频数据获取任务完成，成功: {success_count}，失败: {error_count}，总计: {total_count}"
        }
    except Exception as e:
        logger.error(f"行业板块日频数据获取任务执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}

def update_industry_sector_daily_data():
    """
    更新今日行业板块数据
    每个交易日收盘后执行
    """
    logger.info("开始执行今日行业板块数据更新任务")
    
    try:
        # 导入行业板块服务和模型
        from stock_data.services import industry_sector_service
        from stock_data.models import IndustrySector
        
        # 获取所有行业板块
        sectors = IndustrySector.objects.all()
        
        if not sectors.exists():
            logger.warning("数据库中没有行业板块数据，无法更新今日数据")
            return {"status": "error", "message": "数据库中没有行业板块数据，无法更新今日数据"}
        
        # 计算今日日期
        today = datetime.now().strftime('%Y%m%d')
        
        # 更新每个行业板块的今日数据
        success_count = 0
        error_count = 0
        total_count = sectors.count()
        
        for sector in sectors:
            try:
                logger.info(f"更新行业板块 {sector.code} ({sector.name}) 的今日数据")
                daily_data = industry_sector_service.get_industry_sector_daily(
                    sector_code=sector.code,
                    start_date=today,
                    end_date=today
                )
                
                if daily_data:
                    logger.info(f"成功更新行业板块 {sector.code} 的今日数据")
                    success_count += 1
                else:
                    logger.warning(f"行业板块 {sector.code} 的今日数据为空")
                    error_count += 1
            except Exception as e:
                logger.error(f"更新行业板块 {sector.code} 的今日数据失败: {str(e)}")
                error_count += 1
        
        logger.info(f"今日行业板块数据更新任务完成，成功: {success_count}，失败: {error_count}，总计: {total_count}")
        return {
            "status": "success" if error_count == 0 else "partial",
            "message": f"今日行业板块数据更新任务完成，成功: {success_count}，失败: {error_count}，总计: {total_count}"
        }
    except Exception as e:
        logger.error(f"今日行业板块数据更新任务执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}