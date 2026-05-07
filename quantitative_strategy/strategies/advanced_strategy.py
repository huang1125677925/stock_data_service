#!/usr/bin/env python3
"""
高级综合技术指标策略
基于多种技术指标的综合判断进行交易
"""

import backtrader as bt
import numpy as np
from .base_strategy import BaseQuantStrategy, register_strategy


@register_strategy
class AdvancedStrategy(BaseQuantStrategy):
    _strategy_name = 'advanced'
    _strategy_description = '高级综合策略：基于多种技术指标的综合判断进行交易'
    _strategy_params = {
        'ema_long_period': {'type': 'int', 'default': 21, 'description': 'EMA长周期'},
        'ema_short_period': {'type': 'int', 'default': 8, 'description': 'EMA短周期'},
        'smooth_period': {'type': 'int', 'default': 3, 'description': 'EMA平滑周期'},
        'volume_multiplier': {'type': 'float', 'default': 1.1, 'description': '成交量放大倍数'},
        'dx_threshold': {'type': 'float', 'default': -10.0, 'description': 'DX卖出阈值'},
        'zk_threshold': {'type': 'float', 'default': -5.0, 'description': 'ZK卖出阈值'},
        'stop_loss_pct': {'type': 'float', 'default': 10.0, 'description': '止损百分比'},
        'sell_conditions_count': {'type': 'int', 'default': 2, 'description': '卖出条件满足数量'}
    }
    
    # backtrader参数定义
    params = (
        ('ema_long_period', 21),
        ('ema_short_period', 8),
        ('smooth_period', 3),
        ('volume_multiplier', 1.1),
        ('dx_threshold', -10.0),
        ('zk_threshold', -5.0),
        ('stop_loss_pct', 10.0),
        ('sell_conditions_count', 2),
        ('printlog', True),  # 是否打印日志
    )
    
    """
    高级技术指标综合策略
    
    策略逻辑：
    1. 基于EMA均线系统判断趋势方向
    2. 使用DX动向指标和ZK随机指标确认信号
    3. 成交量放大确认买入时机
    4. 多条件卖出机制和止损保护
    5. 详细的资金管理和风险控制
    """
    
    def __init__(self):
        super().__init__()
        # 获取策略参数
        self.ema_long_period = self.params.ema_long_period
        self.ema_short_period = self.params.ema_short_period
        self.smooth_period = self.params.smooth_period
        self.volume_multiplier = self.params.volume_multiplier
        self.dx_threshold = self.params.dx_threshold
        self.zk_threshold = self.params.zk_threshold
        self.stop_loss_pct = self.params.stop_loss_pct
        self.sell_conditions_count = self.params.sell_conditions_count
        
        # 初始化指标
        self.ema_long = bt.indicators.EMA(period=self.ema_long_period)
        self.ema_short = bt.indicators.EMA(period=self.ema_short_period)
        self.ema_smooth = bt.indicators.EMA(self.ema_short, period=self.smooth_period)
        self.volume_sma = bt.indicators.SMA(self.data.volume, period=20)
        
        # 计算DX和ZK指标
        # 使用DirectionalMovement获取ADX（平均趋向指数）
        self.di = bt.indicators.DirectionalMovement(period=14)
        self.dx = self.di.adx  # 使用DirectionalMovement的ADX（adx）作为动向强度
        self.zk = bt.indicators.Stochastic(period=9, period_dfast=3).percK
    
    def init_indicators(self):
        """
        初始化技术指标
        """
        # 指标已在__init__中初始化
        
        # 初始化指标数据收集结构
        self.indicator_data = {
            'ema_long': [],      # EMA长期线
            'ema_short': [],     # EMA短期线
            'ema_smooth': [],    # EMA平滑线
            'volume_ratio': [],  # 成交量比率
            'dx': [],           # DX动向指标
            'zk': []            # ZK随机指标
        }
    
    def get_strategy_name(self) -> str:
        return "advanced"
    
    def get_strategy_description(self) -> str:
        """
        获取策略描述
        """
        return "高级综合策略：基于EMA均线系统、DX动向指标和ZK控盘指标的综合技术分析策略"
    
    def next(self):
        """
        策略主逻辑：每个交易日执行的策略逻辑
        """
        # 首先调用父类的next方法来记录历史数据
        super().next()
        
        # 检查是否有足够的数据
        if len(self.data) < max(self.ema_long_period, 20):
            return
            
        # 获取当前价格和指标值
        current_price = self.data.close[0]
        ema_long_val = self.ema_long[0]
        ema_short_val = self.ema_short[0]
        ema_smooth_val = self.ema_smooth[0]
        volume_ratio = self.data.volume[0] / self.volume_sma[0] if self.volume_sma[0] > 0 else 0
        dx_val = self.dx[0] if len(self.dx) > 0 else 0
        zk_val = self.zk[0] if len(self.zk) > 0 else 0
        
        # 获取当前资金和持仓
        current_cash = self.broker.get_cash()
        current_position = self.position.size
        
        # 买入逻辑
        if not self.position:  # 没有持仓时考虑买入
            # 买入条件：
            # 1. EMA短期线上穿长期线
            # 2. 平滑EMA确认趋势
            # 3. 成交量放大
            buy_condition1 = ema_short_val > ema_long_val and self.ema_short[-1] <= self.ema_long[-1]
            buy_condition2 = ema_smooth_val > ema_short_val
            buy_condition3 = volume_ratio > self.volume_multiplier
            
            if buy_condition1 and buy_condition2 and buy_condition3:
                # 计算最大可购买股数（预留5%安全边际）
                available_cash = current_cash * 0.95
                max_shares = int(available_cash / current_price)
                
                # 按100股的整数倍买入
                shares_to_buy = (max_shares // 100) * 100
                
                if shares_to_buy >= 100:  # 至少买入100股
                    self.buy(size=shares_to_buy)
                    self.log(f'买入信号 - 价格: {current_price:.2f}, 数量: {shares_to_buy}, '
                           f'EMA短: {ema_short_val:.2f}, EMA长: {ema_long_val:.2f}, '
                           f'成交量比率: {volume_ratio:.2f}, 可用资金: {available_cash:.2f}')
                else:
                    self.log(f'资金不足 - 当前资金: {current_cash:.2f}, 股价: {current_price:.2f}, '
                           f'需要最少资金: {current_price * 100:.2f}')
        
        # 卖出逻辑
        elif self.position:  # 有持仓时考虑卖出
            # 计算持仓成本和当前盈亏
            entry_price = self.position.price
            profit_pct = (current_price - entry_price) / entry_price * 100
            
            # 卖出条件计数
            sell_conditions = 0
            
            # 条件1：DX指标低于阈值
            if dx_val < self.dx_threshold:
                sell_conditions += 1
                
            # 条件2：ZK指标低于阈值
            if zk_val < self.zk_threshold:
                sell_conditions += 1
                
            # 条件3：EMA短期线跌破长期线
            if ema_short_val < ema_long_val and self.ema_short[-1] >= self.ema_long[-1]:
                sell_conditions += 1
                
            # 条件4：止损
            if profit_pct <= -self.stop_loss_pct:
                sell_conditions += 1
                
            # 当满足指定数量的卖出条件时卖出
            if sell_conditions >= self.sell_conditions_count or profit_pct <= -self.stop_loss_pct:
                self.sell(size=current_position)
                sell_reason = "止损" if profit_pct <= -self.stop_loss_pct else f"满足{sell_conditions}个卖出条件"
                self.log(f'卖出信号 - 价格: {current_price:.2f}, 数量: {current_position}, '
                       f'成本: {entry_price:.2f}, 盈亏: {profit_pct:.2f}%, '
                       f'DX: {dx_val:.2f}, ZK: {zk_val:.2f}, 原因: {sell_reason}')
    
    def collect_indicator_data(self):
        """
        收集指标数据
        """
        try:
            # 收集EMA指标数据
            self.indicator_data['ema_long'].append(float(self.ema_long[0]) if len(self.ema_long) > 0 else None)
            self.indicator_data['ema_short'].append(float(self.ema_short[0]) if len(self.ema_short) > 0 else None)
            self.indicator_data['ema_smooth'].append(float(self.ema_smooth[0]) if len(self.ema_smooth) > 0 else None)
            
            # 收集成交量比率
            volume_ratio = self.data.volume[0] / self.volume_sma[0] if len(self.volume_sma) > 0 and self.volume_sma[0] > 0 else None
            self.indicator_data['volume_ratio'].append(volume_ratio)
            
            # 收集DX和ZK指标数据
            self.indicator_data['dx'].append(float(self.dx[0]) if len(self.dx) > 0 else None)
            self.indicator_data['zk'].append(float(self.zk[0]) if len(self.zk) > 0 else None)
        except Exception as e:
            self.log(f'收集指标数据时出错: {str(e)}')