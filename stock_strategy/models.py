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
