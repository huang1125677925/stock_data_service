from django.db import models
from datetime import datetime


class IndividualStock(models.Model):
    """个股基本信息模型"""
    code = models.CharField(max_length=10, unique=True, verbose_name='股票代码')
    name = models.CharField(max_length=50, verbose_name='股票名称')
    industry = models.CharField(max_length=50, null=True, blank=True, verbose_name='所属行业')
    
    # 指数类型选择
    INDEX_TYPE_CHOICES = [
        ('SH_MAIN', '上证主板'),
        ('SZ_MAIN', '深证主板'),
        ('SZ_SME', '深证中小板'),
        ('SZ_GEM', '深证创业板'),
        ('BJ_MAIN', '北交所主板'),
        ('SH_INDEX', '上证指数'),
        ('SZ_INDEX', '深证指数'),
        ('CSI_INDEX', '中证指数'),
        ('OTHER', '其他'),
    ]
    index_type = models.CharField(
        max_length=20, 
        choices=INDEX_TYPE_CHOICES, 
        null=True, 
        blank=True, 
        verbose_name='指数类型'
    )
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
            'index_type': self.index_type,
            'index_type_display': self.get_index_type_display() if self.index_type else None,
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


class BalanceSheet(models.Model):
    """资产负债表模型
    功能：存储个股在特定报告期的资产负债表数据。
    参数（字段）：
    - stock(ForeignKey[IndividualStock]): 所属股票；删除股票级联删除报告。
    - report_date(CharField): 报告期，格式 YYYYMMDD。
    - monetary_funds(DecimalField): 货币资金（元）。
    - accounts_receivable(DecimalField): 应收账款（元）。
    - inventory(DecimalField): 存货（元）。
    - total_assets(DecimalField): 总资产（元）。
    - total_assets_growth_rate(DecimalField): 总资产同比（%）。
    - accounts_payable(DecimalField): 应付账款（元）。
    - total_liabilities(DecimalField): 总负债（元）。
    - advance_receipts(DecimalField): 预收账款（元）。
    - total_liabilities_growth_rate(DecimalField): 总负债同比（%）。
    - debt_to_asset_ratio(DecimalField): 资产负债率（%）。
    - total_equity(DecimalField): 股东权益合计（元）。
    - announcement_date(DateField): 公告日期。
    - created_at(DateTimeField): 创建时间。
    - updated_at(DateTimeField): 更新时间。
    返回值：无（模型用于持久化数据）。
    事件：无（模型不直接触发事件）。
    """
    stock = models.ForeignKey(IndividualStock, on_delete=models.CASCADE, related_name='balance_sheets', verbose_name='所属股票')
    report_date = models.CharField(max_length=8, verbose_name='报告期', help_text='格式：YYYYMMDD，如20240331')
    
    # 资产相关字段
    monetary_funds = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='货币资金(元)')
    accounts_receivable = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='应收账款(元)')
    inventory = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='存货(元)')
    total_assets = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='总资产(元)')
    total_assets_growth_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='总资产同比(%)')
    
    # 负债相关字段
    accounts_payable = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='应付账款(元)')
    total_liabilities = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='总负债(元)')
    advance_receipts = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='预收账款(元)')
    total_liabilities_growth_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='总负债同比(%)')
    
    # 其他指标
    debt_to_asset_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='资产负债率(%)')
    total_equity = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='股东权益合计(元)')
    
    # 基本信息
    announcement_date = models.DateField(null=True, blank=True, verbose_name='公告日期')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'balance_sheet'
        verbose_name = '资产负债表'
        verbose_name_plural = '资产负债表'
        ordering = ['-report_date', 'stock']
        indexes = [
            models.Index(fields=['stock', '-report_date']),
            models.Index(fields=['-report_date']),
            models.Index(fields=['announcement_date']),
        ]
        unique_together = ['stock', 'report_date']
    
    def __str__(self):
        return f'{self.stock.code} - {self.stock.name} - 资产负债表 - {self.report_date}'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'stock_code': self.stock.code,
            'stock_name': self.stock.name,
            'report_date': self.report_date,
            'monetary_funds': float(self.monetary_funds) if self.monetary_funds else None,
            'accounts_receivable': float(self.accounts_receivable) if self.accounts_receivable else None,
            'inventory': float(self.inventory) if self.inventory else None,
            'total_assets': float(self.total_assets) if self.total_assets else None,
            'total_assets_growth_rate': float(self.total_assets_growth_rate) if self.total_assets_growth_rate else None,
            'accounts_payable': float(self.accounts_payable) if self.accounts_payable else None,
            'total_liabilities': float(self.total_liabilities) if self.total_liabilities else None,
            'advance_receipts': float(self.advance_receipts) if self.advance_receipts else None,
            'total_liabilities_growth_rate': float(self.total_liabilities_growth_rate) if self.total_liabilities_growth_rate else None,
            'debt_to_asset_ratio': float(self.debt_to_asset_ratio) if self.debt_to_asset_ratio else None,
            'total_equity': float(self.total_equity) if self.total_equity else None,
            'announcement_date': self.announcement_date.strftime('%Y-%m-%d') if self.announcement_date else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        }


