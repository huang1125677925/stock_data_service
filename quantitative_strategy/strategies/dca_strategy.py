#!/usr/bin/env python3
"""
简化版定投（Dollar-Cost Averaging, DCA）策略

功能：
- 支持按周指定定投日期（如每周二、每周三）；
- 每次定投固定金额；
- 支持设置止盈比例，达到止盈则清仓。

参数：
- invest_day (int): 定投的星期几，int 0-6 对应周一到周日，默认 2（周三）。
- invest_amount (float): 每次定投金额（现金），单位元，默认 1000.0。
- take_profit_pct (float): 止盈百分比（相对持仓均价），默认 15.0。
- lot_size (int): 股票最小交易单位（手/股），默认 100 股。

返回值：
- 通过基类的观测器与记录机制返回完整的交易与指标数据（无需显式返回）。

事件：
- 定投事件：在指定星期触发，按固定金额买入；
- 止盈事件：当收盘价 ≥ 均价 × (1 + take_profit_pct/100) 时清仓。
"""

import backtrader as bt
from .base_strategy import BaseQuantStrategy, register_strategy


@register_strategy
class DCASimpleStrategy(BaseQuantStrategy):
    """
    简化版定投策略实现类

    策略逻辑：
    - 在指定的每周某一天执行定投；
    - 每次定投固定金额；
    - 达到止盈阈值时清仓获利。
    """

    _strategy_name = 'dca_simple'
    _strategy_description = '简化定投策略：按周定投，固定金额，智能止盈'
    _strategy_params = {
        'invest_day': {'type': 'int', 'default': 2, 'description': '定投星期几（0=周一, 1=周二, ..., 6=周日）'},
        'invest_amount': {'type': 'float', 'default': 1000.0, 'description': '每次定投金额（现金），单位元'},
        'take_profit_pct': {'type': 'float', 'default': 15.0, 'description': '止盈百分比'},
        'lot_size': {
            'type': 'int', 
            'default': 100, 
            'description': '最小交易单位（股/手）。例如：100表示每手100股。该参数与invest_amount配合使用：系统先根据定投金额计算可买入的股数，再按此单位取整（向下舍入到最接近的整数倍）。若计算结果不足一个交易单位，则跳过本次买入。常见设置：A股股票为100，ETF通常为100或1000。'
        },
    }

    # backtrader 参数
    params = dict(
        invest_day=2,           # 0=周一, 1=周二, 2=周三, 3=周四, 4=周五, 5=周六, 6=周日
        invest_amount=1000.0,   # 每次定投金额
        take_profit_pct=15.0,   # 止盈百分比
        lot_size=100,           # 最小交易单位
        printlog=True,
    )

    def init_indicators(self):
        """
        初始化策略所需的运行期变量与观测数据结构
        """
        # 运行期状态
        self._invest_day = int(self.params.invest_day) % 7  # 确保在 0-6 范围内
        
        # 指标数据收集结构
        self.indicator_data = {
            'invest_day': [],      # 是否为定投日（0/1）
            'invest_amount': [],   # 本次定投金额
            'position_size': [],   # 当前持仓数量
            'position_value': [],  # 当前持仓市值
            'take_profit_pct': [], # 止盈百分比
        }

    def get_strategy_name(self) -> str:
        return 'dca_simple'

    def get_strategy_description(self) -> str:
        return '简化定投策略：按周定投，固定金额，智能止盈'

    def next(self):
        """
        策略主逻辑

        流程：
        1) 调用基类 next 收集数据；
        2) 若有持仓：检查止盈条件；
        3) 若当天为设定定投日：执行买入。
        """
        # 收集通用数据
        super().next()

        # 若存在未完成订单，跳过
        if self.order:
            return

        # 获取当前日期
        try:
            dt = self.data.datetime.datetime(0)
            current_weekday = dt.weekday()  # Monday=0 ... Sunday=6
        except Exception:
            current_weekday = None

        # 检查是否为定投日
        is_invest_day = (current_weekday is not None and 
                        current_weekday == self._invest_day)

        # 记录当前持仓信息
        position_size = float(self.position.size) if self.position else 0.0
        position_value = position_size * float(self.data.close[0])

        # 处理止盈逻辑
        if self.position and self.position.size > 0:
            avg_price = float(self.position.price)
            current_price = float(self.data.close[0])

            # 止盈检查
            if avg_price > 0:
                target_price = avg_price * (1.0 + float(self.params.take_profit_pct) / 100.0)
                if current_price >= target_price:
                    self.log(f'止盈触发：现价={current_price:.2f} ≥ 目标价={target_price:.2f}，清仓卖出')
                    self.order = self.sell(size=self.position.size)
                    
                    # 记录指标数据
                    self.indicator_data['invest_day'].append(1 if is_invest_day else 0)
                    self.indicator_data['invest_amount'].append(0.0)
                    self.indicator_data['position_size'].append(position_size)
                    self.indicator_data['position_value'].append(position_value)
                    self.indicator_data['take_profit_pct'].append(float(self.params.take_profit_pct))
                    return

        # 定投日买入逻辑
        if is_invest_day:
            # 计算可用资金
            cash = float(self.broker.get_cash())
            price = float(self.data.close[0])
            invest_amount = float(self.params.invest_amount)
            
            # 资金检查
            if cash < invest_amount:
                self.log(f'资金不足：可用现金={cash:.2f} < 定投金额={invest_amount:.2f}，跳过本次定投')
                
                # 记录指标数据
                self.indicator_data['invest_day'].append(1)
                self.indicator_data['invest_amount'].append(0.0)
                self.indicator_data['position_size'].append(position_size)
                self.indicator_data['position_value'].append(position_value)
                self.indicator_data['take_profit_pct'].append(float(self.params.take_profit_pct))
                return

            # 计算股数并按最小交易单位取整
            shares = int(invest_amount / price) if price > 0 else 0
            lot = int(self.params.lot_size)
            
            if shares >= lot:
                shares = (shares // lot) * lot  # 按整手取整
                
                # 记录并执行买入
                self.log(
                    f'定投日买入：weekday={current_weekday}, 现金={cash:.2f}, '
                    f'定投金额={invest_amount:.2f}, 股价={price:.2f}, 股数={shares}'
                )
                self.order = self.buy(size=shares)
                
                # 更新记录
                self.indicator_data['invest_day'].append(1)
                self.indicator_data['invest_amount'].append(invest_amount)
                self.indicator_data['position_size'].append(position_size)
                self.indicator_data['position_value'].append(position_value)
                self.indicator_data['take_profit_pct'].append(float(self.params.take_profit_pct))
            else:
                # 不足一个交易单位
                self.log(f'资金不足以买入最小单位：现金={cash:.2f}, 价格={price:.2f}, 需要≥{lot}股')
                
                # 记录指标数据
                self.indicator_data['invest_day'].append(1)
                self.indicator_data['invest_amount'].append(0.0)
                self.indicator_data['position_size'].append(position_size)
                self.indicator_data['position_value'].append(position_value)
                self.indicator_data['take_profit_pct'].append(float(self.params.take_profit_pct))
        else:
            # 非定投日也记录指标
            self.indicator_data['invest_day'].append(0)
            self.indicator_data['invest_amount'].append(0.0)
            self.indicator_data['position_size'].append(position_size)
            self.indicator_data['position_value'].append(position_value)
            self.indicator_data['take_profit_pct'].append(float(self.params.take_profit_pct))

    def collect_indicator_data(self):
        """
        收集策略相关指标数据

        当前实现：
        - 在 next 中已记录定投日、定投金额、持仓数量、持仓市值与止盈设置。
        """
        # 保持空实现以符合基类接口；数据已在 next 中追加
        return