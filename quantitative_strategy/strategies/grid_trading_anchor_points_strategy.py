#!/usr/bin/env python3
"""
基准点移动网格策略（百分比触发）

功能：
- 用户指定初始基准价（如不指定则以首个收盘价作为基准）；
- 当价格较基准价下跌 x% 时买入；当价格较基准价上涨 y% 时卖出；
- 每次成交后，以本次成交价格作为新的基准价，继续按点差触发交易；
- 买入与卖出支持分别设置交易份额（股数），并遵守最小交易单位；
- 自动记录原始数据与指标数据（继承基类实现），便于后端/前端展示。

参数：
- initial_baseline(float|None): 初始基准价；None 表示使用首个收盘价，默认 None；
- buy_down_points(float): 较基准价下跌触发买入的百分比（%），默认 0.5；
- sell_up_points(float): 较基准价上涨触发卖出的百分比（%），默认 0.5；
- buy_qty(int): 每次买入的目标股数，默认 100；
- sell_qty(int): 每次卖出的目标股数，默认 100；
- lot_size(int): 最小交易单位（股/手），默认 100；
- safety_cash_pct(float): 买入时保留的现金比例，默认 0.05；
- printlog(bool): 是否打印日志，默认 True。

返回值：
- 回测完成后，结果对象包含完整观测器数据、原始数据与指标数据；
  前端可用于绘图与交易明细展示。

事件：
- 买入事件：当收盘价 <= 基准价 × (1 - buy_down_points/100) 时，按 buy_qty 下单；
- 卖出事件：当收盘价 >= 基准价 × (1 + sell_up_points/100) 时，按 sell_qty 下单；
- 成交事件：订单完成后将成交价格设为新的基准价；
- 资金不足事件：买入资金不足时不下单并记录日志；
- 持仓不足事件：卖出数量超过持仓时按剩余持仓卖出。
"""

import backtrader as bt
from typing import Dict, Any
from .base_strategy import BaseQuantStrategy, register_strategy


