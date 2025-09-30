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
        # 记录买入/卖出点（包含利润信息）
        self.trade_records = []
        
        # 观测器数据收集
        self.observer_data = {
            'broker': [],      # 资金和持仓数据
            'buysell': [],     # 买卖信号数据
            'trades': [],      # 交易数据
            'timereturn': [],  # 时间收益数据
            'drawdown': [],    # 回撤数据
            'benchmark': []    # 基准数据
        }
        
        # 原始数据收集
        self.raw_data = {
            'datetime': [],    # 日期时间
            'open': [],        # 开盘价
            'high': [],        # 最高价
            'low': [],         # 最低价
            'close': [],       # 收盘价
            'volume': []       # 成交量
        }
        
        # 指标数据收集
        self.indicator_data = {}
        
        # 用于计算收益率和回撤的历史数据
        self.value_history = []
        self.return_history = []
        self.max_value_history = []
        
        # 用于存储每个交易日的broker数据（资金和持仓变化）
        self.broker_history = []
        
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
            # 订单已提交或已接受
            order_type = "买入" if order.isbuy() else "卖出"
            self.log(f'{order_type}订单已提交: 数量={order.size}, 价格={order.price or "市价"}')
            return
        
        if order.status in [order.Completed]:
            # 记录成交点
            try:
                dt = self.datas[0].datetime.datetime(0)
            except Exception:
                dt = None
            # 创建交易记录字典，存储订单执行的关键信息
            record = {
                'datetime': dt.isoformat() if hasattr(dt, 'isoformat') else None,  # 交易时间（ISO格式字符串）
                'type': 'buy' if order.isbuy() else 'sell',                           # 交易类型：买入或卖出
                'price': float(order.executed.price),                                # 成交价格
                'size': float(order.executed.size),                                  # 成交数量（正数为买入，负数为卖出）
                'value': float(order.executed.value),                                # 成交金额（价格×数量）
                'commission': float(order.executed.comm),                            # 交易手续费
                'pnl': None,           # 毛利润（交易关闭时更新）
                'pnlcomm': None,       # 净利润（交易关闭时更新）
                'pnl_pct': None,       # 利润率百分比（交易关闭时更新）
                'trade_closed': False, # 交易是否已关闭
            }
            self.trade_records.append(record)
            
            if order.isbuy():
                self.log(f'买入执行成功, 价格: {order.executed.price:.2f}, '
                        f'数量: {order.executed.size}, '
                        f'成本: {order.executed.value:.2f}, '
                        f'手续费: {order.executed.comm:.2f}')
                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm
            else:
                self.log(f'卖出执行成功, 价格: {order.executed.price:.2f}, '
                        f'数量: {order.executed.size}, '
                        f'成本: {order.executed.value:.2f}, '
                        f'手续费: {order.executed.comm:.2f}')
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # 详细记录订单失败原因
            order_type = "买入" if order.isbuy() else "卖出"
            if order.status == order.Canceled:
                self.log(f'{order_type}订单被取消: 数量={order.size}, 价格={order.price or "市价"}')
            elif order.status == order.Margin:
                self.log(f'{order_type}订单保证金不足: 数量={order.size}, 价格={order.price or "市价"}, '
                        f'当前资金={self.broker.get_cash():.2f}')
            elif order.status == order.Rejected:
                self.log(f'{order_type}订单被拒绝: 数量={order.size}, 价格={order.price or "市价"}')
        
        self.order = None
    
    def notify_trade(self, trade):
        """
        交易状态通知
        """
        if not trade.isclosed:
            return
        
        self.log(f'交易利润, 毛利润: {trade.pnl:.2f}, 净利润: {trade.pnlcomm:.2f}')
        
        # 将利润信息更新到最后一个对应的卖出交易记录中
        try:
            
            # 找到最后一个卖出交易记录
            for i in range(len(self.trade_records) - 1, -1, -1):
                record = self.trade_records[i]
                if record['type'] == 'sell' and not record['trade_closed']:
                    # 更新利润信息
                    record['pnl'] = float(trade.pnl)           # 记录毛利润（未扣除手续费）
                    record['pnlcomm'] = float(trade.pnlcomm)   # 记录净利润（扣除手续费后的实际收益）
                    record['trade_closed'] = True              # 标记交易已关闭，避免重复更新利润数据
                    
                    # 计算并记录利润率（基于净利润）
                    if record['price'] > 0 and record['size'] != 0:
                        buy_cost = record['price'] * abs(record['size'])  # 买入成本
                        record['pnl_pct'] = (float(trade.pnlcomm) / buy_cost) * 100  # 净利润率 = 净利润/买入成本×100%
                    else:
                        record['pnl_pct'] = 0.0
                    break
            
        except Exception as e:
            self.log(f'更新交易利润时出错: {str(e)}')
    
    def stop(self):
        """
        策略结束时调用，收集观测器数据
        """
        self.log('策略结束，开始收集观测器数据...')
        self.collect_observer_data()
        
    def next(self):
        """
        每个交易日调用，记录历史数据用于后续计算
        """
        # 记录当前的资金状态
        current_value = self.broker.get_value()
        current_cash = self.broker.get_cash()
        
        # 记录历史数据
        self.value_history.append(current_value)
        
        # 收集broker数据（资金和持仓变化）
        try:
            dt = self.data.datetime.datetime(0)
            broker_record = {
                'datetime': dt.isoformat() if hasattr(dt, 'isoformat') else str(dt),
                'cash': float(current_cash),
                'value': float(current_value)
            }
            self.broker_history.append(broker_record)
        except Exception as e:
            self.log(f'收集broker数据时出错: {str(e)}')
        
        # 计算收益率
        if len(self.value_history) > 1:
            initial_value = self.value_history[0]
            current_return = (current_value - initial_value) / initial_value * 100
            self.return_history.append(current_return)
        else:
            self.return_history.append(0.0)
        
        # 计算最大价值（用于回撤计算）
        if len(self.max_value_history) == 0:
            self.max_value_history.append(current_value)
        else:
            max_value = max(self.max_value_history[-1], current_value)
            self.max_value_history.append(max_value)
        
        # 收集原始数据
        self.collect_raw_data()
        
        # 收集指标数据（由子类实现）
        self.collect_indicator_data()
    
    def collect_raw_data(self):
        """
        收集原始OHLCV数据
        """
        try:
            dt = self.data.datetime.datetime(0)
            self.raw_data['datetime'].append(dt.isoformat() if hasattr(dt, 'isoformat') else str(dt))
            self.raw_data['open'].append(float(self.data.open[0]))
            self.raw_data['high'].append(float(self.data.high[0]))
            self.raw_data['low'].append(float(self.data.low[0]))
            self.raw_data['close'].append(float(self.data.close[0]))
            self.raw_data['volume'].append(float(self.data.volume[0]) if hasattr(self.data, 'volume') else 0.0)
        except Exception as e:
            self.log(f'收集原始数据时出错: {str(e)}')
    
    def collect_indicator_data(self):
        """
        收集指标数据
        子类应该重写此方法来收集特定的指标数据
        """
        pass
    
    def collect_observer_data(self):
        """
        收集观测器数据
        在策略结束时调用，收集所有观测器的数据
        """
        try:
            # 使用已收集的broker历史数据
            self.observer_data['broker'] = self.broker_history.copy()
            
            # 收集BuySell观测器数据（买卖信号）
            # 这些数据已经在notify_order中收集到trade_records中
            # 收集买卖信号数据（包含利润信息）
            self.observer_data['buysell'] = self.trade_records.copy()
            
            # 收集Trades观测器数据（交易统计）
            # 这些数据可以从trade_records中计算得出
            trades_data = self._calculate_trades_data()
            self.observer_data['trades'] = trades_data
            
            # 收集TimeReturn观测器数据（时间收益）
            timereturn_data = self._calculate_timereturn_data()
            self.observer_data['timereturn'] = timereturn_data
            
            # 收集DrawDown观测器数据（回撤）
            drawdown_data = self._calculate_drawdown_data()
            self.observer_data['drawdown'] = drawdown_data
            
            # 收集Benchmark观测器数据（基准对比）
            benchmark_data = self._calculate_benchmark_data()
            self.observer_data['benchmark'] = benchmark_data
            
            self.log(f'观测器数据收集完成: broker={len(self.broker_history)}, buysell={len(self.trade_records)}, '
                    f'trades={len(trades_data)}, timereturn={len(timereturn_data)}, '
                    f'drawdown={len(drawdown_data)}, benchmark={len(benchmark_data)}')
            
        except Exception as e:
            self.log(f'收集观测器数据时出错: {str(e)}')
            import traceback
            self.log(f'错误详情: {traceback.format_exc()}')
    
    def _calculate_trades_data(self):
        """计算交易统计数据"""
        trades_data = []
        if not self.trade_records:
            return trades_data
        
        # 按交易对进行配对（买入-卖出）
        buy_orders = [t for t in self.trade_records if t['type'] == 'buy']
        sell_orders = [t for t in self.trade_records if t['type'] == 'sell']
        
        for i, buy in enumerate(buy_orders):
            if i < len(sell_orders):
                sell = sell_orders[i]
                
                # 使用交易记录中的真实利润数据
                if sell['pnl'] is not None and sell['pnlcomm'] is not None:
                    # 使用真实的利润数据
                    pnl = sell['pnl']
                    pnlcomm = sell['pnlcomm']
                else:
                    # 使用计算的利润数据（兼容旧数据）
                    pnl = (sell['price'] - buy['price']) * buy['size'] - buy['commission'] - sell['commission']
                    pnlcomm = pnl
                
                trades_data.append({
                    'buy_datetime': buy['datetime'],      # 买入时间
                    'sell_datetime': sell['datetime'],    # 卖出时间
                    'buy_price': buy['price'],            # 买入价格
                    'sell_price': sell['price'],          # 卖出价格
                    'size': buy['size'],                  # 交易数量（买入和卖出数量相同）
                    'pnl': pnl,                           # 毛利润（卖出价-买入价）×数量-手续费
                    'pnlcomm': pnlcomm,                   # 净利润（毛利润扣除所有手续费）
                    'pnl_pct': (pnl / (buy['price'] * buy['size'])) * 100 if buy['price'] * buy['size'] > 0 else 0  # 利润率百分比 = 利润/买入成本×100%
                })
        
        return trades_data
    
    def _calculate_timereturn_data(self):
        """计算时间收益数据"""
        timereturn_data = []
        
        try:
            # 使用记录的历史数据
            for i, return_value in enumerate(self.return_history):
                if i < len(self.value_history):
                    # 获取对应的日期
                    try:
                        dt = self.data.datetime.datetime(-len(self.return_history) + i)
                    except (IndexError, AttributeError):
                        # 如果无法获取具体日期，使用索引
                        dt = f"Day_{i}"
                    
                    timereturn_data.append({
                        'datetime': dt.isoformat() if hasattr(dt, 'isoformat') else str(dt),
                        'return': float(return_value),
                        'cumulative_return': float(return_value),
                        'portfolio_value': float(self.value_history[i])
                    })
        except Exception as e:
            self.log(f'计算时间收益数据时出错: {str(e)}')
        
        return timereturn_data
    
    def _calculate_drawdown_data(self):
        """计算回撤数据"""
        drawdown_data = []
        
        try:
            # 使用记录的历史数据计算回撤
            for i in range(len(self.value_history)):
                current_value = self.value_history[i]
                max_value = self.max_value_history[i]
                
                # 计算回撤
                if max_value > 0:
                    drawdown = (max_value - current_value) / max_value * 100
                else:
                    drawdown = 0.0
                
                # 获取对应的日期
                try:
                    dt = self.data.datetime.datetime(-len(self.value_history) + i)
                except (IndexError, AttributeError):
                    # 如果无法获取具体日期，使用索引
                    dt = f"Day_{i}"
                
                drawdown_data.append({
                    'datetime': dt.isoformat() if hasattr(dt, 'isoformat') else str(dt),
                    'drawdown': float(drawdown),
                    'max_value': float(max_value),
                    'current_value': float(current_value)
                })
        except Exception as e:
            self.log(f'计算回撤数据时出错: {str(e)}')
        
        return drawdown_data
    
    def _calculate_benchmark_data(self):
        """计算基准对比数据"""
        benchmark_data = []
        
        try:
            # 使用股票价格作为基准
            initial_price = float(self.data.close[0]) if len(self.data) > 0 else 1.0
            
            for i in range(len(self.data)):
                try:
                    dt = self.data.datetime.datetime(i)
                    current_price = float(self.data.close[i])
                    benchmark_return = (current_price - initial_price) / initial_price * 100
                    
                    # 策略收益
                    strategy_value = self.broker.get_value()
                    initial_value = getattr(self._owner.broker, '_startingcash', 100000)
                    strategy_return = (strategy_value - initial_value) / initial_value * 100
                    
                    benchmark_data.append({
                        'datetime': dt.isoformat() if hasattr(dt, 'isoformat') else str(dt),
                        'benchmark_return': benchmark_return,
                        'strategy_return': strategy_return,
                        'excess_return': strategy_return - benchmark_return
                    })
                except (IndexError, AttributeError):
                    break
        except Exception as e:
            self.log(f'计算基准数据时出错: {str(e)}')
        
        return benchmark_data


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