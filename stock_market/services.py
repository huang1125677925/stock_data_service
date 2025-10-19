import pandas as pd
from decimal import Decimal
from .models import IndexHighLowStatistics

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


def get_rise_fall_ratio_data(index_code=None, start_date=None, end_date=None, limit=30):
    """
    查询指数涨跌比数据
    
    功能：从数据库查询指定条件的涨跌比数据
    参数：
        index_code (str, optional): 指数代码，不指定则查询所有
        start_date (str, optional): 开始日期，格式YYYY-MM-DD
        end_date (str, optional): 结束日期，格式YYYY-MM-DD  
        limit (int): 返回记录数限制，默认30条
    返回值：
        list: 涨跌比数据列表
    事件：数据库查询操作
    """
    try:
        queryset = IndexHighLowStatistics.objects.all()
        
        # 按指数代码过滤
        if index_code:
            queryset = queryset.filter(index_code=index_code)
        
        # 按日期范围过滤
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        # 排序并限制数量
        queryset = queryset.order_by('-date')[:limit]
        
        # 转换为字典列表并计算涨跌比
        results = []
        for obj in queryset:
            # 计算20天涨跌比
            high20 = obj.high20 or 0
            low20 = obj.low20 or 0
            total20 = high20 + low20
            rise_fall_ratio_20 = round(high20 / total20, 4) if total20 > 0 else 0
            
            # 计算60天涨跌比
            high60 = obj.high60 or 0
            low60 = obj.low60 or 0
            total60 = high60 + low60
            rise_fall_ratio_60 = round(high60 / total60, 4) if total60 > 0 else 0
            
            # 计算120天涨跌比
            high120 = obj.high120 or 0
            low120 = obj.low120 or 0
            total120 = high120 + low120
            rise_fall_ratio_120 = round(high120 / total120, 4) if total120 > 0 else 0
            
            results.append({
                'id': obj.id,
                'date': obj.date.strftime('%Y-%m-%d'),
                'index_code': obj.index_code,
                'index_name': obj.get_index_code_display(),
                'close': float(obj.close) if obj.close else None,
                'high20': obj.high20,
                'low20': obj.low20,
                'high60': obj.high60,
                'low60': obj.low60,
                'high120': obj.high120,
                'low120': obj.low120,
                'rise_fall_ratio_20': rise_fall_ratio_20,
                'rise_fall_ratio_60': rise_fall_ratio_60,
                'rise_fall_ratio_120': rise_fall_ratio_120,
                'created_at': obj.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': obj.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return results
        
    except Exception as e:
        raise Exception(f"查询涨跌比数据失败: {str(e)}")