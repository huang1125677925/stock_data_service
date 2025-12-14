#!/usr/bin/env python3
"""
网格交易策略

功能：
- 以首个可用价格为锚点构建对称价格网格；
- 价格每跨越一个网格级别，执行对应方向的买卖（下穿买入、上穿卖出）；
- 每次只交易一个网格单位，按设定的每格数量下单，遵守最小交易单位；
- 自动记录原始数据与观测器数据（继承基类实现），便于后端/前端展示。

参数：
- grid_step_pct(float): 网格间距百分比（如 2.0 表示每格±2%），默认 2.0；
- grid_levels(int): 每侧网格数量（向上/向下各多少格），默认 10；
- qty_per_grid(int): 每格交易数量（股数），默认 100；
- lot_size(int): 最小交易单位（手/股），默认 100；
- safety_cash_pct(float): 资金安全边际比例，买入时预留的现金比例，默认 0.05；
- printlog(bool): 是否打印日志，默认 True。

返回值：
- 回测完成后，结果对象包含完整观测器数据、原始数据与指标数据；
  前端可用于绘图与交易明细展示。

事件：
- 买入事件：当收盘价下穿下一条网格价格时，按每格数量买入；
- 卖出事件：当收盘价上穿下一条网格价格时，按每格数量卖出；
- 资金不足事件：买入资金不足时不下单并记录日志；
- 持仓不足事件：卖出数量超过持仓时按剩余持仓卖出。
"""

import math
import backtrader as bt
from .base_strategy import BaseQuantStrategy, register_strategy


