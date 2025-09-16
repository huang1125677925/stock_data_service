from django.db import models
from datetime import datetime


class IndividualStock(models.Model):
    """个股基本信息模型"""
    code = models.CharField(max_length=10, unique=True, verbose_name='股票代码')
    name = models.CharField(max_length=50, verbose_name='股票名称')
    industry = models.CharField(max_length=50, null=True, blank=True, verbose_name='所属行业')
    total_shares = models.BigIntegerField(null=True, blank=True, verbose_name='总股本')
    circulating_shares = models.BigIntegerField(null=True, blank=True, verbose_name='流通股本')
    list_date = models.DateField(null=True, blank=True, verbose_name='上市日期')
    pe_ratio = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name='市盈率')
    pb_ratio = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name='市净率')
    total_market_cap = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='总市值')
    circulating_market_cap = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='流通市值')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'individual_stock'
        verbose_name = '个股基本信息'
        verbose_name_plural = '个股基本信息'
        ordering = ['code']
    
    def __str__(self):
        return f'{self.code} - {self.name}'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'code': self.code,
            'name': self.name,
            'industry': self.industry,
            'total_shares': self.total_shares,
            'circulating_shares': self.circulating_shares,
            'list_date': self.list_date.isoformat() if self.list_date else None,
            'pe_ratio': float(self.pe_ratio) if self.pe_ratio else None,
            'pb_ratio': float(self.pb_ratio) if self.pb_ratio else None,
            'total_market_cap': float(self.total_market_cap) if self.total_market_cap else None,
            'circulating_market_cap': float(self.circulating_market_cap) if self.circulating_market_cap else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class IndividualStockDaily(models.Model):
    """个股日频数据模型"""
    stock = models.ForeignKey(IndividualStock, on_delete=models.CASCADE, related_name='daily_data', verbose_name='所属股票')
    date = models.DateField(verbose_name='交易日期')
    open_price = models.DecimalField(max_digits=10, decimal_places=3, verbose_name='开盘价')
    close_price = models.DecimalField(max_digits=10, decimal_places=3, verbose_name='收盘价')
    high_price = models.DecimalField(max_digits=10, decimal_places=3, verbose_name='最高价')
    low_price = models.DecimalField(max_digits=10, decimal_places=3, verbose_name='最低价')
    change_percent = models.DecimalField(max_digits=8, decimal_places=3, verbose_name='涨跌幅(%)')
    change_amount = models.DecimalField(max_digits=10, decimal_places=3, verbose_name='涨跌额')
    volume = models.BigIntegerField(verbose_name='成交量(手)')
    amount = models.DecimalField(max_digits=20, decimal_places=2, verbose_name='成交额(元)')
    amplitude = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, verbose_name='振幅(%)')
    turnover_rate = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, verbose_name='换手率(%)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        db_table = 'individual_stock_daily'
        verbose_name = '个股日频数据'
        verbose_name_plural = '个股日频数据'
        ordering = ['-date', 'stock']
        indexes = [
            models.Index(fields=['stock', '-date']),
            models.Index(fields=['-date']),
        ]
        unique_together = ['stock', 'date']
    
    def __str__(self):
        return f'{self.stock.name} - {self.date} - {self.change_percent}%'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'stock_code': self.stock.code,
            'stock_name': self.stock.name,
            'date': self.date.isoformat(),
            'open_price': float(self.open_price),
            'close_price': float(self.close_price),
            'high_price': float(self.high_price),
            'low_price': float(self.low_price),
            'change_percent': float(self.change_percent),
            'change_amount': float(self.change_amount),
            'volume': self.volume,
            'amount': float(self.amount),
            'amplitude': float(self.amplitude) if self.amplitude else None,
            'turnover_rate': float(self.turnover_rate) if self.turnover_rate else None,
            'created_at': self.created_at.isoformat()
        }


class IndividualStockRealtime(models.Model):
    """个股实时行情模型"""
    stock = models.ForeignKey(IndividualStock, on_delete=models.CASCADE, related_name='realtime_data', verbose_name='所属股票')
    latest_price = models.DecimalField(max_digits=10, decimal_places=3, verbose_name='最新价')
    change_percent = models.DecimalField(max_digits=8, decimal_places=3, verbose_name='涨跌幅(%)')
    change_amount = models.DecimalField(max_digits=10, decimal_places=3, verbose_name='涨跌额')
    volume = models.BigIntegerField(verbose_name='成交量(手)')
    amount = models.DecimalField(max_digits=20, decimal_places=2, verbose_name='成交额(元)')
    amplitude = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, verbose_name='振幅(%)')
    high = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name='最高价')
    low = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name='最低价')
    open_price = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name='开盘价')
    close_price = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name='昨收价')
    turnover_rate = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, verbose_name='换手率(%)')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='数据时间')
    
    class Meta:
        db_table = 'individual_stock_realtime'
        verbose_name = '个股实时行情'
        verbose_name_plural = '个股实时行情'
        ordering = ['-timestamp', 'stock']
        indexes = [
            models.Index(fields=['stock', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f'{self.stock.code} - {self.stock.name} - {self.latest_price}'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'stock_code': self.stock.code,
            'stock_name': self.stock.name,
            'latest_price': float(self.latest_price),
            'change_percent': float(self.change_percent),
            'change_amount': float(self.change_amount),
            'volume': self.volume,
            'amount': float(self.amount),
            'amplitude': float(self.amplitude) if self.amplitude else None,
            'high': float(self.high) if self.high else None,
            'low': float(self.low) if self.low else None,
            'open_price': float(self.open_price) if self.open_price else None,
            'close_price': float(self.close_price) if self.close_price else None,
            'turnover_rate': float(self.turnover_rate) if self.turnover_rate else None,
            'timestamp': self.timestamp.isoformat()
        }
