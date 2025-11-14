#!/usr/bin/env python3
"""
个股数据查询任务
"""

import sys
import os
from pathlib import Path
from tracemalloc import start
import django

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_data_service.settings')
django.setup()
import tushare as ts

import logging
import baostock as bs
from datetime import datetime, timedelta
import akshare as ak
import pandas as pd
from indival_stock_data.models import IndividualStock, PerformanceReport, BalanceSheet, IncomeStatement, CashFlowStatement
import time
from indival_stock_data.models import IndividualStockDaily
from indival_stock_data.models import IndividualStockWeekly
from django.db import transaction
from typing import Tuple, List, Set, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

from scheduled_tasks.stock_data_query_tasks.stock_data_models import StockDailyData, StockWeeklyData
from scheduled_tasks.stock_data_query_tasks.tushare_data import fetch_bak_daily

from django.utils import timezone
from common.tushare_proxy import call_tushare

logger = logging.getLogger(__name__)

def _get_recent_trade_date() -> str:
    """
    获取最近一个交易日（优先使用Tushare交易日历，失败则按工作日/周末回退）。

    返回值：
    - str：YYYYMMDD 格式的最近交易日
    """
    try:
        today = datetime.now()
        end_date = today.strftime('%Y%m%d')
        start_date = (today - timedelta(days=15)).strftime('%Y%m%d')
        resp = call_tushare(
            interface='trade_cal',
            params={'start_date': start_date, 'end_date': end_date, 'is_open': 1},
            fields='cal_date,is_open,pretrade_date',
            use_query=False
        )
        records = (resp or {}).get('data', {}).get('records', [])
        open_days = [str(r.get('cal_date')) for r in records if str(r.get('is_open')) in ('1', 'True', 'true', '1')]
        if open_days:
            return max(open_days)
    except Exception as e:
        logger.warning(f"获取交易日历失败，使用本地回退逻辑: {e}")

    # 回退：工作日取前一天，周六回退到周五，周日回退到周五
    today = datetime.now()
    if today.weekday() == 5:  # 周六
        latest_trading_date = today - timedelta(days=1)
    elif today.weekday() == 6:  # 周日
        latest_trading_date = today - timedelta(days=2)
    else:
        latest_trading_date = today - timedelta(days=1)
    return latest_trading_date.strftime('%Y%m%d')

def fetch_individual_stocks():
    """
    组件：个股列表日更任务

    功能：
    - 使用 Tushare 备用行情接口（bak_daily）按交易日获取全市场个股核心指标
    - 将数据映射到 IndividualStock 表中，支持批量新增与批量更新

    参数：
    - 无（内部按当前交易日 YYYYMMDD 拉取）

    返回值：
    - dict：{"status": "success|warning|error", "message": str}

    事件：
    - 外部数据源调用：tushare bak_daily
    - 数据库批处理：bulk_create / bulk_update
    - 记录日志统计与异常信息
    """
    logger.info("开始执行个股列表获取任务")
    
    try:
        # 从 Tushare 获取指定交易日的备用行情（覆盖全市场）
        # 使用统一的交易日推断逻辑，获取最近一个交易日（优先Tushare，失败本地回退）
        trade_date = _get_recent_trade_date()
        logger.info(f"从 Tushare 获取备用行情数据 trade_date={trade_date}")
        records = fetch_bak_daily(trade_date=trade_date)

        if not records:
            logger.warning("Tushare 备用行情数据为空")
            return {"status": "warning", "message": "Tushare 备用行情数据为空"}
        
        # 转换数据格式并批量保存到数据库
        from django.db import transaction
        
        # 获取现有股票代码
        existing_codes = set(IndividualStock.objects.values_list('code', flat=True))
        
        # 准备批量创建和更新的数据
        stocks_to_create = []
        stocks_to_update = []
        
        for row in records:
            ts_code = str(row.get('ts_code')) if row.get('ts_code') is not None else ''
            code = ts_code.split('.')[0] if ts_code else ''
            name = str(row.get('name')) if row.get('name') is not None else ''

            # 准备股票数据（用 tushare 字段映射至模型）
            stock_data = {
                'name': name,
                'industry': row.get('industry') if row.get('industry') is not None else None,
                'pe_ratio': float(row.get('pe')) if pd.notna(row.get('pe')) else None,
                'total_market_cap': float(row.get('total_mv')) if pd.notna(row.get('total_mv')) else None,
                'circulating_market_cap': float(row.get('float_mv')) if pd.notna(row.get('float_mv')) else None,
                # 价量与涨跌
                'latest_price': float(row.get('close')) if pd.notna(row.get('close')) else None,
                'change_percent': float(row.get('pct_change')) if pd.notna(row.get('pct_change')) else None,
                'change_amount': float(row.get('change')) if pd.notna(row.get('change')) else None,
                'volume': int(row.get('vol')) if pd.notna(row.get('vol')) else None,
                'amount': float(row.get('amount')) if pd.notna(row.get('amount')) else None,
                'amplitude': float(row.get('swing')) if pd.notna(row.get('swing')) else None,
                'high': float(row.get('high')) if pd.notna(row.get('high')) else None,
                'low': float(row.get('low')) if pd.notna(row.get('low')) else None,
                'open_price': float(row.get('open')) if pd.notna(row.get('open')) else None,
                'close_price': float(row.get('pre_close')) if pd.notna(row.get('pre_close')) else None,
                'volume_ratio': float(row.get('vol_ratio')) if pd.notna(row.get('vol_ratio')) else None,
                'turnover_rate': float(row.get('turn_over')) if pd.notna(row.get('turn_over')) else None,
                # tushare bak_daily 不提供以下字段，置空
                'pb_ratio': None,
                'price_change_speed': None,
                'change_5min': None,
                'change_60d': None,
                'change_ytd': None,
            }
            
            if code in existing_codes:
                # 准备更新数据（仅更新非空字段，避免覆盖已有有效值）
                update_data = {k: v for k, v in stock_data.items() if v is not None}
                if update_data:
                    stocks_to_update.append((code, update_data))
            else:
                # 准备创建数据（允许空字段，确保必填 code）
                stock_data['code'] = code
                stocks_to_create.append(IndividualStock(**stock_data))
        
        # 批量操作

        # 批量创建新股票
        if stocks_to_create:
            with transaction.atomic():
                IndividualStock.objects.bulk_create(stocks_to_create, batch_size=500)
                logger.info(f"批量创建了{len(stocks_to_create)}只新股票（Tushare bak_daily）")
        
        # 批量更新现有股票
        if stocks_to_update:
            # 组件说明：批量更新现有股票
            # 功能：按 code 将待更新字段聚合到对象后一次性 bulk_update
            # 参数：无（使用上文收集的 stocks_to_update）
            # 返回值：无（通过日志反馈）
            # 事件：数据库批量更新
            codes = [code for code, _ in stocks_to_update]
            objs = {obj.code: obj for obj in IndividualStock.objects.filter(code__in=codes)}
            fields_to_update = set()

            for code, data in stocks_to_update:
                obj = objs.get(code)
                if not obj:
                    continue
                for field, value in data.items():
                    setattr(obj, field, value)
                    fields_to_update.add(field)

            if objs and fields_to_update:
                with transaction.atomic():
                    IndividualStock.objects.bulk_update(list(objs.values()), list(fields_to_update), batch_size=500)
                logger.info(f"批量更新了{len(objs)}只现有股票，涉及字段数={len(fields_to_update)}（Tushare bak_daily）")
            else:
                logger.info("无可批量更新的现有股票或字段为空")
        
        stock_count = len(stocks_to_create) + len(stocks_to_update)
        
        logger.info(f"成功获取并保存{stock_count}只个股信息到数据库（Tushare bak_daily）")
        return {"status": "success", "message": f"成功获取并保存{stock_count}只个股信息到数据库（Tushare bak_daily）"}
        
    except Exception as e:
        logger.error(f"个股列表获取任务执行失败（Tushare bak_daily）: {str(e)}")
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
        stocks = IndividualStock.objects.filter()
        
        if not stocks.exists():
            # 如果数据库中没有个股数据，先获取个股列表
            logger.info("数据库中没有个股数据，先获取个股列表")
            return {"status": "error", "message": "数据库中没有个股数据，先获取个股列表"}
        stock_code_list = [stock for stock in stocks if stock.index_type is None]
        print(len(stock_code_list))
        # 更新所有个股的历史数据（最近30天）
        updated_stocks, updated_history = update_stock_history(stock_code_list=stock_code_list, days=10)
        
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
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        updated_stocks = 0
        updated_history = 0

        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()

        # 使用集合操作提高查询效率，避免使用distinct()
        # stock_code_list = set(IndividualStockDaily.objects.filter(
        #             date__gte=start_date_obj,
        #             date__lte=start_date_obj
        #         ).values_list('stock_id', flat=True))
        
        if not stock_code_list:
            logger.warning("需要更新的股票")
            return 0, 0
        
        # 遍历股票列表更新历史数据
        for stock in stock_code_list:
            # if stock.id in stock_code_list:
            #     print(f"股票 {stock.code} 已存在历史数据，无需更新")
            #     continue

            logger.info(f"开始更新股票 {stock.code} 的历史数据")
            try:
                # 获取指定日期范围内已有的历史数据日期（用于去重）
                existing_dates = set(IndividualStockDaily.objects.filter(
                    stock=stock,
                    date__gte=start_date_obj,
                    date__lte=end_date_obj
                ).values_list('date', flat=True))
                time.sleep(0.2)  # 避免请求过于频繁

                print(f"股票 {stock.code} 已存在的历史数据日期数量: {len(existing_dates)}")
                if len(existing_dates) > 1000:
                    logger.info(f"股票 {stock.code} 已存在所有历史数据，无需更新")
                    print(f"股票 {stock.code} 已存在所有历史数据，无需更新")
                    continue


                stock_code = judge_stock_type(stock.code)
                daily_data_list = fetch_stock_daily_data(stock_code, start_date, end_date)
                
                print(f"股票 {stock.code} 从akshare获取到的历史数据数量: {len(daily_data_list)}")
                if not daily_data_list:
                    logger.warning(f"获取股票 {stock.code} 历史行情数据为空")
                    continue
                
                # 准备批量创建的数据
                records_to_create = []
                # 注：现有记录的“批量更新”逻辑在原实现中已注释，这里维持不变以避免额外写压力
                
                for row in daily_data_list:
                    # 使用近似比较而不是精确比较，避免浮点数精度问题
                    # 如果开盘价、收盘价、最高价和最低价非常接近（差异小于0.000001），则认为它们相等
                    if abs(row.open - row.close) < 0.000001 and abs(row.open - row.high) < 0.000001 and abs(row.open - row.low) < 0.000001:
                        continue
                    # 将日期统一为 date 对象
                    date_obj = datetime.strptime(str(row.date), '%Y-%m-%d').date()
                    
                    stock_daily_data = row.to_model_dict()
                    
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


