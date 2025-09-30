#!/usr/bin/env python3
"""
量化策略回测服务
集成backtrader引擎，提供策略回测功能
"""
import sys
import traceback

import backtrader as bt
import pandas as pd
import akshare as ak
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional, List, Tuple
import logging

try:
    # 尝试相对导入（作为Django模块时）
    from .models import BacktestTask, BacktestResult, StrategyConfig
    from .strategies.base_strategy import StrategyRegistry
    from .strategies.ma_cross_strategy import MACrossStrategy
    from .strategies.simple_strategy import MultiIndicatorStrategy
    from .strategies.advanced_strategy import AdvancedStrategy
    from .strategies.minimal_strategy import MinimalStrategy
    # 导入新创建的单指标策略
    from .strategies.macd_strategy import MACDStrategy
    from .strategies.rsi_strategy import RSIStrategy
    from .strategies.wr_strategy import WRStrategy
    from .strategies.kdj_strategy import KDJStrategy
    from .strategies.psy_strategy import PSYStrategy
    from .strategies.bias_strategy import BIASStrategy
    from .strategies.bollinger_strategy import BollingerStrategy
    from .strategies.macd_underwater_strategy import MACDUnderwaterStrategy
    from indival_stock_data.services import IndividualStockService
except ImportError:
    # 如果相对导入失败，尝试绝对导入（独立运行时）
    import os
    import sys
    import django
    from django.conf import settings
    
    # 添加项目根目录到Python路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    sys.path.insert(0, project_root)
    
    # 配置Django环境
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_data_service.settings')
    django.setup()
    
    from quantitative_strategy.models import BacktestTask, BacktestResult, StrategyConfig
    from quantitative_strategy.strategies.base_strategy import StrategyRegistry
    from quantitative_strategy.strategies.ma_cross_strategy import MACrossStrategy
    from quantitative_strategy.strategies.simple_strategy import MultiIndicatorStrategy
    from quantitative_strategy.strategies.advanced_strategy import AdvancedStrategy
    from quantitative_strategy.strategies.minimal_strategy import MinimalStrategy
    # 导入新创建的单指标策略
    from quantitative_strategy.strategies.macd_strategy import MACDStrategy
    from quantitative_strategy.strategies.rsi_strategy import RSIStrategy
    from quantitative_strategy.strategies.wr_strategy import WRStrategy
    from quantitative_strategy.strategies.kdj_strategy import KDJStrategy
    from quantitative_strategy.strategies.psy_strategy import PSYStrategy
    from quantitative_strategy.strategies.bias_strategy import BIASStrategy
    from quantitative_strategy.strategies.bollinger_strategy import BollingerStrategy
    from quantitative_strategy.strategies.macd_underwater_strategy import MACDUnderwaterStrategy

    from indival_stock_data.services import IndividualStockService



logger = logging.getLogger(__name__)


class PandasData(bt.feeds.PandasData):
    """
    自定义Pandas数据源
    适配akshare数据格式
    """
    params = (
        ('datetime', None),
        ('open', 'open'),
        ('high', 'high'),
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
        ('openinterest', -1),
    )


