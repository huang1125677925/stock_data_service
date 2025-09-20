#!/usr/bin/env python3
"""
个股数据抓取任务
定期从akshare获取个股数据并存储到数据库
"""
import sys
import os
from pathlib import Path
import django
# 设置Django环境
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_data_service.settings')
django.setup()

import logging
from datetime import datetime, timedelta
import akshare as ak
import pandas as pd
from indival_stock_data.models import IndividualStock
import time
from indival_stock_data.models import IndividualStockDaily
from django.db import transaction
from typing import Tuple



from django.utils import timezone

logger = logging.getLogger(__name__)

def fetch_individual_stocks():
    """
    从akshare获取所有个股列表并保存到数据库
    每天执行一次
    """
    logger.info("开始执行个股列表获取任务")
    
    try:
        # 从akshare获取股票列表
        logger.info("从akshare获取股票列表数据")
        df = ak.stock_sh_a_spot_em()
        
        if df is None or df.empty:
            logger.warning("从akshare获取股票列表数据为空")
            return {"status": "warning", "message": "从akshare获取股票列表数据为空"}
        
        # 转换数据格式并批量保存到数据库
        from django.db import transaction
        
        # 获取现有股票代码
        existing_codes = set(IndividualStock.objects.values_list('code', flat=True))
        
        # 准备批量创建和更新的数据
        stocks_to_create = []
        stocks_to_update = []
        
        for _, row in df.iterrows():
            code = str(row['代码'])
            name = str(row['名称'])
            
            # 准备股票数据
            stock_data = {
                'name': name,
                'pe_ratio': float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else None,
                'pb_ratio': float(row['市净率']) if pd.notna(row['市净率']) else None,
                'total_market_cap': float(row['总市值']) if pd.notna(row['总市值']) else None,
                'circulating_market_cap': float(row['流通市值']) if pd.notna(row['流通市值']) else None,
                # akshare数据字段
                'latest_price': float(row['最新价']) if pd.notna(row['最新价']) else None,
                'change_percent': float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else None,
                'change_amount': float(row['涨跌额']) if pd.notna(row['涨跌额']) else None,
                'volume': int(row['成交量']) if pd.notna(row['成交量']) else None,
                'amount': float(row['成交额']) if pd.notna(row['成交额']) else None,
                'amplitude': float(row['振幅']) if pd.notna(row['振幅']) else None,
                'high': float(row['最高']) if pd.notna(row['最高']) else None,
                'low': float(row['最低']) if pd.notna(row['最低']) else None,
                'open_price': float(row['今开']) if pd.notna(row['今开']) else None,
                'close_price': float(row['昨收']) if pd.notna(row['昨收']) else None,
                'volume_ratio': float(row['量比']) if pd.notna(row['量比']) else None,
                'turnover_rate': float(row['换手率']) if pd.notna(row['换手率']) else None,
                'price_change_speed': float(row['涨速']) if pd.notna(row['涨速']) else None,
                'change_5min': float(row['5分钟涨跌']) if pd.notna(row['5分钟涨跌']) else None,
                'change_60d': float(row['60日涨跌幅']) if pd.notna(row['60日涨跌幅']) else None,
                'change_ytd': float(row['年初至今涨跌幅']) if pd.notna(row['年初至今涨跌幅']) else None,
            }
            
            if code in existing_codes:
                # 准备更新数据
                stocks_to_update.append((code, stock_data))
            else:
                # 准备创建数据
                stock_data['code'] = code
                stocks_to_create.append(IndividualStock(**stock_data))
        
        # 批量操作
        with transaction.atomic():
            # 批量创建新股票
            if stocks_to_create:
                IndividualStock.objects.bulk_create(stocks_to_create, batch_size=1000)
                logger.info(f"批量创建了{len(stocks_to_create)}只新股票")
            
            # 批量更新现有股票
            if stocks_to_update:
                for code, data in stocks_to_update:
                    IndividualStock.objects.filter(code=code).update(**data)
                logger.info(f"批量更新了{len(stocks_to_update)}只现有股票")
        
        stock_count = len(stocks_to_create) + len(stocks_to_update)
        
        logger.info(f"成功获取并保存{stock_count}只个股信息到数据库")
        return {"status": "success", "message": f"成功获取并保存{stock_count}只个股信息到数据库"}
        
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
        # 获取所有个股
        stocks = IndividualStock.objects.all()
        
        if not stocks.exists():
            # 如果数据库中没有个股数据，先获取个股列表
            logger.info("数据库中没有个股数据，先获取个股列表")
            return {"status": "error", "message": "数据库中没有个股数据，先获取个股列表"}
        stock_code_list = [stock.code for stock in stocks]
        # 更新所有个股的历史数据（最近30天）
        updated_stocks, updated_history = update_stock_history(stock_code_list=stock_code_list, days=4000)
        
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
        updated_stocks, updated_history = individual_stock_service.update_stock_history(stock_code_list=[stock_code], days=days)
        
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

