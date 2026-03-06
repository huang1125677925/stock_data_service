from typing import Dict, Any
from .base_strategy import BaseQuantStrategy, register_strategy


@register_strategy
class GridTradingDailyChangeStrategy(BaseQuantStrategy):
    _strategy_name = 'grid_trading_daily_change'
    _strategy_description = '日涨跌幅网格：按日涨跌幅触发买卖，支持按股数或金额下单'
    _strategy_params: Dict[str, Any] = {
        'buy_change_pct': {'type': 'float', 'default': 1.0, 'description': '日涨跌幅触发买入阈值（%）'},
        'sell_change_pct': {'type': 'float', 'default': 1.0, 'description': '日涨跌幅触发卖出阈值（%）'},
        'buy_mode': {'type': 'str', 'default': 'shares', 'description': "买入模式：'shares' 或 'amount'"},
        'buy_qty': {'type': 'int', 'default': 100, 'description': '买入股数（buy_mode=shares）'},
        'buy_amount': {'type': 'float', 'default': 1000.0, 'description': '买入金额（buy_mode=amount）'},
        'sell_mode': {'type': 'str', 'default': 'shares', 'description': "卖出模式：'shares' 或 'amount'"},
        'sell_qty': {'type': 'int', 'default': 100, 'description': '卖出股数（sell_mode=shares）'},
        'sell_amount': {'type': 'float', 'default': 1000.0, 'description': '卖出金额（sell_mode=amount）'},
        'lot_size': {'type': 'int', 'default': 100, 'description': '最小交易单位（股/手）'},
        'safety_cash_pct': {'type': 'float', 'default': 0.05, 'description': '买入保留现金比例'},
    }

    params = dict(
        buy_change_pct=1.0,
        sell_change_pct=1.0,
        buy_mode='shares',
        buy_qty=100,
        buy_amount=1000.0,
        sell_mode='shares',
        sell_qty=100,
        sell_amount=1000.0,
        lot_size=100,
        safety_cash_pct=0.05,
        printlog=True,
    )

    def init_indicators(self):
        self.lot_size = int(self.params.lot_size)
        self.indicator_data = {
            'prev_close': [],
            'current_price': [],
            'daily_change_pct': [],
            'buy_threshold_pct': [],
            'sell_threshold_pct': [],
            'position_size': [],
        }

    def get_strategy_name(self) -> str:
        return 'grid_trading_daily_change'

    def get_strategy_description(self) -> str:
        return '日涨跌幅网格：按日涨跌幅触发买卖，支持按股数或金额下单'

    def _round_to_lot(self, shares: int) -> int:
        if self.lot_size <= 0:
            return max(1, shares)
        return (shares // self.lot_size) * self.lot_size

    def _can_buy_with_cash(self, price: float, desired_shares: int) -> int:
        cash = float(self.broker.get_cash())
        available_cash = cash * (1.0 - float(self.params.safety_cash_pct))
        max_shares = self._round_to_lot(int(available_cash / max(price, 1e-6)))
        return max(0, min(self._round_to_lot(desired_shares), max_shares))

    def _normalize_mode(self, mode: Any) -> str:
        try:
            mode_str = str(mode).lower()
        except Exception:
            mode_str = 'shares'
        return mode_str if mode_str in ('shares', 'amount') else 'shares'

    def _calc_desired_shares(self, mode: str, qty: int, amount: float, price: float) -> int:
        if mode == 'amount':
            return int(amount / price) if price > 0 else 0
        return int(qty)

    def next(self):
        super().next()

        if self.order:
            return

        current_price = float(self.data.close[0])
        if current_price <= 0:
            return

        if len(self.data) < 2:
            self.indicator_data['prev_close'].append(None)
            self.indicator_data['current_price'].append(current_price)
            self.indicator_data['daily_change_pct'].append(None)
            self.indicator_data['buy_threshold_pct'].append(-abs(float(self.params.buy_change_pct)))
            self.indicator_data['sell_threshold_pct'].append(abs(float(self.params.sell_change_pct)))
            self.indicator_data['position_size'].append(float(self.position.size or 0))
            return

        prev_close = float(self.data.close[-1])
        if prev_close <= 0:
            return

        change_pct = (current_price - prev_close) / prev_close * 100.0
        buy_trigger = -abs(float(self.params.buy_change_pct))
        sell_trigger = abs(float(self.params.sell_change_pct))

        acted = False

        if not acted and change_pct <= buy_trigger:
            buy_mode = self._normalize_mode(self.params.buy_mode)
            desired = self._calc_desired_shares(buy_mode, int(self.params.buy_qty), float(self.params.buy_amount), current_price)
            buy_shares = self._can_buy_with_cash(current_price, desired)
            if buy_shares >= self.lot_size:
                self.order = self.buy(size=buy_shares)
                acted = True
                self.log(f'日跌买入: 涨跌幅={change_pct:.2f}%, 价格={current_price:.4f}, 股数={buy_shares}')
            else:
                self.log(f'资金不足，无法买入最小单位：价格={current_price:.4f}, 需至少={self.lot_size}股')

        if not acted and change_pct >= sell_trigger:
            sell_mode = self._normalize_mode(self.params.sell_mode)
            desired = self._calc_desired_shares(sell_mode, int(self.params.sell_qty), float(self.params.sell_amount), current_price)
            desired = self._round_to_lot(desired)
            position_size = int(self.position.size or 0)
            sell_shares = min(desired, self._round_to_lot(position_size))
            if sell_shares >= self.lot_size:
                self.order = self.sell(size=sell_shares)
                acted = True
                self.log(f'日涨卖出: 涨跌幅={change_pct:.2f}%, 价格={current_price:.4f}, 股数={sell_shares}')
            else:
                if position_size > 0:
                    self.log(f'持仓不足，无法按最小单位卖出：价格={current_price:.4f}, 持仓={position_size}')

        self.indicator_data['prev_close'].append(prev_close)
        self.indicator_data['current_price'].append(current_price)
        self.indicator_data['daily_change_pct'].append(change_pct)
        self.indicator_data['buy_threshold_pct'].append(buy_trigger)
        self.indicator_data['sell_threshold_pct'].append(sell_trigger)
        self.indicator_data['position_size'].append(float(self.position.size or 0))

    def collect_indicator_data(self):
        return
