#!/usr/bin/env python3
"""
定投（Dollar-Cost Averaging, DCA）策略

功能：
- 支持按周指定定投日期（如每周二、每周三）；
- 每次定投现金为 `base_invest_amount` 的整数倍（以 1000 为单位）；
- 根据最新收盘价在近 100 个交易日的分位数动态调整定投力度：
  - 价格处于低分位（≤20%）提高定投倍数；
  - 价格处于高分位（≥80%）降低定投倍数；
- 支持设置止盈比例，达到止盈则清仓。
 - 新增趋势过滤与波动率缩放：在上升趋势中更积极、波动大时保守；
 - 新增风控：固定止损、动态追踪止损、仓位上限与买入冷却期。

参数：
- investment_weekday (int | str): 定投的星期几，int 0-6 对应周一到周日，或字符串 'Monday'/'周一' 等；默认 'Wednesday'。
- base_invest_amount (int): 基础定投金额（现金），默认 1000；实际下单金额为该值的 1000 倍整数。
- take_profit_pct (float): 止盈百分比（相对持仓均价），默认 15.0。
- lot_size (int): 股票最小交易单位（手/股），默认 100 股。
- lookback_days (int): 计算分位数的回溯交易日数，默认 100。
- low_percentile (float): 低分位阈值（0-1），默认 0.2。
- high_percentile (float): 高分位阈值（0-1），默认 0.8。
- min_multiplier (float): 高分位时使用的最小定投倍数，默认 0.5。
- max_multiplier (float): 低分位时使用的最大定投倍数，默认 2.0。
 - sma_period_fast (int): 趋势快线均线周期，默认 20。
 - sma_period_slow (int): 趋势慢线均线周期，默认 100。
 - require_uptrend (bool): 是否要求上升趋势（快线≥慢线且现价≥快线）后才定投，默认 True。
 - atr_period (int): ATR 波动率周期，默认 14。
 - atr_pct_low (float): 低波动水平阈值（ATR/收盘价），默认 0.015。
 - atr_pct_high (float): 高波动水平阈值（ATR/收盘价），默认 0.06。
 - volatility_scale_min (float): 高波动时的最小现金缩放倍数，默认 0.6。
 - volatility_scale_max (float): 低波动时的最大现金放大倍数，默认 1.2。
 - cooldown_bars (int): 买入冷却期（至少间隔 N 根K线再买），默认 3。
 - max_position_value_pct (float): 最大持仓市值占总资产比例上限，默认 0.6（60%）。
 - stop_loss_pct (float): 固定止损百分比（相对持仓均价），默认 10.0。
 - trailing_stop_pct (float): 追踪止损百分比（相对开仓后最高价），默认 12.0。

返回值：
- 通过基类的观测器与记录机制返回完整的交易与指标数据（无需显式返回）。

事件：
- 定投事件：在指定星期触发，按动态倍数计算当日定投金额并买入；
- 止盈事件：当收盘价 ≥ 均价 × (1 + take_profit_pct/100) 时清仓。
 - 止损事件：当收盘价 ≤ 均价 × (1 - stop_loss_pct/100) 时清仓；
 - 追踪止损事件：当收盘价 ≤ 进场以来最高价 × (1 - trailing_stop_pct/100) 时清仓。
"""

import backtrader as bt
from typing import Union
from .base_strategy import BaseQuantStrategy, register_strategy


WEEKDAY_MAP = {
    'monday': 0, 'mon': 0, '周一': 0,
    'tuesday': 1, 'tue': 1, '周二': 1,
    'wednesday': 2, 'wed': 2, '周三': 2,
    'thursday': 3, 'thu': 3, '周四': 3,
    'friday': 4, 'fri': 4, '周五': 4,
    'saturday': 5, 'sat': 5, '周六': 5,
    'sunday': 6, 'sun': 6, '周日': 6,
}


