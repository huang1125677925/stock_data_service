#!/usr/bin/env python3
"""
简化综合技术指标策略
基于均线系统、动量指标和成交量的简化策略

该策略集成了Backtrader观测器数据收集功能：
- Broker: 资金变化记录
- BuySell: 买卖信号记录
- Trades: 交易记录
- TimeReturn: 时间收益率
- DrawDown: 回撤记录
- Benchmark: 基准比较
"""

import backtrader as bt
from pandas.core.arrays import period
from .base_strategy import BaseQuantStrategy, register_strategy

@register_strategy
class MultiIndicatorStrategy(BaseQuantStrategy):
    """
    多指标综合策略
    
    功能：
    - 基于EMA均线系统判断趋势
    - MACD指标确认动量
    - 成交量放大确认资金流入
    - 多重条件确认买卖信号
    - 止损保护机制
    - 自动收集观测器数据用于可视化分析
    
    参数：
    - short_period: 短期EMA周期，默认8
    - long_period: 长期EMA周期，默认21
    - signal_period: 信号平滑周期，默认3
    - volume_multiplier: 成交量放大倍数，默认1.2
    - stop_loss_pct: 止损百分比，默认8.0
    
    返回值：
    - 策略执行结果包含完整的观测器数据
    
    事件：
    - 买入信号：EMA金叉 + 放量 + MACD金叉
    - 卖出信号：EMA死叉 或 控盘度转负 或 MACD死叉
    - 止损信号：亏损超过设定百分比
    """
    
    _strategy_name = 'multi_indicator'
    _strategy_description = '多指标综合策略：基于EMA、MACD、成交量的综合技术分析策略'
    _strategy_params = {
        'short_period': {'type': 'int', 'default': 8, 'description': '短期EMA周期'},
        'long_period': {'type': 'int', 'default': 21, 'description': '长期EMA周期'},
        'signal_period': {'type': 'int', 'default': 3, 'description': '信号平滑周期'},
        'volume_multiplier': {'type': 'float', 'default': 1.2, 'description': '成交量放大倍数'},
        'stop_loss_pct': {'type': 'float', 'default': 8.0, 'description': '止损百分比'}
    }
    
    params = dict(
        short_period=8,        # 短期EMA周期
        long_period=21,        # 长期EMA周期
        signal_period=3,       # 信号平滑周期
        volume_multiplier=1.2, # 成交量放大倍数
        stop_loss_pct=8.0,     # 止损百分比
        printlog=True
    )
    
    def init_indicators(self):
        """
        策略初始化
        初始化技术指标和信号
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
        
        # 3. 主力资金指标 (简化版控盘度)
        self.control = (self.ema_short - self.ema_long) / self.ema_long * 100
        
        # 4. MACD波段指标
        self.macd = bt.indicators.MACD(
            close, 
            period_me1=self.params.short_period, 
            period_me2=self.params.long_period, 
            period_signal=self.params.signal_period
        )
        
        # 5. 成交量指标
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=5
        )
        
        # 买入信号：多重条件确认
        self.buy_signal = bt.And(
            bt.indicators.CrossUp(self.ema_short, self.ema_long),  # EMA金叉
            self.data.volume > self.volume_ma * self.params.volume_multiplier,  # 放量确认
            self.macd.macd > self.macd.signal  # MACD金叉确认
        )
        
        # 卖出信号：多重条件确认
        self.sell_signal = bt.Or(
            bt.indicators.CrossDown(self.ema_short, self.ema_long),  # EMA死叉
            self.control < -3,  # 控盘度转负
            self.macd.macd < self.macd.signal  # MACD死叉
        )
    
    def get_strategy_name(self) -> str:
        """获取策略名称"""
        return "multi_indicator"
    
    def get_strategy_description(self) -> str:
        """获取策略描述"""
        return "多指标综合策略：基于EMA均线系统、MACD动量指标和成交量的综合技术分析策略"
    
    def next(self):
        """
        策略主逻辑
        每个交易日执行的核心逻辑
        """
        # 首先调用父类的next方法来记录历史数据
        super().next()
        
        # 如果有未完成的订单，跳过
        if self.order:
            return
        
        # 获取当前价格和指标值
        current_price = self.data.close[0]
        ema_short_value = self.ema_short[0]
        ema_long_value = self.ema_long[0]
        control_value = self.control[0]
        
        # 获取当前持仓
        if not self.position:
            # 没有持仓，检查买入信号
            if self.buy_signal[0]:
                self.log(f'买入信号: 价格={current_price:.2f}, '
                        f'短期EMA={ema_short_value:.2f}, '
                        f'长期EMA={ema_long_value:.2f}, '
                        f'控盘度={control_value:.2f}%, '
                        f'MACD={self.macd.macd[0]:.4f}, '
                        f'成交量比={self.data.volume[0]/self.volume_ma[0]:.2f}')
                
                # 全仓买入：计算可买入的最大股数
                cash = self.broker.get_cash()
                
                # 预留5%的资金作为安全边际，避免因手续费等导致保证金不足
                available_cash = cash * 0.95
                
                # 计算最大可买股数
                max_shares = int(available_cash / current_price)
                
                # 确保至少能买入100股（1手）
                if max_shares >= 100:
                    # 按100股的整数倍买入
                    max_shares = (max_shares // 100) * 100
                    
                    self.log(f'全仓买入: 总资金={cash:.2f}, 可用资金={available_cash:.2f}, '
                            f'股价={current_price:.2f}, 买入股数={max_shares}')
                    self.order = self.buy(size=max_shares)
                else:
                    self.log(f'资金不足: 总资金={cash:.2f}, 股价={current_price:.2f}, '
                            f'无法买入最小单位(100股)，需要资金={current_price * 100:.2f}')
        
        else:
            # 有持仓，检查卖出信号
            if self.sell_signal[0]:
                self.log(f'卖出信号: 价格={current_price:.2f}, '
                        f'短期EMA={ema_short_value:.2f}, '
                        f'长期EMA={ema_long_value:.2f}, '
                        f'控盘度={control_value:.2f}%, '
                        f'MACD={self.macd.macd[0]:.4f}')
                
                # 全仓卖出：卖出所有持仓
                position_size = self.position.size
                if position_size > 0:
                    self.log(f'全仓卖出: 当前持仓={position_size}')
                    self.order = self.sell(size=position_size)
            
            # 止损：亏损超过设定百分比
            elif self.buy_price and (current_price / self.buy_price - 1) < -self.params.stop_loss_pct / 100:
                loss_pct = (current_price / self.buy_price - 1) * 100
                self.log(f'止损卖出: 价格={current_price:.2f}, '
                        f'买入价={self.buy_price:.2f}, '
                        f'亏损={loss_pct:.2f}% (止损线:{self.params.stop_loss_pct}%)')
                
                # 全仓止损卖出：卖出所有持仓
                position_size = self.position.size
                if position_size > 0:
                    self.log(f'全仓止损卖出: 当前持仓={position_size}')
                    self.order = self.sell(size=position_size)