def fetch_stock_daily_data(stock_code: str, start_date: str = None, end_date: str = None) -> List[StockDailyData]:
    """
    获取指定股票在指定日期范围的日频数据。

    :param stock_code: 股票代码，例如：sh.600000
    :param start_date: 开始日期，格式：YYYY-MM-DD，默认为当前日期前30天
    :param end_date: 结束日期，格式：YYYY-MM-DD，默认为当前日期
    :return: StockDailyData对象列表
    """
    #### 登陆系统 ####
    lg = bs.login()
    # 显示登陆返回信息
    print('login respond error_code:'+lg.error_code)
    print('login respond  error_msg:'+lg.error_msg)

    # 如果未指定日期范围，默认查询最近30天数据
    if not start_date or not end_date:
        from datetime import datetime, timedelta
        today = datetime.now().strftime('%Y-%m-%d')
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        start_date = start_date or thirty_days_ago
        end_date = end_date or today
    
    #### 获取沪深A股历史K线数据 ####
    # 详细指标参数，参见"历史行情指标参数"章节；"分钟线"参数与"日线"参数不同。"分钟线"不包含指数。
    # 分钟线指标：date,time,code,open,high,low,close,volume,amount,adjustflag
    # 周月线指标：date,code,open,high,low,close,volume,amount,adjustflag,turn,pctChg
    # 添加超时处理
    max_retries = 3
    retry_count = 0
    timeout_seconds = 10
    
    while retry_count < max_retries:
        try:
            import signal
            from contextlib import contextmanager
            
            @contextmanager
            def timeout_handler(seconds):
                def handle_timeout(signum, frame):
                    raise TimeoutError(f"查询超时，已经等待{seconds}秒")
                
                # 设置信号处理器
                original_handler = signal.getsignal(signal.SIGALRM)
                signal.signal(signal.SIGALRM, handle_timeout)
                
                # 设置闹钟
                signal.alarm(seconds)
                try:
                    yield
                finally:
                    # 取消闹钟并恢复原始处理器
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, original_handler)
            
            # 使用超时处理器执行查询
            with timeout_handler(timeout_seconds):
                rs = bs.query_history_k_data_plus(stock_code,
                    "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST",
                    start_date=start_date, end_date=end_date,
                    frequency="d", adjustflag="2")
                
                print('query_history_k_data_plus respond error_code:'+rs.error_code)
                print('query_history_k_data_plus respond  error_msg:'+rs.error_msg)
                
                # 如果查询成功，跳出循环
                if rs.error_code == '0':
                    break
                else:
                    # 如果查询失败但不是超时问题，也跳出循环
                    print(f"查询失败，错误码: {rs.error_code}, 错误信息: {rs.error_msg}")
                    break
                    
        except TimeoutError as e:
            retry_count += 1
            print(f"尝试 {retry_count}/{max_retries}: {str(e)}")
            if retry_count >= max_retries:
                print(f"达到最大重试次数 {max_retries}，查询失败")
                # 创建一个空的结果集
                from baostock.data.resultset import ResultSet
                rs = ResultSet()
                rs.error_code = '1'
                rs.error_msg = f'查询超时，已重试 {max_retries} 次'
        except Exception as e:
            retry_count += 1
            print(f"尝试 {retry_count}/{max_retries}: 发生异常 - {str(e)}")
            if retry_count >= max_retries:
                print(f"达到最大重试次数 {max_retries}，查询失败")
                # 创建一个空的结果集
                from baostock.data.resultset import ResultSet
                rs = ResultSet()
                rs.error_code = '1'
                rs.error_msg = f'查询发生异常: {str(e)}'

    #### 处理结果集 ####
    data_list = []
    while (rs.error_code == '0') & rs.next():
        # 获取一条记录，将记录转换为StockDailyData对象
        row_data = rs.get_row_data()
        try:
            stock_data = StockDailyData.from_baostock_row(row_data)
            data_list.append(stock_data)
        except Exception as e:
            print(f"处理数据行时出错: {e}")
            print(f"错误数据行: {row_data}")
    
    #### 登出系统 ####
    bs.logout()
    
    return data_list

