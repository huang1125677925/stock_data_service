#!/usr/bin/env python3
"""
量化策略数据模型
用于存储回测结果和策略配置
"""

from django.db import models
from user_management.models import User
from django.utils import timezone
import json


class StrategyConfig(models.Model):
    """
    策略配置模型
    存储策略的基本信息和参数配置
    """
    
    name = models.CharField(max_length=100, unique=True, verbose_name='策略名称')
    display_name = models.CharField(max_length=200, verbose_name='显示名称')
    description = models.TextField(verbose_name='策略描述')
    strategy_class = models.CharField(max_length=200, verbose_name='策略类名')
    default_params = models.JSONField(default=dict, verbose_name='默认参数')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'quantitative_strategy_config'
        verbose_name = '策略配置'
        verbose_name_plural = '策略配置'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.display_name} ({self.name})'


class BacktestTask(models.Model):
    """
    回测任务模型
    记录每次回测任务的基本信息
    """
    
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '运行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]
    
    task_id = models.CharField(max_length=100, unique=True, verbose_name='任务ID')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name='用户')
    strategy_name = models.CharField(max_length=100, verbose_name='策略名称')
    stock_code = models.CharField(max_length=20, verbose_name='股票代码')
    stock_name = models.CharField(max_length=100, blank=True, verbose_name='股票名称')
    start_date = models.DateField(verbose_name='开始日期')
    end_date = models.DateField(verbose_name='结束日期')
    initial_cash = models.DecimalField(max_digits=15, decimal_places=2, default=100000, verbose_name='初始资金')
    commission = models.DecimalField(max_digits=6, decimal_places=4, default=0.001, verbose_name='手续费率')
    strategy_params = models.JSONField(default=dict, verbose_name='策略参数')
    # 数据频率：daily（日频，默认）、weekly（周频）
    frequency = models.CharField(
        max_length=20,
        default='daily',
        verbose_name='数据频率',
        help_text='数据频率类型：daily（日频，默认）或 weekly（周频）'
    )
    # 数据来源类型：stock（个股，默认）、etf（基金）
    DATA_SOURCE_CHOICES = [
        ('stock', '个股'),
        ('etf', 'ETF'),
    ]
    data_source = models.CharField(
        max_length=20,
        choices=DATA_SOURCE_CHOICES,
        default='stock',
        verbose_name='数据来源',
        help_text='标的类型：stock（个股）或 etf（基金）；当为etf时，stock_code字段存放ETF ts_code'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    
    class Meta:
        db_table = 'quantitative_backtest_task'
        verbose_name = '回测任务'
        verbose_name_plural = '回测任务'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.task_id} - {self.strategy_name} - {self.stock_code} ({self.data_source})'
    
    def mark_completed(self):
        """标记任务完成"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
    
    def mark_failed(self, error_message):
        """标记任务失败"""
        self.status = 'failed'
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save()


class BacktestResult(models.Model):
    """
    回测结果模型
    存储回测的详细结果数据
    """
    
    task = models.OneToOneField(BacktestTask, on_delete=models.CASCADE, verbose_name='回测任务')
    
    # 基础收益指标
    initial_value = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='初始资金')
    final_value = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='最终资金')
    total_return = models.DecimalField(max_digits=10, decimal_places=4, verbose_name='总收益率')
    annual_return = models.DecimalField(max_digits=10, decimal_places=4, verbose_name='年化收益率')
    
    # 风险指标
    sharpe_ratio = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='夏普比率')
    max_drawdown = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='最大回撤')
    volatility = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='波动率')
    
    # 交易统计
    total_trades = models.IntegerField(default=0, verbose_name='总交易次数')
    winning_trades = models.IntegerField(default=0, verbose_name='盈利交易次数')
    losing_trades = models.IntegerField(default=0, verbose_name='亏损交易次数')
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='胜率')
    
    # 详细数据（JSON格式存储）
    daily_returns = models.JSONField(default=list, verbose_name='每日收益率')
    portfolio_values = models.JSONField(default=list, verbose_name='组合价值序列')
    trade_records = models.JSONField(default=list, verbose_name='交易记录')
    
    # 观测器数据
    observer_data = models.JSONField(default=dict, verbose_name='观测器数据', help_text='包含Broker、BuySell、Trades、TimeReturn、DrawDown、Benchmark等观测器数据')
    
    # 原始数据和指标数据
    raw_data = models.JSONField(default=dict, verbose_name='原始数据', help_text='包含OHLCV等原始市场数据')
    indicator_data = models.JSONField(default=dict, verbose_name='指标数据', help_text='包含技术指标计算结果')
    
    # 图表路径
    chart_image = models.CharField(max_length=500, blank=True, null=True, verbose_name='回测图表路径')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        db_table = 'quantitative_backtest_result'
        verbose_name = '回测结果'
        verbose_name_plural = '回测结果'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.task.task_id} - 收益率: {self.total_return}%'
    
    def get_performance_summary(self):
        """获取性能摘要"""
        return {
            'total_return': float(self.total_return),
            'annual_return': float(self.annual_return),
            'sharpe_ratio': float(self.sharpe_ratio) if self.sharpe_ratio else None,
            'max_drawdown': float(self.max_drawdown) if self.max_drawdown else None,
            'volatility': float(self.volatility) if self.volatility else None,
            'total_trades': self.total_trades,
            'win_rate': float(self.win_rate) if self.win_rate else None,
            'chart_image': self.chart_image,  # 添加图表路径
            'observer_data': self.observer_data,  # 添加观测器数据
            'raw_data': self.raw_data,  # 添加原始数据
            'indicator_data': self.indicator_data,  # 添加指标数据
            'trade_records': self.trade_records
        }


class StrategyPerformance(models.Model):
    """
    策略性能统计模型
    用于统计各策略的历史表现
    """
    
    strategy_name = models.CharField(max_length=100, verbose_name='策略名称')
    stock_code = models.CharField(max_length=20, verbose_name='股票代码')
    
    # 统计周期
    period_start = models.DateField(verbose_name='统计开始日期')
    period_end = models.DateField(verbose_name='统计结束日期')
    
    # 性能指标
    avg_return = models.DecimalField(max_digits=10, decimal_places=4, verbose_name='平均收益率')
    avg_sharpe = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='平均夏普比率')
    avg_drawdown = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='平均最大回撤')
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='成功率')
    
    # 统计数据
    total_backtests = models.IntegerField(default=0, verbose_name='回测总数')
    successful_backtests = models.IntegerField(default=0, verbose_name='成功回测数')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'quantitative_strategy_performance'
        verbose_name = '策略性能统计'
        verbose_name_plural = '策略性能统计'
        unique_together = ['strategy_name', 'stock_code', 'period_start', 'period_end']
        ordering = ['-updated_at']
    
    def __str__(self):
        return f'{self.strategy_name} - {self.stock_code} - {self.avg_return}%'
