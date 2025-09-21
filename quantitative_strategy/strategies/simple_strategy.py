#!/usr/bin/env python3
"""
简化综合技术指标策略
基于均线系统、动量指标和成交量的简化策略
"""

import backtrader as bt
from pandas.core.arrays import period
from .base_strategy import BaseQuantStrategy, register_strategy

@register_strategy
class SimpleStrategy(BaseQuantStrategy):
    _strategy_name = 'simple'
    _strategy_description = '简单技术指标策略'
    _strategy_params = {
        'short_period': {'type': 'int', 'default': 5, 'description': '短期周期'},
        'long_period': {'type': 'int', 'default': 20, 'description': '长期周期'},
        'rsi_period': {'type': 'int', 'default': 14, 'description': 'RSI周期'},
        'rsi_oversold': {'type': 'float', 'default': 30.0, 'description': 'RSI超卖阈值'},
        'rsi_overbought': {'type': 'float', 'default': 70.0, 'description': 'RSI超买阈值'}
    }
    """
    简化的综合技术指标策略
    
    策略逻辑：
    1. 基于均线系统
    2. 动量指标
    3. 主力资金动向判断
    4. 波段交易信号
    """
    
    params = dict(
        short_period=8,    # 短期EMA
        long_period=21,    # 长期EMA
        signal_period=3,   # 信号平滑
        printlog=True
    )
    
    def init_indicators(self):
        """
        策略初始化
        """
        # 基础价格
        close = self.data.close
        
        # 1. 均线系统
        self.ema_short = bt.indicators.ExponentialMovingAverage(
            close, period=self.params.short_period
        )
        self.ema_long = bt.indicators.ExponentialMovingAverage(
            close, period=self.params.long_period
        )
        
        
        # 3. 主力资金指标 (简化版控盘)
        self.control = (self.ema_short - self.ema_long) / self.ema_long * 100
        
        # 4. 波段指标
        self.macd = bt.indicators.MACD(
            close, 
            period_me1=8, 
            period_me2=21, 
            period_signal=5
        )
        
        # 5. 成交量指标
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=5
        )
        
        # 买入信号：多重条件确认
        self.buy_signal = bt.And(
            bt.indicators.CrossUp(self.ema_short, self.ema_long),  # 金叉
            self.data.volume > self.volume_ma * 1.2,  # 放量
            self.macd.macd > self.macd.signal  # MACD金叉
        )
        
        # 卖出信号：多重条件确认
        self.sell_signal = bt.Or(
            bt.indicators.CrossDown(self.ema_short, self.ema_long),  # 死叉
            self.control < -3,  # 控盘度转负
            self.macd.macd < self.macd.signal  # MACD死叉
        )
    
    def get_strategy_name(self) -> str:
        return "simple"
    
    def get_strategy_description(self) -> str:
        return "简化综合技术指标策略：基于均线系统、动量指标和成交量的简化策略"
    
    def next(self):
        """
        策略主逻辑
        """
        # 如果有未完成的订单，跳过
        if self.order:
            return
        
        current_price = self.data.close[0]
        
        # 获取当前持仓
        if not self.position:
            # 没有持仓，检查买入信号
            if self.buy_signal[0]:
                self.log(f'买入信号: 价格={current_price:.2f}, '
                        f'短期EMA={self.ema_short[0]:.2f}, '
                        f'长期EMA={self.ema_long[0]:.2f}, '
                        f'控盘度={self.control[0]:.2f}')
                
                                # 全仓买入
                # 计算可用资金
                cash = self.broker.getcash()
                # 计算可以买入的最大股数
                max_shares = int(cash / current_price)
                if max_shares > 0:
                    self.log(f'全仓买入: 可用资金={cash:.2f}, 买入股数={max_shares}')
                    self.order = self.buy(size=max_shares)
        
        else:
            # 有持仓，检查卖出信号
            if self.sell_signal[0]:
                self.log(f'卖出信号: 价格={current_price:.2f}, '
                        f'短期EMA={self.ema_short[0]:.2f}, '
                        f'长期EMA={self.ema_long[0]:.2f}, '
                        f'控盘度={self.control[0]:.2f}')
                
                # 全仓卖出
                # 获取当前持仓数量
                position_size = self.position.size
                if position_size > 0:
                    self.log(f'全仓卖出: 当前持仓={position_size}')
                    self.order = self.sell(size=position_size)
            
            # 止损：亏损超过8%
            elif self.buy_price and (current_price / self.buy_price - 1) < -0.08:
                self.log(f'止损卖出: 价格={current_price:.2f}, '
                        f'买入价={self.buy_price:.2f}, '
                        f'亏损={((current_price / self.buy_price - 1) * 100):.2f}%')
                
                # 全仓卖出
                # 获取当前持仓数量
                position_size = self.position.size
                if position_size > 0:
                    self.log(f'全仓止损卖出: 当前持仓={position_size}')
                    self.order = self.sell(size=position_size)