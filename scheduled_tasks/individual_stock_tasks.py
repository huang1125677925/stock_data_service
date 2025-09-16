#!/usr/bin/env python3
"""
个股数据抓取任务
定期从akshare获取个股数据并存储到数据库
"""

import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
import os

# 设置Django环境
# sys.path.append(str(Path(__file__).resolve().parent.parent))
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_data_service.settings')
# import django
# django.setup()

from django.utils import timezone

logger = logging.getLogger(__name__)

def fetch_individual_stocks():
    """
    获取所有个股列表并保存到数据库
    每天执行一次
    """
    logger.info("开始执行个股列表获取任务")
    
    try:
        # 导入个股数据服务
        from indival_stock_data.services import individual_stock_service
        
        # 获取个股列表
        stocks = individual_stock_service.get_stock_list()
        
        if not stocks:
            logger.warning("获取个股列表为空")
            return {"status": "warning", "message": "获取个股列表为空"}
        
        logger.info(f"成功获取{len(stocks)}只个股")
        return {"status": "success", "message": f"成功获取{len(stocks)}只个股"}
    except Exception as e:
        logger.error(f"个股列表获取任务执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}

def update_individual_stock_realtime():
    """
    更新所有个股的实时行情数据
    交易日每5分钟执行一次
    """
    logger.info("开始执行个股实时行情更新任务")
    
    try:
        # 导入个股数据服务
        from indival_stock_data.services import individual_stock_service
        
        # 更新所有个股信息和实时行情
        updated_count, created_count, failed_count = individual_stock_service.update_all_stocks()
        
        logger.info(f"个股实时行情更新任务完成，更新: {updated_count}，新增: {created_count}，失败: {failed_count}")
        return {
            "status": "success" if failed_count == 0 else "partial",
            "message": f"个股实时行情更新任务完成，更新: {updated_count}，新增: {created_count}，失败: {failed_count}"
        }
    except Exception as e:
        logger.error(f"个股实时行情更新任务执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}

def update_individual_stock_daily_data():
    """
    更新所有个股的日频数据
    每天收盘后执行一次
    只获取最近30天的数据
    """
    logger.info("开始执行个股日频数据更新任务")
    
    try:
        # 导入个股数据服务和模型
        from indival_stock_data.services import individual_stock_service
        from indival_stock_data.models import IndividualStock
        
        # 获取所有个股
        stocks = IndividualStock.objects.all()
        
        if not stocks.exists():
            # 如果数据库中没有个股数据，先获取个股列表
            logger.info("数据库中没有个股数据，先获取个股列表")
            fetch_individual_stocks()
            stocks = IndividualStock.objects.all()
            
            if not stocks.exists():
                logger.warning("获取个股列表失败，无法获取日频数据")
                return {"status": "error", "message": "获取个股列表失败，无法获取日频数据"}
        
        # 更新所有个股的历史数据（最近30天）
        updated_stocks, updated_history = individual_stock_service.update_stock_history(days=4000)
        
        logger.info(f"个股日频数据更新任务完成，更新: {updated_stocks}只个股，{updated_history}条历史数据")
        return {
            "status": "success",
            "message": f"个股日频数据更新任务完成，更新: {updated_stocks}只个股，{updated_history}条历史数据"
        }
    except Exception as e:
        logger.error(f"个股日频数据更新任务执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}

def update_specific_stock_history(stock_code, days=30):
    """
    更新指定个股的历史数据
    
    Args:
        stock_code: 股票代码
        days: 获取的天数，默认30天
    """
    logger.info(f"开始更新股票{stock_code}的历史数据")
    
    try:
        # 导入个股数据服务
        from indival_stock_data.services import individual_stock_service
        
        # 更新指定个股的历史数据
        updated_stocks, updated_history = individual_stock_service.update_stock_history(stock_code=stock_code, days=days)
        
        if updated_stocks == 0:
            logger.warning(f"股票{stock_code}的历史数据更新失败")
            return {"status": "warning", "message": f"股票{stock_code}的历史数据更新失败"}
        
        logger.info(f"股票{stock_code}的历史数据更新完成，更新{updated_history}条历史数据")
        return {
            "status": "success",
            "message": f"股票{stock_code}的历史数据更新完成，更新{updated_history}条历史数据"
        }
    except Exception as e:
        logger.error(f"股票{stock_code}的历史数据更新失败: {str(e)}")
        return {"status": "error", "message": str(e)}

if __name__ == '__main__':
    update_individual_stock_daily_data()