def judge_stock_type(stock_code: str) -> str:
    """
    判断股票代码所属的交易所。

    :param stock_code: 股票代码，例如：000001
    :return: 交易所前缀，例如：sh. 或 sz.
    """
    # 指数股票
    if stock_code.startswith(('sh000', 'sz399')):
        return "sh." + stock_code[2:]
    elif stock_code.startswith(('sz399',)):
        return "sz." + stock_code[2:]

    
    # 普通股票
    if stock_code.startswith(('60', '68')):
        return "sh." + stock_code
    elif stock_code.startswith(('00', '30', '002', '003')):
        return "sz." + stock_code
    elif stock_code.startswith(('83', '87', '88', '82')):
        return "bj." + stock_code  # 北交所股票
    else:
        return "sh." + stock_code  # 默认使用上海交易所


def fetch_stock_weekly_data(stock_code: str, start_date: str = None, end_date: str = None) -> List[StockWeeklyData]:
    """
    获取指定股票在指定日期范围的周频数据。

    功能：
    - 通过 baostock 的 `query_history_k_data_plus` 接口，频率设置为 `w`，获取周线数据
    - 使用统一解析类 `StockWeeklyData` 进行行数据转换

    参数：
    - stock_code(str): 股票代码，例如 `sh.600000`
    - start_date(str): 开始日期，`YYYY-MM-DD`，不传则默认近30天
    - end_date(str): 结束日期，`YYYY-MM-DD`，不传则默认今天

    返回值：
    - List[StockWeeklyData]: 周频数据对象列表

    事件：
    - 外部数据源请求：baostock 登录/查询/登出
    - 超时与重试控制，最大重试3次
    """
    lg = bs.login()
    print('login respond error_code:'+lg.error_code)
    print('login respond  error_msg:'+lg.error_msg)

    if not start_date or not end_date:
        today = datetime.now().strftime('%Y-%m-%d')
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        start_date = start_date or thirty_days_ago
        end_date = end_date or today

    max_retries = 3
    retry_count = 0
    timeout_seconds = 10
    rs = None

    while retry_count < max_retries:
        try:
            import signal
            from contextlib import contextmanager

            @contextmanager
            def timeout_handler(seconds):
                def handle_timeout(signum, frame):
                    raise TimeoutError(f"查询超时，已经等待{seconds}秒")
                original_handler = signal.getsignal(signal.SIGALRM)
                signal.signal(signal.SIGALRM, handle_timeout)
                signal.alarm(seconds)
                try:
                    yield
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, original_handler)

            with timeout_handler(timeout_seconds):
                rs = bs.query_history_k_data_plus(
                    stock_code,
                    "date,code,open,high,low,close,volume,amount,adjustflag,turn,pctChg",
                    start_date=start_date,
                    end_date=end_date,
                    frequency="w",
                    adjustflag="2"
                )

                print('query_history_k_data_plus respond error_code:'+rs.error_code)
                print('query_history_k_data_plus respond  error_msg:'+rs.error_msg)

                if rs.error_code == '0':
                    break
                else:
                    print(f"查询失败，错误码: {rs.error_code}, 错误信息: {rs.error_msg}")
                    break

        except TimeoutError as e:
            retry_count += 1
            print(f"尝试 {retry_count}/{max_retries}: {str(e)}")
            if retry_count >= max_retries:
                print(f"达到最大重试次数 {max_retries}，查询失败")
                from baostock.data.resultset import ResultSet
                rs = ResultSet()
                rs.error_code = '1'
                rs.error_msg = f'查询超时，已重试 {max_retries} 次'
        except Exception as e:
            retry_count += 1
            print(f"尝试 {retry_count}/{max_retries}: 发生异常 - {str(e)}")
            if retry_count >= max_retries:
                print(f"达到最大重试次数 {max_retries}，查询失败")
                from baostock.data.resultset import ResultSet
                rs = ResultSet()
                rs.error_code = '1'
                rs.error_msg = f'查询发生异常: {str(e)}'

    data_list: List[StockWeeklyData] = []
    if rs is not None:
        while (rs.error_code == '0') & rs.next():
            row_data = rs.get_row_data()
            try:
                stock_data = StockWeeklyData.from_baostock_row(row_data)
                data_list.append(stock_data)
            except Exception as e:
                print(f"处理周频数据行时出错: {e}")
                print(f"错误数据行: {row_data}")

    bs.logout()

    return data_list


