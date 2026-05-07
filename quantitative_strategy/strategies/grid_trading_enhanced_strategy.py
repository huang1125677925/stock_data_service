#!/usr/bin/env python3
"""
增强版网格交易策略（GridTradingEnhancedStrategy）

功能：
- 基础网格：围绕锚点构建固定间距的价格网格，价格跨格低买高卖；
- 动态重心重置（Re-center）：价格偏离初始锚点超过N格或连续M天无交易时，重置锚点到当前价或EMA20；
- 基于峰值的回撤买入：价格自最近峰值回撤 buy_drawdown_pct 时，允许半格买入（qty_per_grid/2）；
- 部分止盈保留底仓：卖出时保留至少 min_position_ratio × 峰值持仓作为底仓；
- 使用日内价格触发：用当日 low 触发买入、high 触发卖出；
- 动量加仓（Buy-on-strength）：突破若干日高点且量能配合时，半格加仓并上移卖出网格（重心上移）；
- 半步网格：在强势期（EMA20上行）允许半格买入触发，提高成交频率；卖出仍按整格。

参数：
- grid_step_pct(float): 网格间距百分比（如 2.0 表示每格±2%），默认 2.0；
- grid_levels(int): 每侧网格数量（向上/向下各多少格），默认 10；
- qty_per_grid(int): 每格交易数量（股数），默认 100；
- lot_size(int): 最小交易单位（股/手），默认 100；
- safety_cash_pct(float): 买入保留现金比例，默认 0.05；
- recenter_deviation_levels(int): 偏离锚点超过多少格触发重心重置，默认 3；
- recenter_idle_days(int): 连续无交易天数达到后重心重置，默认 5；
- recenter_mode(str): 重心重置模式，'price' 或 'ema20'，默认 'ema20'；
- buy_drawdown_pct(float): 峰值回撤买入阈值（百分比），默认 1.5；
- min_position_ratio(float): 卖出时保留底仓比例（相对峰值持仓），默认 0.20；
- momentum_period(int): 动量高点突破周期，默认 20；
- volume_multiplier(float): 动量加仓的量能放大倍数，默认 1.3；
- half_step_enabled(bool): 是否启用半步网格买入触发，默认 True。

返回值：
- 回测完成后，结果对象包含完整观测器数据、原始数据与指标数据；用于前端绘图与交易明细展示。

事件：
- 买入事件：跨越下方整格、强势期半格下穿、峰值回撤满足阈值、动量突破加仓；
- 卖出事件：跨越上方整格；
- 重心重置事件：偏离过大或长时间无交易时，将重心重置到当前价或EMA20；
- 资金/持仓约束事件：资金不足或底仓保留导致交易缩减或跳过。
"""

import math
from typing import Dict, Any
import backtrader as bt
from .base_strategy import BaseQuantStrategy, register_strategy


