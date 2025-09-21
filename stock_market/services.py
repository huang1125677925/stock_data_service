import akshare as ak
from datetime import datetime, timedelta
import pandas as pd

def get_latest_trading_date():
    """
    获取最近的交易日期
    由于当天数据需要收盘后才能获取，所以默认获取前一个交易日的数据
    """
    today = datetime.now()
    # 如果是周末，回退到周五
    if today.weekday() == 5:  # 周六
        latest_trading_date = today - timedelta(days=1)
    elif today.weekday() == 6:  # 周日
        latest_trading_date = today - timedelta(days=2)
    else:
        # 工作日默认取前一天
        latest_trading_date = today - timedelta(days=1)
    
    # 格式化为YYYYMMDD格式
    return latest_trading_date.strftime("%Y%m%d")

def get_market_daily_overview(date=None):
    """
    获取上海证券交易所和深圳证券交易所每日概况数据，包括指数值、交易额和涨跌幅
    
    参数:
        date (str, optional): 日期，格式为YYYYMMDD，默认为最近一个交易日
        
    返回:
        dict: 包含上证和深证指数数据的字典
    """
    try:
        # 如果没有提供日期，使用最近的交易日
        if not date:
            date = get_latest_trading_date()
        
        # 获取上证指数数据
        sh_index_df = ak.stock_zh_index_daily(symbol="sh000001")
        # 获取深证成指数据
        sz_index_df = ak.stock_zh_index_daily(symbol="sz399001")
        # 获取沪深300指数数据
        hs300_index_df = ak.stock_zh_index_daily(symbol="sh000300")
        # 获取上证50指数数据
        sz50_index_df = ak.stock_zh_index_daily(symbol="sh000016")
        
        # 获取最近一天的数据
        sh_latest = sh_index_df.iloc[-1]
        sz_latest = sz_index_df.iloc[-1]
        hs300_latest = hs300_index_df.iloc[-1]
        sz50_latest = sz50_index_df.iloc[-1]
        
        # 计算涨跌幅
        sh_change_pct = round((sh_latest['close'] - sh_latest['open']) / sh_latest['open'] * 100, 2)
        sz_change_pct = round((sz_latest['close'] - sz_latest['open']) / sz_latest['open'] * 100, 2)
        hs300_change_pct = round((hs300_latest['close'] - hs300_latest['open']) / hs300_latest['open'] * 100, 2)
        sz50_change_pct = round((sz50_latest['close'] - sz50_latest['open']) / sz50_latest['open'] * 100, 2)
        
        # 构建结果字典
        result = {
            'date': date,
            'shanghai': {
                'index_name': '上证指数',
                'index_code': '000001',
                'latest_value': float(sh_latest['close']),
                'change_percent': float(sh_change_pct),
                'volume': float(sh_latest['volume']),
            },
            'shenzhen': {
                'index_name': '深证成指',
                'index_code': '399001',
                'latest_value': float(sz_latest['close']),
                'change_percent': float(sz_change_pct),
                'volume': float(sz_latest['volume']),
            },
            'hs300': {
                'index_name': '沪深300',
                'index_code': '000300',
                'latest_value': float(hs300_latest['close']),
                'change_percent': float(hs300_change_pct),
                'volume': float(hs300_latest['volume']),
            },
            'sz50': {
                'index_name': '上证50',
                'index_code': '000016',
                'latest_value': float(sz50_latest['close']),
                'change_percent': float(sz50_change_pct),
                'volume': float(sz50_latest['volume']),
            }
        }
    
        return result
    except Exception as e:
        raise Exception(f"获取股市指数数据失败: {str(e)}")

# 保留原函数名称以保持兼容性
def get_sse_daily_overview(date=None):
    """
    获取上海证券交易所每日概况数据（兼容旧版本）
    
    参数:
        date (str, optional): 日期，格式为YYYYMMDD，默认为最近一个交易日
        
    返回:
        dict: 包含上证和深证指数数据的字典
    """
    return get_market_daily_overview(date)