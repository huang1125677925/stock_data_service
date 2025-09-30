#!/usr/bin/env python3
"""
布林带交易策略
基于布林带上下轨的突破进行买卖
"""

import backtrader as bt
from .base_strategy import BaseQuantStrategy, register_strategy


@register_strategy
class BollingerStrategy(BaseQuantStrategy):
    """
    布林带交易策略
    
    策略逻辑：
    1. 当价格跌破布林带下轨时买入（超卖信号）
    2. 当价格突破布林带上轨时卖出（超买信号）
    3. 价格在布林带中轨附近时保持观望
    
    布林带指标说明：
    - 中轨：移动平均线（通常为20日均线）
    - 上轨：中轨 + (标准差 × 倍数)
    - 下轨：中轨 - (标准差 × 倍数)
    """
    
    _strategy_name = 'bollinger'
    _strategy_description = '布林带交易策略'
    _strategy_params = {
        'period': {'type': 'int', 'default': 20, 'description': '移动平均线周期'},
        'devfactor': {'type': 'float', 'default': 2.0, 'description': '标准差倍数'},
        'movav': {'type': 'str', 'default': 'sma', 'description': '移动平均线类型(sma/ema)'}
    }
    
    params = dict(
        period=20,          # 移动平均线周期
        devfactor=2.0,      # 标准差倍数
        movav=bt.indicators.MovAv.SMA,  # 移动平均线类型
        printlog=True
    )
    
    def init_indicators(self):
        """
        初始化技术指标
        """
        # 处理movav参数：如果是字符串，转换为对应的指标类
        movav_class = self.params.movav
        if isinstance(movav_class, str):
            if movav_class.lower() == 'sma':
                movav_class = bt.indicators.MovAv.SMA
            elif movav_class.lower() == 'ema':
                movav_class = bt.indicators.MovAv.EMA
            else:
                # 默认使用SMA
                movav_class = bt.indicators.MovAv.SMA
        
        # 布林带指标
        self.bollinger = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.period,
            devfactor=self.params.devfactor,
            movav=movav_class
        )
        
        # 获取布林带的各个组成部分
        self.bb_top = self.bollinger.lines.top      # 上轨
        self.bb_mid = self.bollinger.lines.mid      # 中轨（移动平均线）
        self.bb_bot = self.bollinger.lines.bot      # 下轨
        
        # 用于判断价格与布林带的关系
        self.price_below_lower = None  # 价格是否在下轨以下
        self.price_above_upper = None  # 价格是否在上轨以上
        
        # 初始化指标数据收集结构
        self.indicator_data = {
            'bb_top': [],       # 布林带上轨
            'bb_mid': [],       # 布林带中轨
            'bb_bot': []        # 布林带下轨
        }
    
    def get_strategy_name(self) -> str:
        """
        获取策略名称
        
        Returns:
            str: 策略名称
        """
        return "bollinger"
    
    def get_strategy_description(self) -> str:
        """
        获取策略描述
        
        Returns:
            str: 策略描述
        """
        return "布林带交易策略：基于布林带上下轨的突破进行买卖操作"
    
    def next(self):
        """
        策略主逻辑
        
        在每个交易日执行的核心策略逻辑：
        1. 检查是否有未完成的订单
        2. 根据价格与布林带的关系判断买卖信号
        3. 执行相应的买卖操作
        """
        # 首先调用父类的next方法来记录历史数据
        super().next()
        
        # 如果有未完成的订单，跳过
        if self.order:
            return
        
        # 获取当前价格和布林带数值
        current_price = self.data.close[0]
        bb_upper = self.bb_top[0]
        bb_middle = self.bb_mid[0]
        bb_lower = self.bb_bot[0]
        
        # 需要至少有足够的历史数据才能进行判断
        if len(self.data) < self.params.period:
            return
        
        # 获取当前持仓状态
        if not self.position:
            # 没有持仓，检查买入信号
            # 当价格跌破布林带下轨时买入（超卖信号）
            if current_price <= bb_lower:
                
                self.log(f'布林带买入信号: 价格={current_price:.2f}, '
                        f'下轨={bb_lower:.2f}, 中轨={bb_middle:.2f}, '
                        f'上轨={bb_upper:.2f}')
                
                # 全仓买入：计算可买入的最大股数
                cash = self.broker.get_cash()
                
                # 预留5%的资金作为安全边际
                available_cash = cash * 0.95
                
                # 计算最大可买股数
                max_shares = int(available_cash / current_price)
                
                # 确保至少能买入100股（1手）
                if max_shares >= 100:
                    # 按100股的整数倍买入
                    max_shares = (max_shares // 100) * 100
                    
                    self.log(f'布林带全仓买入: 总资金={cash:.2f}, 可用资金={available_cash:.2f}, '
                            f'股价={current_price:.2f}, 买入股数={max_shares}')
                    self.order = self.buy(size=max_shares)
                else:
                    self.log(f'资金不足: 总资金={cash:.2f}, 股价={current_price:.2f}, '
                            f'无法买入最小单位(100股)，需要资金={current_price * 100:.2f}')
        
        else:
            # 有持仓，检查卖出信号
            # 当价格突破布林带上轨时卖出（超买信号）
            if current_price >= bb_upper:
                
                self.log(f'布林带卖出信号: 价格={current_price:.2f}, '
                        f'上轨={bb_upper:.2f}, 中轨={bb_middle:.2f}, '
                        f'下轨={bb_lower:.2f}')
                
                # 全仓卖出：卖出所有持仓
                position_size = self.position.size
                if position_size > 0:
                    self.log(f'布林带全仓卖出: 当前持仓={position_size}')
                    self.order = self.sell(size=position_size)
            
            # 可选：添加止损逻辑
            # 如果价格跌破中轨一定幅度，可以考虑止损
            elif current_price < bb_middle * 0.95:  # 跌破中轨5%时止损
                self.log(f'布林带止损信号: 价格={current_price:.2f}, '
                        f'中轨={bb_middle:.2f}, 止损阈值={bb_middle * 0.95:.2f}')
                
                position_size = self.position.size
                if position_size > 0:
                    self.log(f'布林带止损卖出: 当前持仓={position_size}')
                    self.order = self.sell(size=position_size)
    
    def collect_indicator_data(self):
        """
        收集指标数据
        """
        try:
            # 收集布林带指标数据
            self.indicator_data['bb_top'].append(float(self.bb_top[0]) if len(self.bb_top) > 0 else None)
            self.indicator_data['bb_mid'].append(float(self.bb_mid[0]) if len(self.bb_mid) > 0 else None)
            self.indicator_data['bb_bot'].append(float(self.bb_bot[0]) if len(self.bb_bot) > 0 else None)
        except Exception as e:
            self.log(f'收集指标数据时出错: {str(e)}')