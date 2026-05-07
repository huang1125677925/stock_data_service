#!/usr/bin/env python3
"""
动态重心重置网格交易策略（GridTradingRecenteringStrategy）

功能：
- 基于 `grid_trading_strategy.py` 的基础网格逻辑（收盘价跨格低买高卖）；
- 动态重心重置：当价格相对锚点偏离 ≥ N 格，或连续 M 天无交易时，将锚点重置为当前价或 EMA20；重置后重建网格；
- 边界保护：`last_level_index` 仅在网格边界范围内变化，避免越界；
- 跨格确认：收盘价必须越过网格价位并额外超过“确认幅度”（相对步长的比例），以过滤小幅噪声导致的来回交易；

参数：
- grid_step_pct(float): 网格间距百分比（如 2.0 表示每格±2%），默认 2.0；
- grid_levels(int): 每侧网格数量（向上/向下各多少格），默认 10；
- qty_per_grid(int): 每格交易数量（股数），默认 100；
- lot_size(int): 最小交易单位（股/手），默认 100；
- safety_cash_pct(float): 买入保留现金比例，默认 0.05；
- recenter_deviation_levels(int): 偏离锚点超过多少格触发重心重置，默认 3；
- recenter_idle_days(int): 连续无交易天数触发重心重置，默认 5；
- recenter_mode(str): 重心重置模式，'price' 或 'ema20'，默认 'ema20'；
- cross_confirm_ratio(float): 跨格确认比例（相对步长的比例，例如 0.1 表示需超过网格价位额外的 10% 步长），默认 0.0；

返回值：
- 回测完成后，结果对象包含完整观测器数据与网格相关指标数据，便于前端绘图与交易明细展示。

事件：
- 买入事件：当收盘价下穿下一条网格价格时，按每格数量买入；
- 卖出事件：当收盘价上穿下一条网格价格时，按每格数量卖出；
- 重心重置事件：偏离过大或长时间无交易时，锚点重置到当前价或EMA20并重建网格；
- 资金/持仓约束事件：资金不足或持仓不足时，缩减或跳过交易并记录日志。
"""

import math
from typing import Dict, Any
import backtrader as bt
from bisect import bisect_right
from .base_strategy import BaseQuantStrategy, register_strategy


