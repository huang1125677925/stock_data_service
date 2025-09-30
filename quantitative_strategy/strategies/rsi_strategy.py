#!/usr/bin/env python3
"""
RSI指标交易策略
基于相对强弱指标的超买超卖进行买卖
"""

import backtrader as bt
from .base_strategy import BaseQuantStrategy, register_strategy


@register_strategy
class RSIStrategy(BaseQuantStrategy):
    _strategy_name = 'rsi'
    _strategy_description = 'RSI指标交易策略'
    _strategy_params = {
        'period': {'type': 'int', 'default': 14, 'description': 'RSI计算周期'},
        'oversold': {'type': 'float', 'default': 30.0, 'description': '超卖阈值'},
        'overbought': {'type': 'float', 'default': 70.0, 'description': '超买阈值'}
    }
    """
    RSI指标交易策略
    
    策略逻辑：
    1. 当RSI从超卖区域（<30）向上突破时买入
    2. 当RSI从超买区域（>70）向下突破时卖出
    3. RSI在30-70之间时保持观望
    """
    
    params = dict(
        period=14,          # RSI计算周期
        oversold=30.0,      # 超卖阈值
        overbought=70.0,    # 超买阈值
        printlog=True
    )
    
    def init_indicators(self):
        """
        初始化技术指标
        """
        # RSI指标
        self.rsi = bt.indicators.RSI(
            self.data.close,
            period=self.params.period
        )
        
        # 记录前一个RSI值用于判断突破
        self.rsi_prev = None
        
        # 初始化指标数据收集结构
        self.indicator_data = {
            'rsi': []      # RSI指标
        }
    
    def get_strategy_name(self) -> str:
        return "rsi"
    
    def get_strategy_description(self) -> str:
        return "RSI指标交易策略：基于相对强弱指标的超买超卖区域进行买卖"
    
    def next(self):
        """
        策略主逻辑
        """
        # 首先调用父类的next方法来记录历史数据
        super().next()
        
        # 如果有未完成的订单，跳过
        if self.order:
            return
        
        # 获取当前RSI值
        current_rsi = self.rsi[0]
        
        # 需要至少有一个历史RSI值才能判断趋势
        if len(self.rsi) < 2:
            return
        
        prev_rsi = self.rsi[-1]
        
        # 获取当前持仓
        if not self.position:
            # 没有持仓，检查买入信号
            # RSI从超卖区域向上突破
            if prev_rsi <= self.params.oversold and current_rsi > self.params.oversold:
                
                self.log(f'RSI买入信号: 价格={self.data.close[0]:.2f}, '
                        f'RSI={current_rsi:.2f}, 前值={prev_rsi:.2f}, '
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
                    
                    self.log(f'RSI全仓买入: 总资金={cash:.2f}, 可用资金={available_cash:.2f}, '
                            f'股价={current_price:.2f}, 买入股数={max_shares}')
                    self.order = self.buy(size=max_shares)
                else:
                    self.log(f'资金不足: 总资金={cash:.2f}, 股价={current_price:.2f}, '
                            f'无法买入最小单位(100股)，需要资金={current_price * 100:.2f}')
        
        else:
            # 有持仓，检查卖出信号
            # RSI从超买区域向下突破
            if prev_rsi >= self.params.overbought and current_rsi < self.params.overbought:
                self.log(f'RSI卖出信号: 价格={self.data.close[0]:.2f}, '
                        f'RSI={current_rsi:.2f}, 前值={prev_rsi:.2f}, '
                        f'超买阈值={self.params.overbought}')
                
                # 全仓卖出：卖出所有持仓
                position_size = self.position.size
                if position_size > 0:
                    self.log(f'RSI全仓卖出: 当前持仓={position_size}')
                    self.order = self.sell(size=position_size)
    
    def collect_indicator_data(self):
        """
        收集指标数据
        """
        try:
            # 收集RSI指标数据
            self.indicator_data['rsi'].append(float(self.rsi[0]) if len(self.rsi) > 0 else None)
        except Exception as e:
            self.log(f'收集指标数据时出错: {str(e)}')