#!/usr/bin/env python3
"""
10日均线趋势分批仓位管理策略

功能：
- 技术分析侧：要求均线多头排列（5>10>20），并在调整后收盘价首次上穿10日均线触发进场/加仓信号；
- 资金管理侧：采用固定分批开仓与加仓计划，开仓30%，随后按 30%/20%/10% 继续加仓；
- 风险控制：采用跟踪止损——收盘价跌破10日均线或相对成本亏损达10%，首次触发卖出当前仓位的一半，若连续第二次仍触发则清仓；
- 止盈：与止损触发位一致（跌破10日线/回撤超过10%时分批减仓），视为保护利润的动态止盈。

参数：
- fast_period(int)：快速均线周期，默认5；
- mid_period(int)：中期均线周期，默认10（用于触发信号的均线）；
- slow_period(int)：慢速均线周期，默认20；
- initial_pct(float)：首次开仓目标占比，默认0.30；
- add_plan(list[float])：后续加仓占比序列，默认[0.30, 0.20, 0.10]；
- stop_loss_pct(float)：相对成本的最大允许亏损比例，默认10.0；
- lot_size(int)：最小交易单位（手），默认100；
- printlog(bool)：是否打印日志。

返回值：
- 通过基类的观测器数据收集（broker/buysell/trades/timereturn/drawdown/benchmark），用于后续可视化与回测分析。

事件：
- 进场事件：均线多头排列且收盘价上穿10日均线（crossover>0）；
- 加仓事件：再次满足进场事件（每次触发按剩余加仓计划执行）；
- 止损/止盈事件：收盘价跌破10日均线或相对成本亏损达到设定阈值（第一次触发减半，连续第二次触发清仓）。
"""

import backtrader as bt
from .base_strategy import BaseQuantStrategy, register_strategy


