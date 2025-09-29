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
        'short_period': {'type': 'int', 'default': 20, 'description': '短期均线周期'},
        'long_period': {'type': 'int', 'default': 50, 'description': '长期均线周期'}
    }
    """
    移动平均线交叉策略
    
    策略逻辑：
    1. 当短期均线上穿长期均线时买入（金叉）
    2. 当短期均线下穿长期均线时卖出（死叉）
    """
    
    params = dict(
        short_period=20,    # 短期均线周期
        long_period=50,    # 长期均线周期
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
        
        # 交叉信号
        self.crossover = bt.indicators.CrossOver(
            self.ma_short, self.ma_long
        )
        
        # 初始化指标数据收集结构
        self.indicator_data = {
            'ma_short': [],      # 短期移动平均线
            'ma_long': [],       # 长期移动平均线
            'crossover': []      # 交叉信号
        }
    
    def get_strategy_name(self) -> str:
        return "ma_cross"
    
    def get_strategy_description(self) -> str:
        return "移动平均线交叉策略：基于短期和长期移动平均线的金叉死叉进行买卖"
    
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
            if self.crossover > 0:  # 金叉
                
                self.log(f'买入信号: 价格={self.data.close[0]:.2f}, '
                        f'短期均线={self.ma_short[0]:.2f}, '
                        f'长期均线={self.ma_long[0]:.2f}')
                
                # 全仓买入：计算可买入的最大股数
                cash = self.broker.get_cash()
                current_price = self.data.close[0]
                
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
            if self.crossover < 0:  # 死叉
                self.log(f'卖出信号: 价格={self.data.close[0]:.2f}, '
                        f'短期均线={self.ma_short[0]:.2f}, '
                        f'长期均线={self.ma_long[0]:.2f}')
                
                # 全仓卖出：卖出所有持仓
                position_size = self.position.size
                if position_size > 0:
                    self.log(f'全仓卖出: 当前持仓={position_size}')
                    self.order = self.sell(size=position_size)
    
    def collect_indicator_data(self):
        """
        收集指标数据
        """
        try:
            # 收集移动平均线数据
            self.indicator_data['ma_short'].append(float(self.ma_short[0]) if len(self.ma_short) > 0 else None)
            self.indicator_data['ma_long'].append(float(self.ma_long[0]) if len(self.ma_long) > 0 else None)
            self.indicator_data['crossover'].append(float(self.crossover[0]) if len(self.crossover) > 0 else None)
        except Exception as e:
            self.log(f'收集指标数据时出错: {str(e)}')