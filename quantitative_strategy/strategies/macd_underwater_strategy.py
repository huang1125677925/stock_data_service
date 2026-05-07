#!/usr/bin/env python3
"""
MACD水下金叉交易策略
基于MACD水下金叉买入，跌破5日线卖出
"""

import backtrader as bt
from .base_strategy import BaseQuantStrategy, register_strategy


@register_strategy
class MACDUnderwaterStrategy(BaseQuantStrategy):
    """
    MACD水下金叉交易策略
    
    策略逻辑：
    1. 买入条件：MACD线在0轴下方且MACD线上穿信号线（水下金叉）
    2. 卖出条件：股价跌破5日均线
    3. 采用全仓买入策略
    
    参数说明：
    - fast_period: 快速EMA周期，默认12
    - slow_period: 慢速EMA周期，默认26
    - signal_period: 信号线周期，默认9
    - ma5_period: 5日均线周期，默认5
    """
    
    _strategy_name = 'macd_underwater'
    _strategy_description = 'MACD水下金叉交易策略'
    _strategy_params = {
        'fast_period': {'type': 'int', 'default': 12, 'description': '快速EMA周期'},
        'slow_period': {'type': 'int', 'default': 26, 'description': '慢速EMA周期'},
        'signal_period': {'type': 'int', 'default': 9, 'description': '信号线周期'},
        'ma5_period': {'type': 'int', 'default': 5, 'description': '5日均线周期'}
    }
    
    params = dict(
        fast_period=12,     # 快速EMA周期
        slow_period=26,     # 慢速EMA周期
        signal_period=9,    # 信号线周期
        ma5_period=5,       # 5日均线周期
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
        
        # 5日均线
        self.ma5 = bt.indicators.SimpleMovingAverage(
            self.data.close, 
            period=self.params.ma5_period
        )
        
        # MACD交叉信号
        self.crossover = bt.indicators.CrossOver(
            self.macd.macd, self.macd.signal
        )
        
        # 价格与5日均线的交叉信号
        self.price_ma5_cross = bt.indicators.CrossOver(
            self.data.close, self.ma5
        )
        
        # 初始化指标数据收集结构
        self.indicator_data = {
            'macd': [],         # MACD线
            'signal': [],       # 信号线
            'histo': [],        # 柱状图
            'ma5': [],          # 5日均线
            'crossover': [],    # MACD交叉信号
            'price_ma5_cross': []  # 价格与5日均线交叉信号
        }
    
    def get_strategy_name(self) -> str:
        """
        获取策略名称
        
        Returns:
            str: 策略名称
        """
        return "macd_underwater"
    
    def get_strategy_description(self) -> str:
        """
        获取策略描述
        
        Returns:
            str: 策略描述
        """
        return "MACD水下金叉交易策略：MACD水下金叉买入，跌破5日线卖出"
    
    def next(self):
        """
        策略主逻辑
        
        执行每个交易日的策略判断：
        1. 检查买入信号：MACD水下金叉
        2. 检查卖出信号：跌破5日均线
        """
        # 首先调用父类的next方法来记录历史数据
        super().next()
        
        # 如果有未完成的订单，跳过
        if self.order:
            return
        
        # 获取当前持仓
        if not self.position:
            # 没有持仓，检查买入信号
            # 条件：MACD线在0轴下方且发生金叉
            if (self.crossover > 0 and  # MACD金叉
                self.macd.macd[0] < 0):  # MACD线在0轴下方（水下）
                
                self.log(f'MACD水下金叉买入信号: 价格={self.data.close[0]:.2f}, '
                        f'MACD={self.macd.macd[0]:.4f}, '
                        f'信号线={self.macd.signal[0]:.4f}, '
                        f'5日均线={self.ma5[0]:.2f}')
                
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
                    
                    self.log(f'MACD水下金叉全仓买入: 总资金={cash:.2f}, 可用资金={available_cash:.2f}, '
                            f'股价={current_price:.2f}, 买入股数={max_shares}')
                    self.order = self.buy(size=max_shares)
                else:
                    self.log(f'资金不足: 总资金={cash:.2f}, 股价={current_price:.2f}, '
                            f'无法买入最小单位(100股)，需要资金={current_price * 100:.2f}')
        
        else:
            # 有持仓，检查卖出信号
            # 条件：股价跌破5日均线
            if self.price_ma5_cross < 0:  # 价格下穿5日均线
                self.log(f'跌破5日线卖出信号: 价格={self.data.close[0]:.2f}, '
                        f'5日均线={self.ma5[0]:.2f}, '
                        f'MACD={self.macd.macd[0]:.4f}')
                
                # 全仓卖出：卖出所有持仓
                position_size = self.position.size
                if position_size > 0:
                    self.log(f'跌破5日线全仓卖出: 当前持仓={position_size}')
                    self.order = self.sell(size=position_size)
    
    def collect_indicator_data(self):
        """
        收集指标数据
        
        收集MACD、5日均线等技术指标的历史数据，
        用于后续的策略分析和可视化展示
        """
        try:
            # 收集MACD指标数据
            self.indicator_data['macd'].append(
                float(self.macd.macd[0]) if len(self.macd.macd) > 0 else None
            )
            self.indicator_data['signal'].append(
                float(self.macd.signal[0]) if len(self.macd.signal) > 0 else None
            )
            self.indicator_data['histo'].append(
                float(self.macd_histo.histo[0]) if len(self.macd_histo.histo) > 0 else None
            )
            
            # 收集5日均线数据
            self.indicator_data['ma5'].append(
                float(self.ma5[0]) if len(self.ma5) > 0 else None
            )
            
            # 收集交叉信号数据
            self.indicator_data['crossover'].append(
                float(self.crossover[0]) if len(self.crossover) > 0 else None
            )
            self.indicator_data['price_ma5_cross'].append(
                float(self.price_ma5_cross[0]) if len(self.price_ma5_cross) > 0 else None
            )
            
        except Exception as e:
            self.log(f'收集指标数据时出错: {str(e)}')