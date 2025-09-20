#!/usr/bin/env python3
"""
最简单可产生成交点的策略
- 价格上穿/下穿简单移动平均线作为买卖信号
"""

import backtrader as bt
from .base_strategy import BaseQuantStrategy, register_strategy


@register_strategy
class MinimalStrategy(BaseQuantStrategy):
    _strategy_name = 'minimal'
    _strategy_description = '最简单均线策略：收盘价上穿均线买入，下穿均线卖出'
    _strategy_params = {
        'period': {'type': 'int', 'default': 10, 'description': '均线周期'}
    }

    # 策略参数
    params = dict(
        period=10,
        printlog=True,
    )

    def init_indicators(self):
        """
        初始化技术指标：简单移动平均线 + 价格与均线的交叉
        """
        self.sma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.period)
        self.crossover = bt.indicators.CrossOver(self.data.close, self.sma)

    def get_strategy_name(self) -> str:
        return 'minimal'

    def get_strategy_description(self) -> str:
        return '最简单均线策略：价格上穿均线买入，下穿均线卖出'

    def next(self):
        """
        策略主逻辑：
        - 未持仓且价格上穿均线(金叉)：买入
        - 已持仓且价格下穿均线(死叉)：卖出
        """
        if self.order:
            return

        price = self.data.close[0]

        if not self.position:
            if self.crossover > 0:  # 上穿
                self.log(f'买入信号: 价格={price:.2f}, 均线={self.sma[0]:.2f}')
                self.order = self.buy()
        else:
            if self.crossover < 0:  # 下穿
                self.log(f'卖出信号: 价格={price:.2f}, 均线={self.sma[0]:.2f}')
                self.order = self.sell()