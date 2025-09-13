from django.db import models
from datetime import datetime

class CCTVNews(models.Model):
    """CCTV新闻模型"""
    
    title = models.CharField(max_length=500, verbose_name='标题')
    content = models.TextField(verbose_name='内容')
    ai_content = models.TextField(blank=True, null=True, verbose_name='AI分析内容')
    publish_date = models.DateField(verbose_name='发布日期')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        db_table = 'cctv_news'
        verbose_name = 'CCTV新闻'
        verbose_name_plural = 'CCTV新闻'
        ordering = ['-publish_date']
    
    def __str__(self):
        return self.title
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'ai_content': self.ai_content,
            'publish_date': self.publish_date.strftime('%Y-%m-%d') if self.publish_date else None,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else None
        }
    
    @property
    def summary(self):
        """获取内容摘要"""
        if len(self.content) > 100:
            return self.content[:100] + '...'
        return self.content