def update_stock_weekly_history(
    stock_code_list: list = None,
    days: int = 30,
    batch_size: int = 300,
    sleep_seconds: float = 0.03,
    ignore_conflicts: bool = True,
    order_by_date: bool = True
) -> Tuple[int, int]:
    """
    批量更新股票周频历史数据。

    功能：
    - 迭代股票列表，在指定日期范围内抓取周频数据并写入 `IndividualStockWeekly`
    - 按批量进行 `bulk_create`，可选忽略冲突，支持轻微节流

    参数：
    - stock_code_list(list): 股票对象列表（`IndividualStock`），若为 None 则返回0
    - days(int): 回溯天数（会转换为日期范围）
    - batch_size(int): 批量写入大小
    - sleep_seconds(float): 批次间休眠秒数
    - ignore_conflicts(bool): 是否忽略唯一冲突
    - order_by_date(bool): 是否按日期排序后写入

    返回值：
    - Tuple[int, int]: (有新增数据的股票数, 新增的历史数据条数)

    事件：
    - 日志记录、数据库批量插入事务、异常捕获
    """
    try:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        updated_stocks = 0
        updated_history = 0

        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()

        if not stock_code_list:
            logger.warning("需要更新的股票")
            return 0, 0

        for stock in stock_code_list:
            logger.info(f"开始更新股票 {stock.code} 的周频历史数据")
            try:
                existing_dates = set(IndividualStockWeekly.objects.filter(
                    stock=stock,
                    date__gte=start_date_obj,
                    date__lte=end_date_obj
                ).values_list('date', flat=True))
                time.sleep(0.2)

                stock_code = judge_stock_type(stock.code)
                weekly_data_list = fetch_stock_weekly_data(stock_code, start_date, end_date)

                if not weekly_data_list:
                    logger.warning(f"获取股票 {stock.code} 周频历史数据为空")
                    continue

                records_to_create = []
                for row in weekly_data_list:
                    if abs(row.open - row.close) < 0.000001 and abs(row.open - row.high) < 0.000001 and abs(row.open - row.low) < 0.000001:
                        continue
                    date_obj = datetime.strptime(str(row.date), '%Y-%m-%d').date()
                    stock_weekly_data = row.to_model_dict()

                    if date_obj not in existing_dates:
                        stock_weekly_data['stock'] = stock
                        stock_weekly_data['date'] = date_obj
                        records_to_create.append(IndividualStockWeekly(**stock_weekly_data))

                if order_by_date and records_to_create:
                    try:
                        records_to_create.sort(key=lambda obj: obj.date)
                    except Exception:
                        pass

                created_total_for_stock = 0
                if records_to_create:
                    total = len(records_to_create)
                    batches = (total + batch_size - 1) // batch_size
                    for i in range(0, total, batch_size):
                        chunk = records_to_create[i:i + batch_size]
                        try:
                            with transaction.atomic():
                                inserted = IndividualStockWeekly.objects.bulk_create(
                                    chunk,
                                    batch_size=batch_size,
                                    ignore_conflicts=ignore_conflicts
                                )
                            created_total_for_stock += len(inserted)
                        except Exception as be:
                            logger.error(f"股票 {stock.code} 周频第 {i//batch_size + 1}/{batches} 个批次插入失败: {be}")
                        if sleep_seconds > 0:
                            time.sleep(sleep_seconds)

                if created_total_for_stock > 0:
                    updated_stocks += 1
                    updated_history += created_total_for_stock
                    logger.info(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 完成股票 {stock.code} 的周频数据写入: 新增 {created_total_for_stock} 条")
            except Exception as e:
                logger.error(f"更新股票 {stock.code} 周频历史数据失败: {str(e)}")

        logger.info(f"更新股票周频历史数据完成: 更新 {updated_stocks} 只股票，新增 {updated_history} 条历史数据")
        return updated_stocks, updated_history
    except Exception as e:
        logger.error(f"更新股票周频历史数据失败: {str(e)}")
        return 0, 0


def update_individual_stock_weekly_data():
    """
    更新所有个股的周频数据
    功能：每天/每周定时执行，批量抓取并入库周频数据（不含指数）
    参数：无
    返回值：
    - dict：包含 status 与 message 的结果字典
    事件：
    - 读取个股列表、过滤指数、调用批量入库函数并记录日志
    """
    logger.info("开始执行个股周频数据更新任务")

    try:
        stocks = IndividualStock.objects.filter()
        if not stocks.exists():
            logger.info("数据库中没有个股数据，先获取个股列表")
            return {"status": "error", "message": "数据库中没有个股数据，先获取个股列表"}

        stock_code_list = [stock for stock in stocks if stock.index_type is None]
        updated_stocks, updated_history = update_stock_weekly_history(stock_code_list=stock_code_list, days=3000)

        logger.info(f"个股周频数据更新任务完成，更新: {updated_stocks}只个股，{updated_history}条历史数据")
        return {
            "status": "success",
            "message": f"个股周频数据更新任务完成，更新: {updated_stocks}只个股，{updated_history}条历史数据"
        }
    except Exception as e:
        logger.error(f"个股周频数据更新任务执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}

def fetch_performance_report(date: str):
    """
    从akshare获取指定日期的业绩快报数据并保存到数据库
    
    Args:
        date: 报告期，格式：YYYYMMDD，如"20200331"
        
    Returns:
        dict: 包含status和message的结果字典
    """
    logger.info(f"开始执行业绩快报数据获取任务: {date}")
    
    try:
        # 获取要更新的股票列表
        stocks = IndividualStock.objects.all()
        stock_dict = {stock.code: stock for stock in stocks}
        
        if not stocks.exists():
            logger.warning("没有找到需要更新的股票")
            return

        # 从akshare获取数据
        logger.info(f"从akshare获取业绩快报数据: {date}")
        df = ak.stock_yjbb_em(date=date)
        
        if df is None or df.empty:
            logger.warning(f"未获取到业绩快报数据: {date}")
            return {"status": "warning", "message": f"未获取到业绩快报数据: {date}"}
        
        # 处理并保存数据
        created_count = 0
        failed_count = 0
        
        # 收集需要创建的数据
        reports_to_create = []
        
        with transaction.atomic():
            for _, row in df.iterrows():
                try:
                    stock_code = str(row['股票代码'])
                    stock = stock_dict.get(stock_code, None)
                    if not stock:
                        logger.debug(f"股票记录不存在，跳过: {stock_code}")
                        failed_count += 1
                        continue
                    
                    # 解析数据
                    report_data = _parse_performance_data(row, date)
                    
                    # 添加到批量创建列表
                    reports_to_create.append(PerformanceReport(
                        stock=stock,
                        report_date=date,
                        **report_data
                    ))
                        
                except Exception as e:
                    logger.error(f"处理业绩快报数据失败 {stock_code}: {str(e)}")
                    failed_count += 1
                    continue
            
            # 批量创建
            if reports_to_create:
                PerformanceReport.objects.bulk_create(reports_to_create, batch_size=500)
                created_count = len(reports_to_create)
        
        logger.info(f"业绩快报数据获取任务完成: 新增{created_count}条，跳过{failed_count}条")
        
        return {
            "status": "success" if failed_count == 0 else "partial",
            "message": f"业绩快报数据获取任务完成: 新增{created_count}条，跳过{failed_count}条",
            "created": created_count,
            "failed": failed_count
        }
        
    except Exception as e:
        logger.error(f"业绩快报数据获取任务执行失败 {date}: {str(e)}")
        return {"status": "error", "message": str(e)}



def _parse_performance_data(row, date: str) -> dict:
    """
    解析业绩快报数据
    
    Args:
        row: pandas行数据
        date: 报告期
        
    Returns:
        dict: 解析后的数据字典
    """
    def safe_float(value):
        """安全转换为浮点数"""
        if pd.isna(value) or value == '' or value == '-':
            return None
        try:
            return round(float(value), 2)
        except (ValueError, TypeError):
            return None
    
    def safe_str(value):
        """安全转换为字符串"""
        if pd.isna(value) or value == '':
            return None
        return str(value)
    
    def parse_growth_rate(value):
        """解析增长率，去除%符号，并处理极端值"""
        if pd.isna(value) or value == '' or value == '-':
            return None
        try:
            str_value = str(value)
            if str_value.endswith('%'):
                float_value = float(str_value[:-1])
            else:
                float_value = float(str_value)
            
            # 限制值在数据库字段允许的范围内
            # DecimalField(max_digits=12, decimal_places=4)的实际安全范围应更小
            max_allowed = 9999.9999  # 更保守的限制，确保不会超出范围
            min_allowed = -max_allowed
            
            if float_value > max_allowed:
                logger.warning(f"增长率值过大，已限制: {float_value} -> {max_allowed}")
                float_value = max_allowed
            elif float_value < min_allowed:
                logger.warning(f"增长率值过小，已限制: {float_value} -> {min_allowed}")
                float_value = min_allowed
                
            return round(float_value, 2)
        except (ValueError, TypeError) as e:
            logger.error(f"解析增长率失败: {value}, 错误: {str(e)}")
            return None
    
    return {
        'earnings_per_share': safe_float(row.get('每股收益')),
        'operating_revenue': safe_float(row.get('营业总收入-营业总收入')),
        'operating_revenue_growth_rate': parse_growth_rate(row.get('营业总收入-同比增长')),
        'operating_revenue_quarter_growth': parse_growth_rate(row.get('营业总收入-季度环比增长')),
        'net_profit': safe_float(row.get('净利润-净利润')),
        'net_profit_growth_rate': parse_growth_rate(row.get('净利润-同比增长')),
        'net_profit_quarter_growth': parse_growth_rate(row.get('净利润-季度环比增长')),
        'net_assets_per_share': safe_float(row.get('每股净资产')),
        'roe': safe_float(row.get('净资产收益率')),
        'operating_cash_flow_per_share': safe_float(row.get('每股经营现金流量')),
        'gross_profit_margin': safe_float(row.get('销售毛利率')),
        'industry': safe_str(row.get('所处行业')),
        'announcement_date': safe_str(row.get('最新公告日期')),
    }


def del_error_data():
    """
    删除数据列表中的错误数据行。
    """
    # 获取要更新的股票列表
    stocks = IndividualStock.objects.all()
    
    if not stocks.exists():
        logger.warning("没有找到需要更新的股票")
        return 0, 0
    cnt = 1
    # 遍历股票列表更新历史数据
    for stock in stocks:
        stock_type = judge_stock_type(stock.code)
        if stock_type != "sh.":
            continue
        cnt += 1
        IndividualStockDaily.objects.filter(stock=stock).delete()
        logger.info(f"删除股票 {stock.code} 的错误数据")

        time.sleep(0.05)
    
    print(f"删除了 {cnt} 只股票的错误数据")


def fetch_all_performance_reports(start_year=2015, end_date='20240930'):
    """
    获取从指定年份开始到指定日期的所有季报、中报、三季报和年报数据
    
    Args:
        start_year: 开始年份，默认2015年
        end_date: 结束日期，格式YYYYMMDD，默认20240930
        
    Returns:
        dict: 包含status和message的结果字典
    """
    logger.info(f"开始批量获取从{start_year}年到{end_date}的业绩报告数据")
    
    # 生成所有季度报告日期
    report_dates = []
    end_year = int(end_date[:4])
    end_quarter = int(end_date[4:6]) // 3
    
    for year in range(start_year, end_year + 1):
        # 对于每年，添加四个季度的报告日期
        quarters = [
            f"{year}0331",  # 一季报
            f"{year}0630",  # 中报
            f"{year}0930",  # 三季报
            f"{year}1231"   # 年报
        ]
        
        # 如果是结束年份，只添加到指定季度
        if year == end_year:
            quarters = quarters[:end_quarter]
            
        report_dates.extend(quarters)
    
    # 按时间顺序排序（从早到晚）
    report_dates.sort()
    
    total_created = 0
    total_failed = 0
    results = []
    
    for date in report_dates:
        logger.info(f"获取 {date} 的业绩报告数据")
        try:
            result = fetch_performance_report(date)
            if result and isinstance(result, dict):
                total_created += result.get('created', 0)
                total_failed += result.get('failed', 0)
                results.append(result)
            # 添加延时，避免频繁请求
            time.sleep(5)
        except Exception as e:
            logger.error(f"获取 {date} 业绩报告数据失败: {str(e)}")
            results.append({"status": "error", "date": date, "message": str(e)})
    
    summary = {
        "status": "success" if total_failed == 0 else "partial",
        "message": f"批量获取业绩报告完成: 共处理{len(report_dates)}个报告期，新增{total_created}条，失败{total_failed}条",
        "total_created": total_created,
        "total_failed": total_failed,
        "details": results
    }
    
    logger.info(summary["message"])
    return summary

def fetch_balance_sheet(date: str):
    """
    从akshare获取指定日期的资产负债表数据并保存到数据库
    
    Args:
        date: 报告期，格式：YYYYMMDD，如"20200331"
        
    Returns:
        dict: 包含status和message的结果字典
    """
    logger.info(f"开始执行资产负债表数据获取任务: {date}")
    
    try:
        # 获取要更新的股票列表
        stocks = IndividualStock.objects.all()
        stock_dict = {stock.code: stock for stock in stocks}
        
        if not stocks.exists():
            logger.warning("没有找到需要更新的股票")
            return {"status": "warning", "message": "没有找到需要更新的股票"}

        # 从akshare获取数据
        logger.info(f"从akshare获取资产负债表数据: {date}")
        df = ak.stock_zcfz_em(date=date)
        
        if df is None or df.empty:
            logger.warning(f"未获取到资产负债表数据: {date}")
            return {"status": "warning", "message": f"未获取到资产负债表数据: {date}"}
        
        # 处理并保存数据
        created_count = 0
        failed_count = 0
        
        # 收集需要创建的数据
        balance_sheets_to_create = []
        
        with transaction.atomic():
            for _, row in df.iterrows():
                try:
                    stock_code = str(row['股票代码'])
                    stock = stock_dict.get(stock_code, None)
                    if not stock:
                        logger.debug(f"股票记录不存在，跳过: {stock_code}")
                        failed_count += 1
                        continue
                    
                    # 解析数据
                    balance_sheet_data = _parse_balance_sheet_data(row, date)
                    
                    # 添加到批量创建列表
                    balance_sheets_to_create.append(BalanceSheet(
                        stock=stock,
                        report_date=date,
                        **balance_sheet_data
                    ))
                        
                except Exception as e:
                    logger.error(f"处理资产负债表数据失败 {stock_code}: {str(e)}")
                    failed_count += 1
                    continue
            
            # 批量创建
            if balance_sheets_to_create:
                BalanceSheet.objects.bulk_create(balance_sheets_to_create, batch_size=500, ignore_conflicts=True)
                created_count = len(balance_sheets_to_create)
        
        logger.info(f"资产负债表数据获取任务完成: 新增{created_count}条，跳过{failed_count}条")
        
        return {
            "status": "success" if failed_count == 0 else "partial",
            "message": f"资产负债表数据获取任务完成: 新增{created_count}条，跳过{failed_count}条",
            "created": created_count,
            "failed": failed_count
        }
        
    except Exception as e:
        logger.error(f"资产负债表数据获取任务执行失败 {date}: {str(e)}")
        return {"status": "error", "message": str(e)}


def fetch_income_statement(date: str):
    """
    从akshare获取指定日期的利润表数据并保存到数据库
    
    Args:
        date: 报告期，格式：YYYYMMDD，如"20200331"
        
    Returns:
        dict: 包含status和message的结果字典
    """
    logger.info(f"开始执行利润表数据获取任务: {date}")
    
    try:
        # 获取要更新的股票列表
        stocks = IndividualStock.objects.all()
        stock_dict = {stock.code: stock for stock in stocks}
        
        if not stocks.exists():
            logger.warning("没有找到需要更新的股票")
            return {"status": "warning", "message": "没有找到需要更新的股票"}

        # 从akshare获取数据
        logger.info(f"从akshare获取利润表数据: {date}")
        df = ak.stock_lrb_em(date=date)
        
        if df is None or df.empty:
            logger.warning(f"未获取到利润表数据: {date}")
            return {"status": "warning", "message": f"未获取到利润表数据: {date}"}
        
        # 处理并保存数据
        created_count = 0
        failed_count = 0
        
        # 收集需要创建的数据
        income_statements_to_create = []
        
        with transaction.atomic():
            for _, row in df.iterrows():
                try:
                    stock_code = str(row['股票代码'])
                    stock = stock_dict.get(stock_code, None)
                    if not stock:
                        logger.debug(f"股票记录不存在，跳过: {stock_code}")
                        failed_count += 1
                        continue
                    
                    # 解析数据
                    income_statement_data = _parse_income_statement_data(row, date)
                    
                    # 添加到批量创建列表
                    income_statements_to_create.append(IncomeStatement(
                        stock=stock,
                        report_date=date,
                        **income_statement_data
                    ))
                        
                except Exception as e:
                    logger.error(f"处理利润表数据失败 {stock_code}: {str(e)}")
                    failed_count += 1
                    continue
            
            # 批量创建
            if income_statements_to_create:
                IncomeStatement.objects.bulk_create(income_statements_to_create, batch_size=500)
                created_count = len(income_statements_to_create)
        
        logger.info(f"利润表数据获取任务完成: 新增{created_count}条，跳过{failed_count}条")
        
        return {
            "status": "success" if failed_count == 0 else "partial",
            "message": f"利润表数据获取任务完成: 新增{created_count}条，跳过{failed_count}条",
            "created": created_count,
            "failed": failed_count
        }
        
    except Exception as e:
        logger.error(f"利润表数据获取任务执行失败 {date}: {str(e)}")
        return {"status": "error", "message": str(e)}


def fetch_cash_flow_statement(date: str):
    """
    从akshare获取指定日期的现金流量表数据并保存到数据库
    
    Args:
        date: 报告期，格式：YYYYMMDD，如"20200331"
        
    Returns:
        dict: 包含status和message的结果字典
    """
    logger.info(f"开始执行现金流量表数据获取任务: {date}")
    
    try:
        # 获取要更新的股票列表
        stocks = IndividualStock.objects.all()
        stock_dict = {stock.code: stock for stock in stocks}
        
        if not stocks.exists():
            logger.warning("没有找到需要更新的股票")
            return {"status": "warning", "message": "没有找到需要更新的股票"}

        # 从akshare获取数据
        logger.info(f"从akshare获取现金流量表数据: {date}")
        df = ak.stock_xjll_em(date=date)
        
        if df is None or df.empty:
            logger.warning(f"未获取到现金流量表数据: {date}")
            return {"status": "warning", "message": f"未获取到现金流量表数据: {date}"}
        
        # 处理并保存数据
        created_count = 0
        failed_count = 0
        
        # 收集需要创建的数据
        cash_flow_statements_to_create = []
        
        with transaction.atomic():
            for _, row in df.iterrows():
                try:
                    stock_code = str(row['股票代码'])
                    stock = stock_dict.get(stock_code, None)
                    if not stock:
                        logger.debug(f"股票记录不存在，跳过: {stock_code}")
                        failed_count += 1
                        continue
                    
                    # 解析数据
                    cash_flow_statement_data = _parse_cash_flow_statement_data(row, date)
                    
                    # 添加到批量创建列表
                    cash_flow_statements_to_create.append(CashFlowStatement(
                        stock=stock,
                        report_date=date,
                        **cash_flow_statement_data
                    ))
                        
                except Exception as e:
                    logger.error(f"处理现金流量表数据失败 {stock_code}: {str(e)}")
                    failed_count += 1
                    continue
            
            # 批量创建
            if cash_flow_statements_to_create:
                CashFlowStatement.objects.bulk_create(cash_flow_statements_to_create, batch_size=500, ignore_conflicts=True)
                created_count = len(cash_flow_statements_to_create)
        
        logger.info(f"现金流量表数据获取任务完成: 新增{created_count}条，跳过{failed_count}条")
        
        return {
            "status": "success" if failed_count == 0 else "partial",
            "message": f"现金流量表数据获取任务完成: 新增{created_count}条，跳过{failed_count}条",
            "created": created_count,
            "failed": failed_count
        }
        
    except Exception as e:
        logger.error(f"现金流量表数据获取任务执行失败 {date}: {str(e)}")
        return {"status": "error", "message": str(e)}


def _parse_balance_sheet_data(row, date: str) -> dict:
    """
    解析资产负债表数据
    
    Args:
        row: pandas行数据
        date: 报告期
        
    Returns:
        dict: 解析后的数据字典
    """
    def safe_float(value):
        """安全转换为浮点数"""
        if pd.isna(value) or value == '' or value == '-':
            return None
        try:
            return round(float(value), 2)
        except (ValueError, TypeError):
            return None
    
    def safe_str(value):
        """安全转换为字符串"""
        if pd.isna(value) or value == '':
            return None
        return str(value)
    
    def parse_growth_rate(value):
        """解析增长率，去除%符号，并处理极端值"""
        if pd.isna(value) or value == '' or value == '-':
            return None
        try:
            str_value = str(value)
            if str_value.endswith('%'):
                float_value = float(str_value[:-1])
            else:
                float_value = float(str_value)
            
            # 限制值在数据库字段允许的范围内
            max_allowed = 9999.9999
            min_allowed = -max_allowed
            
            if float_value > max_allowed:
                logger.warning(f"增长率值过大，已限制: {float_value} -> {max_allowed}")
                float_value = max_allowed
            elif float_value < min_allowed:
                logger.warning(f"增长率值过小，已限制: {float_value} -> {min_allowed}")
                float_value = min_allowed
                
            return round(float_value, 2)
        except (ValueError, TypeError) as e:
            logger.error(f"解析增长率失败: {value}, 错误: {str(e)}")
            return None
    
    return {
        'monetary_funds': safe_float(row.get('资产-货币资金')),  # 货币资金(元)
        'accounts_receivable': safe_float(row.get('资产-应收账款')),  # 应收账款(元)
        'inventory': safe_float(row.get('资产-存货')),  # 存货(元)
        'total_assets': safe_float(row.get('资产-总资产')),  # 总资产(元)
        'total_assets_growth_rate': parse_growth_rate(row.get('资产-总资产同比')),  # 总资产同比增长率(%)
        'accounts_payable': safe_float(row.get('负债-应付账款')),  # 应付账款(元)
        'total_liabilities': safe_float(row.get('负债-总负债')),  # 总负债(元)
        'advance_receipts': safe_float(row.get('负债-预收账款')),  # 预收账款(元)
        'total_liabilities_growth_rate': parse_growth_rate(row.get('负债-总负债同比')),  # 总负债同比增长率(%)
        'debt_to_asset_ratio': safe_float(row.get('资产负债率')),  # 资产负债率(%)
        'total_equity': safe_float(row.get('股东权益合计')),  # 股东权益合计(元)
        'announcement_date': safe_str(row.get('公告日期')),  # 公告日期
    }



def _parse_income_statement_data(row, date: str) -> dict:
    """
    解析利润表数据
    
    Args:
        row: pandas行数据
        date: 报告期
        
    Returns:
        dict: 解析后的数据字典
    """
    def safe_float(value):
        """安全转换为浮点数"""
        if pd.isna(value) or value == '' or value == '-':
            return None
        try:
            return round(float(value), 2)
        except (ValueError, TypeError):
            return None
    
    def safe_str(value):
        """安全转换为字符串"""
        if pd.isna(value) or value == '':
            return None
        return str(value)
    
    def parse_growth_rate(value):
        """解析增长率，去除%符号，并处理极端值"""
        if pd.isna(value) or value == '' or value == '-':
            return None
        try:
            str_value = str(value)
            if str_value.endswith('%'):
                float_value = float(str_value[:-1])
            else:
                float_value = float(str_value)
            
            # 限制值在数据库字段允许的范围内
            max_allowed = 9999.9999
            min_allowed = -max_allowed
            
            if float_value > max_allowed:
                logger.warning(f"增长率值过大，已限制: {float_value} -> {max_allowed}")
                float_value = max_allowed
            elif float_value < min_allowed:
                logger.warning(f"增长率值过小，已限制: {float_value} -> {min_allowed}")
                float_value = min_allowed
                
            return round(float_value, 2)
        except (ValueError, TypeError) as e:
            logger.error(f"解析增长率失败: {value}, 错误: {str(e)}")
            return None
    
    return {
        'net_profit': safe_float(row.get('净利润')),  # 净利润(元)
        'net_profit_growth_rate': parse_growth_rate(row.get('净利润同比')),  # 净利润同比增长率(%)
        'operating_revenue': safe_float(row.get('营业总收入')),  # 营业总收入(元)
        'operating_revenue_growth_rate': parse_growth_rate(row.get('营业总收入同比')),  # 营业总收入同比增长率(%)
        'operating_expenses': safe_float(row.get('营业总支出-营业支出')),  # 营业支出(元)
        'sales_expenses': safe_float(row.get('营业总支出-销售费用')),  # 销售费用(元)
        'management_expenses': safe_float(row.get('营业总支出-管理费用')),  # 管理费用(元)
        'financial_expenses': safe_float(row.get('营业总支出-财务费用')),  # 财务费用(元)
        'total_operating_expenses': safe_float(row.get('营业总支出-营业总支出')),  # 营业总支出(元)
        'operating_profit': safe_float(row.get('营业利润')),  # 营业利润(元)
        'total_profit': safe_float(row.get('利润总额')),  # 利润总额(元)
        'announcement_date': safe_str(row.get('公告日期')),  # 公告日期
    }


def _parse_cash_flow_statement_data(row, date: str) -> dict:
    """
    解析现金流量表数据
    
    Args:
        row: pandas行数据
        date: 报告期
        
    Returns:
        dict: 解析后的数据字典
    """
    def safe_float(value):
        """安全转换为浮点数"""
        if pd.isna(value) or value == '' or value == '-':
            return None
        try:
            return round(float(value), 2)
        except (ValueError, TypeError):
            return None
    
    def safe_str(value):
        """安全转换为字符串"""
        if pd.isna(value) or value == '':
            return None
        return str(value)
    
    def parse_growth_rate(value):
        """解析增长率，去除%符号，并处理极端值"""
        if pd.isna(value) or value == '' or value == '-':
            return None
        try:
            str_value = str(value)
            if str_value.endswith('%'):
                float_value = float(str_value[:-1])
            else:
                float_value = float(str_value)
            
            # 限制值在数据库字段允许的范围内
            max_allowed = 9999.9999
            min_allowed = -max_allowed
            
            if float_value > max_allowed:
                logger.warning(f"增长率值过大，已限制: {float_value} -> {max_allowed}")
                float_value = max_allowed
            elif float_value < min_allowed:
                logger.warning(f"增长率值过小，已限制: {float_value} -> {min_allowed}")
                float_value = min_allowed
                
            return round(float_value, 2)
        except (ValueError, TypeError) as e:
            logger.error(f"解析增长率失败: {value}, 错误: {str(e)}")
            return None
    
    return {
        'net_cash_flow': safe_float(row.get('净现金流-净现金流')),
        'net_cash_flow_growth_rate': parse_growth_rate(row.get('净现金流-同比增长')),
        'operating_cash_flow': safe_float(row.get('经营性现金流-现金流量净额')),
        'operating_cash_flow_ratio': parse_growth_rate(row.get('经营性现金流-净现金流占比')),
        'investing_cash_flow': safe_float(row.get('投资性现金流-现金流量净额')),
        'investing_cash_flow_ratio': parse_growth_rate(row.get('投资性现金流-净现金流占比')),
        'financing_cash_flow': safe_float(row.get('融资性现金流-现金流量净额')),
        'financing_cash_flow_ratio': parse_growth_rate(row.get('融资性现金流-净现金流占比')),
        'announcement_date': safe_str(row.get('公告日期')),
    }


def fetch_all_financial_statements(start_year=2015, end_date='20240930'):
    """
    获取从指定年份开始到指定日期的所有财务报表数据（资产负债表、利润表、现金流量表）
    
    Args:
        start_year: 开始年份，默认2015年
        end_date: 结束日期，格式YYYYMMDD，默认20240930
        
    Returns:
        dict: 包含status和message的结果字典
    """
    logger.info(f"开始批量获取从{start_year}年到{end_date}的财务报表数据")
    
    # 生成所有季度报告日期
    report_dates = []
    end_year = int(end_date[:4])
    end_quarter = int(end_date[4:6]) // 3
    
    for year in range(start_year, end_year + 1):
        # 对于每年，添加四个季度的报告日期
        quarters = [
            f"{year}0331",  # 一季报
            f"{year}0630",  # 中报
            f"{year}0930",  # 三季报
            f"{year}1231"   # 年报
        ]
        
        # 如果是结束年份，只添加到指定季度
        if year == end_year:
            quarters = quarters[:end_quarter]
            
        report_dates.extend(quarters)
    
    # 按时间顺序排序（从早到晚）
    report_dates.sort()
    
    total_results = {
        'balance_sheet': {'created': 0, 'failed': 0},
        'income_statement': {'created': 0, 'failed': 0},
        'cash_flow_statement': {'created': 0, 'failed': 0}
    }
    
    results = []
    
    for date in report_dates:
        logger.info(f"获取 {date} 的财务报表数据")
        
        # 获取资产负债表数据
        try:
            balance_result = fetch_balance_sheet(date)
            if balance_result and isinstance(balance_result, dict):
                total_results['balance_sheet']['created'] += balance_result.get('created', 0)
                total_results['balance_sheet']['failed'] += balance_result.get('failed', 0)
            time.sleep(3)  # 延时避免频繁请求
        except Exception as e:
            logger.error(f"获取 {date} 资产负债表数据失败: {str(e)}")
            total_results['balance_sheet']['failed'] += 1
        
        # 获取利润表数据
        try:
            income_result = fetch_income_statement(date)
            if income_result and isinstance(income_result, dict):
                total_results['income_statement']['created'] += income_result.get('created', 0)
                total_results['income_statement']['failed'] += income_result.get('failed', 0)
            time.sleep(3)  # 延时避免频繁请求
        except Exception as e:
            logger.error(f"获取 {date} 利润表数据失败: {str(e)}")
            total_results['income_statement']['failed'] += 1
        
        # 获取现金流量表数据
        try:
            cash_flow_result = fetch_cash_flow_statement(date)
            if cash_flow_result and isinstance(cash_flow_result, dict):
                total_results['cash_flow_statement']['created'] += cash_flow_result.get('created', 0)
                total_results['cash_flow_statement']['failed'] += cash_flow_result.get('failed', 0)
            time.sleep(3)  # 延时避免频繁请求
        except Exception as e:
            logger.error(f"获取 {date} 现金流量表数据失败: {str(e)}")
            total_results['cash_flow_statement']['failed'] += 1
    
    total_created = sum(result['created'] for result in total_results.values())
    total_failed = sum(result['failed'] for result in total_results.values())
    
    summary = {
        "status": "success" if total_failed == 0 else "partial",
        "message": f"批量获取财务报表完成: 共处理{len(report_dates)}个报告期，新增{total_created}条，失败{total_failed}条",
        "total_created": total_created,
        "total_failed": total_failed,
        "details": total_results
    }
    
    logger.info(summary["message"])
    return summary

def update_index_stock_daily_data():
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
        stock_code_list = [stock for stock in stocks if stock.index_type]
        # 更新所有个股的历史数据（最近30天）
        updated_stocks, updated_history = update_stock_history(stock_code_list=stock_code_list, days=500)
        
        logger.info(f"个股日频数据更新任务完成，更新: {updated_stocks}只个股，{updated_history}条历史数据")
        return {
            "status": "success",
            "message": f"个股日频数据更新任务完成，更新: {updated_stocks}只个股，{updated_history}条历史数据"
        }
    except Exception as e:
        logger.error(f"个股日频数据更新任务执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}

def write_concept_to_db():
    """
    功能: 并发抓取东财概念成分并将概念写入个股表的 `dc_concept` 字段。

    参数: 无（内部固定 `trade_date` 为 `'20251106'`，如需变更可后续扩展参数）。

    返回值: dict
    - `status`: `success` 或 `partial` 或 `error`
    - `message`: 执行摘要信息
    - `concept_count`: 概念数量
    - `affected_stocks`: 实际写库的个股数量

    事件: 
    - 网络请求: 调用 Tushare Pro 接口 `dc_index` 与 `dc_member`
    - 数据库更新: 合并去重概念后更新 `IndividualStock.dc_concept`
    """
    ts.set_token('')
    trade_date = '20251106'

    try:
        # 先获取所有概念索引
        pro_index = ts.pro_api()
        df_index = pro_index.dc_index(trade_date=trade_date, fields='ts_code,name,turnover_rate,up_num,down_num')
        if df_index is None or df_index.empty:
            logger.warning(f"{trade_date} 未获取到概念索引数据")
            return {"status": "error", "message": "未获取到概念索引数据", "concept_count": 0, "affected_stocks": 0}

        concept_rows = list(df_index.itertuples(index=False))

        # 并发抓取每个概念对应的成分股，收敛为 {stock_code: set(concepts)}
        stock_to_concepts: Dict[str, Set[str]] = defaultdict(set)

        def _fetch_members_for_concept(ts_code: str, concept_name: str, date: str) -> List[Tuple[str, str]]:
            """抓取单个概念的成分股。(功能/参数/返回值/事件)

            功能: 通过 `dc_member` 获取该概念在指定交易日的成分股列表。
            参数: `ts_code` 概念代码; `concept_name` 概念名称; `date` 交易日期。
            返回值: `List[Tuple[stock_code, concept_name]]`，其中 `stock_code` 为不带市场后缀的代码。
            事件: 调用 Tushare Pro 的 `dc_member` 接口进行网络请求。
            """
            try:
                local_pro = ts.pro_api()
                print(f"[dc_member] 开始: {concept_name}({ts_code}) date={date}")
                logger.info(f"开始获取概念成分: {concept_name}({ts_code}) {date}")
                time.sleep(1)  # 延时避免频繁请求
                df_members = local_pro.dc_member(trade_date=date, ts_code=ts_code)
                results: List[Tuple[str, str]] = []
                if df_members is not None and not df_members.empty:
                    for _, r in df_members.iterrows():
                        stock_code = r['con_code'][:-3]
                        results.append((stock_code, concept_name))
                print(f"[dc_member] 完成: {concept_name}({ts_code}) 成分数={len(results)}")
                logger.info(f"获取完成: {concept_name}({ts_code}) 成分数={len(results)}")
                return results
            except Exception as exc:
                logger.error(f"获取概念成分失败: {concept_name}({ts_code}) - {exc}")
                return []

        max_workers = min(8, len(concept_rows)) if len(concept_rows) > 0 else 1
        print(f"[并发] 概念数={len(concept_rows)} max_workers={max_workers}")
        logger.info(f"并发抓取概念成分: 概念数={len(concept_rows)} max_workers={max_workers}")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ctx = {}
            for row in concept_rows:
                name = getattr(row, 'name')
                ts_code = row.ts_code
                print(f"[并发] 提交任务: {name}({ts_code})")
                logger.info(f"提交抓取任务: {name}({ts_code})")
                f = executor.submit(_fetch_members_for_concept, ts_code, name, trade_date)
                future_to_ctx[f] = (ts_code, name)

            for future in as_completed(future_to_ctx):
                ts_code, name = future_to_ctx[future]
                members = future.result()
                print(f"[并发] 收到结果: {name}({ts_code}) 成分数={len(members)}")
                logger.info(f"收到抓取结果: {name}({ts_code}) 成分数={len(members)}")
                for stock_code, concept_name in members:
                    stock_to_concepts[stock_code].add(concept_name)

        # 合并写库：单线程执行以避免并发写导致的覆盖问题
        affected = 0
        print(f"[聚合] 待写入股票数={len(stock_to_concepts)}")
        logger.info(f"聚合完成，待写入股票数={len(stock_to_concepts)}")
        for stock_code, concepts in stock_to_concepts.items():
            indival_stock = IndividualStock.objects.filter(code=stock_code).first()
            if not indival_stock:
                continue
            existing = set(filter(None, (indival_stock.dc_concept or '').split(',')))
            merged = sorted(existing.union(concepts))
            new_value = ','.join(merged) if merged else None
            if new_value != (indival_stock.dc_concept or None):
                indival_stock.dc_concept = new_value
                indival_stock.save(update_fields=['dc_concept'])
                affected += 1
                print(f"[写库] 更新 {stock_code}: 概念数={len(merged)}")
                logger.info(f"更新股票 {stock_code}: 概念数={len(merged)}")

        message = f"并发写入概念完成: 概念数{len(concept_rows)}，影响个股{affected}"
        logger.info(message)
        return {"status": "success", "message": message, "concept_count": len(concept_rows), "affected_stocks": affected}

    except Exception as e:
        logger.error(f"并发写入概念任务失败: {e}")
        return {"status": "error", "message": str(e), "concept_count": 0, "affected_stocks": 0}
    

    
    # for concept in concepts:
    #     IndividualStock.objects.filter(stock_code=concept['stock_code']).update(
    #         dc_concept=concept['dc_concept']
    #     )


if __name__ == '__main__':
    # update_individual_stock_daily_data()
    # fetch_individual_stocks()
    
    # 从2015年开始获取季报、中报、三季报、年报到20240930
    # fetch_all_performance_reports(start_year=2015, end_date='20240930')

    # fetch_performance_report('20210331')

    # fetch_income_statement('20250630')

    # fetch_cash_flow_statement('20250630')

    # fetch_balance_sheet('20250630')


    # fetch_stock_daily_data('sh.000001', '2024-09-30', '2025-10-18')
    update_individual_stock_daily_data()
    update_individual_stock_weekly_data()
    # update_index_stock_daily_data()
    # update_individual_stock_daily_data()
    # fetch_individual_stocks()
    # write_concept_to_db()


# 个股数据 
# ('22 18,20,23 * * 1-5', 'scheduled_tasks.stock_data_query_tasks.individual_stock_tasks.fetch_individual_stocks', f'>> {BASE_DIR}/logs/fetch_individual_stock_list.log 2>&1'), 
# ('40 17,19,22 * * 1-5', 'scheduled_tasks.stock_data_query_tasks.individual_stock_tasks.update_individual_stock_daily_data', f'>> {BASE_DIR}/logs/update_individual_stock_daily_data.log 2>&1'),
# ('50 17,20,23 * * 1-5', 'scheduled_tasks.stock_data_query_tasks.individual_stock_tasks.update_index_stock_daily_data', f'>> {BASE_DIR}/logs/update_index_stock_daily_data.log 2>&1'),
    
