#!/usr/bin/env python3
"""
个股数据抓取任务
定期从akshare获取个股数据并存储到数据库
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

import logging
import baostock as bs
from datetime import datetime, timedelta
import akshare as ak
import pandas as pd
from indival_stock_data.models import IndividualStock
import time
from indival_stock_data.models import IndividualStockDaily
from django.db import transaction
from typing import Tuple, List
# 导入StockDailyData数据类
from scheduled_tasks.stock_data_query_tasks.stock_data_models import StockDailyData



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
        df = ak.stock_zh_a_spot_em()
        
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
        
        # 批量创建新股票
        if stocks_to_create:
            with transaction.atomic():
                IndividualStock.objects.bulk_create(stocks_to_create, batch_size=500)
                logger.info(f"批量创建了{len(stocks_to_create)}只新股票")
        
        # 批量更新现有股票
        if stocks_to_update:
            for code, data in stocks_to_update:
                with transaction.atomic():
                    IndividualStock.objects.filter(code=code).update(**data)
                logger.info(f"更新了股票 {code} 的数据")
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
        updated_stocks, updated_history = update_stock_history(stock_code_list=stock_code_list, days=30)
        
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
        
        # 获取要更新的股票列表
        stocks = IndividualStock.objects.all()

        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()

        # 使用集合操作提高查询效率，避免使用distinct()
        # stock_code_list = set(IndividualStockDaily.objects.filter(
        #             date__gte=start_date_obj,
        #             date__lte=start_date_obj
        #         ).values_list('stock_id', flat=True))
        
        if not stocks.exists():
            logger.warning("没有找到需要更新的股票")
            return 0, 0
        
        # 遍历股票列表更新历史数据
        for stock in stocks:
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


                exchange_prefix = judge_stock_type(stock.code)
                daily_data_list = fetch_stock_daily_data(exchange_prefix + stock.code, start_date, end_date)
                
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
    if stock_code.startswith(('60', '68')):
        return "sh."
    elif stock_code.startswith(('00', '30', '002', '003')):
        return "sz."
    elif stock_code.startswith(('83', '87', '88', '82')):
        return "bj."  # 北交所股票
    else:
        return "sh."  # 默认使用上海交易所

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


if __name__ == '__main__':
    update_individual_stock_daily_data()