@register_strategy
class MATenTrailingStrategy(BaseQuantStrategy):
    """
    10日均线趋势分批仓位管理策略实现类
    """

    _strategy_name = 'ma_10_trailing_strategy'
    _strategy_description = '10日均线趋势分批仓位管理：多头排列+上穿10日线进场，加仓30/20/10，跌破10日线或亏损≥10%分批止损'
    _strategy_params = {
        'fast_period': {'type': 'int', 'default': 5, 'description': '快速均线周期'},
        'mid_period': {'type': 'int', 'default': 10, 'description': '中期均线周期（触发线）'},
        'slow_period': {'type': 'int', 'default': 20, 'description': '慢速均线周期'},
        'initial_pct': {'type': 'float', 'default': 0.30, 'description': '首次开仓目标占比'},
        'add_plan': {'type': 'list', 'default': [0.30, 0.20, 0.10], 'description': '后续加仓占比序列'},
        'stop_loss_pct': {'type': 'float', 'default': 10.0, 'description': '最大允许亏损百分比'},
        'lot_size': {'type': 'int', 'default': 100, 'description': '最小交易单位（股/手）'},
    }

    # backtrader参数
    params = dict(
        fast_period=5,
        mid_period=10,
        slow_period=20,
        initial_pct=0.30,
        add_plan=(0.30, 0.20, 0.10),
        stop_loss_pct=10.0,
        lot_size=100,
        printlog=True,
    )

    # 运行期变量
    def __init__(self):
        super().__init__()
        # 分批相关
        self.total_target_shares = 0  # 以首次进场价格计算的总目标可买股数（按资金与安全边际）
        self.add_index = 0            # 已执行到的加仓步数索引
        self.stop_consecutive = 0     # 连续触发止损次数计数（0/1/2）

    def init_indicators(self):
        """
        初始化技术指标：SMA(5/10/20)与收盘价上穿10日线的交叉信号
        """
        self.sma_fast = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.fast_period)
        self.sma_mid = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.mid_period)
        self.sma_slow = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.slow_period)
        self.cross_mid = bt.indicators.CrossOver(self.data.close, self.sma_mid)

        # 指标数据收集结构
        self.indicator_data = {
            'sma_fast': [],
            'sma_mid': [],
            'sma_slow': [],
            'cross_mid': [],
            'drawdown_pct': [],
        }

    def get_strategy_name(self) -> str:
        return self._strategy_name

    def get_strategy_description(self) -> str:
        return self._strategy_description

    # ======= 核心交易逻辑 =======
    def next(self):
        """
        策略主逻辑：
        - 记录基础数据（由基类完成）；
        - 多头排列+上穿10日线进场与加仓；
        - 跌破10日线或亏损≥10%分批止损/止盈。
        """
        super().next()

        # 若有未完成订单，跳过
        if self.order:
            return

        # 当前价格与基础条件
        price = float(self.data.close[0])
        bullish = (self.sma_fast[0] > self.sma_mid[0] > self.sma_slow[0])
        entry_signal = bullish and (self.cross_mid[0] > 0)  # 首次确认上穿10日线

        # 计算相对成本的浮动盈亏
        dd_pct = 0.0
        if self.position.size > 0:
            avg_cost = float(self.position.price)
            dd_pct = (price - avg_cost) / avg_cost * 100.0

        stop_trigger = False
        if self.position.size > 0:
            below_ma = (self.data.close[0] < self.sma_mid[0])
            loss_hit = (dd_pct <= -self.params.stop_loss_pct)
            stop_trigger = loss_hit

        # ===== 进场/加仓 =====
        if self.position.size == 0:
            # 没有持仓，仅在进场信号时首仓买入30%
            if entry_signal:
                cash = float(self.broker.get_cash())
                available_cash = cash * 0.95  # 预留5%
                # 以当前价格计算最大可买股数（按最小交易单位取整）
                max_shares = int(available_cash / price)
                max_shares = (max_shares // self.params.lot_size) * self.params.lot_size
                if max_shares <= 0:
                    self.log(f'资金不足，无法开仓：可用资金={available_cash:.2f}, 当前价={price:.2f}')
                    return

                # 建立总目标持仓与首仓规模
                self.total_target_shares = max_shares
                initial_size = int(max_shares * self.params.initial_pct)
                initial_size = (initial_size // self.params.lot_size) * self.params.lot_size
                initial_size = max(initial_size, self.params.lot_size)

                self.add_index = 0
                self.stop_consecutive = 0
                self.log(f'进场买入：目标总仓={self.total_target_shares}, 首仓={initial_size}, 价格={price:.2f}')
                self.order = self.buy(size=initial_size)

        else:
            # 已有持仓：处理加仓与止损/止盈
            if entry_signal and self.position.size < self.total_target_shares and self.add_index < len(self.params.add_plan):
                # 当前步计划规模（基于首次可买最大股数）
                plan_pct = float(self.params.add_plan[self.add_index])
                add_size = int(self.total_target_shares * plan_pct)
                add_size = (add_size // self.params.lot_size) * self.params.lot_size

                # 不超过目标总仓
                add_size = min(add_size, self.total_target_shares - int(self.position.size))
                if add_size > 0:
                    self.add_index += 1
                    self.stop_consecutive = 0  # 新的上穿信号出现，重置连续止损计数
                    self.log(f'加仓：第{self.add_index}次，加{add_size}股，价格={price:.2f}')
                    self.order = self.buy(size=add_size)

            # 止损/止盈（统一触发位）：跌破10日线或亏损≥阈值
            elif stop_trigger:
                if self.stop_consecutive == 0:
                    # 第一次触发：减半
                    sell_size = int(self.position.size * 0.5)
                    sell_size = (sell_size // self.params.lot_size) * self.params.lot_size
                    sell_size = max(sell_size, self.params.lot_size)  # 至少一个最小单位
                    sell_size = min(sell_size, int(self.position.size))
                    self.stop_consecutive = 1
                    self.log(f'止损/止盈第一次触发：减半卖出 {sell_size} 股，价格={price:.2f}，回撤={dd_pct:.2f}%')
                    self.order = self.sell(size=sell_size)
                else:
                    # 连续第二次触发：清仓
                    sell_size = int(self.position.size)
                    self.stop_consecutive = 2
                    self.add_index = 0
                    self.log(f'止损/止盈第二次触发：清仓卖出 {sell_size} 股，价格={price:.2f}，回撤={dd_pct:.2f}%')
                    self.order = self.sell(size=sell_size)
            else:
                # 无触发则清零连续止损计数
                self.stop_consecutive = 0

    def collect_indicator_data(self):
        """
        收集指标数据：5/10/20日均线、上穿信号值、相对成本的盈亏百分比。
        """
        try:
            self.indicator_data['sma_fast'].append(float(self.sma_fast[0]) if len(self.sma_fast) > 0 else None)
            self.indicator_data['sma_mid'].append(float(self.sma_mid[0]) if len(self.sma_mid) > 0 else None)
            self.indicator_data['sma_slow'].append(float(self.sma_slow[0]) if len(self.sma_slow) > 0 else None)
            self.indicator_data['cross_mid'].append(float(self.cross_mid[0]) if len(self.cross_mid) > 0 else None)

            if self.position.size > 0:
                price = float(self.data.close[0])
                avg_cost = float(self.position.price)
                dd_pct = (price - avg_cost) / avg_cost * 100.0
            else:
                dd_pct = 0.0
            self.indicator_data['drawdown_pct'].append(dd_pct)
        except Exception as e:
            self.log(f'收集指标数据时出错: {str(e)}')