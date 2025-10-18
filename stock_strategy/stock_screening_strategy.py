"""
股票筛选策略模块
基于前高突破和成交量放大的股票筛选策略
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from django.db.models import Q
from indival_stock_data.models import IndividualStock, IndividualStockDaily


class StockScreeningStrategy:
    """
    股票筛选策略类
    
    功能：根据窗口大小参数筛选符合条件的股票
    策略逻辑：
    1. 获取每只股票最近x个交易日的数据
    2. 识别前高日期（当日最高价是窗口内最高价，且成交量≥前一日成交量的1.5倍）
    3. 判断前高日期后是否有成交量突破前高日成交量的情况
    4. 符合条件的股票加入待观察列表
    
    参数：
    - window_size: 窗口大小（交易日数量）
    - volume_multiplier: 成交量放大倍数，默认1.5
    
    返回值：
    - 待观察股票列表，包含股票信息和相关数据
    """
    
    def __init__(self, window_size: int = 20, volume_multiplier: float = 1.5):
        """
        初始化策略参数
        
        Args:
            window_size: 分析窗口大小（交易日数量）
            volume_multiplier: 成交量放大倍数
        """
        self.window_size = window_size
        self.volume_multiplier = volume_multiplier
    
    def get_recent_trading_data(self, stock: IndividualStock, days: int) -> List[IndividualStockDaily]:
        """
        获取指定股票最近的交易日数据
        
        Args:
            stock: 股票对象
            days: 获取天数
            
        Returns:
            按日期降序排列的交易数据列表
        """
        return list(
            IndividualStockDaily.objects.filter(stock=stock)
            .order_by('-date')[:days]
        )[::-1]
    
    def identify_previous_high(self, trading_data: List[IndividualStockDaily]) -> Optional[Tuple[IndividualStockDaily, int]]:
        """
        识别前高日期
        
        前高定义：
        1. 当日最高价是窗口内的最高价
        2. 当日成交量 >= 前一日成交量 * volume_multiplier
        3. 最高点和最低点的差值不超过最高点的30%
        4. 前高那天收盘价高于开盘价
        
        Args:
            trading_data: 按日期升序排列的交易数据列表
            
        Returns:
            (前高日数据, 在列表中的索引) 或 None
        """
        if len(trading_data) < 2:
            return None
        
        # 找到窗口内的最高价和最低价
        max_high_price = max(float(data.high_price) for data in trading_data)
        min_low_price = min(float(data.low_price) for data in trading_data)
        
        # 前置判断：检查最高点和最低点的差值是否超过最高点的30%
        price_diff = max_high_price - min_low_price
        max_allowed_diff = max_high_price * 0.3
        if price_diff > max_allowed_diff:
            return None
        
        # 遍历数据寻找前高日（从第二天开始，因为需要比较前一日成交量）
        for i in range(1, len(trading_data)):
            current_day = trading_data[i]
            previous_day = trading_data[i - 1]  # 时间上的前一天
            
            # 检查是否为最高价
            if float(current_day.high_price) == max_high_price:
                # 检查成交量条件（与时间上的前一天比较）
                if float(current_day.volume) >= float(previous_day.volume) * self.volume_multiplier:
                    # 检查收盘价是否高于开盘价
                    if float(current_day.close_price) > float(current_day.open_price):
                        return current_day, i
        
        return None
    
    def check_volume_breakthrough(self, trading_data: List[IndividualStockDaily], 
                                previous_high_index: int, previous_high_volume: float) -> Optional[int]:
        """
        检查前高日期后是否有成交量突破
        
        Args:
            trading_data: 按日期升序排列的交易数据列表
            previous_high_index: 前高日在列表中的索引
            previous_high_volume: 前高日的成交量（浮点数）
            
        Returns:
            突破日的索引，如果没有突破则返回None
        """
        # 检查前高日之后的交易日（索引更大的日期更新）
        for i in range(previous_high_index + 1, len(trading_data)):
            if float(trading_data[i].volume) > previous_high_volume and len(trading_data) - i <=10 and i - previous_high_index > 20 and float(trading_data[i].close_price) > float(trading_data[i].open_price):
                return i
        
        return None
    
    def analyze_single_stock(self, stock: IndividualStock) -> Optional[Dict]:
        """
        分析单只股票是否符合筛选条件
        
        Args:
            stock: 股票对象
            
        Returns:
            符合条件时返回分析结果字典，否则返回None
        """
        # 获取最近的交易数据
        trading_data = self.get_recent_trading_data(stock, self.window_size)
        
        if len(trading_data) < self.window_size:
            return None  # 数据不足
        
        # 识别前高
        previous_high_result = self.identify_previous_high(trading_data)
        if not previous_high_result:
            return None  # 未找到前高
        
        previous_high_day, previous_high_index = previous_high_result
        
        # 检查成交量突破
        breakthrough_index = self.check_volume_breakthrough(
            trading_data, previous_high_index, float(previous_high_day.volume)
        )
        
        if breakthrough_index is None:
            return None  # 无成交量突破
        
        breakthrough_day = trading_data[breakthrough_index]
        
        # 构建结果
        return {
            'stock_code': stock.code,
            'stock_name': stock.name,
            'industry': stock.industry,
            'previous_high_date': previous_high_day.date,
            'previous_high_price': float(previous_high_day.high_price),
            'previous_high_volume': previous_high_day.volume,
            'window_size': self.window_size,
            'volume_multiplier': self.volume_multiplier,
            'analysis_date': datetime.now().date(),
            'breakthrough_price': float(breakthrough_day.close_price),
            'breakthrough_volume': breakthrough_day.volume,
            'breakthrough_date': breakthrough_day.date
        }
    
    def screen_stocks(self, stock_codes: Optional[List[str]] = None) -> List[Dict]:
        """
        批量筛选股票
        
        Args:
            stock_codes: 指定股票代码列表，为None时筛选所有股票
            
        Returns:
            符合条件的股票列表
        """
        # 获取股票查询集
        if stock_codes:
            stocks = IndividualStock.objects.filter(code__in=stock_codes)
        else:
            stocks = IndividualStock.objects.all()
        
        results = []
        
        for stock in stocks:
            try:
                analysis_result = self.analyze_single_stock(stock)
                if analysis_result:
                    print(stock.name, analysis_result)
                    results.append(analysis_result)
            except Exception as e:
                # 记录错误但继续处理其他股票
                print(f"分析股票 {stock.code} 时出错: {str(e)}")
                continue
        
        return results
    
    def get_top_candidates(self, stock_codes: Optional[List[str]] = None, 
                          limit: int = 50) -> List[Dict]:
        """
        获取排名靠前的候选股票
        
        Args:
            stock_codes: 指定股票代码列表
            limit: 返回数量限制
            
        Returns:
            按最新成交量排序的候选股票列表
        """
        candidates = self.screen_stocks(stock_codes)
        
        # 按最新成交量降序排序
        candidates.sort(key=lambda x: x['latest_volume'], reverse=True)
        
        return candidates[:limit]