class IncomeStatement(models.Model):
    """利润表模型
    功能：存储个股在特定报告期的利润表数据。
    参数（字段）：
    - stock(ForeignKey[IndividualStock]): 所属股票；删除股票级联删除报告。
    - report_date(CharField): 报告期，格式 YYYYMMDD。
    - net_profit(DecimalField): 净利润（元）。
    - net_profit_growth_rate(DecimalField): 净利润同比（%）。
    - operating_revenue(DecimalField): 营业总收入（元）。
    - operating_revenue_growth_rate(DecimalField): 营业总收入同比（%）。
    - operating_expenses(DecimalField): 营业支出（元）。
    - sales_expenses(DecimalField): 销售费用（元）。
    - management_expenses(DecimalField): 管理费用（元）。
    - financial_expenses(DecimalField): 财务费用（元）。
    - total_operating_expenses(DecimalField): 营业总支出（元）。
    - operating_profit(DecimalField): 营业利润（元）。
    - total_profit(DecimalField): 利润总额（元）。
    - announcement_date(DateField): 公告日期。
    - created_at(DateTimeField): 创建时间。
    - updated_at(DateTimeField): 更新时间。
    返回值：无（模型用于持久化数据）。
    事件：无（模型不直接触发事件）。
    """
    stock = models.ForeignKey(IndividualStock, on_delete=models.CASCADE, related_name='income_statements', verbose_name='所属股票')
    report_date = models.CharField(max_length=8, verbose_name='报告期', help_text='格式：YYYYMMDD，如20240331')
    
    # 利润相关字段
    net_profit = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='净利润(元)')
    net_profit_growth_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='净利润同比(%)')
    
    # 收入相关字段
    operating_revenue = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='营业总收入(元)')
    operating_revenue_growth_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='营业总收入同比(%)')
    
    # 支出相关字段
    operating_expenses = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='营业支出(元)')
    sales_expenses = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='销售费用(元)')
    management_expenses = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='管理费用(元)')
    financial_expenses = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='财务费用(元)')
    total_operating_expenses = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='营业总支出(元)')
    
    # 其他利润指标
    operating_profit = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='营业利润(元)')
    total_profit = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='利润总额(元)')
    
    # 基本信息
    announcement_date = models.DateField(null=True, blank=True, verbose_name='公告日期')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'income_statement'
        verbose_name = '利润表'
        verbose_name_plural = '利润表'
        ordering = ['-report_date', 'stock']
        indexes = [
            models.Index(fields=['stock', '-report_date']),
            models.Index(fields=['-report_date']),
            models.Index(fields=['announcement_date']),
        ]
        unique_together = ['stock', 'report_date']
    
    def __str__(self):
        return f'{self.stock.code} - {self.stock.name} - 利润表 - {self.report_date}'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'stock_code': self.stock.code,
            'stock_name': self.stock.name,
            'report_date': self.report_date,
            'net_profit': float(self.net_profit) if self.net_profit else None,
            'net_profit_growth_rate': float(self.net_profit_growth_rate) if self.net_profit_growth_rate else None,
            'operating_revenue': float(self.operating_revenue) if self.operating_revenue else None,
            'operating_revenue_growth_rate': float(self.operating_revenue_growth_rate) if self.operating_revenue_growth_rate else None,
            'operating_expenses': float(self.operating_expenses) if self.operating_expenses else None,
            'sales_expenses': float(self.sales_expenses) if self.sales_expenses else None,
            'management_expenses': float(self.management_expenses) if self.management_expenses else None,
            'financial_expenses': float(self.financial_expenses) if self.financial_expenses else None,
            'total_operating_expenses': float(self.total_operating_expenses) if self.total_operating_expenses else None,
            'operating_profit': float(self.operating_profit) if self.operating_profit else None,
            'total_profit': float(self.total_profit) if self.total_profit else None,
            'announcement_date': self.announcement_date.strftime('%Y-%m-%d') if self.announcement_date else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        }


