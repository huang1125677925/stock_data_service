#!/usr/bin/env python3
"""
心理线(PSY)指标交易策略
基于心理线指标的超买超卖进行买卖
"""

import backtrader as bt
from .base_strategy import BaseQuantStrategy, register_strategy


class PSYIndicator(bt.Indicator):
    """
    心理线(PSY)指标
    PSY = N日内上涨天数 / N * 100
    """
    lines = ('psy',)
    params = (('period', 12),)
    
    def __init__(self):
        # 计算每日涨跌
        self.up_days = self.data.close > self.data.close(-1)
        
    def next(self):
        # 计算N日内上涨天数
        if len(self) < self.params.period:
            self.lines.psy[0] = 50.0  # 默认值
        else:
            up_count = sum(self.up_days.get(ago=i) for i in range(self.params.period))
            self.lines.psy[0] = (up_count / self.params.period) * 100


@register_strategy
class PSYStrategy(BaseQuantStrategy):
    _strategy_name = 'psy'
    _strategy_description = '心理线指标交易策略'
    _strategy_params = {
        'period': {'type': 'int', 'default': 12, 'description': 'PSY计算周期'},
        'oversold': {'type': 'float', 'default': 25.0, 'description': '超卖阈值'},
        'overbought': {'type': 'float', 'default': 75.0, 'description': '超买阈值'}
    }
    """
    心理线(PSY)指标交易策略
    
    策略逻辑：
    1. 当PSY从超卖区域（<25）向上突破时买入
    2. 当PSY从超买区域（>75）向下突破时卖出
    3. PSY在25-75之间时保持观望
    
    心理线反映市场心理状态，数值越高表示市场越乐观
    """
    
    params = dict(
        period=12,          # PSY计算周期
        oversold=25.0,      # 超卖阈值
        overbought=75.0,    # 超买阈值
        printlog=True
    )
    
    def init_indicators(self):
        """
        初始化技术指标
        """
        # 心理线指标
        self.psy = PSYIndicator(
            self.data,
            period=self.params.period
        )
    
    def get_strategy_name(self) -> str:
        return "psy"
    
    def get_strategy_description(self) -> str:
        return "心理线指标交易策略：基于心理线指标的超买超卖区域进行买卖"
    
    def next(self):
        """
        策略主逻辑
        """
        # 如果有未完成的订单，跳过
        if self.order:
            return
        
        # 获取当前PSY值
        current_psy = self.psy[0]
        
        # 需要至少有一个历史PSY值才能判断趋势
        if len(self.psy) < 2:
            return
        
        prev_psy = self.psy[-1]
        
        # 获取当前持仓
        if not self.position:
            # 没有持仓，检查买入信号
            # PSY从超卖区域向上突破
            if prev_psy <= self.params.oversold and current_psy > self.params.oversold:
                
                self.log(f'PSY买入信号: 价格={self.data.close[0]:.2f}, '
                        f'PSY={current_psy:.2f}, 前值={prev_psy:.2f}, '
                        f'超卖阈值={self.params.oversold}')
                
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
                    
                    self.log(f'PSY全仓买入: 总资金={cash:.2f}, 可用资金={available_cash:.2f}, '
                            f'股价={current_price:.2f}, 买入股数={max_shares}')
                    self.order = self.buy(size=max_shares)
                else:
                    self.log(f'资金不足: 总资金={cash:.2f}, 股价={current_price:.2f}, '
                            f'无法买入最小单位(100股)，需要资金={current_price * 100:.2f}')
        
        else:
            # 有持仓，检查卖出信号
            # PSY从超买区域向下突破
            if prev_psy >= self.params.overbought and current_psy < self.params.overbought:
                self.log(f'PSY卖出信号: 价格={self.data.close[0]:.2f}, '
                        f'PSY={current_psy:.2f}, 前值={prev_psy:.2f}, '
                        f'超买阈值={self.params.overbought}')
                
                # 全仓卖出：卖出所有持仓
                position_size = self.position.size
                if position_size > 0:
                    self.log(f'PSY全仓卖出: 当前持仓={position_size}')
                    self.order = self.sell(size=position_size)