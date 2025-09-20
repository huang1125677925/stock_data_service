#!/usr/bin/env python3
"""
高级综合技术指标策略
基于多种技术指标的综合判断进行交易
"""

import backtrader as bt
import numpy as np
from .base_strategy import BaseQuantStrategy, register_strategy


@register_strategy
class AdvancedStrategy(BaseQuantStrategy):
    _strategy_name = 'advanced'
    _strategy_description = '高级综合策略，结合多种技术指标'
    _strategy_params = {
        'short_period': {'type': 'int', 'default': 5, 'description': '短期周期'},
        'long_period': {'type': 'int', 'default': 20, 'description': '长期周期'},
        'rsi_period': {'type': 'int', 'default': 14, 'description': 'RSI周期'},
        'rsi_oversold': {'type': 'float', 'default': 30.0, 'description': 'RSI超卖阈值'},
        'rsi_overbought': {'type': 'float', 'default': 70.0, 'description': 'RSI超买阈值'}
    }
    """
    高级技术指标综合策略
    
    策略逻辑：
    1. 基于自定义加权价格计算趋势指标
    2. 使用动量指标(MTM)和动向指标(DX)判断买卖点
    3. 控盘指标判断主力资金动向
    4. 波段买卖指标结合均线系统
    5. 涨跌停过滤机制
    """
    
    params = dict(
        p=21,           # EMA长周期
        s=8,            # EMA短周期
        m1=3,           # EMA平滑周期
        printlog=True   # 是否打印日志
    )
    
    def init_indicators(self):
        """
        策略初始化：计算所有需要的技术指标
        """
        # 基础价格数据
        self.close = self.data.close
        self.open = self.data.open
        self.high = self.data.high
        self.low = self.data.low
        
        # 1. 自定义加权价格 A0
        self.A0 = (3 * self.close + self.low + self.open + self.high) / 6
        
        # 2. 加权移动平均线 X (21日加权平均)
        self.X = bt.indicators.WeightedMovingAverage(self.A0, period=self.params.p)
        
        # 3. 动量指标 MTM
        self.MTM = self.close - bt.indicators.Delay(self.close, period=1)
        
        # 4. 动向指标 DX
        abs_mtm = bt.indicators.Abs(self.MTM)
        ema_mtm = bt.indicators.EMA(self.MTM, period=6)
        ema_abs_mtm = bt.indicators.EMA(abs_mtm, period=6)
        
        # 避免除零错误
        self.DX = bt.indicators.DivByZero(
            100 * bt.indicators.EMA(ema_mtm, period=6),
            bt.indicators.EMA(ema_abs_mtm, period=6),
            zero=0.0
        )
        
        # 5. 控盘指标 ZK (主力控盘度)
        ema_s = bt.indicators.EMA(self.A0, period=self.params.s)
        ema_p = bt.indicators.EMA(self.A0, period=self.params.p)
        self.ZK = 100 * (ema_s - ema_p) / ema_p
        
        # 6. 波段买卖指标 XG
        self.XG = bt.indicators.EMA(self.ZK, period=self.params.m1)
        
        # 7. 趋势指标 QS
        self.QS = bt.indicators.EMA(self.XG, period=self.params.m1)
        
        # 8. 涨跌停判断
        self.is_limit_up = (self.close / bt.indicators.Delay(self.close, period=1) - 1) >= 0.095
        self.is_limit_down = (self.close / bt.indicators.Delay(self.close, period=1) - 1) <= -0.095
        
        # 9. 成交量指标
        self.volume_ma = bt.indicators.SimpleMovingAverage(self.data.volume, period=5)
    
    def get_strategy_name(self) -> str:
        return "advanced"
    
    def get_strategy_description(self) -> str:
        return "高级综合技术指标策略：基于多种技术指标的综合判断进行交易"
    
    def next(self):
        """
        策略主逻辑
        """
        # 如果有未完成的订单，跳过
        if self.order:
            return
        
        # 跳过涨跌停
        if self.is_limit_up[0] or self.is_limit_down[0]:
            return
        
        # 获取当前指标值
        current_price = self.close[0]
        dx_value = self.DX[0] if len(self.DX) > 0 else 0
        zk_value = self.ZK[0] if len(self.ZK) > 0 else 0
        xg_value = self.XG[0] if len(self.XG) > 0 else 0
        qs_value = self.QS[0] if len(self.QS) > 0 else 0
        
        # 获取当前持仓
        if not self.position:
            # 没有持仓，检查买入信号
            buy_conditions = [
                current_price > self.X[0],  # 价格在加权均线之上
                dx_value > 0,  # 动向指标为正
                zk_value > 0,  # 控盘指标为正（主力控盘）
                xg_value > qs_value,  # 波段指标上升
                self.data.volume[0] > self.volume_ma[0] * 1.1,  # 成交量放大
            ]
            
            if all(buy_conditions):
                self.log(f'买入信号: 价格={current_price:.2f}, '
                        f'DX={dx_value:.2f}, ZK={zk_value:.2f}, '
                        f'XG={xg_value:.2f}, QS={qs_value:.2f}')
                
                # 买入
                self.order = self.buy()
        
        else:
            # 有持仓，检查卖出信号
            sell_conditions = [
                current_price < self.X[0],  # 价格跌破加权均线
                dx_value < -10,  # 动向指标明显为负
                zk_value < -5,  # 控盘指标为负（主力出货）
                xg_value < qs_value,  # 波段指标下降
            ]
            
            # 满足任意两个卖出条件就卖出
            if sum(sell_conditions) >= 2:
                self.log(f'卖出信号: 价格={current_price:.2f}, '
                        f'DX={dx_value:.2f}, ZK={zk_value:.2f}, '
                        f'XG={xg_value:.2f}, QS={qs_value:.2f}')
                
                # 卖出
                self.order = self.sell()
            
            # 止损：亏损超过10%
            elif self.buy_price and (current_price / self.buy_price - 1) < -0.10:
                self.log(f'止损卖出: 价格={current_price:.2f}, '
                        f'买入价={self.buy_price:.2f}, '
                        f'亏损={((current_price / self.buy_price - 1) * 100):.2f}%')
                
                self.order = self.sell()