class CashFlowStatement(models.Model):
    """现金流量表模型
    功能：存储个股在特定报告期的现金流量表数据。
    参数（字段）：
    - stock(ForeignKey[IndividualStock]): 所属股票；删除股票级联删除报告。
    - report_date(CharField): 报告期，格式 YYYYMMDD。
    - net_cash_flow(DecimalField): 净现金流（元）。
    - net_cash_flow_growth_rate(DecimalField): 净现金流同比增长（%）。
    - operating_cash_flow(DecimalField): 经营性现金流量净额（元）。
    - operating_cash_flow_ratio(DecimalField): 经营性现金流净现金流占比（%）。
    - investing_cash_flow(DecimalField): 投资性现金流量净额（元）。
    - investing_cash_flow_ratio(DecimalField): 投资性现金流净现金流占比（%）。
    - financing_cash_flow(DecimalField): 融资性现金流量净额（元）。
    - financing_cash_flow_ratio(DecimalField): 融资性现金流净现金流占比（%）。
    - announcement_date(DateField): 公告日期。
    - created_at(DateTimeField): 创建时间。
    - updated_at(DateTimeField): 更新时间。
    返回值：无（模型用于持久化数据）。
    事件：无（模型不直接触发事件）。
    """
    stock = models.ForeignKey(IndividualStock, on_delete=models.CASCADE, related_name='cash_flow_statements', verbose_name='所属股票')
    report_date = models.CharField(max_length=8, verbose_name='报告期', help_text='格式：YYYYMMDD，如20240331')
    
    # 净现金流相关字段
    net_cash_flow = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='净现金流(元)')
    net_cash_flow_growth_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='净现金流同比增长(%)')
    
    # 经营性现金流相关字段
    operating_cash_flow = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='经营性现金流量净额(元)')
    operating_cash_flow_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='经营性现金流净现金流占比(%)')
    
    # 投资性现金流相关字段
    investing_cash_flow = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='投资性现金流量净额(元)')
    investing_cash_flow_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='投资性现金流净现金流占比(%)')
    
    # 融资性现金流相关字段
    financing_cash_flow = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True, verbose_name='融资性现金流量净额(元)')
    financing_cash_flow_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='融资性现金流净现金流占比(%)')
    
    # 基本信息
    announcement_date = models.DateField(null=True, blank=True, verbose_name='公告日期')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'cash_flow_statement'
        verbose_name = '现金流量表'
        verbose_name_plural = '现金流量表'
        ordering = ['-report_date', 'stock']
        indexes = [
            models.Index(fields=['stock', '-report_date']),
            models.Index(fields=['-report_date']),
            models.Index(fields=['announcement_date']),
        ]
        unique_together = ['stock', 'report_date']
    
    def __str__(self):
        return f'{self.stock.code} - {self.stock.name} - 现金流量表 - {self.report_date}'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'stock_code': self.stock.code,
            'stock_name': self.stock.name,
            'report_date': self.report_date,
            'net_cash_flow': float(self.net_cash_flow) if self.net_cash_flow else None,
            'net_cash_flow_growth_rate': float(self.net_cash_flow_growth_rate) if self.net_cash_flow_growth_rate else None,
            'operating_cash_flow': float(self.operating_cash_flow) if self.operating_cash_flow else None,
            'operating_cash_flow_ratio': float(self.operating_cash_flow_ratio) if self.operating_cash_flow_ratio else None,
            'investing_cash_flow': float(self.investing_cash_flow) if self.investing_cash_flow else None,
            'investing_cash_flow_ratio': float(self.investing_cash_flow_ratio) if self.investing_cash_flow_ratio else None,
            'financing_cash_flow': float(self.financing_cash_flow) if self.financing_cash_flow else None,
            'financing_cash_flow_ratio': float(self.financing_cash_flow_ratio) if self.financing_cash_flow_ratio else None,
            'announcement_date': self.announcement_date.strftime('%Y-%m-%d') if self.announcement_date else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        }


