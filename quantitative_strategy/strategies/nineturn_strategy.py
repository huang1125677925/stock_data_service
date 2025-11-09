#!/usr/bin/env python3
"""
神奇九转策略（DeMark Nine Turn）

功能：
- 使用 Tushare 接口 `stk_nineturn` 获取九转信号数据，并与常规 OHLCV 数据融合
- 当出现“下九转”（`nine_down_turn == -9`）当天买入
- 当出现“上九转”（`nine_up_turn == +9`）当天卖出

参数：
- printlog: 是否打印日志（继承自基类）

返回值：
- 策略执行过程中，交易记录、观测器数据、原始数据与指标数据将由基类统一收集并在回测结果中返回

事件：
- 买入事件：检测到 `nine_down_turn` 信号
- 卖出事件：检测到 `nine_up_turn` 信号

使用约束：
- 回测服务在添加数据源前，应预先从 Tushare 获取该股票在回测区间的九转数据，并将信号列合并到 DataFrame 中
- 数据列名需为 `nine_down_turn` 与 `nine_up_turn`，类型为数值（1 表示触发，0 表示未触发）
"""

import backtrader as bt
from typing import Dict, Any

from .base_strategy import BaseQuantStrategy, register_strategy


@register_strategy
class NineTurnStrategy(BaseQuantStrategy):
    """
    神奇九转买卖策略

    策略逻辑：
    - 下九转（-9）触发时买入
    - 上九转（+9）触发时卖出

    数据要求：
    - DataFeed 中包含两列数值型信号：`nine_down_turn`, `nine_up_turn`（1/0）
    - 该两列由服务层在回测前调用 Tushare 接口预取并合并
    """

    _strategy_name = 'nineturn'
    _strategy_description = '神奇九转策略：下九转买入、上九转卖出'
    _strategy_params: Dict[str, Any] = {}

    def init_indicators(self) -> None:
        """
        初始化技术指标

        本策略直接使用数据源中的九转信号列，不额外创建指标。
        """
        # 占位，确保方法存在
        pass

    def get_strategy_name(self) -> str:
        """获取策略名称"""
        return self._strategy_name

    def get_strategy_description(self) -> str:
        """获取策略描述"""
        return self._strategy_description

    def next(self) -> None:
        """
        策略主逻辑：
        - 无持仓且当日 `nine_down_turn == 1` → 买入（尽量用满仓，保留5%安全边际）
        - 有持仓且当日 `nine_up_turn == 1` → 卖出（全仓卖出）
        """
        # 调用父类记录基础数据与观测器
        super().next()

        # 若已有未完成订单则跳过
        if self.order:
            return

        current_price = float(self.data.close[0])

        # 信号读取：若列不存在则视为0
        try:
            down_signal = int(self.data.nine_down_turn[0])
        except Exception:
            down_signal = 0

        try:
            up_signal = int(self.data.nine_up_turn[0])
        except Exception:
            up_signal = 0

        # 买入逻辑：下九转
        if not self.position and down_signal == 1:
            # 预留5%资金作为安全边际
            cash = float(self.broker.get_cash())
            available_cash = cash * 0.95
            max_shares = int(available_cash / current_price) if current_price > 0 else 0

            if max_shares > 0:
                self.log(f'下九转触发，买入信号：价格={current_price:.2f}, 数量={max_shares}')
                self.order = self.buy(size=max_shares)
        # 卖出逻辑：上九转
        elif self.position and up_signal == 1:
            size = int(self.position.size)
            if size > 0:
                self.log(f'上九转触发，卖出信号：价格={current_price:.2f}, 数量={size}')
                self.order = self.sell(size=size)

    def collect_indicator_data(self) -> None:
        """
        收集指标数据

        要求：上下九转为信号值，统一以一个字典传入。
        示例：{'nine_down_turn': 0/1, 'nine_up_turn': 0/1}
        """
        # 读取九转信号，缺失则按 0 处理
        try:
            down_signal = int(self.data.nine_down_turn[0])
        except Exception:
            down_signal = 0

        try:
            up_signal = int(self.data.nine_up_turn[0])
        except Exception:
            up_signal = 0

        # 统一以一个字典传入到 indicator_data
        self.indicator_data.setdefault('up_signal', []).append(up_signal)
        self.indicator_data.setdefault('down_signal', []).append(down_signal)