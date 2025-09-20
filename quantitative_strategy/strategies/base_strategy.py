#!/usr/bin/env python3
"""
量化策略基类
定义所有策略的通用接口和基础功能
"""

import backtrader as bt
from abc import ABCMeta, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseQuantStrategyMeta(type(bt.Strategy), ABCMeta):
    """解决元类冲突的自定义元类"""
    pass


class BaseQuantStrategy(bt.Strategy, metaclass=BaseQuantStrategyMeta):
    """
    量化策略基类
    
    所有具体策略都应该继承此基类并实现相应的抽象方法
    """
    
    # 默认参数
    params = dict(
        printlog=True,  # 是否打印日志
    )
    
    def __init__(self):
        """
        策略初始化
        子类应该在此方法中初始化技术指标
        """
        super().__init__()
        self.order = None  # 当前订单
        self.buy_price = None  # 买入价格
        self.buy_comm = None  # 买入手续费
        # 记录买入/卖出点
        self.trade_records = []
        
        # 初始化技术指标
        self.init_indicators()
    
    @abstractmethod
    def init_indicators(self):
        """
        初始化技术指标
        子类必须实现此方法
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """
        获取策略名称
        子类必须实现此方法
        """
        pass
    
    @abstractmethod
    def get_strategy_description(self) -> str:
        """
        获取策略描述
        子类必须实现此方法
        """
        pass
    
    def get_strategy_params(self) -> Dict[str, Any]:
        """
        获取策略参数
        子类可以重写此方法来返回自定义参数
        """
        return {key: getattr(self.params, key) for key in self.params._getkeys()}
    
    def log(self, txt, dt=None):
        """
        日志记录函数
        """
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}, {txt}')
    
    def notify_order(self, order):
        """
        订单状态通知
        """
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            # 记录成交点
            try:
                dt = self.datas[0].datetime.datetime(0)
            except Exception:
                dt = None
            record = {
                'datetime': dt.isoformat() if hasattr(dt, 'isoformat') else None,
                'type': 'buy' if order.isbuy() else 'sell',
                'price': float(order.executed.price),
                'size': float(order.executed.size),
                'value': float(order.executed.value),
                'commission': float(order.executed.comm),
            }
            self.trade_records.append(record)
            
            if order.isbuy():
                self.log(f'买入执行, 价格: {order.executed.price:.2f}, '
                        f'成本: {order.executed.value:.2f}, '
                        f'手续费: {order.executed.comm:.2f}')
                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm
            else:
                self.log(f'卖出执行, 价格: {order.executed.price:.2f}, '
                        f'成本: {order.executed.value:.2f}, '
                        f'手续费: {order.executed.comm:.2f}')
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/拒绝')
        
        self.order = None
    
    def notify_trade(self, trade):
        """
        交易状态通知
        """
        if not trade.isclosed:
            return
        
        self.log(f'交易利润, 毛利润: {trade.pnl:.2f}, 净利润: {trade.pnlcomm:.2f}')
    
    def stop(self):
        """
        策略结束时调用
        """
        portfolio_value = self.broker.getvalue()
        self.log(f'策略结束, 最终资金: {portfolio_value:.2f}')


class StrategyRegistry:
    """
    策略注册器
    用于管理所有可用的策略
    """
    
    _strategies = {}
    
    @classmethod
    def register(cls, strategy_class):
        """
        注册策略类
        
        Args:
            strategy_class: 策略类
        
        Returns:
            strategy_class: 返回策略类本身，用于装饰器
        """
        if not issubclass(strategy_class, BaseQuantStrategy):
            raise ValueError(f"策略类 {strategy_class.__name__} 必须继承自 BaseQuantStrategy")
        
        # 直接从类获取策略信息，避免实例化
        strategy_name = getattr(strategy_class, '_strategy_name', strategy_class.__name__)
        strategy_description = getattr(strategy_class, '_strategy_description', '')
        strategy_params = getattr(strategy_class, '_strategy_params', {})
        
        strategy_info = {
            'class': strategy_class,
            'name': strategy_name,
            'description': strategy_description,
            'params': strategy_params
        }
        
        cls._strategies[strategy_name] = strategy_info
        logger.info(f"策略 {strategy_name} 注册成功")
        
        return strategy_class
    
    @classmethod
    def get_strategy(cls, strategy_name: str):
        """
        获取策略类
        """
        strategy_info = cls._strategies.get(strategy_name)
        return strategy_info['class'] if strategy_info else None
    
    @classmethod
    def get_strategy_class(cls, strategy_name: str):
        """
        获取策略类（别名方法，保持向后兼容）
        """
        return cls.get_strategy(strategy_name)
    
    @classmethod
    def get_all_strategies(cls) -> Dict[str, Any]:
        """
        获取所有注册的策略信息
        返回可JSON序列化的策略信息，不包含策略类
        """
        serializable_strategies = []
        for name, info in cls._strategies.items():
            serializable_strategies.append({
                'name': info['name'],
                'description': info['description'],
                'params': info['params']
            })
        return serializable_strategies


def register_strategy(strategy_class):
    """
    策略注册装饰器
    """
    return StrategyRegistry.register(strategy_class)