def update_stock_history(
    stock_code_list: list = None, 
    days: int = 30, 
    batch_size: int = 300, 
    sleep_seconds: float = 0.03, 
    ignore_conflicts: bool = True, 
    order_by_date: bool = True) -> Tuple[int, int]:
    """
    更新股票历史数据（支持小批量分事务提交以降低数据库压力）
    
    功能:
        - 从 akshare 拉取指定股票近 N 天的日线数据
        - 仅对不存在的记录进行批量插入（遵循 unique_together(stock, date)）
        - 采用“每个小批次一个事务”的方式提交，降低长事务带来的锁与日志压力
        - 可选忽略唯一冲突（ignore_conflicts），增强并发场景的健壮性
        - 可选按日期升序插入（order_by_date），优化索引写入的顺序性
        - 可选在批次之间短暂休眠（sleep_seconds），进行轻微节流
    
    参数:
        stock_code_list (list): 股票代码列表; 若为 None 则更新所有股票。
        days (int): 回溯的天数，默认 30。
        batch_size (int): 每次 bulk_create 的批量大小，默认 300，建议 200~500 以降低单次事务压力。
        sleep_seconds (float): 每个批次写入完成后的休眠秒数，默认 0.0（不休眠）。
        ignore_conflicts (bool): 批量插入发生唯一冲突时是否忽略，默认 True。
        order_by_date (bool): 是否按日期升序写入，默认 True，有助于降低随机写入带来的索引压力。
    
    返回值:
        Tuple[int, int]: (有新增数据的股票数, 新增的历史数据条数)
    
    事件:
        - 日志事件: logger.info/ warning/ error 记录拉取、过滤、插入与异常信息
        - 数据库事件: 以 batch_size 为单位开启事务，执行 bulk_create 并可选忽略唯一冲突
    """
    try:
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

        updated_stocks = 0
        updated_history = 0
        
        # 获取要更新的股票列表
        if stock_code_list:
            stocks = IndividualStock.objects.filter(code__in=stock_code_list)
        else:
            stocks = IndividualStock.objects.all()
        
        if not stocks.exists():
            logger.warning("没有找到需要更新的股票")
            return 0, 0
        
        # 遍历股票列表更新历史数据
        for stock in stocks:
            logger.info(f"开始更新股票 {stock.code} 的历史数据")
            try:
                # 从 akshare 获取历史数据
                df = ak.stock_zh_a_hist(symbol=stock.code, period="daily", start_date=start_date, end_date=end_date, adjust="")
                time.sleep(0.1)  # 避免请求过于频繁
                if df is None or df.empty:
                    logger.warning(f"获取股票 {stock.code} 历史行情数据为空")
                    continue

                # 可选：按日期升序，优化索引顺序写入
                if order_by_date and '日期' in df.columns:
                    try:
                        df = df.sort_values('日期')
                    except Exception:
                        pass
                
                # 获取指定日期范围内已有的历史数据日期（用于去重）
                start_date_obj = datetime.strptime(start_date, '%Y%m%d').date()
                end_date_obj = datetime.strptime(end_date, '%Y%m%d').date()
                existing_dates = set(IndividualStockDaily.objects.filter(
                    stock=stock,
                    date__gte=start_date_obj,
                    date__lte=end_date_obj
                ).values_list('date', flat=True))
                
                # 准备批量创建的数据
                records_to_create = []
                # 注：现有记录的“批量更新”逻辑在原实现中已注释，这里维持不变以避免额外写压力
                
                for _, row in df.iterrows():
                    # 将日期统一为 date 对象
                    date_val = row['日期']
                    if hasattr(date_val, 'strftime'):
                        date_str = date_val.strftime('%Y-%m-%d')
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    else:
                        # 兜底：如果不是时间类型，尝试直接解析
                        try:
                            date_obj = datetime.strptime(str(date_val), '%Y-%m-%d').date()
                        except Exception:
                            continue
                    
                    stock_daily_data = {
                        'open_price': float(row['开盘']) if pd.notna(row.get('开盘')) else 0.0,
                        'close_price': float(row['收盘']) if pd.notna(row.get('收盘')) else 0.0,
                        'high_price': float(row['最高']) if pd.notna(row.get('最高')) else 0.0,
                        'low_price': float(row['最低']) if pd.notna(row.get('最低')) else 0.0,
                        'change_percent': float(row['涨跌幅']) if pd.notna(row.get('涨跌幅')) else 0.0,
                        'change_amount': float(row['涨跌额']) if pd.notna(row.get('涨跌额')) else 0.0,
                        'volume': int(row['成交量']) if pd.notna(row.get('成交量')) else 0,
                        'amount': float(row['成交额']) if pd.notna(row.get('成交额')) else 0.0,
                        'amplitude': float(row['振幅']) if pd.notna(row.get('振幅')) else None,
                        'turnover_rate': float(row['换手率']) if pd.notna(row.get('换手率')) else None,
                    }
                    
                    # 仅为不存在的 (stock, date) 组合创建记录
                    if date_obj not in existing_dates:
                        stock_daily_data['stock'] = stock
                        stock_daily_data['date'] = date_obj
                        records_to_create.append(IndividualStockDaily(**stock_daily_data))
                
                # 可选：按日期升序插入，降低随机写入带来的索引抖动
                if order_by_date and records_to_create:
                    try:
                        records_to_create.sort(key=lambda obj: obj.date)
                    except Exception:
                        pass
                
                # 分批提交，每个批次单独事务，降低锁与日志压力
                created_total_for_stock = 0
                if records_to_create:
                    total = len(records_to_create)
                    batches = (total + batch_size - 1) // batch_size
                    for i in range(0, total, batch_size):
                        chunk = records_to_create[i:i + batch_size]
                        try:
                            with transaction.atomic():
                                inserted = IndividualStockDaily.objects.bulk_create(
                                    chunk,
                                    batch_size=batch_size,
                                    ignore_conflicts=ignore_conflicts
                                )
                            created_total_for_stock += len(inserted)
                        except Exception as be:
                            # 单批失败不影响后续批次，记录错误并继续
                            logger.error(f"股票 {stock.code} 第 {i//batch_size + 1}/{batches} 个批次插入失败: {be}")
                        
                        # 轻微节流，避免连续重写放大压力
                        if sleep_seconds > 0:
                            time.sleep(sleep_seconds)
                    logger.info(f"股票 {stock.code} 新增 {created_total_for_stock} 条历史数据，共 {batches} 个批次（目标批量 {batch_size}）。")
                
                if created_total_for_stock > 0:
                    updated_stocks += 1
                    updated_history += created_total_for_stock
                    logger.info(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 完成股票 {stock.code} 的历史数据写入: 新增 {created_total_for_stock} 条")
            except Exception as e:
                logger.error(f"更新股票 {stock.code} 历史数据失败: {str(e)}")
        
        logger.info(f"更新股票历史数据完成: 更新 {updated_stocks} 只股票，新增 {updated_history} 条历史数据")
        return updated_stocks, updated_history
        
    except Exception as e:
        logger.error(f"更新股票历史数据失败: {str(e)}")
        return 0, 0

if __name__ == '__main__':
    update_individual_stock_daily_data()