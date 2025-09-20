#!/usr/bin/env python3
"""
移动平均线交叉策略
基于短期和长期移动平均线的金叉死叉进行买卖
"""

import backtrader as bt
from .base_strategy import BaseQuantStrategy, register_strategy


@register_strategy
class MACrossStrategy(BaseQuantStrategy):
    _strategy_name = 'ma_cross'
    _strategy_description = '移动平均线交叉策略'
    _strategy_params = {
        'short_period': {'type': 'int', 'default': 5, 'description': '短期均线周期'},
        'long_period': {'type': 'int', 'default': 20, 'description': '长期均线周期'}
    }
    """
    移动平均线交叉策略
    
    策略逻辑：
    1. 当短期均线上穿长期均线时买入（金叉）
    2. 当短期均线下穿长期均线时卖出（死叉）
    3. 结合成交量确认信号
    """
    
    params = dict(
        short_period=5,    # 短期均线周期
        long_period=20,    # 长期均线周期
        volume_factor=1.2, # 成交量放大倍数
        printlog=True
    )
    
    def init_indicators(self):
        """
        初始化技术指标
        """
        # 移动平均线
        self.ma_short = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.short_period
        )
        
        self.ma_long = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.long_period
        )
        
        # 成交量均线
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=10
        )
        
        # 交叉信号
        self.crossover = bt.indicators.CrossOver(
            self.ma_short, self.ma_long
        )
    
    def get_strategy_name(self) -> str:
        return "ma_cross"
    
    def get_strategy_description(self) -> str:
        return "移动平均线交叉策略：基于短期和长期移动平均线的金叉死叉进行买卖"
    
    def next(self):
        """
        策略主逻辑
        """
        # 如果有未完成的订单，跳过
        if self.order:
            return
        
        # 获取当前持仓
        if not self.position:
            # 没有持仓，检查买入信号
            if (self.crossover > 0 and  # 金叉
                self.data.volume[0] > self.volume_ma[0] * self.params.volume_factor):  # 放量
                
                self.log(f'买入信号: 价格={self.data.close[0]:.2f}, '
                        f'短期均线={self.ma_short[0]:.2f}, '
                        f'长期均线={self.ma_long[0]:.2f}')
                
                # 买入
                self.order = self.buy()
        
        else:
            # 有持仓，检查卖出信号
            if self.crossover < 0:  # 死叉
                self.log(f'卖出信号: 价格={self.data.close[0]:.2f}, '
                        f'短期均线={self.ma_short[0]:.2f}, '
                        f'长期均线={self.ma_long[0]:.2f}')
                
                # 卖出
                self.order = self.sell()