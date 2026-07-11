from django.db import models

class StockMarketDaily(models.Model):
    """
    上海证券交易所每日概况数据模型
    """
    date = models.DateField(verbose_name="日期", unique=True)
    data_json = models.JSONField(verbose_name="每日概况数据")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "上证每日概况"
        verbose_name_plural = verbose_name
        ordering = ['-date']

    def __str__(self):
        return f"上证每日概况 {self.date}"


class IndexBasicData(models.Model):
    """
    指数基础数据表模型
    
    功能：存储各种股票指数的基础信息
    字段：
        - code: 指数代码，如'000001.SH'
        - name: 指数名称，如'上证指数'
        - created_at: 创建时间
        - updated_at: 更新时间
    """
    code = models.CharField(max_length=20, unique=True, verbose_name="代码", help_text="指数代码，如'000001.SH'")
    name = models.CharField(max_length=100, verbose_name="名称", help_text="指数名称，如'上证指数'")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "指数基础数据"
        verbose_name_plural = verbose_name
        ordering = ['code']
        db_table = 'stock_market_index_basic_data'

    def __str__(self):
        return f"{self.code} - {self.name}"


class IndexHighLowStatistics(models.Model):
    """
    指数涨跌统计数据模型
    
    功能：存储不同指数的涨跌统计数据，包括创新高、新低的股票数量
    参数：
        - date: 统计日期
        - index_code: 指数代码，区分all/sz50/hs300/zz500
        - close: 收盘价
        - high20: 20日新高数量
        - low20: 20日新低数量
        - high60: 60日新高数量
        - low60: 60日新低数量
        - high120: 120日新高数量
        - low120: 120日新低数量
        - rise_fall_ratio: 涨跌比（涨的数量/涨+跌数量）
    返回值：指数涨跌统计数据记录
    事件：创建、更新时自动记录时间戳
    """
    INDEX_CODE_CHOICES = [
        ('all', '全部A股'),
        ('sz50', '上证50'),
        ('hs300', '沪深300'),
        ('zz500', '中证500'),
    ]
    
    date = models.DateField(verbose_name="统计日期", help_text="数据统计的日期")
    index_code = models.CharField(
        max_length=10, 
        choices=INDEX_CODE_CHOICES,
        verbose_name="指数代码", 
        help_text="指数类型：all-全部A股, sz50-上证50, hs300-沪深300, zz500-中证500"
    )
    close = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="收盘价",
        help_text="当日收盘价"
    )
    high20 = models.IntegerField(
        null=True, 
        blank=True,
        verbose_name="20日新高数量",
        help_text="创20日新高的股票数量"
    )
    low20 = models.IntegerField(
        null=True, 
        blank=True,
        verbose_name="20日新低数量",
        help_text="创20日新低的股票数量"
    )
    high60 = models.IntegerField(
        null=True, 
        blank=True,
        verbose_name="60日新高数量",
        help_text="创60日新高的股票数量"
    )
    low60 = models.IntegerField(
        null=True, 
        blank=True,
        verbose_name="60日新低数量",
        help_text="创60日新低的股票数量"
    )
    high120 = models.IntegerField(
        null=True, 
        blank=True,
        verbose_name="120日新高数量",
        help_text="创120日新高的股票数量"
    )
    low120 = models.IntegerField(
        null=True, 
        blank=True,
        verbose_name="120日新低数量",
        help_text="创120日新低的股票数量"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "指数涨跌统计"
        verbose_name_plural = verbose_name
        ordering = ['-date', 'index_code']
        db_table = 'stock_market_index_high_low_statistics'
        unique_together = ['date', 'index_code']  # 确保同一天同一指数只有一条记录

    def __str__(self):
        return f"{self.get_index_code_display()} {self.date} 涨跌统计"