class BacktestService:
    """
    回测服务类
    提供策略回测的核心功能
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_stock_data(self, stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        获取股票历史数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
        
        Returns:
            股票数据DataFrame或None
        """
        try:
            # 导入个股数据服务
            from indival_stock_data.services import IndividualStockService
            
            # 创建个股数据服务实例
            stock_service = IndividualStockService()
            
            # 转换日期格式 (YYYY-MM-DD -> YYYYMMDD)
            start_date_formatted = start_date.replace('-', '')
            end_date_formatted = end_date.replace('-', '')
            
            # 使用个股数据服务获取历史数据
            stock_history = stock_service.get_stock_history(
                stock_code=stock_code,
                start_date=start_date_formatted,
                end_date=end_date_formatted,
                # adjust="qfq"  # 前复权
            )
            
            if not stock_history:
                self.logger.warning(f"未获取到股票 {stock_code} 的数据")
                return None
            
            # 转换为DataFrame
            df = pd.DataFrame(stock_history)
            
            if df.empty:
                self.logger.warning(f"股票 {stock_code} 数据为空")
                return None
            
            # 重命名列名以适配backtrader
            column_mapping = {
                'date': 'datetime',
                'open_price': 'open',
                'close_price': 'close',
                'high_price': 'high',
                'low_price': 'low',
                'volume': 'volume'
            }
            
            # 只重命名存在的列
            existing_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
            df.rename(columns=existing_columns, inplace=True)
            
            # 设置日期索引
            if 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'])
                df.set_index('datetime', inplace=True)
                # 确保索引严格递增且无重复，避免回测引擎在一次性计算（once）阶段索引越界
                df.sort_index(inplace=True)
                df = df[~df.index.duplicated(keep='first')]
            
            # 确保数据类型正确
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 删除包含NaN的行
            df.dropna(inplace=True)
            
            self.logger.info(f"成功获取股票 {stock_code} 数据，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            self.logger.error(f"获取股票数据失败: {str(e)}")
            return None
    
    def create_backtest_task(self, 
                           strategy_name: str,
                           stock_code: str,
                           start_date: str,
                           end_date: str,
                           initial_cash: float = 100000,
                           commission: float = 0.001,
                           strategy_params: Dict[str, Any] = None,
                           user=None) -> str:
        """
        创建回测任务
        
        Args:
            strategy_name: 策略名称
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            initial_cash: 初始资金
            commission: 手续费率
            strategy_params: 策略参数
            user: 用户对象
        
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        
        # 获取股票名称
        stock_name = self._get_stock_name(stock_code)
        
        task = BacktestTask.objects.create(
            task_id=task_id,
            user=user,
            strategy_name=strategy_name,
            stock_code=stock_code,
            stock_name=stock_name,
            start_date=start_date,
            end_date=end_date,
            initial_cash=Decimal(str(initial_cash)),
            commission=Decimal(str(commission)),
            strategy_params=strategy_params or {},
            status='pending'
        )
        
        self.logger.info(f"创建回测任务: {task_id}")
        return task_id
    
    def run_backtest(self, task_id: str) -> Dict[str, Any]:
        """
        执行回测
        
        Args:
            task_id: 任务ID
        
        Returns:
            回测结果字典
        """
        try:
            # 获取任务
            task = BacktestTask.objects.get(task_id=task_id)
            task.status = 'running'
            task.save()
            
            # 获取股票数据
            df = self.get_stock_data(
                task.stock_code,
                task.start_date.strftime('%Y-%m-%d'),
                task.end_date.strftime('%Y-%m-%d')
            )
            
            if df is None or df.empty:
                raise ValueError(f"无法获取股票 {task.stock_code} 的数据")
            print(f"股票 {task.stock_code} 数据长度: {len(df)}")
            # 获取策略类
            strategy_class = StrategyRegistry.get_strategy(task.strategy_name)
            if strategy_class is None:
                raise ValueError(f"未找到策略: {task.strategy_name}")
            
            # 创建回测引擎
            cerebro = bt.Cerebro()
            
            # 添加策略（过滤未定义的参数，避免意外的关键字参数错误）
            filtered_params = {}
            if isinstance(task.strategy_params, dict):
                allowed = set()
                if hasattr(strategy_class, 'params'):
                    if hasattr(strategy_class.params, '_getkeys'):
                        allowed = set(strategy_class.params._getkeys())
                    elif isinstance(strategy_class.params, dict):
                        allowed = set(strategy_class.params.keys())
                filtered_params = {k: v for k, v in task.strategy_params.items() if k in allowed}
                dropped = set(task.strategy_params.keys()) - set(filtered_params.keys())
                if dropped:
                    self.logger.warning(f"以下策略参数未在 {task.strategy_name} 中定义，已忽略: {sorted(list(dropped))}")
            
            cerebro.addstrategy(strategy_class, **filtered_params)
            
            data = PandasData(dataname=df)
            cerebro.adddata(data)
            
            # 设置初始资金和手续费
            cerebro.broker.set_cash(float(task.initial_cash))
            cerebro.broker.setcommission(commission=float(task.commission))
            
            # 添加观测器
            cerebro.addobserver(bt.observers.Broker)
            cerebro.addobserver(bt.observers.BuySell)
            cerebro.addobserver(bt.observers.Trades)
            cerebro.addobserver(bt.observers.TimeReturn)
            cerebro.addobserver(bt.observers.DrawDown)
            cerebro.addobserver(bt.observers.Benchmark)
            
            # 添加分析器
            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
            
            # 运行回测
            initial_value = cerebro.broker.getvalue()
            results = cerebro.run(runonce=False, preload=False, maxcpus=1)
            final_value = cerebro.broker.getvalue()
            
            # 检查回测结果
            if not results or len(results) == 0:
                raise ValueError("回测执行失败，未返回任何结果")
            
            # 获取分析结果
            strategy_result = results[0]
            analyzers = strategy_result.analyzers
            
            # 获取观测器数据
            observer_data = {}
            if hasattr(strategy_result, 'observer_data'):
                observer_data = strategy_result.observer_data
            
            # 获取原始数据和指标数据
            raw_data = {}
            indicator_data = {}
            if hasattr(strategy_result, 'raw_data'):
                raw_data = strategy_result.raw_data
            if hasattr(strategy_result, 'indicator_data'):
                indicator_data = strategy_result.indicator_data
            
            # 计算收益指标
            total_return = (final_value - initial_value) / initial_value * 100
            
            # 计算年化收益率
            days = (task.end_date - task.start_date).days
            annual_return = ((final_value / initial_value) ** (365.0 / days) - 1) * 100 if days > 0 else 0
            
            # 获取分析器结果
            sharpe_ratio = analyzers.sharpe.get_analysis().get('sharperatio', None)
            drawdown_info = analyzers.drawdown.get_analysis()
            max_drawdown = drawdown_info.get('max', {}).get('drawdown', 0)
            trade_info = analyzers.trades.get_analysis()
            
            # 交易统计
            total_trades = trade_info.get('total', {}).get('total', 0)
            winning_trades = trade_info.get('won', {}).get('total', 0)
            losing_trades = trade_info.get('lost', {}).get('total', 0)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # 保存结果
            result = BacktestResult.objects.create(
                task=task,
                initial_value=Decimal(str(initial_value)),
                final_value=Decimal(str(final_value)),
                total_return=Decimal(str(round(total_return, 4))),
                annual_return=Decimal(str(round(annual_return, 4))),
                sharpe_ratio=Decimal(str(round(sharpe_ratio, 4))) if sharpe_ratio else None,
                max_drawdown=Decimal(str(round(max_drawdown, 4))) if max_drawdown else None,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=Decimal(str(round(win_rate, 2))) if win_rate else None,
                daily_returns=[],  # 可以后续添加详细的每日收益数据
                portfolio_values=[],  # 可以后续添加组合价值序列
                trade_records=getattr(strategy_result, 'trade_records', []),  # 保存买入/卖出成交点
                observer_data=observer_data,  # 保存观测器数据
                raw_data=raw_data,  # 保存原始数据
                indicator_data=indicator_data  # 保存指标数据
            )
            
            # 标记任务完成
            task.mark_completed()
            
            self.logger.info(f"回测任务 {task_id} 完成")
            
            return {
                'task_id': task_id,
                'status': 'completed',
                'result': result.get_performance_summary()
            }
            
        except Exception as e:
            self.logger.error(f"回测任务 {task_id} 失败: {str(e)}\n堆栈跟踪: {traceback.format_exc()}")
            
            # 标记任务失败
            try:
                task = BacktestTask.objects.get(task_id=task_id)
                task.mark_failed(str(e))
            except:
                pass
            
            return {
                'task_id': task_id,
                'status': 'failed',
                'error': str(e)
            }
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
        
        Returns:
            任务状态信息
        """
        try:
            task = BacktestTask.objects.get(task_id=task_id)
            
            result_data = {
                'task_id': task_id,
                'status': task.status,
                'strategy_name': task.strategy_name,
                'stock_code': task.stock_code,
                'stock_name': task.stock_name,
                'start_date': task.start_date.strftime('%Y-%m-%d'),
                'end_date': task.end_date.strftime('%Y-%m-%d'),
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat()
            }
            
            if task.status == 'completed':
                try:
                    result = BacktestResult.objects.get(task=task)
                    result_data['result'] = result.get_performance_summary()
                    result_data['completed_at'] = task.completed_at.isoformat() if task.completed_at else None
                except BacktestResult.DoesNotExist:
                    pass
            elif task.status == 'failed':
                result_data['error'] = task.error_message
                result_data['completed_at'] = task.completed_at.isoformat() if task.completed_at else None
            
            return result_data
            
        except BacktestTask.DoesNotExist:
            return {
                'task_id': task_id,
                'status': 'not_found',
                'error': '任务不存在'
            }
    
    def get_available_strategies(self) -> Dict[str, Any]:
        """
        获取可用策略列表
        
        Returns:
            策略信息字典
        """
        return StrategyRegistry.get_all_strategies()
    
    def _get_stock_name(self, stock_code: str) -> str:
        """
        获取股票名称
        
        Args:
            stock_code: 股票代码
        
        Returns:
            股票名称
        """
        try:
            # 这里可以通过akshare或其他方式获取股票名称
            # 暂时返回代码本身
            stock_object = IndividualStockService()._get_or_create_stock(stock_code)
            return stock_object.name if stock_object else stock_code
        except:
            return stock_code


# 全局服务实例
backtest_service = BacktestService()

def run_backtest_task():
    """
    运行回测任务
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务执行结果
    """

    try:        
        # 获取股票数据
        df = backtest_service.get_stock_data(
            '000020',
            '2024-01-01',
            '2025-10-01'
        )

        task = BacktestTask(
            stock_code='000020',
            stock_name='中国双汇',
            strategy_name='ma_cross',
            start_date=datetime(2024, 9, 28).date(),
            end_date=datetime(2025, 10, 1).date(),
            initial_cash=100000,
            commission=0.0003
        )
        
        if df is None or df.empty:
            raise ValueError(f"无法获取股票 {task.stock_code} 的数据")
        print(f"股票 {task.stock_code} 数据长度: {len(df)}")
        # 获取策略类
        strategy_class = StrategyRegistry.get_strategy(task.strategy_name)
        if strategy_class is None:
            raise ValueError(f"未找到策略: {task.strategy_name}")
        
        # 创建回测引擎
        cerebro = bt.Cerebro()
        
        
        cerebro.addstrategy(strategy_class)
        
        data = PandasData(dataname=df)
        cerebro.adddata(data)
        
        # 设置初始资金和手续费
        cerebro.broker.set_cash(float(task.initial_cash))
        cerebro.broker.setcommission(commission=float(task.commission))
        
        # 添加分析器
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        # 运行回测
        initial_value = cerebro.broker.getvalue()
        results = cerebro.run(runonce=False, preload=False, maxcpus=1)
        final_value = cerebro.broker.getvalue()
        
        # 检查回测结果
        if not results or len(results) == 0:
            raise ValueError("回测执行失败，未返回任何结果")
        
        # 获取分析结果
        strategy_result = results[0]
        analyzers = strategy_result.analyzers
        
        # 计算收益指标
        total_return = (final_value - initial_value) / initial_value * 100
        
        # 计算年化收益率
        days = (task.end_date - task.start_date).days
        annual_return = ((final_value / initial_value) ** (365.0 / days) - 1) * 100 if days > 0 else 0
        
        # 获取分析器结果
        sharpe_ratio = analyzers.sharpe.get_analysis().get('sharperatio', None)
        drawdown_info = analyzers.drawdown.get_analysis()
        max_drawdown = drawdown_info.get('max', {}).get('drawdown', 0)
        trade_info = analyzers.trades.get_analysis()
        
        # 交易统计
        total_trades = trade_info.get('total', {}).get('total', 0)
        winning_trades = trade_info.get('won', {}).get('total', 0)
        losing_trades = trade_info.get('lost', {}).get('total', 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # 保存结果
        print(f"初始资金: {initial_value:.2f}")
        print(f"最终资金: {final_value:.2f}")
        print(f"总收益率: {total_return:.2f}%")
        print(f"年化收益率: {annual_return:.2f}%")
        print(f"夏普比率: {sharpe_ratio:.2f}" if sharpe_ratio else "夏普比率: None")
        print(f"最大回撤: {max_drawdown:.2f}%")
        print(f"总交易次数: {total_trades}")
        print(f"盈利交易次数: {winning_trades}")
        print(f"亏损交易次数: {losing_trades}")
        print(f"胜率: {win_rate:.2f}%" if win_rate else "胜率: None")
        
        
        backtest_service.logger.info(f"回测任务 完成")
        

        
    except Exception as e:
        backtest_service.logger.error(f"堆栈跟踪: {traceback.format_exc()}")


if __name__ == '__main__':
    run_backtest_task()