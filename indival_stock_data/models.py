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
    
    # akshare数据字段
    latest_price = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name='最新价')
    change_percent = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, verbose_name='涨跌幅(%)')
    change_amount = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name='涨跌额')
    volume = models.BigIntegerField(null=True, blank=True, verbose_name='成交量')
    amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='成交额')
    amplitude = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, verbose_name='振幅(%)')
    high = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name='最高')
    low = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name='最低')
    open_price = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name='今开')
    close_price = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name='昨收')
    volume_ratio = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, verbose_name='量比')
    turnover_rate = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, verbose_name='换手率(%)')
    price_change_speed = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, verbose_name='涨速(%)')
    change_5min = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, verbose_name='5分钟涨跌(%)')
    change_60d = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, verbose_name='60日涨跌幅(%)')
    change_ytd = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, verbose_name='年初至今涨跌幅(%)')
    
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
            # akshare数据字段
            'latest_price': float(self.latest_price) if self.latest_price else None,
            'change_percent': float(self.change_percent) if self.change_percent else None,
            'change_amount': float(self.change_amount) if self.change_amount else None,
            'volume': self.volume,
            'amount': float(self.amount) if self.amount else None,
            'amplitude': float(self.amplitude) if self.amplitude else None,
            'high': float(self.high) if self.high else None,
            'low': float(self.low) if self.low else None,
            'open_price': float(self.open_price) if self.open_price else None,
            'close_price': float(self.close_price) if self.close_price else None,
            'volume_ratio': float(self.volume_ratio) if self.volume_ratio else None,
            'turnover_rate': float(self.turnover_rate) if self.turnover_rate else None,
            'price_change_speed': float(self.price_change_speed) if self.price_change_speed else None,
            'change_5min': float(self.change_5min) if self.change_5min else None,
            'change_60d': float(self.change_60d) if self.change_60d else None,
            'change_ytd': float(self.change_ytd) if self.change_ytd else None,
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


class PerformanceReport(models.Model):
    """业绩快报模型
    功能：存储个股在特定报告期的核心经营与财务指标。
    参数（字段）：
    - stock(ForeignKey[IndividualStock]): 所属股票；删除股票级联删除报告。
    - report_date(CharField): 报告期，格式 YYYYMMDD。
    - earnings_per_share(DecimalField): 每股收益（元）。
    - operating_revenue(DecimalField): 营业总收入（元）。
    - operating_revenue_growth_rate(DecimalField): 营业总收入-同比增长（%）。
    - operating_revenue_quarter_growth(DecimalField): 营业总收入-季度环比增长（%）。
    - net_profit(DecimalField): 净利润（元）。
    - net_profit_growth_rate(DecimalField): 净利润-同比增长（%）。
    - net_profit_quarter_growth(DecimalField): 净利润-季度环比增长（%）。
    - net_assets_per_share(DecimalField): 每股净资产（元）。
    - roe(DecimalField): 净资产收益率（%）。
    - operating_cash_flow_per_share(DecimalField): 每股经营现金流量（元）。
    - gross_profit_margin(DecimalField): 销售毛利率（%）。
    - industry(CharField): 所处行业。
    - announcement_date(DateField): 最新公告日期。
    - created_at(DateTimeField): 创建时间。
    - updated_at(DateTimeField): 更新时间。
    返回值：无（模型用于持久化数据）。
    事件：无（模型不直接触发事件）。
    """
    stock = models.ForeignKey(IndividualStock, on_delete=models.CASCADE, related_name='performance_reports', verbose_name='所属股票')
    report_date = models.CharField(max_length=8, verbose_name='报告期', help_text='格式：YYYYMMDD，如20200331')
    earnings_per_share = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='每股收益(元)')
    
    # 营业总收入相关字段
    operating_revenue = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='营业总收入(元)')
    operating_revenue_growth_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='营业总收入-同比增长(%)')
    operating_revenue_quarter_growth = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='营业总收入-季度环比增长(%)')
    
    # 净利润相关字段
    net_profit = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='净利润(元)')
    net_profit_growth_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='净利润-同比增长(%)')
    net_profit_quarter_growth = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='净利润-季度环比增长(%)')
    
    # 其他财务指标
    net_assets_per_share = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='每股净资产(元)')
    roe = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, verbose_name='净资产收益率(%)')
    operating_cash_flow_per_share = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name='每股经营现金流量(元)')
    gross_profit_margin = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, verbose_name='销售毛利率(%)')
    
    # 基本信息
    industry = models.CharField(max_length=100, null=True, blank=True, verbose_name='所处行业')
    announcement_date = models.DateField(null=True, blank=True, verbose_name='最新公告日期')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'performance_report'
        verbose_name = '业绩快报'
        verbose_name_plural = '业绩快报'
        ordering = ['-report_date', 'stock']
        indexes = [
            models.Index(fields=['stock', '-report_date']),
            models.Index(fields=['-report_date']),
            models.Index(fields=['announcement_date']),
        ]
        unique_together = ['stock', 'report_date']
    
    def __str__(self):
        return f'{self.stock.code} - {self.stock.name} - {self.report_date}'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'stock_code': self.stock.code,
            'stock_name': self.stock.name,
            'report_date': self.report_date,
            'earnings_per_share': float(self.earnings_per_share) if self.earnings_per_share else None,
            'operating_revenue': float(self.operating_revenue) if self.operating_revenue else None,
            'operating_revenue_growth_rate': float(self.operating_revenue_growth_rate) if self.operating_revenue_growth_rate else None,
            'operating_revenue_quarter_growth': float(self.operating_revenue_quarter_growth) if self.operating_revenue_quarter_growth else None,
            'net_profit': float(self.net_profit) if self.net_profit else None,
            'net_profit_growth_rate': float(self.net_profit_growth_rate) if self.net_profit_growth_rate else None,
            'net_profit_quarter_growth': float(self.net_profit_quarter_growth) if self.net_profit_quarter_growth else None,
            'net_assets_per_share': float(self.net_assets_per_share) if self.net_assets_per_share else None,
            'roe': float(self.roe) if self.roe else None,
            'operating_cash_flow_per_share': float(self.operating_cash_flow_per_share) if self.operating_cash_flow_per_share else None,
            'gross_profit_margin': float(self.gross_profit_margin) if self.gross_profit_margin else None,
            'industry': self.industry,
            'announcement_date': self.announcement_date.strftime('%Y-%m-%d') if self.announcement_date else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        }


class StrategyResult(models.Model):
    """策略选股结果模型"""
    strategy_name = models.CharField(max_length=100, verbose_name='策略名称')
    strategy_description = models.TextField(verbose_name='策略描述')
    strategy_result = models.TextField(verbose_name='策略结果', help_text='JSON格式存储策略选股结果')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'strategy_result'
        verbose_name = '策略选股结果'
        verbose_name_plural = '策略选股结果'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['strategy_name']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f'{self.strategy_name} - {self.created_at.strftime("%Y-%m-%d %H:%M:%S")}'
    
    def to_dict(self):
        """转换为字典格式"""
        import json
        try:
            strategy_result_data = json.loads(self.strategy_result) if self.strategy_result else {}
        except json.JSONDecodeError:
            strategy_result_data = {}
        
        return {
            'id': self.id,
            'strategy_name': self.strategy_name,
            'strategy_description': self.strategy_description,
            'strategy_result': strategy_result_data,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
