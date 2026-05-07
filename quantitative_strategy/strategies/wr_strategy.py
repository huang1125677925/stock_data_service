#!/usr/bin/env python3
"""
威廉指标(WR)交易策略
基于威廉指标的超买超卖进行买卖
"""

import backtrader as bt
from .base_strategy import BaseQuantStrategy, register_strategy


@register_strategy
class WRStrategy(BaseQuantStrategy):
    _strategy_name = 'wr'
    _strategy_description = '威廉指标交易策略'
    _strategy_params = {
        'period': {'type': 'int', 'default': 14, 'description': 'WR计算周期'},
        'oversold': {'type': 'float', 'default': -80.0, 'description': '超卖阈值'},
        'overbought': {'type': 'float', 'default': -20.0, 'description': '超买阈值'}
    }
    """
    威廉指标(WR)交易策略
    
    策略逻辑：
    1. 当WR从超卖区域（<-80）向上突破时买入
    2. 当WR从超买区域（>-20）向下突破时卖出
    3. WR在-80到-20之间时保持观望
    
    注意：威廉指标的值域为-100到0，数值越小表示越超卖
    """
    
    params = dict(
        period=14,          # WR计算周期
        oversold=-80.0,     # 超卖阈值
        overbought=-20.0,   # 超买阈值
        printlog=True
    )
    
    def init_indicators(self):
        """
        初始化技术指标
        """
        # 威廉指标
        self.wr = bt.indicators.WilliamsR(
            self.data,
            period=self.params.period
        )
        
        # 初始化指标数据收集结构
        self.indicator_data = {
            'wr': []      # 威廉指标
        }
    
    def get_strategy_name(self) -> str:
        return "wr"
    
    def get_strategy_description(self) -> str:
        return "威廉指标交易策略：基于威廉指标的超买超卖区域进行买卖"
    
    def next(self):
        """
        策略主逻辑
        """
        # 首先调用父类的next方法来记录历史数据
        super().next()
        
        # 如果有未完成的订单，跳过
        if self.order:
            return
        
        # 获取当前WR值
        current_wr = self.wr[0]
        
        # 需要至少有一个历史WR值才能判断趋势
        if len(self.wr) < 2:
            return
        
        prev_wr = self.wr[-1]
        
        # 获取当前持仓
        if not self.position:
            # 没有持仓，检查买入信号
            # WR从超卖区域向上突破
            if prev_wr <= self.params.oversold and current_wr > self.params.oversold:
                
                self.log(f'WR买入信号: 价格={self.data.close[0]:.2f}, '
                        f'WR={current_wr:.2f}, 前值={prev_wr:.2f}, '
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
                    
                    self.log(f'WR全仓买入: 总资金={cash:.2f}, 可用资金={available_cash:.2f}, '
                            f'股价={current_price:.2f}, 买入股数={max_shares}')
                    self.order = self.buy(size=max_shares)
                else:
                    self.log(f'资金不足: 总资金={cash:.2f}, 股价={current_price:.2f}, '
                            f'无法买入最小单位(100股)，需要资金={current_price * 100:.2f}')
        
        else:
            # 有持仓，检查卖出信号
            # WR从超买区域向下突破
            if prev_wr >= self.params.overbought and current_wr < self.params.overbought:
                self.log(f'WR卖出信号: 价格={self.data.close[0]:.2f}, '
                        f'WR={current_wr:.2f}, 前值={prev_wr:.2f}, '
                        f'超买阈值={self.params.overbought}')
                
                # 全仓卖出：卖出所有持仓
                position_size = self.position.size
                if position_size > 0:
                    self.log(f'WR全仓卖出: 当前持仓={position_size}')
                    self.order = self.sell(size=position_size)
    
    def collect_indicator_data(self):
        """
        收集指标数据
        """
        try:
            # 收集威廉指标数据
            self.indicator_data['wr'].append(float(self.wr[0]) if len(self.wr) > 0 else None)
        except Exception as e:
            self.log(f'收集指标数据时出错: {str(e)}')