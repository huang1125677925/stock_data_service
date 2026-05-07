from django.db import models
from user_management.models import User
from indival_stock_data.models import IndividualStock

class Holding(models.Model):
    """
    个人持有/关注股票模型
    功能：记录用户持有或关注的股票信息
    字段：
    - user(User): 关联的用户
    - stock(IndividualStock): 关联的股票
    - industry(str): 行业名称（冗余存储，默认取自股票模型）
    - relation_type(str): 关系类型，持有(HELD)或关注(WATCHED)
    - created_at(datetime): 创建时间
    约束：
    - 用户、股票、关系类型唯一约束，避免重复记录
    """
    RELATION_CHOICES = [
        ('HELD', '持有'),
        ('WATCHED', '关注'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='holdings', verbose_name='用户')
    stock = models.ForeignKey(IndividualStock, on_delete=models.CASCADE, related_name='user_holdings', verbose_name='股票')
    industry = models.CharField(max_length=50, null=True, blank=True, verbose_name='所属行业')
    relation_type = models.CharField(max_length=10, choices=RELATION_CHOICES, default='WATCHED', verbose_name='关系类型')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '个人持有/关注股票'
        verbose_name_plural = '个人持有/关注股票'
        ordering = ['-created_at']
        unique_together = ('user', 'stock', 'relation_type')

    def save(self, *args, **kwargs):
        # 如果未显式提供行业，默认从股票模型中取值
        if not self.industry and self.stock and getattr(self.stock, 'industry', None):
            self.industry = self.stock.industry
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.stock.code} ({self.get_relation_type_display()})"