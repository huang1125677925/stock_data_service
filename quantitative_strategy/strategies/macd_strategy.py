#!/usr/bin/env python3
"""
MACD指标交易策略
基于MACD指标的金叉死叉进行买卖
"""

import backtrader as bt
from .base_strategy import BaseQuantStrategy, register_strategy


@register_strategy
class MACDStrategy(BaseQuantStrategy):
    _strategy_name = 'macd'
    _strategy_description = 'MACD指标交易策略'
    _strategy_params = {
        'fast_period': {'type': 'int', 'default': 12, 'description': '快速EMA周期'},
        'slow_period': {'type': 'int', 'default': 26, 'description': '慢速EMA周期'},
        'signal_period': {'type': 'int', 'default': 9, 'description': '信号线周期'}
    }
    """
    MACD指标交易策略
    
    策略逻辑：
    1. 当MACD线上穿信号线时买入（金叉）
    2. 当MACD线下穿信号线时卖出（死叉）
    3. 可选择结合MACD柱状图的正负变化
    """
    
    params = dict(
        fast_period=12,     # 快速EMA周期
        slow_period=26,     # 慢速EMA周期
        signal_period=9,    # 信号线周期
        printlog=True
    )
    
    def init_indicators(self):
        """
        初始化技术指标
        """
        # MACD指标
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.fast_period,
            period_me2=self.params.slow_period,
            period_signal=self.params.signal_period
        )
        
        # MACD柱状图（macd - signal）
        self.macd_histo = bt.indicators.MACDHisto(
            self.data.close,
            period_me1=self.params.fast_period,
            period_me2=self.params.slow_period,
            period_signal=self.params.signal_period
        )
        
        # MACD交叉信号
        self.crossover = bt.indicators.CrossOver(
            self.macd.macd, self.macd.signal
        )
        
        # 初始化指标数据收集结构
        self.indicator_data = {
            'macd': [],         # MACD线
            'signal': [],       # 信号线
            'histo': [],        # 柱状图
            'crossover': []     # 交叉信号
        }
    
    def get_strategy_name(self) -> str:
        return "macd"
    
    def get_strategy_description(self) -> str:
        return "MACD指标交易策略：基于MACD线与信号线的金叉死叉进行买卖"
    
    def next(self):
        """
        策略主逻辑
        """
        # 首先调用父类的next方法来记录历史数据
        super().next()
        
        # 如果有未完成的订单，跳过
        if self.order:
            return
        
        # 获取当前持仓
        if not self.position:
            # 没有持仓，检查买入信号
            if self.crossover > 0:  # MACD金叉
                
                self.log(f'MACD买入信号: 价格={self.data.close[0]:.2f}, '
                        f'MACD={self.macd.macd[0]:.4f}, '
                        f'信号线={self.macd.signal[0]:.4f}, '
                        f'柱状图={self.macd_histo.histo[0]:.4f}')
                
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
                    
                    self.log(f'MACD全仓买入: 总资金={cash:.2f}, 可用资金={available_cash:.2f}, '
                            f'股价={current_price:.2f}, 买入股数={max_shares}')
                    self.order = self.buy(size=max_shares)
                else:
                    self.log(f'资金不足: 总资金={cash:.2f}, 股价={current_price:.2f}, '
                            f'无法买入最小单位(100股)，需要资金={current_price * 100:.2f}')
        
        else:
            # 有持仓，检查卖出信号
            if self.crossover < 0:  # MACD死叉
                self.log(f'MACD卖出信号: 价格={self.data.close[0]:.2f}, '
                        f'MACD={self.macd.macd[0]:.4f}, '
                        f'信号线={self.macd.signal[0]:.4f}, '
                        f'柱状图={self.macd_histo.histo[0]:.4f}')
                
                # 全仓卖出：卖出所有持仓
                position_size = self.position.size
                if position_size > 0:
                    self.log(f'MACD全仓卖出: 当前持仓={position_size}')
                    self.order = self.sell(size=position_size)
    
    def collect_indicator_data(self):
        """
        收集指标数据
        """
        try:
            # 收集MACD指标数据
            self.indicator_data['macd'].append(float(self.macd.macd[0]) if len(self.macd.macd) > 0 else None)
            self.indicator_data['signal'].append(float(self.macd.signal[0]) if len(self.macd.signal) > 0 else None)
            self.indicator_data['histo'].append(float(self.macd_histo.histo[0]) if len(self.macd_histo.histo) > 0 else None)
            self.indicator_data['crossover'].append(float(self.crossover[0]) if len(self.crossover) > 0 else None)
        except Exception as e:
            self.log(f'收集指标数据时出错: {str(e)}')