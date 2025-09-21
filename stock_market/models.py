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