@register_strategy
class GridTradingStrategy(BaseQuantStrategy):
    _strategy_name = 'grid_trading'
    _strategy_description = '网格交易策略：固定价格间隔的低买高卖网格化交易'
    _strategy_params = {
        'grid_step_pct': {'type': 'float', 'default': 2.0, 'description': '网格间距百分比（±%）'},
        'grid_levels': {'type': 'int', 'default': 10, 'description': '每侧网格数量'},
        'qty_per_grid': {'type': 'int', 'default': 100, 'description': '每格交易股数'},
        'lot_size': {'type': 'int', 'default': 100, 'description': '最小交易单位（股/手）'},
        'safety_cash_pct': {'type': 'float', 'default': 0.05, 'description': '买入保留现金比例'},
    }

    # 策略参数
    params = dict(
        grid_step_pct=2.0,   # 每格百分比间距
        grid_levels=10,      # 每侧网格数量
        qty_per_grid=100,    # 每格交易股数
        lot_size=100,        # 最小交易单位
        safety_cash_pct=0.05,# 买入保留现金比例
        printlog=True,
    )

    def init_indicators(self):
        """
        初始化策略所需的状态与指标结构。

        说明：
        - 网格策略不依赖传统技术指标，这里仅初始化锚点价与网格价格表结构；
        - 指标数据字典用于记录运行过程中的关键变量，便于后端输出。
        """
        self.anchor_price = None           # 锚点价格（首个可用收盘价）
        self.grid_prices = []              # 网格价格列表（由锚点与间距生成）
        self.last_level_index = None       # 上次成交所在的网格索引
        self.qty_per_grid = int(self.params.qty_per_grid)
        self.lot_size = int(self.params.lot_size)

        # 指标数据收集结构
        self.indicator_data = {
            'anchor_price': [],
            'current_price': [],
            'nearest_level_index': [],
            'last_level_index': [],
            'position_size': [],
        }

    def get_strategy_name(self) -> str:
        """获取策略名称"""
        return 'grid_trading'

    def get_strategy_description(self) -> str:
        """获取策略描述"""
        return '网格交易策略：围绕锚点构建固定间距网格，价格跨格低买高卖'

    def _build_grid(self, anchor: float):
        """
        基于锚点价格构建网格价格列表。

        Args:
            anchor: 锚点价格（float）

        Returns:
            None（更新 self.grid_prices）
        """
        step = float(self.params.grid_step_pct) / 100.0
        levels = int(self.params.grid_levels)
        # 采用等比近似法：anchor * (1 + i*step)，i ∈ [-levels, levels]
        prices = []
        for i in range(-levels, levels + 1):
            prices.append(anchor * (1.0 + i * step))
        self.grid_prices = sorted(prices)

    def _find_nearest_level_index(self, price: float) -> int:
        """
        查找与当前价格最近的网格索引。

        Args:
            price: 当前价格

        Returns:
            最近网格的索引（int）
        """
        if not self.grid_prices:
            return 0
        # 二分或线性均可；网格数量有限，直接线性即可
        nearest_idx = 0
        min_diff = float('inf')
        for i, p in enumerate(self.grid_prices):
            d = abs(p - price)
            if d < min_diff:
                min_diff = d
                nearest_idx = i
        return nearest_idx

    def _round_to_lot(self, shares: int) -> int:
        """
        将股数向下取整到最小交易单位。
        """
        if self.lot_size <= 0:
            return max(1, shares)
        return (shares // self.lot_size) * self.lot_size

    def next(self):
        """
        策略主逻辑：
        - 首次运行设置锚点与网格；
        - 若价格向下跨越一格：买入一个网格单位；
        - 若价格向上跨越一格：卖出一个网格单位；
        - 每个bar最多执行一次网格交易，避免过度交易。
        """
        # 先调用基类，收集通用数据
        super().next()

        # 若存在未完成订单，跳过
        if self.order:
            return

        # 当前收盘价
        current_price = float(self.data.close[0])
        if current_price <= 0:
            return

        # 初始化锚点与网格
        if self.anchor_price is None:
            self.anchor_price = current_price
            self._build_grid(self.anchor_price)
            # 初始最近索引设置为当前
            self.last_level_index = self._find_nearest_level_index(current_price)
            self.log(f'初始化锚点与网格: anchor={self.anchor_price:.4f}, levels={len(self.grid_prices)}')
            return

        # 计算最近网格索引
        nearest_idx = self._find_nearest_level_index(current_price)

        # 网格交易决策：仅当跨越相邻网格才动作
        acted = False
        # 下穿一格：买入一个单位
        if self.last_level_index is not None and nearest_idx < self.last_level_index:
            # 买入一个网格单位
            cash = float(self.broker.get_cash())
            available_cash = cash * (1.0 - float(self.params.safety_cash_pct))
            # 目标股数按每格数量，向下取整到最小单位
            target_shares = self._round_to_lot(int(self.params.qty_per_grid))
            # 资金检查：最大可买
            max_shares = self._round_to_lot(int(available_cash / current_price))
            buy_shares = min(target_shares, max_shares)
            if buy_shares >= self.lot_size:
                self.log(f'网格买入: 现价={current_price:.2f}, buy_shares={buy_shares}, cash={cash:.2f}')
                self.order = self.buy(size=buy_shares)
                self.last_level_index -= 1
                acted = True
            else:
                self.log(f'资金不足，无法按最小单位买入：现价={current_price:.2f}, 需至少={self.lot_size}股')

        # 上穿一格：卖出一个单位
        elif self.last_level_index is not None and nearest_idx > self.last_level_index and not acted:
            position_size = int(self.position.size or 0)
            sell_shares = min(self._round_to_lot(int(self.params.qty_per_grid)), self._round_to_lot(position_size))
            if sell_shares >= self.lot_size:
                self.log(f'网格卖出: 现价={current_price:.2f}, sell_shares={sell_shares}, position={position_size}')
                self.order = self.sell(size=sell_shares)
                self.last_level_index += 1
                acted = True
            else:
                if position_size > 0:
                    self.log(f'持仓不足，无法按最小单位卖出：现价={current_price:.2f}, 持仓={position_size}')

        # 收集指标数据
        self.indicator_data['anchor_price'].append(self.anchor_price)
        self.indicator_data['current_price'].append(current_price)
        self.indicator_data['nearest_level_index'].append(nearest_idx)
        self.indicator_data['last_level_index'].append(self.last_level_index if self.last_level_index is not None else None)
        self.indicator_data['position_size'].append(float(self.position.size or 0))

    def collect_indicator_data(self):
        """
        收集策略相关指标数据。

        当前实现：
        - 指标数据在 next 中已追加，这里保持空实现以符合基类接口。
        """
        return