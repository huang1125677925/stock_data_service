from django.db import models


class EtfBasic(models.Model):
    """
    ETF 基本信息模型
    功能：存储ETF的基础信息，字段参考 Tushare ETF 基本信息文档。
    参数：无（Django 模型字段定义）
    返回值：无（实例由 ORM 管理）
    事件：数据库迁移创建表、插入/更新/查询记录。
    """
    ts_code = models.CharField(max_length=20, unique=True, verbose_name='TS代码')
    csname = models.CharField(max_length=100, null=True, blank=True, verbose_name='中文简称')
    extname = models.CharField(max_length=100, verbose_name='ETF扩位简称')
    cname = models.CharField(max_length=200, null=True, blank=True, verbose_name='基金中文全称')
    index_code = models.CharField(max_length=20, null=True, blank=True, verbose_name='跟踪指数代码')
    index_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='跟踪指数名称')
    exchange = models.CharField(max_length=20, null=True, blank=True, verbose_name='交易所')

    LIST_STATUS_CHOICES = [
        ('L', '上市'),
        ('D', '退市'),
        ('P', '待上市'),
    ]
    list_status = models.CharField(max_length=1, choices=LIST_STATUS_CHOICES, default='L', verbose_name='上市状态')
    setup_date = models.DateField(null=True, blank=True, verbose_name='设立日期')
    list_date = models.DateField(null=True, blank=True, verbose_name='上市日期')
    delist_date = models.DateField(null=True, blank=True, verbose_name='退市日期')
    etf_type = models.CharField(max_length=20, null=True, blank=True, verbose_name='ETF类型')

    mgr_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='基金管理人简称')
    custod_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='基金托管人名称')
    mgt_fee = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True, verbose_name='管理费率')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'etf_basic'
        verbose_name = 'ETF 基本信息'
        verbose_name_plural = 'ETF 基本信息'
        ordering = ['ts_code']
        indexes = [
            models.Index(fields=['ts_code']),
            models.Index(fields=['exchange']),
            models.Index(fields=['list_status']),
        ]

    def __str__(self):
        return f'{self.ts_code} - {self.extname}'


class EtfDaily(models.Model):
    """
    ETF 日线行情模型
    功能：存储ETF的日线行情数据，字段参考 Tushare ETF 日线行情文档。
    参数：无（Django 模型字段定义）
    返回值：无（实例由 ORM 管理）
    事件：数据库迁移创建表、插入/更新/查询记录。
    """
    ts_code = models.CharField(max_length=20, verbose_name='TS代码')
    trade_date = models.DateField(verbose_name='交易日期')
    open = models.DecimalField(max_digits=12, decimal_places=4, verbose_name='开盘价')
    high = models.DecimalField(max_digits=12, decimal_places=4, verbose_name='最高价')
    low = models.DecimalField(max_digits=12, decimal_places=4, verbose_name='最低价')
    close = models.DecimalField(max_digits=12, decimal_places=4, verbose_name='收盘价')
    pre_close = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, verbose_name='昨收盘价')
    change = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, verbose_name='涨跌额')
    pct_chg = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True, verbose_name='涨跌幅(%)')
    vol = models.BigIntegerField(verbose_name='成交量(手)')
    amount = models.DecimalField(max_digits=20, decimal_places=2, verbose_name='成交额(元)')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'etf_daily'
        verbose_name = 'ETF 日线行情'
        verbose_name_plural = 'ETF 日线行情'
        ordering = ['-trade_date', 'ts_code']
        unique_together = ['ts_code', 'trade_date']
        indexes = [
            models.Index(fields=['ts_code', '-trade_date']),
            models.Index(fields=['-trade_date']),
        ]

    def __str__(self):
        return f'{self.ts_code} - {self.trade_date} - {self.close}'