@register_strategy
class DCAInvestmentStrategy(BaseQuantStrategy):
    """
    定投策略实现类

    策略逻辑：
    - 在指定的每周某一天执行定投；
    - 近 100 日价格分位数越低，定投金额越大；分位数越高，定投金额越小；
    - 达到止盈阈值时清仓获利；
    - 趋势过滤与波动率缩放控制买入积极度；
    - 固定止损与追踪止损控制下行风险；
    - 仓位上限与买入冷却期避免过度集中与过度频繁交易。
    """

    _strategy_name = 'dca_investment'
    _strategy_description = '定投策略：按周定投，分位数动态与趋势/波动控制，含止盈止损与仓位管理'
    _strategy_params = {
        'investment_weekday': {'type': 'str', 'default': 'Wednesday', 'description': '定投星期几（支持中英文/缩写）'},
        'base_invest_amount': {'type': 'int', 'default': 1000, 'description': '基础定投金额（现金），单位元'},
        'take_profit_pct': {'type': 'float', 'default': 15.0, 'description': '止盈百分比'},
        'lot_size': {'type': 'int', 'default': 100, 'description': '最小交易单位（股/手）'},
        'lookback_days': {'type': 'int', 'default': 100, 'description': '分位数计算回溯天数'},
        'low_percentile': {'type': 'float', 'default': 0.2, 'description': '低分位阈值'},
        'high_percentile': {'type': 'float', 'default': 0.8, 'description': '高分位阈值'},
        'min_multiplier': {'type': 'float', 'default': 0.5, 'description': '高分位时最小定投倍数'},
        'max_multiplier': {'type': 'float', 'default': 2.0, 'description': '低分位时最大定投倍数'},
        'sma_period_fast': {'type': 'int', 'default': 20, 'description': '趋势快线均线周期'},
        'sma_period_slow': {'type': 'int', 'default': 100, 'description': '趋势慢线均线周期'},
        'require_uptrend': {'type': 'bool', 'default': True, 'description': '是否要求上升趋势后才定投'},
        'atr_period': {'type': 'int', 'default': 14, 'description': 'ATR波动率周期'},
        'atr_pct_low': {'type': 'float', 'default': 0.015, 'description': '低波动阈值 ATR/收盘价'},
        'atr_pct_high': {'type': 'float', 'default': 0.06, 'description': '高波动阈值 ATR/收盘价'},
        'volatility_scale_min': {'type': 'float', 'default': 0.6, 'description': '高波动时最小现金倍数'},
        'volatility_scale_max': {'type': 'float', 'default': 1.2, 'description': '低波动时最大现金倍数'},
        'cooldown_bars': {'type': 'int', 'default': 3, 'description': '买入冷却期（K线数）'},
        'max_position_value_pct': {'type': 'float', 'default': 0.6, 'description': '最大持仓市值占资产比例'},
        'stop_loss_pct': {'type': 'float', 'default': 10.0, 'description': '固定止损百分比'},
        'trailing_stop_pct': {'type': 'float', 'default': 12.0, 'description': '追踪止损百分比'},
    }

    # backtrader 参数
    params = dict(
        investment_weekday='Wednesday',
        base_invest_amount=1000,
        take_profit_pct=15.0,
        lot_size=100,
        lookback_days=100,
        low_percentile=0.2,
        high_percentile=0.8,
        min_multiplier=0.5,
        max_multiplier=2.0,
        sma_period_fast=20,
        sma_period_slow=100,
        require_uptrend=True,
        atr_period=14,
        atr_pct_low=0.015,
        atr_pct_high=0.06,
        volatility_scale_min=0.6,
        volatility_scale_max=1.2,
        cooldown_bars=3,
        max_position_value_pct=0.6,
        stop_loss_pct=10.0,
        trailing_stop_pct=12.0,
        printlog=True,
    )

    def init_indicators(self):
        """
        初始化策略所需的运行期变量与观测数据结构
        """
        # 运行期状态
        self._weekday_idx = self._normalize_weekday(self.params.investment_weekday)
        self._last_buy_bar_index = None
        self._highest_close_since_entry = None

        # 指标数据收集结构
        self.indicator_data = {
            'percentile': [],     # 当前价格相对近 lookback_days 的分位数（0-1）
            'scaled_amount': [],  # 动态调整后的定投金额（现金）
            'atr_pct': [],        # ATR占比（波动率）
            'trend_ok': [],       # 趋势过滤是否通过（0/1）
            'pos_value_pct': [],  # 当前持仓占资产比例
            'cooldown': [],       # 本次是否受冷却期限制（0/1）
        }

        # 技术指标
        self._sma_fast = bt.indicators.SMA(self.data.close, period=int(self.params.sma_period_fast))
        self._sma_slow = bt.indicators.SMA(self.data.close, period=int(self.params.sma_period_slow))
        self._atr = bt.indicators.ATR(self.data, period=int(self.params.atr_period))

    def get_strategy_name(self) -> str:
        return 'dca_investment'

    def get_strategy_description(self) -> str:
        return '定投策略：按周定投，依据分位数/趋势/波动动态调整金额，含止盈止损与仓位管理'

    def next(self):
        """
        策略主逻辑

        流程：
        1) 调用基类 next 收集数据；
        2) 若有持仓：先检查固定止损、追踪止损、止盈；
        3) 若当天为设定定投日：在通过趋势过滤/冷却期/仓位上限后，计算分位数与波动率缩放执行买入。
        """
        # 收集通用数据
        super().next()

        # 若存在未完成订单，跳过
        if self.order:
            return

        # 先处理风控：止损 / 追踪止损 / 止盈
        if self.position and self.position.size > 0:
            avg_price = float(self.position.price)
            current_price = float(self.data.close[0])
            # 更新进场以来最高价
            self._highest_close_since_entry = (
                max(self._highest_close_since_entry or current_price, current_price)
            )

            # 固定止损
            if avg_price > 0:
                stop_loss_price = avg_price * (1.0 - float(self.params.stop_loss_pct) / 100.0)
                if current_price <= stop_loss_price:
                    self.log(f'固定止损触发：现价={current_price:.2f} ≤ 止损价={stop_loss_price:.2f}，清仓卖出')
                    self.order = self.sell(size=self.position.size)
                    return

            # 追踪止损（相对最高价）
            if self._highest_close_since_entry:
                trailing_price = self._highest_close_since_entry * (1.0 - float(self.params.trailing_stop_pct) / 100.0)
                if current_price <= trailing_price:
                    self.log(
                        f'追踪止损触发：现价={current_price:.2f} ≤ 追踪价={trailing_price:.2f} (最高={self._highest_close_since_entry:.2f})，清仓卖出'
                    )
                    self.order = self.sell(size=self.position.size)
                    return

            # 止盈（保留原逻辑）
            if avg_price > 0:
                target_price = avg_price * (1.0 + float(self.params.take_profit_pct) / 100.0)
                if current_price >= target_price:
                    self.log(f'止盈触发：现价={current_price:.2f} ≥ 目标价={target_price:.2f}，清仓卖出')
                    self.order = self.sell(size=self.position.size)
                    return  # 当日已清仓，避免同时定投
        else:
            # 无持仓时重置最高价
            self._highest_close_since_entry = None

        # 定投日买入逻辑
        try:
            dt = self.data.datetime.datetime(0)
            weekday = dt.weekday()  # Monday=0 ... Sunday=6
        except Exception:
            weekday = None

        if weekday is None or weekday != self._weekday_idx:
            # 非定投日也记录一次指标，确保数组长度与回测K线一致
            percentile_n = self._compute_percentile_lookback(self.params.lookback_days)
            price_n = float(self.data.close[0])
            atr_pct_n = float(self._atr[0]) / price_n if price_n > 0 else 0.0
            equity_n = float(self.broker.getvalue())
            pos_val_n = float(self.position.size) * price_n if self.position else 0.0
            trend_ok_n = 1 if self._trend_allowed() else 0

            self.indicator_data['percentile'].append(percentile_n)
            self.indicator_data['scaled_amount'].append(0.0)
            self.indicator_data['atr_pct'].append(atr_pct_n)
            self.indicator_data['trend_ok'].append(trend_ok_n)
            self.indicator_data['pos_value_pct'].append((pos_val_n / equity_n) if equity_n > 0 else 0.0)
            self.indicator_data['cooldown'].append(0)
            return  # 非定投日

        # 冷却期：避免过度频繁买入
        bar_index = len(self)
        in_cooldown = False
        if self._last_buy_bar_index is not None:
            if (bar_index - self._last_buy_bar_index) < int(self.params.cooldown_bars):
                in_cooldown = True
        if in_cooldown:
            # 指标记录后返回
            percentile_cd = self._compute_percentile_lookback(self.params.lookback_days)
            atr_pct_cd = float(self._atr[0]) / float(self.data.close[0]) if float(self.data.close[0]) > 0 else 0.0
            equity = float(self.broker.getvalue())
            pos_val = float(self.position.size) * float(self.data.close[0]) if self.position else 0.0
            self.indicator_data['percentile'].append(percentile_cd)
            self.indicator_data['scaled_amount'].append(0.0)
            self.indicator_data['atr_pct'].append(atr_pct_cd)
            self.indicator_data['trend_ok'].append(0)
            self.indicator_data['pos_value_pct'].append((pos_val / equity) if equity > 0 else 0.0)
            self.indicator_data['cooldown'].append(1)
            return

        # 趋势过滤：要求上升趋势时才定投（可配置）
        trend_ok = self._trend_allowed()
        if self.params.require_uptrend and (not trend_ok):
            # 指标记录后返回
            percentile_t = self._compute_percentile_lookback(self.params.lookback_days)
            atr_pct_t = float(self._atr[0]) / float(self.data.close[0]) if float(self.data.close[0]) > 0 else 0.0
            equity = float(self.broker.getvalue())
            pos_val = float(self.position.size) * float(self.data.close[0]) if self.position else 0.0
            self.indicator_data['percentile'].append(percentile_t)
            self.indicator_data['scaled_amount'].append(0.0)
            self.indicator_data['atr_pct'].append(atr_pct_t)
            self.indicator_data['trend_ok'].append(0)
            self.indicator_data['pos_value_pct'].append((pos_val / equity) if equity > 0 else 0.0)
            self.indicator_data['cooldown'].append(0)
            return

        # 计算近 N 日分位数
        percentile = self._compute_percentile_lookback(self.params.lookback_days)
        multiplier = self._compute_multiplier(percentile)

        # 波动率缩放
        price_now = float(self.data.close[0])
        atr_now = float(self._atr[0]) if self._atr[0] is not None else 0.0
        atr_pct = (atr_now / price_now) if price_now > 0 else 0.0
        vol_scale = self._compute_volatility_scale(atr_pct)
        multiplier *= vol_scale

        # 动态定投现金（为 1000 的整数倍）
        base_amount = int(self.params.base_invest_amount)
        raw_amount = base_amount * multiplier
        # 四舍五入到 1000 的整数倍，至少 1000
        invest_amount = max(1000, int(round(raw_amount / 1000.0)) * 1000)

        # 资金与下单股数计算
        cash = float(self.broker.get_cash())
        price = float(self.data.close[0])
        equity = float(self.broker.getvalue())
        # 仓位上限控制
        position_value = float(self.position.size) * price if self.position else 0.0
        max_pos_value = float(self.params.max_position_value_pct) * equity if equity > 0 else 0.0
        if max_pos_value > 0 and (position_value >= max_pos_value):
            self.log(
                f'仓位上限限制：当前持仓市值占比≥{self.params.max_position_value_pct*100:.1f}% ，跳过买入'
            )
            # 指标记录后返回
            self.indicator_data['percentile'].append(percentile)
            self.indicator_data['scaled_amount'].append(0.0)
            self.indicator_data['atr_pct'].append(atr_pct)
            self.indicator_data['trend_ok'].append(1 if trend_ok else 0)
            self.indicator_data['pos_value_pct'].append((position_value / equity) if equity > 0 else 0.0)
            self.indicator_data['cooldown'].append(0)
            return

        if cash < invest_amount:
            # 资金不足则按可用资金的 95% 定投（保留手续费空间）
            invest_amount = int(cash * 0.95)
            invest_amount = max(1000, (invest_amount // 1000) * 1000)

        # 计算股数并按最小交易单位取整
        shares = int(invest_amount / price) if price > 0 else 0
        lot = int(self.params.lot_size)
        if shares >= lot:
            shares = (shares // lot) * lot
        else:
            # 不足一个交易单位则不下单
            self.log(f'资金不足以买入最小单位：现金={cash:.2f}, 价格={price:.2f}, 需要≥{lot}股')
            # 收集指标数据后返回
            self.indicator_data['percentile'].append(percentile)
            self.indicator_data['scaled_amount'].append(0.0)
            self.indicator_data['atr_pct'].append(atr_pct)
            self.indicator_data['trend_ok'].append(1 if trend_ok else 0)
            self.indicator_data['pos_value_pct'].append((position_value / equity) if equity > 0 else 0.0)
            self.indicator_data['cooldown'].append(0)
            return

        # 记录并执行买入
        self.log(
            f'定投日买入：weekday={weekday}, 分位数={percentile:.3f}, 倍数={multiplier:.2f}, '
            f'波动率ATR%={atr_pct:.3f}, 现金={cash:.2f}, 计划金额={invest_amount}, 股价={price:.2f}, 股数={shares}'
        )
        self.order = self.buy(size=shares)
        self._last_buy_bar_index = bar_index
        # 初始化最高价（下一根更新更准确，这里先记录当前价）
        self._highest_close_since_entry = price

        # 收集指标数据
        self.indicator_data['percentile'].append(percentile)
        self.indicator_data['scaled_amount'].append(float(invest_amount))
        self.indicator_data['atr_pct'].append(atr_pct)
        self.indicator_data['trend_ok'].append(1 if trend_ok else 0)
        self.indicator_data['pos_value_pct'].append((position_value / equity) if equity > 0 else 0.0)
        self.indicator_data['cooldown'].append(0)

    def collect_indicator_data(self):
        """
        收集策略相关指标数据

        当前实现：
        - 在 next 中已记录分位数、定投金额、波动率、趋势过滤、仓位比例与冷却期标识。
        """
        # 保持空实现以符合基类接口；数据已在 next 中追加
        return

    # ---------- 内部工具方法 ----------
    def _normalize_weekday(self, w: Union[int, str]) -> int:
        """
        规范化参数到 0-6 的 weekday 索引

        参数：
        - w (int | str): 周几，int 0-6 或字符串（支持中英文与缩写）。

        返回值：
        - int: 0-6，分别对应周一到周日。
        """
        if isinstance(w, int):
            if 0 <= w <= 6:
                return w
            # 越界默认周三
            return 2
        key = str(w).strip().lower()
        return WEEKDAY_MAP.get(key, 2)

    def _compute_percentile_lookback(self, n: int) -> float:
        """
        计算当前收盘价在近 n 日中的分位数（0-1）

        参数：
        - n (int): 回溯交易日数。

        返回值：
        - float: 分位数，范围 [0, 1]；若样本不足，返回 0.5。
        """
        n = max(1, int(n))
        values = []
        # 收集最多 n 天的历史收盘价（含当日）
        for i in range(0, min(len(self.data), n)):
            try:
                v = float(self.data.close[-i]) if i > 0 else float(self.data.close[0])
                values.append(v)
            except Exception:
                break
        if len(values) < 5:
            return 0.5
        current = float(self.data.close[0])
        # 计算百分位排名：<= 当前价的数量 / 总数
        count_le = sum(1 for v in values if v <= current)
        percentile = count_le / float(len(values))
        return max(0.0, min(1.0, percentile))

    def _compute_multiplier(self, p: float) -> float:
        """
        根据分位数计算定投倍数

        规则：
        - p ≤ low_percentile → 使用 max_multiplier；
        - p ≥ high_percentile → 使用 min_multiplier；
        - 其余区间线性插值：从 max_multiplier 过渡到 min_multiplier。

        参数：
        - p (float): 分位数（0-1）。

        返回值：
        - float: 定投倍数。
        """
        lp = float(self.params.low_percentile)
        hp = float(self.params.high_percentile)
        min_m = float(self.params.min_multiplier)
        max_m = float(self.params.max_multiplier)

        p = max(0.0, min(1.0, p))
        if p <= lp:
            return max_m
        if p >= hp:
            return min_m
        # 线性插值：p 从 lp→hp 时，从 max_m → min_m
        t = (p - lp) / (hp - lp)
        return max_m + t * (min_m - max_m)

    def _compute_volatility_scale(self, atr_pct: float) -> float:
        """
        根据波动率（ATR/收盘价）计算现金缩放倍数

        规则：
        - atr_pct ≤ atr_pct_low → 使用 volatility_scale_max（更积极）；
        - atr_pct ≥ atr_pct_high → 使用 volatility_scale_min（更保守）；
        - 中间线性插值。

        参数：
        - atr_pct (float): ATR占比（ATR/收盘价）。

        返回值：
        - float: 现金缩放倍数。
        """
        low = float(self.params.atr_pct_low)
        high = float(self.params.atr_pct_high)
        smin = float(self.params.volatility_scale_min)
        smax = float(self.params.volatility_scale_max)
        x = max(0.0, atr_pct)
        if x <= low:
            return smax
        if x >= high:
            return smin
        # 线性插值：x 从 low→high 时，从 smax → smin
        t = (x - low) / (high - low)
        return smax + t * (smin - smax)

    def _trend_allowed(self) -> bool:
        """
        趋势过滤：
        - 要求快线均线 ≥ 慢线均线；
        - 要求现价 ≥ 快线均线。

        返回值：
        - bool: 趋势过滤是否通过。
        """
        try:
            fast = float(self._sma_fast[0])
            slow = float(self._sma_slow[0])
            price = float(self.data.close[0])
        except Exception:
            return True  # 指标不可用时不拦截
        return (fast >= slow) and (price >= fast)