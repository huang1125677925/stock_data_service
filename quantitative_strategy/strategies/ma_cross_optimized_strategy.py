#!/usr/bin/env python3
"""
移动平均线交叉优化策略（含止损/止盈/长期均线保护）

功能：
- 采用短期与长期简单移动平均线的金叉/死叉作为基础交易信号；
- 增加止损与止盈机制：根据持仓成本与当前收盘价的收益率进行风控；
- 增加长期均线保护：当收盘价低于长期均线时，触发卖出保护；
- 保留基础仓位管理逻辑：按95%可用资金，且按100股整数倍买入。

参数：
- short_period(int): 短期均线周期，默认20；
- long_period(int): 长期均线周期，默认50；
- stop_loss_pct(float): 止损百分比，默认8.0；
- take_profit_pct(float): 止盈百分比，默认15.0；
- lot_size(int): 最小交易单位（股/手），默认100；
- printlog(bool): 是否打印日志，默认True。

返回值：
- 策略执行过程中，将通过基类收集原始数据、观测器数据，并在本策略中收集指标数据
 供后续可视化与回测结果分析使用。

事件：
- 买入事件：短期均线上穿长期均线（金叉）；
- 卖出事件：满足任一条件即触发：
  1) 短期均线下穿长期均线（死叉）；
  2) 收盘价低于长期均线（长期均线保护）；
  3) 当前收益率 ≤ -stop_loss_pct（止损）；
  4) 当前收益率 ≥ take_profit_pct（止盈）。
"""

import backtrader as bt
from .base_strategy import BaseQuantStrategy, register_strategy


