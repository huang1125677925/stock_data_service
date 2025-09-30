#!/usr/bin/env python3
"""
乖离率(BIAS)指标交易策略
基于乖离率指标的超买超卖进行买卖
"""

import backtrader as bt
from .base_strategy import BaseQuantStrategy, register_strategy


class BIASIndicator(bt.Indicator):
    """
    乖离率(BIAS)指标
    BIAS = (收盘价 - N日移动平均价) / N日移动平均价 * 100
    """
    lines = ('bias',)
    params = (('period', 20),)
    
    def __init__(self):
        # 计算移动平均线
        self.ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.period
        )
        
    def next(self):
        # 计算乖离率
        if self.ma[0] != 0:
            self.lines.bias[0] = ((self.data.close[0] - self.ma[0]) / self.ma[0]) * 100
        else:
            self.lines.bias[0] = 0.0


@register_strategy
class BIASStrategy(BaseQuantStrategy):
    _strategy_name = 'bias'
    _strategy_description = '乖离率指标交易策略'
    _strategy_params = {
        'period': {'type': 'int', 'default': 20, 'description': 'BIAS计算周期'},
        'oversold': {'type': 'float', 'default': -10.0, 'description': '超卖阈值'},
        'overbought': {'type': 'float', 'default': 10.0, 'description': '超买阈值'}
    }
    """
    乖离率(BIAS)指标交易策略
    
    策略逻辑：
    1. 当BIAS从超卖区域（<-10%）向上突破时买入
    2. 当BIAS从超买区域（>10%）向下突破时卖出
    3. BIAS在-10%到10%之间时保持观望
    
    乖离率反映股价偏离移动平均线的程度，正值表示股价高于均线，负值表示股价低于均线
    """
    
    params = dict(
        period=20,          # BIAS计算周期
        oversold=-10.0,     # 超卖阈值（负值）
        overbought=10.0,    # 超买阈值（正值）
        printlog=True
    )
    
    def init_indicators(self):
        """
        初始化技术指标
        """
        # 乖离率指标
        self.bias = BIASIndicator(
            self.data,
            period=self.params.period
        )
        
        # 移动平均线（用于显示）
        self.ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.period
        )
        
        # 初始化指标数据收集结构
        self.indicator_data = {
            'bias': [],     # 乖离率指标
            'ma': []        # 移动平均线
        }
    
    def get_strategy_name(self) -> str:
        return "bias"
    
    def get_strategy_description(self) -> str:
        return "乖离率指标交易策略：基于乖离率指标的超买超卖区域进行买卖"
    
    def next(self):
        """
        策略主逻辑
        """
        # 首先调用父类的next方法来记录历史数据
        super().next()
        
        # 如果有未完成的订单，跳过
        if self.order:
            return
        
        # 获取当前BIAS值
        current_bias = self.bias[0]
        
        # 需要至少有一个历史BIAS值才能判断趋势
        if len(self.bias) < 2:
            return
        
        prev_bias = self.bias[-1]
        
        # 获取当前持仓
        if not self.position:
            # 没有持仓，检查买入信号
            # BIAS从超卖区域向上突破
            if prev_bias <= self.params.oversold and current_bias > self.params.oversold:
                
                self.log(f'BIAS买入信号: 价格={self.data.close[0]:.2f}, '
                        f'BIAS={current_bias:.2f}%, 前值={prev_bias:.2f}%, '
                        f'均线={self.ma[0]:.2f}, 超卖阈值={self.params.oversold}%')
                
                # 全仓买入：计算可买入的最大股数
                cash = self.broker.get_cash()
                current_price = self.data.close[0]
                
                # 预留5%的资金作为安全边际
                available_cash = cash * 0.95
                
                # 计算最大可买股数
                max_shares = int(available_cash / current_price)
                
                # 确保至少能买入100股（1手）
                if max_shares >= 100:
                    # 按100股的整数倍买入
                    max_shares = (max_shares // 100) * 100
                    
                    self.log(f'BIAS全仓买入: 总资金={cash:.2f}, 可用资金={available_cash:.2f}, '
                            f'股价={current_price:.2f}, 买入股数={max_shares}')
                    self.order = self.buy(size=max_shares)
                else:
                    self.log(f'资金不足: 总资金={cash:.2f}, 股价={current_price:.2f}, '
                            f'无法买入最小单位(100股)，需要资金={current_price * 100:.2f}')
        
        else:
            # 有持仓，检查卖出信号
            # BIAS从超买区域向下突破
            if prev_bias >= self.params.overbought and current_bias < self.params.overbought:
                self.log(f'BIAS卖出信号: 价格={self.data.close[0]:.2f}, '
                        f'BIAS={current_bias:.2f}%, 前值={prev_bias:.2f}%, '
                        f'均线={self.ma[0]:.2f}, 超买阈值={self.params.overbought}%')
                
                # 全仓卖出：卖出所有持仓
                position_size = self.position.size
                if position_size > 0:
                    self.log(f'BIAS全仓卖出: 当前持仓={position_size}')
                    self.order = self.sell(size=position_size)
    
    def collect_indicator_data(self):
        """
        收集指标数据
        """
        try:
            # 收集BIAS指标数据
            self.indicator_data['bias'].append(float(self.bias[0]) if len(self.bias) > 0 else None)
            self.indicator_data['ma'].append(float(self.ma[0]) if len(self.ma) > 0 else None)
        except Exception as e:
            self.log(f'收集指标数据时出错: {str(e)}')