from django.db import models
from datetime import datetime

class IndexRPS(models.Model):
    """指数RPS强度排名模型"""
    index_code = models.CharField(max_length=20, verbose_name='指数代码')
    index_name = models.CharField(max_length=50, verbose_name='指数简称')
    period = models.IntegerField(verbose_name='周期(天)')
    change_percent = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='涨跌幅(%)')
    rps_value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='RPS值')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        db_table = 'index_rps'
        verbose_name = '指数RPS强度排名'
        verbose_name_plural = '指数RPS强度排名'
        unique_together = ('index_code', 'period', 'created_at')
        ordering = ['-created_at', '-rps_value']
    
    def __str__(self):
        return f'{self.index_name} - {self.period}日 - {self.rps_value}'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'index_code': self.index_code,
            'index_name': self.index_name,
            'period': self.period,
            'change_percent': float(self.change_percent),
            'rps_value': float(self.rps_value),
            'created_at': self.created_at.isoformat()
        }


class StockSelectionRecord(models.Model):
    """
    组件：选股记录模型（StockSelectionRecord）

    功能：
    - 存储模型运行过程中的个股命中记录，用于回溯与分析。

    参数（字段）：
    - market (CharField): 市场，如 `CN`、`US` 等。
    - code (CharField): 证券代码，如 `600519`。
    - name (CharField): 证券名称，如 `贵州茅台`。
    - trade_date (DateField): 交易日期，命中记录对应的交易日。
    - predict_rise_prob (DecimalField): 预测上涨概率(%)，0-100 区间，保留两位小数。
    - confidence (DecimalField): 预测置信度(%)，0-100 区间，保留两位小数。
    - actual_rise_ratio_5d (DecimalField): 5日实际上涨比例(%)，0-100 区间，保留两位小数，可为空。
    - prediction_type (CharField): 预测类型，如 `MACD_XGBoost`、`MA_Cross` 等，用于区分来源模型。
    - created_at (DateTimeField): 记录创建时间。

    返回值：
    - to_dict() -> dict: 返回该记录的字典表示，便于序列化或接口返回。

    事件：
    - 本模型未内置事件。如需扩展可结合 Django 信号(post_save、pre_save)实现通知或联动。
    """

    market = models.CharField(max_length=20, verbose_name='市场')
    code = models.CharField(max_length=20, verbose_name='代码')
    name = models.CharField(max_length=50, verbose_name='名称')
    trade_date = models.DateField(verbose_name='交易日')
    predict_rise_prob = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='预测上涨概率(%)')
    confidence = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='置信度(%)')
    actual_rise_ratio_5d = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='5日实际上涨比例(%)')
    prediction_type = models.CharField(max_length=200, verbose_name='预测类型')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'stock_selection_record'
        verbose_name = '选股记录'
        verbose_name_plural = '选股记录'
        # 按用户需求，存储前基于(交易日, 代码)去重，这里用唯一约束保证一致性
        unique_together = ('code', 'trade_date')
        ordering = ['-trade_date', '-predict_rise_prob']

    def __str__(self):
        return f'{self.trade_date} {self.code} {self.name} ({self.predict_rise_prob}%, {self.confidence}%)'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'market': self.market,
            'code': self.code,
            'name': self.name,
            'trade_date': self.trade_date.isoformat(),
            'predict_rise_prob': float(self.predict_rise_prob),
            'confidence': float(self.confidence),
            'actual_rise_ratio_5d': float(self.actual_rise_ratio_5d) if self.actual_rise_ratio_5d is not None else None,
            'prediction_type': self.prediction_type,
            'created_at': self.created_at.isoformat(),
        }