@register_strategy
class MACrossOptimizedStrategy(BaseQuantStrategy):
    """
    移动平均线交叉优化策略实现类

    功能：
    - 基于短期/长期简单移动平均线的金叉/死叉交易信号；
    - 增强风控：止损/止盈与长期均线保护；

    参数：
    - short_period(int): 短期均线周期；
    - long_period(int): 长期均线周期；
    - stop_loss_pct(float): 止损百分比；
    - take_profit_pct(float): 止盈百分比；
    - lot_size(int): 最小交易单位（股/手）；
    - printlog(bool): 是否打印日志；

    返回值：
    - 通过基类的观测器与记录机制返回完整的交易与指标数据集合；

    事件：
    - 买入：金叉；
    - 卖出：死叉 或 收盘价低于长期均线 或 触发止损/止盈。
    """

    _strategy_name = 'ma_cross_optimized'
    _strategy_description = '移动平均线交叉优化：含止损/止盈，收盘价低于长期均线时卖出'
    _strategy_params = {
        'short_period': {'type': 'int', 'default': 20, 'description': '短期均线周期'},
        'long_period': {'type': 'int', 'default': 50, 'description': '长期均线周期'},
        'stop_loss_pct': {'type': 'float', 'default': 8.0, 'description': '止损百分比'},
        'take_profit_pct': {'type': 'float', 'default': 15.0, 'description': '止盈百分比'},
        'lot_size': {'type': 'int', 'default': 100, 'description': '最小交易单位（股/手）'}
    }

    # backtrader参数
    params = dict(
        short_period=20,
        long_period=50,
        stop_loss_pct=8.0,
        take_profit_pct=15.0,
        lot_size=100,
        printlog=True,
    )

    def init_indicators(self):
        """
        初始化技术指标

        返回：无显式返回；初始化内部指标与数据收集结构
        """
        close = self.data.close

        # 简单移动平均线
        self.ma_short = bt.indicators.SimpleMovingAverage(close, period=self.params.short_period)
        self.ma_long = bt.indicators.SimpleMovingAverage(close, period=self.params.long_period)

        # 交叉信号（>0 金叉；<0 死叉）
        self.crossover = bt.indicators.CrossOver(self.ma_short, self.ma_long)

        # 指标数据收集结构
        self.indicator_data = {
            'ma_short': [],        # 短期均线
            'ma_long': [],         # 长期均线
            'crossover': [],       # 交叉信号
            'profit_pct': [],      # 当前持仓收益率
            'stop_loss_pct': [],   # 止损阈值
            'take_profit_pct': []  # 止盈阈值
        }

    def get_strategy_name(self) -> str:
        """获取策略名称"""
        return self._strategy_name

    def get_strategy_description(self) -> str:
        """获取策略描述"""
        return self._strategy_description

    def next(self):
        """
        策略主逻辑

        流程：
        - 记录原始数据（调用父类next）；
        - 无持仓：金叉触发全仓买入（95%资金，按lot_size取整）；
        - 有持仓：满足任一卖出事件（死叉/收盘价<长期均线/止损/止盈）触发全仓卖出。

        参数：无
        返回值：无（通过内部状态与记录体现结果）
        """
        # 记录数据
        super().next()

        # 若存在未完成订单，则跳过本周期
        if self.order:
            return

        current_price = float(self.data.close[0])

        if not self.position:
            # 买入条件：金叉
            if self.crossover > 0:
                self.log(
                    f'买入信号(金叉): 价格={current_price:.2f}, 短期均线={float(self.ma_short[0]):.2f}, 长期均线={float(self.ma_long[0]):.2f}'
                )

                # 资金与买入股数计算（保留原策略逻辑）
                cash = self.broker.get_cash()
                available_cash = cash * 0.95
                max_shares = int(available_cash / current_price)

                if max_shares >= self.params.lot_size:
                    max_shares = (max_shares // self.params.lot_size) * self.params.lot_size
                    self.log(
                        f'全仓买入: 总资金={cash:.2f}, 可用资金={available_cash:.2f}, 股价={current_price:.2f}, 买入股数={max_shares}'
                    )
                    self.order = self.buy(size=max_shares)
                else:
                    self.log(
                        f'资金不足: 总资金={cash:.2f}, 股价={current_price:.2f}, '
                        f'无法买入最小单位({self.params.lot_size}股)，需要资金={current_price * self.params.lot_size:.2f}'
                    )
        else:
            # 有持仓，评估卖出条件
            position_size = int(self.position.size)
            avg_cost = float(self.position.price) if self.position.price else current_price
            profit_pct = (current_price - avg_cost) / avg_cost * 100.0 if avg_cost > 0 else 0.0

            # 卖出条件集合
            long_ma_breach = current_price < float(self.ma_long[0])  # 收盘价低于长期均线
            dead_cross = self.crossover < 0                            # 死叉
            stop_loss_trigger = profit_pct <= -float(self.params.stop_loss_pct)
            take_profit_trigger = profit_pct >= float(self.params.take_profit_pct)

            if position_size > 0 and (dead_cross or long_ma_breach or stop_loss_trigger or take_profit_trigger):
                reason = []
                if dead_cross:
                    reason.append('死叉')
                if long_ma_breach:
                    reason.append('收盘价低于长期均线')
                if stop_loss_trigger:
                    reason.append(f'止损({profit_pct:.2f}%)≤-{self.params.stop_loss_pct}%')
                if take_profit_trigger:
                    reason.append(f'止盈({profit_pct:.2f}%)≥{self.params.take_profit_pct}%')

                self.log(
                    '卖出信号: ' +
                    f'价格={current_price:.2f}, 均线(短/长)={float(self.ma_short[0]):.2f}/{float(self.ma_long[0]):.2f}, ' +
                    f'收益率={profit_pct:.2f}%, 原因={'/'.join(reason)}'
                )
                self.order = self.sell(size=position_size)

            # 更新指标数据中的收益率（即使不触发卖出也记录）
            self.indicator_data['profit_pct'].append(profit_pct)
            self.indicator_data['stop_loss_pct'].append(float(self.params.stop_loss_pct))
            self.indicator_data['take_profit_pct'].append(float(self.params.take_profit_pct))

    def collect_indicator_data(self):
        """
        收集指标数据

        返回：无（数据进入 self.indicator_data）
        """
        try:
            self.indicator_data['ma_short'].append(float(self.ma_short[0]) if len(self.ma_short) > 0 else None)
            self.indicator_data['ma_long'].append(float(self.ma_long[0]) if len(self.ma_long) > 0 else None)
            self.indicator_data['crossover'].append(float(self.crossover[0]) if len(self.crossover) > 0 else None)

            # 若在next中未写入收益率（无持仓场景），补None占位
            if len(self.indicator_data['profit_pct']) < len(self.indicator_data['ma_short']):
                self.indicator_data['profit_pct'].append(None)
                self.indicator_data['stop_loss_pct'].append(float(self.params.stop_loss_pct))
                self.indicator_data['take_profit_pct'].append(float(self.params.take_profit_pct))
        except Exception as e:
            self.log(f'收集指标数据时出错: {str(e)}')