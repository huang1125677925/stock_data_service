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
        - 未持仓且价格上穿均线(金叉)：全仓买入
        - 已持仓且价格下穿均线(死叉)：全仓卖出
        """
        # 首先调用父类的next方法来记录历史数据
        super().next()
        
        # 如果有未完成的订单，跳过
        if self.order:
            return

        # 获取当前价格和均线值
        current_price = self.data.close[0]
        sma_value = self.sma[0]

        # 获取当前持仓
        if not self.position:
            # 没有持仓，检查买入信号
            if self.crossover > 0:  # 价格上穿均线（金叉）
                
                self.log(f'买入信号: 价格={current_price:.2f}, '
                        f'均线={sma_value:.2f}')
                
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
            if self.crossover < 0:  # 价格下穿均线（死叉）
                self.log(f'卖出信号: 价格={current_price:.2f}, '
                        f'均线={sma_value:.2f}')
                
                # 全仓卖出：卖出所有持仓
                position_size = self.position.size
                if position_size > 0:
                    self.log(f'全仓卖出: 当前持仓={position_size}')
                    self.order = self.sell(size=position_size)