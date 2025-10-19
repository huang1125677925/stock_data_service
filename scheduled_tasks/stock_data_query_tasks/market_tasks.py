import sys
import os
from pathlib import Path
from tracemalloc import start
import django

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_data_service.settings')
django.setup()

import logging
import baostock as bs
from datetime import datetime, timedelta
import akshare as ak
import pandas as pd
from indival_stock_data.models import IndividualStock, PerformanceReport, BalanceSheet, IncomeStatement, CashFlowStatement
import time
from django.db import transaction
from typing import Tuple, List
import decimal

from scheduled_tasks.stock_data_query_tasks.stock_data_models import StockDailyData

from django.utils import timezone
from decimal import Decimal
from stock_market.models import IndexHighLowStatistics, StockMarketFundFlow

logger = logging.getLogger(__name__)

def fetch_market_stocks():
    """
    从akshare获取所有股票和指数列表并保存到数据库
    每天执行一次
    """
    logger.info("开始执行股票和指数列表获取任务")
    
    try:
        # 从akshare获取指数列表
        logger.info("从akshare获取指数列表数据")
        df = ak.stock_zh_index_spot_sina()
        
        if df is None or df.empty:
            logger.warning("从akshare获取股票列表数据为空")
            return {"status": "warning", "message": "从akshare获取股票列表数据为空"}
        
        # 转换数据格式并批量保存到数据库
        from django.db import transaction
        
        # 获取现有股票代码和index_type的组合
        existing_records = set(IndividualStock.objects.values_list('code', 'index_type'))
        
        # 准备批量创建和更新的数据
        stocks_to_create = []
        stocks_to_update = []
        
        for _, row in df.iterrows():
            code = str(row['代码'])
            name = str(row['名称'])

            # 过滤掉以 sz980 开头的股票代码
            if code.startswith('sh000'):
                index_type = "SH_INDEX"
            elif code.startswith('sz399'):
                index_type = "SZ_INDEX"
            else:
                continue
            
            # 准备股票数据
            stock_data = {
                'name': name,
                # akshare数据字段 - 根据当前接口字段调整
                'index_type': index_type,
                'latest_price': float(row['最新价']) if pd.notna(row['最新价']) else None,
                'change_percent': float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else None,
                'change_amount': float(row['涨跌额']) if pd.notna(row['涨跌额']) else None,
                'volume': int(row['成交量']) if pd.notna(row['成交量']) else None,
                'amount': float(row['成交额']) if pd.notna(row['成交额']) else None,
                'high': float(row['最高']) if pd.notna(row['最高']) else None,
                'low': float(row['最低']) if pd.notna(row['最低']) else None,
                'open_price': float(row['今开']) if pd.notna(row['今开']) else None,
                'close_price': float(row['昨收']) if pd.notna(row['昨收']) else None,
            }
            
            if (code, index_type) in existing_records:
                # 准备更新数据 - 根据code和index_type同时匹配
                stocks_to_update.append((code, index_type, stock_data))
            else:
                # 准备创建数据
                stock_data['code'] = code
                stocks_to_create.append(IndividualStock(**stock_data))
        
        # 批量操作
        
        # 批量创建新股票
        if stocks_to_create:
            with transaction.atomic():
                IndividualStock.objects.bulk_create(stocks_to_create, batch_size=500)
                logger.info(f"批量创建了{len(stocks_to_create)}只新股票")
        
        # 批量更新现有股票
        if stocks_to_update:
            for code, index_type, data in stocks_to_update:
                with transaction.atomic():
                    IndividualStock.objects.filter(code=code, index_type=index_type).update(**data)
                logger.info(f"更新了股票 {code} (类型: {index_type}) 的数据")
            logger.info(f"批量更新了{len(stocks_to_update)}只现有股票")
        
        stock_count = len(stocks_to_create) + len(stocks_to_update)
        
        logger.info(f"成功获取并保存{stock_count}只个股信息到数据库")
        return {"status": "success", "message": f"成功获取并保存{stock_count}只个股信息到数据库"}
        
    except Exception as e:
        logger.error(f"个股列表获取任务执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}

def fetch_market_fund_flow():
    """
    从akshare获取所有股票和指数的资金流数据并保存到数据库
    每天执行一次
    """
    logger.info("开始执行股票和指数资金流数据获取任务")
    
    try:
        # 从akshare获取资金流数据
        logger.info("从akshare获取资金流数据")
        df = ak.stock_market_fund_flow()
        
        if df is None or df.empty:
            logger.warning("从akshare获取资金流数据为空")
            return {"status": "warning", "message": "从akshare获取资金流数据为空"}
        
        # 转换数据格式并批量保存到数据库
        from django.db import transaction
        
        # 获取现有股票代码和index_type的组合
        existing_records = set(IndividualStock.objects.values_list('code', 'index_type'))
        
        # 准备批量创建和更新的数据
        fund_flow_to_create = []
        fund_flow_to_update = []
        
        for _, row in df.iterrows():
            code = str(row['代码'])
            name = str(row['名称'])
    
    except Exception as e:
        logger.error(f"资金流数据获取任务执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}


def fetch_market_pe_lg():
    """
    从akshare获取所有股票和指数的市盈率数据并保存到数据库
    每天执行一次
    """
    logger.info("开始执行股票和指数市盈率数据获取任务")
    
    try:
        # 从akshare获取市盈率数据
        logger.info("从akshare获取市盈率数据")
        df = ak.stock_a_high_low_statistics()
        
        if df is None or df.empty:
            logger.warning("从akshare获取市盈率数据为空")
            return {"status": "warning", "message": "从akshare获取市盈率数据为空"}
        
        # 转换数据格式并批量保存到数据库
        from django.db import transaction
        
        # 获取现有股票代码和index_type的组合
        existing_records = set(IndividualStock.objects.values_list('code', 'index_type'))
        
        # 准备批量创建和更新的数据
        pe_lg_to_create = []
        pe_lg_to_update = []
        
        for _, row in df.iterrows():
            code = str(row['代码'])
            name = str(row['名称'])
    
    except Exception as e:
        logger.error(f"市盈率数据获取任务执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}


def fetch_index_high_low_statistics(symbol='all', save_to_db=True):
    """
    从akshare获取指数涨跌统计数据，包括创新高、新低的股票数量
    
    功能：从akshare获取指定指数的涨跌统计数据，存储所有数据到数据库
    参数：
        symbol (str): 指数代码，可选值：'all', 'sz50', 'hs300', 'zz500'
        save_to_db (bool): 是否保存到数据库，默认为True
    返回值：
        dict: 包含统计数据的字典，包括处理的记录数量
    事件：数据获取成功后批量保存到数据库，避免重复数据
    """
    logger.info(f"开始获取{symbol}指数涨跌统计数据")
    
    try:
        # 获取akshare数据
        df = ak.stock_a_high_low_statistics(symbol=symbol)
        
        if df.empty:
            logger.warning(f"未获取到{symbol}的涨跌统计数据")
            return {"status": "warning", "message": f"未获取到{symbol}的涨跌统计数据"}
        
        logger.info(f"从akshare获取到{len(df)}条{symbol}指数数据")
        
        # 保存到数据库
        if save_to_db:
            # 获取数据库中已存在的记录，避免重复插入
            existing_records = set(
                IndexHighLowStatistics.objects.filter(
                    index_code=symbol
                ).values_list('date', flat=True)
            )
            
            # 准备批量创建的数据列表
            records_to_create = []
            skipped_count = 0
            
            for _, row in df.iterrows():
                # 检查是否已存在
                row_date = row['date']
                if row_date in existing_records:
                    skipped_count += 1
                    continue
                
                # 构建数据记录
                record_data = IndexHighLowStatistics(
                    date=row_date,
                    index_code=symbol,
                    close=Decimal(str(row.get('close', 0))) if row.get('close') else None,
                    high20=int(row.get('high20', 0) or 0),
                    low20=int(row.get('low20', 0) or 0),
                    high60=int(row.get('high60', 0) or 0),
                    low60=int(row.get('low60', 0) or 0),
                    high120=int(row.get('high120', 0) or 0),
                    low120=int(row.get('low120', 0) or 0)
                )
                records_to_create.append(record_data)
            
            # 批量创建新记录
            created_count = 0
            if records_to_create:
                with transaction.atomic():
                    IndexHighLowStatistics.objects.bulk_create(records_to_create, batch_size=500)
                    created_count = len(records_to_create)
                    logger.info(f"批量创建了{created_count}条{symbol}指数涨跌统计数据")
            
            # 构建返回结果
            result_data = {
                'symbol': symbol,
                'total_records': len(df),
                'created_count': created_count,
                'skipped_count': skipped_count,
                'existing_count': len(existing_records)
            }
            
            logger.info(f"成功处理{symbol}指数数据：总共{len(df)}条，新增{created_count}条，跳过{skipped_count}条")
            return {"status": "success", "data": result_data}
        else:
            # 不保存到数据库时，返回最新一条数据（保持向后兼容）
            latest_data = df.iloc[-1]
            result_data = {
                'date': latest_data['date'],
                'index_code': symbol,
                'close': Decimal(str(latest_data.get('close', 0))) if latest_data.get('close') else None,
                'high20': int(latest_data.get('high20', 0) or 0),
                'low20': int(latest_data.get('low20', 0) or 0),
                'high60': int(latest_data.get('high60', 0) or 0),
                'low60': int(latest_data.get('low60', 0) or 0),
                'high120': int(latest_data.get('high120', 0) or 0),
                'low120': int(latest_data.get('low120', 0) or 0)
            }
            return {"status": "success", "data": result_data}
        
    except Exception as e:
        logger.error(f"获取{symbol}涨跌统计数据失败: {str(e)}")
        return {"status": "error", "message": str(e)}


def fetch_all_index_high_low_statistics(save_to_db=True):
    """
    获取所有指数的涨跌统计数据
    
    功能：批量获取all、sz50、hs300、zz500四个指数的涨跌统计数据
    参数：
        save_to_db (bool): 是否保存到数据库，默认为True
    返回值：
        dict: 包含所有指数统计数据的字典
    事件：批量获取并保存数据到数据库
    """
    logger.info("开始批量获取所有指数涨跌统计数据")
    
    symbols = ['all', 'sz50', 'hs300', 'zz500']
    results = {}
    success_count = 0
    
    for symbol in symbols:
        try:
            result = fetch_index_high_low_statistics(symbol=symbol, save_to_db=save_to_db)
            results[symbol] = result
            if result['status'] == 'success':
                success_count += 1
        except Exception as e:
            logger.error(f"获取{symbol}数据失败: {str(e)}")
            results[symbol] = {'status': 'error', 'message': str(e)}
    
    logger.info(f"批量获取指数涨跌统计数据完成，成功{success_count}个，总共{len(symbols)}个")
    return {
        "status": "success" if success_count > 0 else "error",
        "message": f"成功获取{success_count}个指数数据，总共{len(symbols)}个",
        "results": results
    }


def fetch_stock_a_congestion_lg():
    ak.stock_a_congestion_lg()

def fetch_stock_market_fund_flow(save_to_db=True):
    """
    获取股票市场资金流数据并存储到数据库
    
    功能：从akshare获取大盘资金流数据，包括主力、大单、中单、小单、超大单的净流入情况
    参数：
        - save_to_db: 是否保存到数据库，默认True
    返回值：包含状态、消息和数据的字典
    事件：数据获取成功后自动保存到StockMarketFundFlow表
    
    数据字段说明：
    "日期",
    "主力净流入-净额",
    "小单净流入-净额", 
    "中单净流入-净额",
    "大单净流入-净额",
    "超大单净流入-净额",
    "主力净流入-净占比",
    "小单净流入-净占比",
    "中单净流入-净占比", 
    "大单净流入-净占比",
    "超大单净流入-净占比",
    "上证-收盘价",
    "上证-涨跌幅",
    "深证-收盘价",
    "深证-涨跌幅"
    """
    try:
        logger.info("开始获取股票市场资金流数据")
        
        # 获取数据
        df = ak.stock_market_fund_flow()
        
        if df is None or df.empty:
            logger.warning("未获取到股票市场资金流数据")
            return {
                "status": "warning",
                "message": "未获取到数据",
                "data": None
            }
        
        logger.info(f"获取到{len(df)}条股票市场资金流数据")
        
        if save_to_db:
            saved_count = 0
            skipped_count = 0
            
            # 先获取数据库中已存在的所有日期
            existing_dates = set(StockMarketFundFlow.objects.values_list('date', flat=True))
            logger.info(f"数据库中已存在{len(existing_dates)}条资金流数据")
            
            # 收集需要批量创建的新数据
            new_records = []
            
            for index, row in df.iterrows():
                try:
                    # 解析日期
                    date_str = str(row['日期'])
                    if pd.isna(row['日期']) or date_str == 'nan':
                        continue
                        
                    # 尝试不同的日期格式
                    try:
                        if '-' in date_str:
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                        else:
                            date_obj = datetime.strptime(date_str, '%Y%m%d').date()
                    except ValueError:
                        logger.warning(f"无法解析日期: {date_str}")
                        continue
                    
                    # 检查日期是否已存在
                    if date_obj in existing_dates:
                        skipped_count += 1
                        continue
                    
                    # 准备新记录数据
                    new_record = StockMarketFundFlow(
                        date=date_obj,
                        main_net_inflow_amount=_safe_decimal(row.get('主力净流入-净额')),
                        small_net_inflow_amount=_safe_decimal(row.get('小单净流入-净额')),
                        medium_net_inflow_amount=_safe_decimal(row.get('中单净流入-净额')),
                        large_net_inflow_amount=_safe_decimal(row.get('大单净流入-净额')),
                        super_large_net_inflow_amount=_safe_decimal(row.get('超大单净流入-净额')),
                        main_net_inflow_ratio=_safe_decimal(row.get('主力净流入-净占比')),
                        small_net_inflow_ratio=_safe_decimal(row.get('小单净流入-净占比')),
                        medium_net_inflow_ratio=_safe_decimal(row.get('中单净流入-净占比')),
                        large_net_inflow_ratio=_safe_decimal(row.get('大单净流入-净占比')),
                        super_large_net_inflow_ratio=_safe_decimal(row.get('超大单净流入-净占比')),
                        shanghai_close_price=_safe_decimal(row.get('上证-收盘价')),
                        shanghai_change_rate=_safe_decimal(row.get('上证-涨跌幅')),
                        shenzhen_close_price=_safe_decimal(row.get('深证-收盘价')),
                        shenzhen_change_rate=_safe_decimal(row.get('深证-涨跌幅')),
                    )
                    new_records.append(new_record)
                        
                except Exception as e:
                    logger.error(f"处理第{index}行数据失败: {str(e)}")
                    continue
            
            # 批量创建新记录
            if new_records:
                with transaction.atomic():
                    StockMarketFundFlow.objects.bulk_create(new_records, batch_size=1000)
                    saved_count = len(new_records)
                logger.info(f"批量创建了{saved_count}条新的资金流数据")
            
            logger.info(f"股票市场资金流数据处理完成，新增{saved_count}条，跳过{skipped_count}条已存在数据")
            
            return {
                "status": "success",
                "message": f"成功获取并保存股票市场资金流数据，新增{saved_count}条，跳过{skipped_count}条已存在数据",
                "data": {
                    "total_records": len(df),
                    "saved_count": saved_count,
                    "skipped_count": skipped_count
                }
            }
        else:
            return {
                "status": "success", 
                "message": f"成功获取{len(df)}条股票市场资金流数据",
                "data": df.to_dict('records')
            }
            
    except Exception as e:
        logger.error(f"获取股票市场资金流数据失败: {str(e)}")
        return {
            "status": "error",
            "message": f"获取数据失败: {str(e)}",
            "data": None
        }


def _safe_decimal(value):
    """
    安全转换为Decimal类型
    
    功能：将各种类型的数值安全转换为Decimal，处理NaN、None等特殊值
    参数：
        - value: 待转换的值
    返回值：Decimal对象或None
    """
    if pd.isna(value) or value is None or str(value).lower() in ['nan', 'none', '']:
        return None
    try:
        return Decimal(str(value))
    except (ValueError, TypeError, decimal.InvalidOperation):
        return None


if __name__ == '__main__':
    # fetch_all_index_high_low_statistics()
    fetch_all_index_high_low_statistics()