from django.db import models
from datetime import datetime

class StockInfo(models.Model):
    """股票基本信息模型"""
    code = models.CharField(max_length=10, unique=True, verbose_name='股票代码')
    name = models.CharField(max_length=50, verbose_name='股票名称')
    industry = models.CharField(max_length=50, null=True, blank=True, verbose_name='所属行业')
    total_shares = models.BigIntegerField(null=True, blank=True, verbose_name='总股本')
    circulating_shares = models.BigIntegerField(null=True, blank=True, verbose_name='流通股本')
    list_date = models.DateField(null=True, blank=True, verbose_name='上市日期')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'stock_info'
        verbose_name = '股票基本信息'
        verbose_name_plural = '股票基本信息'
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
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class StockRealtime(models.Model):
    """股票实时行情模型"""
    code = models.CharField(max_length=10, db_index=True, verbose_name='股票代码')
    name = models.CharField(max_length=50, verbose_name='股票名称')
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
    pe_ratio = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name='市盈率')
    pb_ratio = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name='市净率')
    market_cap = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='总市值')
    circulating_market_cap = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='流通市值')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='数据时间')
    
    class Meta:
        db_table = 'stock_realtime'
        verbose_name = '股票实时行情'
        verbose_name_plural = '股票实时行情'
        ordering = ['-timestamp', 'code']
        indexes = [
            models.Index(fields=['code', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f'{self.code} - {self.name} - {self.latest_price}'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'code': self.code,
            'name': self.name,
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
            'pe_ratio': float(self.pe_ratio) if self.pe_ratio else None,
            'pb_ratio': float(self.pb_ratio) if self.pb_ratio else None,
            'market_cap': float(self.market_cap) if self.market_cap else None,
            'circulating_market_cap': float(self.circulating_market_cap) if self.circulating_market_cap else None,
            'timestamp': self.timestamp.isoformat()
        }

class MarketSummary(models.Model):
    """市场摘要模型"""
    date = models.DateField(unique=True, verbose_name='日期')
    total_stocks = models.IntegerField(verbose_name='股票总数')
    rising_stocks = models.IntegerField(verbose_name='上涨股票数')
    falling_stocks = models.IntegerField(verbose_name='下跌股票数')
    flat_stocks = models.IntegerField(verbose_name='平盘股票数')
    total_volume = models.BigIntegerField(verbose_name='总成交量')
    total_amount = models.DecimalField(max_digits=20, decimal_places=2, verbose_name='总成交额')
    avg_change_percent = models.DecimalField(max_digits=8, decimal_places=3, verbose_name='平均涨跌幅(%)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        db_table = 'market_summary'
        verbose_name = '市场摘要'
        verbose_name_plural = '市场摘要'
        ordering = ['-date']
    
    def __str__(self):
        return f'{self.date} - 总数:{self.total_stocks}'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'date': self.date.isoformat(),
            'total_stocks': self.total_stocks,
            'rising_stocks': self.rising_stocks,
            'falling_stocks': self.falling_stocks,
            'flat_stocks': self.flat_stocks,
            'total_volume': self.total_volume,
            'total_amount': float(self.total_amount),
            'avg_change_percent': float(self.avg_change_percent),
            'created_at': self.created_at.isoformat()
        }