class StockTag(models.Model):
    """股票标记表模型
    功能：存储股票的各种标记因子，用于股票筛选和分类。
    参数（字段）：
    - stock(ForeignKey[IndividualStock]): 所属股票；删除股票级联删除标记。
    - pattern_type(CharField): 形态类型标记。
    - technical_indicator_type(CharField): 技术指标类型标记。
    - stock_type(CharField): 股票类型标记。
    - market_cap_type(CharField): 市值大小类型标记。
    - pe_range_type(CharField): PE区间类型标记。
    - pb_range_type(CharField): PB区间类型标记。
    - industry_type(CharField): 行业类型标记。
    - volume_type(CharField): 成交量类型标记。
    - volatility_type(CharField): 波动率类型标记。
    - trend_type(CharField): 趋势类型标记。
    - created_at(DateTimeField): 创建时间。
    - updated_at(DateTimeField): 更新时间。
    返回值：无（模型用于持久化数据）。
    事件：无（模型不直接触发事件）。
    """
    
    # 形态类型选择
    PATTERN_TYPE_CHOICES = [
        ('BREAKOUT', '突破形态'),
        ('REVERSAL', '反转形态'),
        ('CONSOLIDATION', '整理形态'),
        ('HEAD_SHOULDERS', '头肩形态'),
        ('DOUBLE_TOP', '双顶形态'),
        ('DOUBLE_BOTTOM', '双底形态'),
        ('TRIANGLE', '三角形态'),
        ('FLAG', '旗形形态'),
        ('WEDGE', '楔形形态'),
        ('CHANNEL', '通道形态'),
        ('BOX_BREAKOUT', '箱型突破'),
        ('OTHER', '其他形态'),
    ]
    
    # 技术指标类型选择
    TECHNICAL_INDICATOR_TYPE_CHOICES = [
        ('MACD_BULLISH', 'MACD多头'),
        ('MACD_BEARISH', 'MACD空头'),
        ('RSI_OVERSOLD', 'RSI超卖'),
        ('RSI_OVERBOUGHT', 'RSI超买'),
        ('KDJ_GOLDEN_CROSS', 'KDJ金叉'),
        ('KDJ_DEATH_CROSS', 'KDJ死叉'),
        ('MA_BULLISH', '均线多头排列'),
        ('MA_BEARISH', '均线空头排列'),
        ('BOLL_UPPER', '布林上轨'),
        ('BOLL_LOWER', '布林下轨'),
        ('VOLUME_SURGE', '放量突破'),
        ('VOLUME_SHRINK', '缩量整理'),
        ('OTHER', '其他指标'),
    ]
    
    # 股票类型选择
    STOCK_TYPE_CHOICES = [
        ('BLUE_CHIP', '蓝筹股'),
        ('GROWTH', '成长股'),
        ('VALUE', '价值股'),
        ('SMALL_CAP', '小盘股'),
        ('MID_CAP', '中盘股'),
        ('LARGE_CAP', '大盘股'),
        ('CONCEPT', '概念股'),
        ('THEME', '题材股'),
        ('ST', 'ST股票'),
        ('NEW_STOCK', '次新股'),
        ('DIVIDEND', '高股息'),
        ('OTHER', '其他类型'),
    ]
    
    # 市值大小类型选择
    MARKET_CAP_TYPE_CHOICES = [
        ('MEGA_CAP', '超大盘股(>1000亿)'),
        ('LARGE_CAP', '大盘股(300-1000亿)'),
        ('MID_CAP', '中盘股(100-300亿)'),
        ('SMALL_CAP', '小盘股(50-100亿)'),
        ('MICRO_CAP', '微盘股(<50亿)'),
    ]
    
    # PE区间类型选择
    PE_RANGE_TYPE_CHOICES = [
        ('NEGATIVE', '负PE'),
        ('LOW', '低PE(0-15)'),
        ('MODERATE', '适中PE(15-25)'),
        ('HIGH', '高PE(25-50)'),
        ('VERY_HIGH', '极高PE(>50)'),
    ]
    
    # PB区间类型选择
    PB_RANGE_TYPE_CHOICES = [
        ('VERY_LOW', '极低PB(<1)'),
        ('LOW', '低PB(1-2)'),
        ('MODERATE', '适中PB(2-3)'),
        ('HIGH', '高PB(3-5)'),
        ('VERY_HIGH', '极高PB(>5)'),
    ]
    
    # 行业类型选择
    INDUSTRY_TYPE_CHOICES = [
        ('TECHNOLOGY', '科技行业'),
        ('FINANCE', '金融行业'),
        ('HEALTHCARE', '医疗健康'),
        ('CONSUMER', '消费行业'),
        ('INDUSTRIAL', '工业制造'),
        ('ENERGY', '能源行业'),
        ('MATERIALS', '原材料'),
        ('UTILITIES', '公用事业'),
        ('REAL_ESTATE', '房地产'),
        ('TELECOM', '电信服务'),
        ('OTHER', '其他行业'),
    ]
    
    # 成交量类型选择
    VOLUME_TYPE_CHOICES = [
        ('VOLUME_SURGE', '放量'),
        ('VOLUME_NORMAL', '正常量'),
        ('VOLUME_SHRINK', '缩量'),
        ('VOLUME_EXTREME', '极量'),
    ]
    
    # 波动率类型选择
    VOLATILITY_TYPE_CHOICES = [
        ('LOW_VOLATILITY', '低波动'),
        ('MODERATE_VOLATILITY', '中等波动'),
        ('HIGH_VOLATILITY', '高波动'),
        ('EXTREME_VOLATILITY', '极端波动'),
    ]
    
    # 趋势类型选择
    TREND_TYPE_CHOICES = [
        ('STRONG_UPTREND', '强势上涨'),
        ('WEAK_UPTREND', '弱势上涨'),
        ('SIDEWAYS', '横盘整理'),
        ('WEAK_DOWNTREND', '弱势下跌'),
        ('STRONG_DOWNTREND', '强势下跌'),
    ]
    
    stock = models.ForeignKey(IndividualStock, on_delete=models.CASCADE, related_name='stock_tags', verbose_name='所属股票')
    
    # 各种标记因子字段
    pattern_type = models.CharField(
        max_length=20, 
        choices=PATTERN_TYPE_CHOICES, 
        null=True, 
        blank=True, 
        verbose_name='形态类型'
    )
    technical_indicator_type = models.CharField(
        max_length=20, 
        choices=TECHNICAL_INDICATOR_TYPE_CHOICES, 
        null=True, 
        blank=True, 
        verbose_name='技术指标类型'
    )
    stock_type = models.CharField(
        max_length=20, 
        choices=STOCK_TYPE_CHOICES, 
        null=True, 
        blank=True, 
        verbose_name='股票类型'
    )
    market_cap_type = models.CharField(
        max_length=20, 
        choices=MARKET_CAP_TYPE_CHOICES, 
        null=True, 
        blank=True, 
        verbose_name='市值大小类型'
    )
    pe_range_type = models.CharField(
        max_length=20, 
        choices=PE_RANGE_TYPE_CHOICES, 
        null=True, 
        blank=True, 
        verbose_name='PE区间类型'
    )
    pb_range_type = models.CharField(
        max_length=20, 
        choices=PB_RANGE_TYPE_CHOICES, 
        null=True, 
        blank=True, 
        verbose_name='PB区间类型'
    )
    industry_type = models.CharField(
        max_length=20, 
        choices=INDUSTRY_TYPE_CHOICES, 
        null=True, 
        blank=True, 
        verbose_name='行业类型'
    )
    volume_type = models.CharField(
        max_length=20, 
        choices=VOLUME_TYPE_CHOICES, 
        null=True, 
        blank=True, 
        verbose_name='成交量类型'
    )
    volatility_type = models.CharField(
        max_length=20, 
        choices=VOLATILITY_TYPE_CHOICES, 
        null=True, 
        blank=True, 
        verbose_name='波动率类型'
    )
    trend_type = models.CharField(
        max_length=20, 
        choices=TREND_TYPE_CHOICES, 
        null=True, 
        blank=True, 
        verbose_name='趋势类型'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'stock_tag'
        verbose_name = '股票标记'
        verbose_name_plural = '股票标记'
        ordering = ['-created_at', 'stock']
        indexes = [
            models.Index(fields=['stock', '-created_at']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['pattern_type']),
            models.Index(fields=['technical_indicator_type']),
            models.Index(fields=['stock_type']),
            models.Index(fields=['market_cap_type']),
            models.Index(fields=['pe_range_type']),
            models.Index(fields=['pb_range_type']),
            models.Index(fields=['industry_type']),
            models.Index(fields=['volume_type']),
            models.Index(fields=['volatility_type']),
            models.Index(fields=['trend_type']),
        ]
        unique_together = ['stock', ]
    
    def __str__(self):
        return f'{self.stock.code} - {self.stock.name}'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'stock_code': self.stock.code,
            'stock_name': self.stock.name,
            'pattern_type': self.pattern_type,
            'pattern_type_display': self.get_pattern_type_display() if self.pattern_type else None,
            'technical_indicator_type': self.technical_indicator_type,
            'technical_indicator_type_display': self.get_technical_indicator_type_display() if self.technical_indicator_type else None,
            'stock_type': self.stock_type,
            'stock_type_display': self.get_stock_type_display() if self.stock_type else None,
            'market_cap_type': self.market_cap_type,
            'market_cap_type_display': self.get_market_cap_type_display() if self.market_cap_type else None,
            'pe_range_type': self.pe_range_type,
            'pe_range_type_display': self.get_pe_range_type_display() if self.pe_range_type else None,
            'pb_range_type': self.pb_range_type,
            'pb_range_type_display': self.get_pb_range_type_display() if self.pb_range_type else None,
            'industry_type': self.industry_type,
            'industry_type_display': self.get_industry_type_display() if self.industry_type else None,
            'volume_type': self.volume_type,
            'volume_type_display': self.get_volume_type_display() if self.volume_type else None,
            'volatility_type': self.volatility_type,
            'volatility_type_display': self.get_volatility_type_display() if self.volatility_type else None,
            'trend_type': self.trend_type,
            'trend_type_display': self.get_trend_type_display() if self.trend_type else None,
            'remarks': self.remarks,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