@register_strategy
class GridTradingRecenteringStrategy(BaseQuantStrategy):
    _strategy_name = 'grid_trading_recenter'
    _strategy_description = '网格策略(收盘触发)+动态重心重置：偏离≥N格或连续M天无交易，重置锚点到当前价或EMA20'
    _strategy_params: Dict[str, Any] = {
        'grid_step_pct': {'type': 'float', 'default': 2.0, 'description': '网格间距百分比（±%）'},
        'grid_levels': {'type': 'int', 'default': 10, 'description': '每侧网格数量'},
        'qty_per_grid': {'type': 'int', 'default': 100, 'description': '每格交易股数'},
        'lot_size': {'type': 'int', 'default': 100, 'description': '最小交易单位（股/手）'},
        'safety_cash_pct': {'type': 'float', 'default': 0.05, 'description': '买入保留现金比例'},
        'recenter_deviation_levels': {'type': 'int', 'default': 3, 'description': '偏离锚点超过格数触发重心重置'},
        'recenter_idle_days': {'type': 'int', 'default': 5, 'description': '连续无交易天数触发重心重置'},
        'recenter_mode': {'type': 'str', 'default': 'ema20', 'description': "重置模式: 'price' 或 'ema20'"},
        'cross_confirm_ratio': {'type': 'float', 'default': 0.0, 'description': '跨格确认比例（相对步长），如0.1表示额外10%步长'},
    }

    # backtrader参数
    params = dict(
        grid_step_pct=2.0,
        grid_levels=10,
        qty_per_grid=100,
        lot_size=100,
        safety_cash_pct=0.05,
        recenter_deviation_levels=3,
        recenter_idle_days=5,
        recenter_mode='ema20',
        cross_confirm_ratio=0.0,
        printlog=True,
    )

    def init_indicators(self):
        """
        初始化策略指标与状态。

        - EMA20用于重心重置的参考；
        - 锚点、网格与最近索引用于网格逻辑；
        - 空闲计数器用于触发重心重置。
        """
        # 指标
        self.ema20 = bt.indicators.EMA(self.data.close, period=20)

        # 网格状态
        self.anchor_price = None
        self.grid_prices = []
        self.last_level_index = None

        # 运行状态
        self.idle_days = 0

        # 交易尺度
        self.qty_per_grid = int(self.params.qty_per_grid)
        self.lot_size = int(self.params.lot_size)

        # 指标数据收集
        self.indicator_data = {
            'anchor_price': [],
            'current_price': [],
            'nearest_level_index': [],
            'last_level_index': [],
            'position_size': [],
            'ema20': [],
            'recentered': [],
        }

    def get_strategy_name(self) -> str:
        """获取策略名称"""
        return 'grid_trading_recenter'

    def get_strategy_description(self) -> str:
        """获取策略描述"""
        return '网格策略(收盘触发)+动态重心重置：偏离≥N格或连续M天无交易，重置锚点到当前价或EMA20'

    # 工具方法
    def _build_grid(self, anchor: float):
        """基于锚点价格构建网格价格列表。"""
        step = float(self.params.grid_step_pct) / 100.0
        levels = int(self.params.grid_levels)
        prices = [anchor * (1.0 + i * step) for i in range(-levels, levels + 1)]
        self.grid_prices = sorted(prices)

    def _find_nearest_level_index(self, price: float) -> int:
        """查找与当前价格最近的网格索引。"""
        if not self.grid_prices:
            return 0
        nearest_idx, min_diff = 0, float('inf')
        for i, p in enumerate(self.grid_prices):
            d = abs(p - price)
            if d < min_diff:
                min_diff, nearest_idx = d, i
        return nearest_idx

    def _get_floor_index(self, price: float) -> int:
        """返回不超过当前价格的最大网格索引（严格跨格判定用）。"""
        if not self.grid_prices:
            return 0
        idx = bisect_right(self.grid_prices, price) - 1
        if idx < 0:
            return 0
        max_idx = len(self.grid_prices) - 1
        return min(max_idx, idx)

    def _round_to_lot(self, shares: int) -> int:
        """将股数向下取整到最小交易单位。"""
        if self.lot_size <= 0:
            return max(1, shares)
        return (shares // self.lot_size) * self.lot_size

    def _can_buy_with_cash(self, price: float, desired_shares: int) -> int:
        """依据现金与最小单位，返回可买股数。"""
        cash = float(self.broker.get_cash())
        available_cash = cash * (1.0 - float(self.params.safety_cash_pct))
        max_shares = self._round_to_lot(int(available_cash / price))
        return max(0, min(self._round_to_lot(desired_shares), max_shares))

    def _recenter_if_needed(self, current_price: float, nearest_idx: int) -> bool:
        """
        检查是否需要重心重置：偏离超过N格或连续M天无交易。
        重置后锚点设为当前价或EMA20，并重建网格；返回是否发生重置。
        """
        if self.anchor_price is None:
            return False
        deviation_levels = abs(nearest_idx - self._find_nearest_level_index(self.anchor_price))
        need_recenter = (
            deviation_levels >= int(self.params.recenter_deviation_levels)
            or self.idle_days >= int(self.params.recenter_idle_days)
        )
        if not need_recenter:
            return False
        # 选择重心
        target = current_price
        if str(self.params.recenter_mode).lower() == 'ema20':
            try:
                target = float(self.ema20[0]) if not math.isnan(float(self.ema20[0])) else current_price
            except Exception:
                target = current_price
        self.anchor_price = target
        self._build_grid(self.anchor_price)
        self.last_level_index = self._find_nearest_level_index(current_price)
        self.idle_days = 0
        self.log(f'重心重置: anchor={self.anchor_price:.4f}, deviation_levels={deviation_levels}, idle_days={self.idle_days}')
        return True

    def next(self):
        """
        策略主逻辑（收盘触发）：
        - 初始化锚点与网格；
        - 优先检查重心重置；
        - 收盘价跨格低买高卖；
        - 边界保护与空闲天数统计。
        """
        super().next()

        # 当前收盘价
        price_close = float(self.data.close[0])
        if price_close <= 0:
            return

        # 若有未完成订单，跳过
        if self.order:
            return

        # 初始化锚点与网格
        if self.anchor_price is None:
            self.anchor_price = price_close
            self._build_grid(self.anchor_price)
            # 使用“地板索引”初始化，确保仅在严格穿越网格价位时触发交易
            self.last_level_index = self._get_floor_index(price_close)
            self.log(f'初始化锚点与网格: anchor={self.anchor_price:.4f}, levels={len(self.grid_prices)}')
            return

        # 最近网格索引与重心重置检查
        nearest_idx = self._find_nearest_level_index(price_close)
        recentered = self._recenter_if_needed(price_close, nearest_idx)

        # 采用严格跨格判定：以当前收盘价对应的“地板索引”作为当日所处的网格档位
        floor_idx = self._get_floor_index(price_close)

        # 计算跨格确认幅度（相对步长的比例）
        step = float(self.params.grid_step_pct) / 100.0
        confirm_ratio = max(0.0, float(self.params.cross_confirm_ratio))
        margin_factor = step * confirm_ratio

        acted = False

        # 1) 网格买入触发（下穿整格）— 使用收盘价（边界受 grid_levels 约束）
        if self.last_level_index is not None:
            if floor_idx < self.last_level_index and not acted:
                target_idx = max(0, int(self.last_level_index) - 1)
                if target_idx != self.last_level_index:
                    # 需满足：收盘价低于目标网格价位减去确认幅度
                    threshold_price = self.grid_prices[target_idx] * (1.0 - margin_factor)
                    if price_close <= threshold_price:
                        buy_shares = self._can_buy_with_cash(price_close, self.qty_per_grid)
                        if buy_shares >= self.lot_size:
                            self.order = self.buy(size=buy_shares)
                            self.last_level_index = target_idx
                            acted = True
                            self.idle_days = 0
                            self.log(f'整格买入: close={price_close:.4f}, threshold={threshold_price:.4f}, size={buy_shares}, idx {self.last_level_index+1}->{self.last_level_index}')
                    else:
                        self.log(f'买入未满足确认幅度: close={price_close:.4f} > threshold={threshold_price:.4f}')
                else:
                    self.log('整格买入边界触发：已到达下侧最小网格，跳过')

        # 2) 网格卖出触发（上穿整格）— 使用收盘价（边界受 grid_levels 约束）
        if not acted and self.last_level_index is not None:
            if floor_idx > self.last_level_index:
                max_idx = len(self.grid_prices) - 1
                target_idx = min(max_idx, int(self.last_level_index) + 1)
                if target_idx != self.last_level_index:
                    # 需满足：收盘价高于目标网格价位加上确认幅度
                    threshold_price = self.grid_prices[target_idx] * (1.0 + margin_factor)
                    if price_close >= threshold_price:
                        desired = self._round_to_lot(self.qty_per_grid)
                        position_size = int(self.position.size or 0)
                        sell_shares = min(desired, self._round_to_lot(position_size))
                        if sell_shares >= self.lot_size:
                            self.order = self.sell(size=sell_shares)
                            self.last_level_index = target_idx
                            acted = True
                            self.idle_days = 0
                            self.log(f'整格卖出: close={price_close:.4f}, threshold={threshold_price:.4f}, size={sell_shares}, idx {self.last_level_index-1}->{self.last_level_index}')
                        else:
                            if position_size > 0:
                                self.log(f'持仓不足，无法按最小单位卖出：close={price_close:.4f}, 持仓={position_size}')
                    else:
                        self.log(f'卖出未满足确认幅度: close={price_close:.4f} < threshold={threshold_price:.4f}')
                else:
                    self.log('整格卖出边界触发：已到达上侧最大网格，跳过')

        # 空闲计数与指标数据收集
        if not acted and not recentered:
            self.idle_days += 1

        self.indicator_data['anchor_price'].append(self.anchor_price)
        self.indicator_data['current_price'].append(price_close)
        # 记录严格判定下的当日“地板索引”，用于前端复现跨格触发
        self.indicator_data['nearest_level_index'].append(floor_idx)
        self.indicator_data['last_level_index'].append(self.last_level_index)
        self.indicator_data['position_size'].append(float(self.position.size or 0))
        try:
            self.indicator_data['ema20'].append(float(self.ema20[0]))
        except Exception:
            self.indicator_data['ema20'].append(None)
        self.indicator_data['recentered'].append(bool(recentered))

    def collect_indicator_data(self):
        """
        收集策略指标数据（已在next中持续追加）。
        """
        return