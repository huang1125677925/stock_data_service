#!/usr/bin/env python3
"""
KDJ指标交易策略
基于KDJ指标的金叉死叉和超买超卖进行买卖
"""

import backtrader as bt
from .base_strategy import BaseQuantStrategy, register_strategy


@register_strategy
class KDJStrategy(BaseQuantStrategy):
    _strategy_name = 'kdj'
    _strategy_description = 'KDJ指标交易策略'
    _strategy_params = {
        'period': {'type': 'int', 'default': 9, 'description': 'KDJ计算周期'},
        'period_dfast': {'type': 'int', 'default': 3, 'description': 'D线平滑周期'},
        'period_dslow': {'type': 'int', 'default': 3, 'description': 'J线平滑周期'},
        'oversold': {'type': 'float', 'default': 20.0, 'description': '超卖阈值'},
        'overbought': {'type': 'float', 'default': 80.0, 'description': '超买阈值'}
    }
    """
    KDJ指标交易策略
    
    策略逻辑：
    1. 当K线上穿D线且在超卖区域（<20）时买入
    2. 当K线下穿D线且在超买区域（>80）时卖出
    3. 结合J线的方向确认信号强度
    """
    
    params = dict(
        period=9,           # KDJ计算周期
        period_dfast=3,     # D线平滑周期
        period_dslow=3,     # J线平滑周期
        oversold=20.0,      # 超卖阈值
        overbought=80.0,    # 超买阈值
        printlog=True
    )
    
    def init_indicators(self):
        """
        初始化技术指标
        """
        # KDJ指标（使用Stochastic指标实现）
        self.stoch = bt.indicators.Stochastic(
            self.data,
            period=self.params.period,
            period_dfast=self.params.period_dfast,
            period_dslow=self.params.period_dslow
        )
        
        # K线和D线
        self.k_line = self.stoch.percK
        self.d_line = self.stoch.percD
        
        # J线计算：J = 3K - 2D
        self.j_line = 3 * self.k_line - 2 * self.d_line
        
        # KD交叉信号
        self.kd_crossover = bt.indicators.CrossOver(
            self.k_line, self.d_line
        )
        
        # 初始化指标数据收集结构
        self.indicator_data = {
            'k_line': [],       # K线
            'd_line': [],       # D线
            'j_line': [],       # J线
            'kd_crossover': []  # KD交叉信号
        }
    
    def get_strategy_name(self) -> str:
        return "kdj"
    
    def get_strategy_description(self) -> str:
        return "KDJ指标交易策略：基于KDJ指标的金叉死叉和超买超卖区域进行买卖"
    
    def next(self):
        """
        策略主逻辑
        """
        # 首先调用父类的next方法来记录历史数据
        super().next()
        
        # 如果有未完成的订单，跳过
        if self.order:
            return
        
        # 获取当前KDJ值
        current_k = self.k_line[0]
        current_d = self.d_line[0]
        current_j = self.j_line[0]
        
        # 获取当前持仓
        if not self.position:
            # 没有持仓，检查买入信号
            # K线上穿D线且在超卖区域
            if (self.kd_crossover > 0 and 
                current_k < self.params.oversold and 
                current_d < self.params.oversold):
                
                self.log(f'KDJ买入信号: 价格={self.data.close[0]:.2f}, '
                        f'K={current_k:.2f}, D={current_d:.2f}, J={current_j:.2f}, '
                        f'超卖阈值={self.params.oversold}')
                
                # 全仓买入：计算可买入的最大股数
                cash = self.broker.get_cash()
                current_price = self.data.close[0]
                
                # 预留5%的资金作为安全边际
                available_cash = cash * 0.95
                
                # 计算最大可买股数
                max_shares = int(available_cash / current_price)
                
                # 确保至少能买入100股（1手）
                if max_shares >= 100:
                    # 按100股的整数倍买入
                    max_shares = (max_shares // 100) * 100
                    
                    self.log(f'KDJ全仓买入: 总资金={cash:.2f}, 可用资金={available_cash:.2f}, '
                            f'股价={current_price:.2f}, 买入股数={max_shares}')
                    self.order = self.buy(size=max_shares)
                else:
                    self.log(f'资金不足: 总资金={cash:.2f}, 股价={current_price:.2f}, '
                            f'无法买入最小单位(100股)，需要资金={current_price * 100:.2f}')
        
        else:
            # 有持仓，检查卖出信号
            # K线下穿D线且在超买区域
            if (self.kd_crossover < 0 and 
                current_k > self.params.overbought and 
                current_d > self.params.overbought):
                
                self.log(f'KDJ卖出信号: 价格={self.data.close[0]:.2f}, '
                        f'K={current_k:.2f}, D={current_d:.2f}, J={current_j:.2f}, '
                        f'超买阈值={self.params.overbought}')
                
                # 全仓卖出：卖出所有持仓
                position_size = self.position.size
                if position_size > 0:
                    self.log(f'KDJ全仓卖出: 当前持仓={position_size}')
                    self.order = self.sell(size=position_size)
    
    def collect_indicator_data(self):
        """
        收集指标数据
        """
        try:
            # 收集KDJ指标数据
            self.indicator_data['k_line'].append(float(self.k_line[0]) if len(self.k_line) > 0 else None)
            self.indicator_data['d_line'].append(float(self.d_line[0]) if len(self.d_line) > 0 else None)
            self.indicator_data['j_line'].append(float(self.j_line[0]) if len(self.j_line) > 0 else None)
            self.indicator_data['kd_crossover'].append(float(self.kd_crossover[0]) if len(self.kd_crossover) > 0 else None)
        except Exception as e:
            self.log(f'收集指标数据时出错: {str(e)}')