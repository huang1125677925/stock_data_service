from django.test import TestCase
from .models import CCTVNews
from datetime import date

class CCTVNewsTestCase(TestCase):
    def setUp(self):
        CCTVNews.objects.create(
            title='测试新闻',
            content='这是一条测试新闻内容',
            publish_date=date.today()
        )
    
    def test_news_creation(self):
        news = CCTVNews.objects.get(title='测试新闻')
        self.assertEqual(news.content, '这是一条测试新闻内容')
        self.assertEqual(str(news), '测试新闻')