@register_strategy
class GridTradingEnhancedStrategy(BaseQuantStrategy):
    _strategy_name = 'grid_trading_enhanced'
    _strategy_description = '增强版网格：重心重置、峰值回撤半格买入、动量半格加仓、保留底仓、用日内高低触发'
    _strategy_params: Dict[str, Any] = {
        'grid_step_pct': {'type': 'float', 'default': 2.0, 'description': '网格间距百分比（±%）'},
        'grid_levels': {'type': 'int', 'default': 10, 'description': '每侧网格数量'},
        'qty_per_grid': {'type': 'int', 'default': 100, 'description': '每格交易股数'},
        'lot_size': {'type': 'int', 'default': 100, 'description': '最小交易单位（股/手）'},
        'safety_cash_pct': {'type': 'float', 'default': 0.05, 'description': '买入保留现金比例'},
        'recenter_deviation_levels': {'type': 'int', 'default': 3, 'description': '偏离锚点超过格数触发重心重置'},
        'recenter_idle_days': {'type': 'int', 'default': 5, 'description': '连续无交易天数触发重心重置'},
        'recenter_mode': {'type': 'str', 'default': 'ema20', 'description': "重置模式: 'price' 或 'ema20'"},
        'buy_drawdown_pct': {'type': 'float', 'default': 1.5, 'description': '峰值回撤买入阈值(%)'},
        'min_position_ratio': {'type': 'float', 'default': 0.20, 'description': '保留底仓比例(相对峰值持仓)'},
        'momentum_period': {'type': 'int', 'default': 20, 'description': '动量突破周期'},
        'volume_multiplier': {'type': 'float', 'default': 1.3, 'description': '动量加仓量能倍数'},
        'half_step_enabled': {'type': 'bool', 'default': True, 'description': '启用半步网格买入'},
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
        buy_drawdown_pct=1.5,
        min_position_ratio=0.20,
        momentum_period=20,
        volume_multiplier=1.3,
        half_step_enabled=True,
        printlog=True,
    )

    def init_indicators(self):
        """
        初始化策略指标与状态。

        - EMA20、最高价与成交量均线用于动量判断；
        - 锚点、网格与最近索引用于网格逻辑；
        - 峰值价格与峰值持仓用于回撤买入与底仓保留；
        - 空闲计数器用于触发重心重置。
        """
        # 价格与量能指标
        self.ema20 = bt.indicators.EMA(self.data.close, period=20)
        self.highest_n = bt.indicators.Highest(self.data.high, period=int(self.params.momentum_period))
        self.vol_sma = bt.indicators.SMA(self.data.volume, period=int(self.params.momentum_period))

        # 网格状态
        self.anchor_price = None
        self.grid_prices = []
        self.last_level_index = None

        # 运行状态
        self.idle_days = 0
        self.last_trade_bar_index = None
        self.peak_price = None
        self.peak_position_size = 0

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
            'peak_price': [],
            'recentered': [],
        }

    def get_strategy_name(self) -> str:
        """获取策略名称"""
        return 'grid_trading_enhanced'

    def get_strategy_description(self) -> str:
        """获取策略描述"""
        return '增强版网格：重心重置/峰值回撤半格/动量半格加仓/保留底仓/日内触发'

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

    def _allowed_sell_shares(self, desired_shares: int) -> int:
        """
        计算在保留底仓约束下允许卖出的股数。
        保留至少 min_position_ratio × 峰值持仓作为底仓。
        """
        position_size = int(self.position.size or 0)
        min_base = int(math.ceil(float(self.params.min_position_ratio) * float(self.peak_position_size)))
        allowed = max(0, position_size - min_base)
        return min(self._round_to_lot(desired_shares), self._round_to_lot(allowed))

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
        策略主逻辑：
        - 初始化锚点与网格；
        - 优先检查重心重置；
        - 用日内 low/high 触发买卖；
        - 峰值回撤半格买入与动量半格加仓；
        - 卖出时保留底仓约束；
        - 每个bar最多执行一次交易，并统计空闲天数。
        """
        super().next()

        # 当前价格与日内高低
        price_close = float(self.data.close[0])
        price_low = float(self.data.low[0])
        price_high = float(self.data.high[0])
        if price_close <= 0:
            return

        # 初始化锚点与网格
        if self.anchor_price is None:
            self.anchor_price = price_close
            self._build_grid(self.anchor_price)
            self.last_level_index = self._find_nearest_level_index(price_close)
            self.peak_price = price_high
            self.peak_position_size = int(self.position.size or 0)
            self.log(f'初始化锚点与网格: anchor={self.anchor_price:.4f}, levels={len(self.grid_prices)}')
            return

        # 更新峰值价格与峰值持仓
        self.peak_price = max(self.peak_price or price_high, price_high)
        self.peak_position_size = max(self.peak_position_size or 0, int(self.position.size or 0))

        # 若有未完成订单，跳过
        if self.order:
            return

        # 最近网格索引
        nearest_idx = self._find_nearest_level_index(price_close)

        # 重心重置检查
        recentered = self._recenter_if_needed(price_close, nearest_idx)

        acted = False
        step = float(self.params.grid_step_pct) / 100.0

        # 1) 网格买入触发（下穿整格）— 使用日内low（边界受 grid_levels 约束）
        if self.last_level_index is not None:
            if nearest_idx < self.last_level_index and not acted:
                # 目标索引向下移动一格，但不越界
                target_idx = max(0, int(self.last_level_index) - 1)
                if target_idx == self.last_level_index:
                    # 已处于下侧边界，避免越界交易
                    self.log('整格买入边界触发：已到达下侧最小网格，跳过')
                else:
                    buy_shares = self._can_buy_with_cash(price_low, self.qty_per_grid)
                    if buy_shares >= self.lot_size:
                        self.order = self.buy(size=buy_shares)
                        self.last_level_index = target_idx
                        acted = True
                        self.idle_days = 0
                        self.log(f'整格买入: low={price_low:.2f}, size={buy_shares}')

        # 2) 半步网格买入（强势期）— 使用low，阈值为半格中点
        if not acted and bool(self.params.half_step_enabled):
            try:
                strong_trend = float(self.ema20[0]) > float(self.ema20[-1]) and price_close > float(self.ema20[0])
            except Exception:
                strong_trend = False
            if strong_trend and self.last_level_index is not None and self.last_level_index > 0:
                upper_idx = int(self.last_level_index)
                lower_idx = upper_idx - 1
                # 索引边界检查
                if 0 <= lower_idx < len(self.grid_prices) and 0 <= upper_idx < len(self.grid_prices):
                    # 半格阈值为上下两格的中点价
                    mid_price = (self.grid_prices[upper_idx] + self.grid_prices[lower_idx]) / 2.0
                    if price_low <= mid_price:
                        half_shares = max(self.lot_size, self._round_to_lot(self.qty_per_grid // 2))
                        buy_shares = self._can_buy_with_cash(price_low, half_shares)
                        if buy_shares >= self.lot_size:
                            self.order = self.buy(size=buy_shares)
                            # 不改变last_level_index，作为回补逻辑
                            acted = True
                            self.idle_days = 0
                            self.log(f'半步买入(强势期): low={price_low:.2f}, mid={mid_price:.2f}, size={buy_shares}')

        # 3) 回撤买入（峰值回撤）— 使用low，允许半格
        if not acted and self.peak_price:
            drawdown_pct = (self.peak_price - price_low) / self.peak_price * 100.0 if self.peak_price > 0 else 0.0
            if drawdown_pct >= float(self.params.buy_drawdown_pct):
                half_shares = max(self.lot_size, self._round_to_lot(self.qty_per_grid // 2))
                buy_shares = self._can_buy_with_cash(price_low, half_shares)
                if buy_shares >= self.lot_size:
                    self.order = self.buy(size=buy_shares)
                    acted = True
                    self.idle_days = 0
                    self.log(f'峰值回撤买入: low={price_low:.2f}, peak={self.peak_price:.2f}, drawdown={drawdown_pct:.2f}%, size={buy_shares}')

        # 4) 动量加仓（突破近N日高点且量能配合）— 使用high，半格加仓并上移卖出网格（重心上移）
        if not acted:
            try:
                vol_ok = float(self.data.volume[0]) > float(self.vol_sma[0]) * float(self.params.volume_multiplier)
                breakout = price_high > float(self.highest_n[-1])  # 突破前一日近N日高点
            except Exception:
                vol_ok, breakout = False, False
            if breakout and vol_ok:
                half_shares = max(self.lot_size, self._round_to_lot(self.qty_per_grid // 2))
                buy_shares = self._can_buy_with_cash(price_close, half_shares)
                if buy_shares >= self.lot_size:
                    self.order = self.buy(size=buy_shares)
                    acted = True
                    self.idle_days = 0
                    # 上移卖出网格：将重心重置到当前价，利于后续高位分批卖出
                    self.anchor_price = price_close
                    self._build_grid(self.anchor_price)
                    self.last_level_index = self._find_nearest_level_index(price_close)
                    self.log(f'动量加仓: high={price_high:.2f}, size={buy_shares}，重心上移至{self.anchor_price:.2f}')

        # 5) 网格卖出触发（上穿整格）— 使用日内high；保留底仓约束（边界受 grid_levels 约束）
        if not acted and self.last_level_index is not None:
            if nearest_idx > self.last_level_index:
                # 目标索引向上移动一格，但不越界
                max_idx = len(self.grid_prices) - 1
                target_idx = min(max_idx, int(self.last_level_index) + 1)
                if target_idx == self.last_level_index:
                    self.log('整格卖出边界触发：已到达上侧最大网格，跳过')
                else:
                    desired = self._round_to_lot(self.qty_per_grid)
                    sell_shares = self._allowed_sell_shares(desired)
                    if sell_shares >= self.lot_size:
                        self.order = self.sell(size=sell_shares)
                        self.last_level_index = target_idx
                        acted = True
                        self.idle_days = 0
                        self.log(f'整格卖出: high={price_high:.2f}, size={sell_shares}, 保留底仓≥{self.params.min_position_ratio*100:.1f}%峰值持仓')
                    else:
                        # 无可卖数量（底仓保护）
                        self.log(f'卖出受限(底仓保护)：position={int(self.position.size or 0)}, peak_pos={self.peak_position_size}')

        # 空闲计数与指标数据收集
        if not acted:
            self.idle_days += 1

        self.indicator_data['anchor_price'].append(self.anchor_price)
        self.indicator_data['current_price'].append(price_close)
        self.indicator_data['nearest_level_index'].append(nearest_idx)
        self.indicator_data['last_level_index'].append(self.last_level_index)
        self.indicator_data['position_size'].append(float(self.position.size or 0))
        try:
            self.indicator_data['ema20'].append(float(self.ema20[0]))
        except Exception:
            self.indicator_data['ema20'].append(None)
        self.indicator_data['peak_price'].append(self.peak_price)
        self.indicator_data['recentered'].append(bool(recentered))

    def collect_indicator_data(self):
        """
        收集策略指标数据（已在next中持续追加）。
        """
        return