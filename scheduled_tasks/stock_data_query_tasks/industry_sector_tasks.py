#!/usr/bin/env python3
"""
行业板块数据抓取任务
定期从akshare获取行业板块数据并存储到数据库
"""

import sys
import os
from pathlib import Path
from tracemalloc import start
import django
# 设置Django环境
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_data_service.settings')
django.setup()

# 导入行业板块服务和模型
from indival_stock_data.models import IndividualStock
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
import time

# 导入行业板块服务和模型
from industry_stock_data.services import industry_sector_service
from industry_stock_data.models import IndustrySector, IndustrySectorFundFlow
import akshare as ak
import pandas as pd
from industry_stock_data.models import IndustrySectorDaily


from django.utils import timezone

logger = logging.getLogger(__name__)

def fetch_industry_sectors():
    """
    获取所有行业板块列表并保存到数据库
    每天执行一次
    """
    logger.info("开始执行行业板块列表获取任务")
    # 从akshare获取行业板块数据
    try:
        logger.info("从akshare获取行业板块数据")
        df = ak.stock_board_industry_name_em()
        
        if df is None or df.empty:
            logger.warning("从akshare获取行业板块数据为空")
            return {"status": "warning", "message": "从akshare获取行业板块数据为空"}
        
        # 转换数据格式并保存到数据库
        count = 0
        for _, row in df.iterrows():
            # 提取所有可用字段
            sector_data = {
                'name': str(row['板块名称']),
                'description': None,
                'latest_price': float(row['最新价']) if '最新价' in row and not pd.isna(row['最新价']) else None,
                'change_amount': float(row['涨跌额']) if '涨跌额' in row and not pd.isna(row['涨跌额']) else None,
                'change_percent': float(row['涨跌幅']) if '涨跌幅' in row and not pd.isna(row['涨跌幅']) else None,
                'total_market_value': int(row['总市值']) if '总市值' in row and not pd.isna(row['总市值']) else None,
                'turnover_rate': float(row['换手率']) if '换手率' in row and not pd.isna(row['换手率']) else None,
                'rise_count': int(row['上涨家数']) if '上涨家数' in row and not pd.isna(row['上涨家数']) else None,
                'fall_count': int(row['下跌家数']) if '下跌家数' in row and not pd.isna(row['下跌家数']) else None,
                'leading_stock': str(row['领涨股票']) if '领涨股票' in row and not pd.isna(row['领涨股票']) else None,
                'leading_stock_change_percent': float(row['领涨股票-涨跌幅']) if '领涨股票-涨跌幅' in row and not pd.isna(row['领涨股票-涨跌幅']) else None,
            }
            
            # 保存到数据库
            obj, created = IndustrySector.objects.update_or_create(
                code=str(row['板块代码']),
                defaults=sector_data
            )
            count += 1
        
        logger.info(f"成功从akshare获取并更新{count}个行业板块数据")
        
        # 获取更新后的行业板块列表
        sectors = industry_sector_service.get_industry_sectors()
        
        if not sectors:
            logger.warning("获取行业板块列表为空")
            return {"status": "warning", "message": "获取行业板块列表为空"}
        
        logger.info(f"成功获取{len(sectors)}个行业板块")
        return {"status": "success", "message": f"成功从akshare获取并更新{count}个行业板块数据"}
    except Exception as e:
        logger.error(f"从akshare获取行业板块数据失败: {str(e)}")
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
        from industry_stock_data.services import industry_sector_service
        from industry_stock_data.models import IndustrySector
        
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
        start_date = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        
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
    更新最近15天行业板块数据
    每个交易日收盘后执行
    """
    logger.info("开始执行最近15天行业板块数据更新任务")
    
    try:

        
        # 获取所有行业板块
        sectors = IndustrySector.objects.all()
        
        if not sectors.exists():
            logger.warning("数据库中没有行业板块数据，无法更新今日数据")
            return {"status": "error", "message": "数据库中没有行业板块数据，无法更新今日数据"}
        
        # 计算日期范围（最近15天）
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=14)).strftime('%Y%m%d')
        
        # 更新每个行业板块的最近15天数据
        success_count = 0
        error_count = 0
        total_count = sectors.count()
        
        for sector in sectors:
            time.sleep(0.5)
            try:
                logger.info(f"更新行业板块 {sector.code} ({sector.name}) 的最近15天数据")
                
                # 先从数据库查询已有数据
                existing_data = industry_sector_service.get_industry_sector_daily(
                    sector_code=sector.code,
                    start_date=start_date,
                    end_date=end_date
                )
                
                # 从akshare获取最近15天的数据
                logger.info(f"从akshare获取行业板块{sector.code}最近15天日频数据")
                try:
                    df = ak.stock_board_industry_hist_em(
                        symbol=sector.code,
                        start_date=start_date,
                        end_date=end_date,
                        period="日k",
                        adjust=""
                    )
                    
                    if df is None or df.empty:
                        logger.warning(f"获取行业板块{sector.code}日频数据为空")
                        continue
                    
                    # 获取数据库中已存在的日期
                    existing_dates = set()
                    if existing_data:
                        existing_dates = {datetime.strptime(item['date'], '%Y-%m-%d').date() for item in existing_data}
                    
                    # 准备批量创建的对象列表
                    objects_to_create = []
                    new_dates = []
                    
                    # 转换数据格式并检查哪些日期的数据缺失
                    for _, row in df.iterrows():
                        date_str = str(row['日期'])
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                        
                        # 检查数据是否已存在
                        if date_obj in existing_dates:
                            continue
                        
                        # 创建日频数据对象
                        daily_data_obj = IndustrySectorDaily(
                            sector=sector,
                            date=date_obj,
                            open_price=float(row['开盘']),
                            close_price=float(row['收盘']),
                            high_price=float(row['最高']),
                            low_price=float(row['最低']),
                            change_percent=float(row['涨跌幅']),
                            change_amount=float(row['涨跌额']),
                            total_volume=int(row['成交量']),
                            total_amount=float(row['成交额']),
                            amplitude=float(row['振幅']) if '振幅' in row and pd.notna(row['振幅']) else None,
                            turnover_rate=float(row['换手率']) if '换手率' in row and pd.notna(row['换手率']) else None,
                            # 以下字段需要从其他接口获取或计算
                            rising_stocks=0,
                            falling_stocks=0,
                            flat_stocks=0,
                            total_market_cap=None
                        )
                        
                        # 添加到批量创建列表
                        objects_to_create.append(daily_data_obj)
                        new_dates.append(date_obj.strftime('%Y-%m-%d'))
                    
                    # 批量创建数据
                    if objects_to_create:
                        IndustrySectorDaily.objects.bulk_create(objects_to_create)
                        logger.info(f"批量创建行业板块{sector.code}的{len(objects_to_create)}条日频数据: {', '.join(new_dates)}")
                        success_count += 1
                    else:
                        logger.info(f"行业板块{sector.code}的数据已是最新")
                        success_count += 1
                        
                except Exception as e:
                     logger.error(f"从akshare获取行业板块{sector.code}日频数据失败: {str(e)}")
                     error_count += 1
                     continue
                 
                # 检查是否成功获取或更新了数据
                if existing_data or objects_to_create:
                    logger.info(f"成功更新行业板块 {sector.code} 的最近15天数据")
                    success_count += 1
                else:
                     logger.warning(f"行业板块 {sector.code} 的最近15天数据为空")
                     error_count += 1
            except Exception as e:
                logger.error(f"更新行业板块 {sector.code} 的最近15天数据失败: {str(e)}")
                error_count += 1
        
        logger.info(f"最近15天行业板块数据更新任务完成，成功: {success_count}，失败: {error_count}，总计: {total_count}")
        return {
            "status": "success" if error_count == 0 else "partial",
            "message": f"今日行业板块数据更新任务完成，成功: {success_count}，失败: {error_count}，总计: {total_count}"
        }
    except Exception as e:
        logger.error(f"今日行业板块数据更新任务执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}


def mark_stock_industry():
    """
    标记个股所属行业任务
    获取所有行业板块，然后获取每个行业板块的成分股，更新个股的行业字段
    每周执行一次
    """
    logger.info("开始执行个股行业标记任务")
    
    try:

        
        # 获取所有行业板块
        sectors = IndustrySector.objects.all()
        
        if not sectors.exists():
            # 如果数据库中没有行业板块数据，先获取行业板块列表
            logger.info("数据库中没有行业板块数据，先获取行业板块列表")
            fetch_industry_sectors()
            sectors = IndustrySector.objects.all()
            
            if not sectors.exists():
                logger.warning("获取行业板块列表失败，无法标记个股行业")
                return {"status": "error", "message": "获取行业板块列表失败，无法标记个股行业"}
        
        # 统计数据
        success_count = 0
        error_count = 0
        total_count = sectors.count()
        updated_stocks = 0
        
        # 遍历所有行业板块
        for sector in sectors:
            try:
                logger.info(f"获取行业板块 {sector.code} ({sector.name}) 的成分股")
                
                # 从akshare获取行业板块成分股
                try:
                    # 从akshare获取
                    logger.info(f"从akshare获取行业板块{sector.code}成分股")
                    time.sleep(4)
                    df = ak.stock_board_industry_cons_em(symbol=sector.code)

                    
                    if df is None or df.empty:
                        logger.warning(f"获取行业板块{sector.code}成分股为空")
                        error_count += 1
                        continue
                    
                    # 更新每只股票的行业信息
                    for _, row in df.iterrows():
                        stock_code = str(row['代码'])
                        
                        # 更新或创建个股信息
                        try:
                            stock, created = IndividualStock.objects.update_or_create(
                                code=stock_code,
                                defaults={
                                    'name': str(row['名称']),
                                    'industry': sector.name,
                                }
                            )
                            
                            if created:
                                logger.info(f"创建个股 {stock_code} ({stock.name}) 并标记行业为 {sector.name}")
                            else:
                                logger.info(f"更新个股 {stock_code} ({stock.name}) 的行业为 {sector.name}")
                            
                            updated_stocks += 1
                        except Exception as e:
                            logger.error(f"更新个股 {stock_code} 的行业信息失败: {str(e)}")
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"从akshare获取行业板块{sector.code}成分股失败: {str(e)}")
                    error_count += 1
                    continue
                
            except Exception as e:
                logger.error(f"处理行业板块 {sector.code} 的成分股失败: {str(e)}")
                error_count += 1
        
        logger.info(f"个股行业标记任务完成，成功处理行业板块: {success_count}，失败: {error_count}，总计: {total_count}，更新个股数: {updated_stocks}")
        return {
            "status": "success" if error_count == 0 else "partial",
            "message": f"个股行业标记任务完成，成功处理行业板块: {success_count}，失败: {error_count}，总计: {total_count}，更新个股数: {updated_stocks}"
        }
    except Exception as e:
        logger.error(f"个股行业标记任务执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}

def fetch_industry_sector_fund_flow_data():
    """
    获取所有行业板块的资金流数据并保存到数据库
    每天收盘后执行一次，获取最近30天的资金流数据
    """
    logger.info("开始执行行业板块资金流数据获取任务")
    
    try:
        # 获取所有行业板块
        sectors = IndustrySector.objects.all()
        
        if not sectors.exists():
            # 如果数据库中没有行业板块数据，先获取行业板块列表
            logger.warning("获取行业板块列表失败，无法获取资金流数据")
            return {"status": "error", "message": "获取行业板块列表失败，无法获取资金流数据"}
        
        # 获取每个行业板块的资金流数据
        success_count = 0
        error_count = 0
        total_count = sectors.count()
        total_records = 0
        
        for sector in sectors:
            time.sleep(2)  # 避免请求过于频繁
            try:
                logger.info(f"获取行业板块 {sector.code} ({sector.name}) 的资金流数据")
                
                # 从akshare获取资金流数据
                df = ak.stock_sector_fund_flow_hist(symbol=sector.name)
                
                if df is None or df.empty:
                    logger.warning(f"行业板块 {sector.name} 的资金流数据为空")
                    error_count += 1
                    continue
                
                # 准备批量创建的数据列表
                fund_flow_objects = []
                records_count = 0
                
                for _, row in df.iterrows():
                    try:
                        # 解析日期
                        date_str = str(row['日期'])
                        if len(date_str) == 8:  # YYYYMMDD格式
                            date = datetime.strptime(date_str, '%Y%m%d').date()
                        else:  # YYYY-MM-DD格式
                            date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        
                        # 创建IndustrySectorFundFlow对象
                        fund_flow_obj = IndustrySectorFundFlow(
                            sector=sector,
                            date=date,
                            main_net_inflow_amount=float(row['主力净流入-净额']) if not pd.isna(row['主力净流入-净额']) else 0.0,
                            main_net_inflow_ratio=float(row['主力净流入-净占比']) if not pd.isna(row['主力净流入-净占比']) else 0.0,
                            super_large_net_inflow_amount=float(row['超大单净流入-净额']) if not pd.isna(row['超大单净流入-净额']) else 0.0,
                            super_large_net_inflow_ratio=float(row['超大单净流入-净占比']) if not pd.isna(row['超大单净流入-净占比']) else 0.0,
                            large_net_inflow_amount=float(row['大单净流入-净额']) if not pd.isna(row['大单净流入-净额']) else 0.0,
                            large_net_inflow_ratio=float(row['大单净流入-净占比']) if not pd.isna(row['大单净流入-净占比']) else 0.0,
                            medium_net_inflow_amount=float(row['中单净流入-净额']) if not pd.isna(row['中单净流入-净额']) else 0.0,
                            medium_net_inflow_ratio=float(row['中单净流入-净占比']) if not pd.isna(row['中单净流入-净占比']) else 0.0,
                            small_net_inflow_amount=float(row['小单净流入-净额']) if not pd.isna(row['小单净流入-净额']) else 0.0,
                            small_net_inflow_ratio=float(row['小单净流入-净占比']) if not pd.isna(row['小单净流入-净占比']) else 0.0,
                        )
                        fund_flow_objects.append(fund_flow_obj)
                        records_count += 1
                        
                    except Exception as e:
                        logger.error(f"处理行业板块 {sector.name} 日期 {row['日期']} 的资金流数据失败: {str(e)}")
                        continue
                
                # 批量创建数据，使用ignore_conflicts=True避免重复数据错误
                if fund_flow_objects:
                    IndustrySectorFundFlow.objects.bulk_create(fund_flow_objects, batch_size=500, ignore_conflicts=True)
                
                logger.info(f"成功获取行业板块 {sector.name} 的 {records_count} 条资金流数据")
                success_count += 1
                total_records += records_count
                
            except Exception as e:
                logger.error(f"获取行业板块 {sector.name} 的资金流数据失败: {str(e)}")
                error_count += 1
        
        logger.info(f"行业板块资金流数据获取任务完成，成功: {success_count}，失败: {error_count}，总计: {total_count}，总记录数: {total_records}")
        return {
            "status": "success" if error_count == 0 else "partial",
            "message": f"行业板块资金流数据获取任务完成，成功: {success_count}，失败: {error_count}，总计: {total_count}，总记录数: {total_records}"
        }
        
    except Exception as e:
        logger.error(f"行业板块资金流数据获取任务执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}


def update_industry_sector_fund_flow_data():
    """
    更新最近7天行业板块资金流数据
    每个交易日收盘后执行，只更新最近的数据
    """
    logger.info("开始执行最近7天行业板块资金流数据更新任务")
    
    try:
        # 获取所有行业板块
        sectors = IndustrySector.objects.all()
        
        if not sectors.exists():
            logger.warning("数据库中没有行业板块数据，无法更新资金流数据")
            return {"status": "error", "message": "数据库中没有行业板块数据，无法更新资金流数据"}
        
        # 更新每个行业板块的最近7天资金流数据
        success_count = 0
        error_count = 0
        total_count = sectors.count()
        total_records = 0
        
        for sector in sectors:
            time.sleep(0.5)  # 避免请求过于频繁
            try:
                logger.info(f"更新行业板块 {sector.code} ({sector.name}) 的最近7天资金流数据")
                
                # 从akshare获取资金流数据
                df = ak.stock_sector_fund_flow_hist(symbol=sector.name)
                
                if df is None or df.empty:
                    logger.warning(f"行业板块 {sector.name} 的资金流数据为空")
                    error_count += 1
                    continue
                
                # 只处理最近7天的数据
                recent_date = datetime.now().date() - timedelta(days=7)
                
                # 获取该板块已存在的资金流数据日期
                existing_dates = set(
                    IndustrySectorFundFlow.objects.filter(
                        sector=sector,
                        date__gte=recent_date
                    ).values_list('date', flat=True)
                )
                
                # 准备批量创建和更新的数据
                fund_flow_objects_to_create = []
                fund_flow_objects_to_update = []
                records_count = 0
                
                for _, row in df.iterrows():
                    try:
                        # 解析日期
                        date_str = str(row['日期'])
                        if len(date_str) == 8:  # YYYYMMDD格式
                            date = datetime.strptime(date_str, '%Y%m%d').date()
                        else:  # YYYY-MM-DD格式
                            date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        
                        # 只处理最近7天的数据
                        if date < recent_date:
                            continue
                        
                        # 准备数据
                        fund_flow_data = {
                            'main_net_inflow_amount': float(row['主力净流入-净额']) if not pd.isna(row['主力净流入-净额']) else 0.0,
                            'main_net_inflow_ratio': float(row['主力净流入-净占比']) if not pd.isna(row['主力净流入-净占比']) else 0.0,
                            'super_large_net_inflow_amount': float(row['超大单净流入-净额']) if not pd.isna(row['超大单净流入-净额']) else 0.0,
                            'super_large_net_inflow_ratio': float(row['超大单净流入-净占比']) if not pd.isna(row['超大单净流入-净占比']) else 0.0,
                            'large_net_inflow_amount': float(row['大单净流入-净额']) if not pd.isna(row['大单净流入-净额']) else 0.0,
                            'large_net_inflow_ratio': float(row['大单净流入-净占比']) if not pd.isna(row['大单净流入-净占比']) else 0.0,
                            'medium_net_inflow_amount': float(row['中单净流入-净额']) if not pd.isna(row['中单净流入-净额']) else 0.0,
                            'medium_net_inflow_ratio': float(row['中单净流入-净占比']) if not pd.isna(row['中单净流入-净占比']) else 0.0,
                            'small_net_inflow_amount': float(row['小单净流入-净额']) if not pd.isna(row['小单净流入-净额']) else 0.0,
                            'small_net_inflow_ratio': float(row['小单净流入-净占比']) if not pd.isna(row['小单净流入-净占比']) else 0.0,
                        }
                        
                        if date in existing_dates:
                            # 如果记录已存在，准备更新
                            try:
                                existing_obj = IndustrySectorFundFlow.objects.get(sector=sector, date=date)
                                for field, value in fund_flow_data.items():
                                    setattr(existing_obj, field, value)
                                fund_flow_objects_to_update.append(existing_obj)
                            except IndustrySectorFundFlow.DoesNotExist:
                                # 如果查询时记录不存在，创建新记录
                                fund_flow_obj = IndustrySectorFundFlow(
                                    sector=sector,
                                    date=date,
                                    **fund_flow_data
                                )
                                fund_flow_objects_to_create.append(fund_flow_obj)
                        else:
                            # 如果记录不存在，准备创建
                            fund_flow_obj = IndustrySectorFundFlow(
                                sector=sector,
                                date=date,
                                **fund_flow_data
                            )
                            fund_flow_objects_to_create.append(fund_flow_obj)
                        
                        records_count += 1
                        
                    except Exception as e:
                        logger.error(f"处理行业板块 {sector.name} 日期 {row['日期']} 的资金流数据失败: {str(e)}")
                        continue
                
                # 批量创建新记录
                if fund_flow_objects_to_create:
                    IndustrySectorFundFlow.objects.bulk_create(fund_flow_objects_to_create, ignore_conflicts=True)
                
                # 批量更新已存在的记录
                if fund_flow_objects_to_update:
                    IndustrySectorFundFlow.objects.bulk_update(
                        fund_flow_objects_to_update,
                        ['main_net_inflow_amount', 'main_net_inflow_ratio', 'super_large_net_inflow_amount', 
                         'super_large_net_inflow_ratio', 'large_net_inflow_amount', 'large_net_inflow_ratio',
                         'medium_net_inflow_amount', 'medium_net_inflow_ratio', 'small_net_inflow_amount', 
                         'small_net_inflow_ratio']
                    )
                
                logger.info(f"成功更新行业板块 {sector.name} 的 {records_count} 条资金流数据")
                success_count += 1
                total_records += records_count
                
            except Exception as e:
                logger.error(f"更新行业板块 {sector.name} 的资金流数据失败: {str(e)}")
                error_count += 1
        
        logger.info(f"行业板块资金流数据更新任务完成，成功: {success_count}，失败: {error_count}，总计: {total_count}，总记录数: {total_records}")
        return {
            "status": "success" if error_count == 0 else "partial",
            "message": f"行业板块资金流数据更新任务完成，成功: {success_count}，失败: {error_count}，总计: {total_count}，总记录数: {total_records}"
        }
        
    except Exception as e:
        logger.error(f"行业板块资金流数据更新任务执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}

if __name__ == '__main__':
    # fetch_industry_sector_fund_flow_data()
    # update_industry_sector_fund_flow_data()
    update_industry_sector_daily_data()