@register_strategy
class GridTradingAnchorPointsStrategy(BaseQuantStrategy):
    _strategy_name = 'grid_trading_anchor_points'
    _strategy_description = '基准点移动网格：按百分比相对基准低买高卖，每次成交价重置基准'
    _strategy_params: Dict[str, Any] = {
        'initial_baseline': {'type': 'float', 'default': None, 'description': '初始基准价；None则使用首个收盘价'},
        'buy_down_points': {'type': 'float', 'default': 0.5, 'description': '较基准价下跌触发买入的百分比（%）'},
        'sell_up_points': {'type': 'float', 'default': 0.5, 'description': '较基准价上涨触发卖出的百分比（%）'},
        'buy_qty': {'type': 'int', 'default': 100, 'description': '每次买入股数'},
        'sell_qty': {'type': 'int', 'default': 100, 'description': '每次卖出股数'},
        'lot_size': {'type': 'int', 'default': 100, 'description': '最小交易单位（股/手）'},
        'safety_cash_pct': {'type': 'float', 'default': 0.05, 'description': '买入保留现金比例'},
        'enable_double_on_consecutive_buy': {'type': 'int', 'default': 0, 'description': '连续买入加倍开关：1开启，0关闭'},
    }

    params = dict(
        initial_baseline=None,
        buy_down_points=0.5,
        sell_up_points=0.5,
        buy_qty=100,
        sell_qty=100,
        lot_size=100,
        safety_cash_pct=0.05,
        enable_double_on_consecutive_buy=0,
        printlog=True,
    )

    def init_indicators(self):
        """
        初始化策略状态与指标结构。
        - 维护当前基准价（成交后重置）；
        - 指标数据用于记录基准价、阈值与持仓等。
        """
        self.anchor_price = None
        self.lot_size = int(self.params.lot_size)
        self.buy_qty = int(self.params.buy_qty)
        self.sell_qty = int(self.params.sell_qty)
        self.last_action = None
        self.last_buy_size = 0

        self.indicator_data = {
            'anchor_price': [],
            'current_price': [],
            'buy_threshold': [],
            'sell_threshold': [],
            'position_size': [],
        }

    def get_strategy_name(self) -> str:
        return 'grid_trading_anchor_points'

    def get_strategy_description(self) -> str:
        return '基准点移动网格：相对基准按百分比低买高卖，每次以成交价重置基准'

    def _round_to_lot(self, shares: int) -> int:
        if self.lot_size <= 0:
            return max(1, shares)
        return (shares // self.lot_size) * self.lot_size

    def _can_buy_with_cash(self, price: float, desired_shares: int) -> int:
        cash = float(self.broker.get_cash())
        available_cash = cash * (1.0 - float(self.params.safety_cash_pct))
        max_shares = self._round_to_lot(int(available_cash / max(price, 1e-6)))
        return max(0, min(self._round_to_lot(desired_shares), max_shares))

    def notify_order(self, order):
        """
        订单回调：在成交完成时将成交价设为新的基准价（anchor_price）。
        """
        super().notify_order(order)
        try:
            if order.status in [order.Completed]:
                self.anchor_price = float(order.executed.price)
                self.log(f'重置基准价: anchor={self.anchor_price:.4f}')
                if order.isbuy():
                    self.last_action = 'buy'
                    try:
                        self.last_buy_size = int(order.executed.size)
                    except Exception:
                        pass
                else:
                    self.last_action = 'sell'
        except Exception:
            pass

    def next(self):
        """
        策略主逻辑：
        - 初始化基准价；
        - 计算买入/卖出阈值（相对基准的百分比偏移）；
        - 当收盘价越过阈值时执行对应方向交易，每个bar最多执行一次；
        - 成交完成后由 notify_order 重置基准价为成交价。
        """
        super().next()

        if self.order:
            return

        current_price = float(self.data.close[0])
        if current_price <= 0:
            return

        # 初始化基准价：使用参数initial_baseline或首个收盘价
        if self.anchor_price is None:
            init_base = self.params.initial_baseline
            try:
                init_base = float(init_base) if init_base is not None else None
            except Exception:
                init_base = None
            self.anchor_price = init_base if init_base and init_base > 0 else current_price
            self.log(f'初始化基准价: anchor={self.anchor_price:.4f}')
            # 先记录指标，下一bar开始交易
            self.indicator_data['anchor_price'].append(self.anchor_price)
            self.indicator_data['current_price'].append(current_price)
            down_pct = float(self.params.buy_down_points)
            up_pct = float(self.params.sell_up_points)
            self.indicator_data['buy_threshold'].append(self.anchor_price * (1.0 - down_pct / 100.0))
            self.indicator_data['sell_threshold'].append(self.anchor_price * (1.0 + up_pct / 100.0))
            self.indicator_data['position_size'].append(float(self.position.size or 0))
            return

        # 计算阈值
        down_pct = float(self.params.buy_down_points)
        up_pct = float(self.params.sell_up_points)
        buy_threshold = self.anchor_price * (1.0 - down_pct / 100.0)
        sell_threshold = self.anchor_price * (1.0 + up_pct / 100.0)

        acted = False

        # 买入触发
        if not acted and current_price <= buy_threshold:
            buy_shares = 0
            if int(self.params.enable_double_on_consecutive_buy) == 1 and self.last_action == 'buy' and self.last_buy_size >= self.lot_size:
                double_size = self._round_to_lot(self.last_buy_size * 2)
                single_size = self._round_to_lot(self.last_buy_size)
                if self._can_buy_with_cash(current_price, double_size) >= double_size:
                    buy_shares = double_size
                elif self._can_buy_with_cash(current_price, single_size) >= single_size:
                    buy_shares = single_size
                else:
                    buy_shares = 0
            else:
                buy_shares = self._can_buy_with_cash(current_price, self.buy_qty)
            if buy_shares >= self.lot_size:
                self.order = self.buy(size=buy_shares)
                acted = True
                self.log(f'买入触发: close={current_price:.4f} <= buy_thr={buy_threshold:.4f}, size={buy_shares}')
            else:
                self.log(f'资金不足，无法买入最小单位：close={current_price:.4f}, 需至少={self.lot_size}股')

        # 卖出触发
        if not acted and current_price >= sell_threshold:
            desired = self._round_to_lot(self.sell_qty)
            if int(self.params.enable_double_on_consecutive_buy) == 1 and self.last_buy_size >= self.lot_size:
                desired = self._round_to_lot(self.last_buy_size)
            position_size = int(self.position.size or 0)
            sell_shares = min(desired, self._round_to_lot(position_size))
            if sell_shares >= self.lot_size:
                self.order = self.sell(size=sell_shares)
                acted = True
                self.log(f'卖出触发: close={current_price:.4f} >= sell_thr={sell_threshold:.4f}, size={sell_shares}')
            else:
                if position_size > 0:
                    self.log(f'持仓不足，无法按最小单位卖出：close={current_price:.4f}, 持仓={position_size}')

        # 指标数据收集
        self.indicator_data['anchor_price'].append(self.anchor_price)
        self.indicator_data['current_price'].append(current_price)
        self.indicator_data['buy_threshold'].append(buy_threshold)
        self.indicator_data['sell_threshold'].append(sell_threshold)
        self.indicator_data['position_size'].append(float(self.position.size or 0))

    def collect_indicator_data(self):
        """
        指标数据在 next 中已追加，这里保持空实现以符合基类接口。
        """
        return
