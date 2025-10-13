#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取股票历史交易数据
使用akshare接口获取指定股票的历史交易数据，并保存为CSV文件
"""

import akshare as ak
import pandas as pd
import os
from datetime import datetime, timedelta


def get_stock_history_data(symbol, start_date=None, end_date=None, adjust=""):
    """
    获取指定股票的历史交易数据
    
    参数:
        symbol (str): 股票代码，如'000001'
        start_date (str): 开始日期，格式'YYYYMMDD'，默认为一年前
        end_date (str): 结束日期，格式'YYYYMMDD'，默认为今天
        adjust (str): 复权方式，默认为不复权；qfq: 前复权；hfq: 后复权
    
    返回:
        DataFrame: 包含历史交易数据的DataFrame
    """
    
    # 设置默认日期范围
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=3650)).strftime('%Y%m%d')
    
    print(f"正在获取股票 {symbol} 的历史数据...")
    print(f"日期范围: {start_date} 到 {end_date}")
    
    try:
        # 使用akshare获取历史行情数据
        stock_data = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=adjust
        )
        
        if stock_data.empty:
            print(f"警告: 股票 {symbol} 没有获取到任何数据")
            return None
        
        # 重命名列以符合要求
        stock_data = stock_data.rename(columns={
            '日期': 'trade_date',
            '开盘': 'open',
            '最高': 'high',
            '最低': 'low',
            '收盘': 'close',
            '成交量': 'vol'
        })
        
        # 只保留需要的列
        stock_data = stock_data[['trade_date', 'open', 'high', 'low', 'close', 'vol']]
        
        # 转换日期格式为 YYYY-MM-DD
        stock_data['trade_date'] = pd.to_datetime(stock_data['trade_date']).dt.strftime('%Y-%m-%d')
        
        # 按日期排序（升序）
        stock_data = stock_data.sort_values('trade_date').reset_index(drop=True)
        
        print(f"成功获取 {len(stock_data)} 条数据")
        return stock_data
        
    except Exception as e:
        print(f"获取股票 {symbol} 数据时发生错误: {str(e)}")
        return None


def save_to_csv(data, symbol, output_dir="data"):
    """
    将数据保存为CSV文件
    
    参数:
        data (DataFrame): 要保存的数据
        symbol (str): 股票代码，用于文件名
        output_dir (str): 输出目录，默认为'data'
    """
    if data is None or data.empty:
        print("没有数据需要保存")
        return False
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成文件名
    filename = f"{symbol}.csv"
    filepath = os.path.join(output_dir, filename)
    
    try:
        # 保存为CSV文件
        data.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"数据已保存到: {filepath}")
        return True
        
    except Exception as e:
        print(f"保存文件时发生错误: {str(e)}")
        return False


def main():
    """
    主函数，用于测试和演示
    """
    # 示例：获取平安银行(000001)的历史数据
    symbol = "399300"
    
    # 获取数据
    stock_data = get_stock_history_data(symbol)
    
    if stock_data is not None:
        # 显示前5条数据
        print("\n数据预览:")
        print(stock_data.head())
        
        # 保存到CSV文件
        save_to_csv(stock_data, symbol)


if __name__ == "__main__":
    main()