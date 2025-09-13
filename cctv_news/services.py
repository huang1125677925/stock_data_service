#!/usr/bin/env python3
"""
Django CCTV新闻服务
提供新闻数据的获取、处理和管理功能
"""

import logging
import json
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
from lxml import etree
from django.core.cache import cache
from django.conf import settings
from django.db.models import Q
from .models import CCTVNews
from common.validators import validate_news_content, sanitize_input

logger = logging.getLogger(__name__)

class CCTVNewsService:
    """CCTV新闻服务类"""
    
    def __init__(self):
        self.base_url = 'https://tv.cctv.com/lm/xwlb/'
        self.cache_timeout = getattr(settings, 'NEWS_CACHE_TIMEOUT', 1800)  # 缓存30分钟
        self.request_timeout = getattr(settings, 'NEWS_REQUEST_TIMEOUT', 30)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        logger.info(f"CCTV新闻服务初始化: cache_timeout={self.cache_timeout}s")
    
    def get_news_list(self, page: int = 1, limit: int = 20) -> Optional[List[Dict]]:
        """
        获取新闻列表
        
        Args:
            page: 页码
            limit: 每页数量
        
        Returns:
            新闻列表
        """
        try:
            offset = (page - 1) * limit
            
            # 从数据库获取新闻列表
            news_queryset = CCTVNews.objects.all().order_by('-publish_date')[offset:offset + limit]
            
            news_list = []
            for news in news_queryset:
                news_data = {
                    'id': news.id,
                    'title': news.title,
                    'content': news.content,
                    'ai_content': news.ai_content,
                    'publish_date': news.publish_date.strftime('%Y-%m-%d') if news.publish_date else None,
                    'create_time': news.create_time.strftime('%Y-%m-%d %H:%M:%S') if news.create_time else None
                }
                news_list.append(news_data)
            
            return news_list
            
        except Exception as e:
            logger.error(f"获取新闻列表失败: {str(e)}")
            return None
    
    def get_news_detail(self, news_id: int) -> Optional[Dict]:
        """
        获取新闻详情
        
        Args:
            news_id: 新闻ID
        
        Returns:
            新闻详情
        """
        cache_key = f'news_detail_{news_id}'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存获取新闻{news_id}详情")
            return cached_data
        
        try:
            news = CCTVNews.objects.get(id=news_id)
            
            news_detail = {
                'id': news.id,
                'title': news.title,
                'content': news.content,
                'ai_content': news.ai_content,
                'publish_date': news.publish_date.strftime('%Y-%m-%d') if news.publish_date else None,
                'create_time': news.create_time.strftime('%Y-%m-%d %H:%M:%S') if news.create_time else None
            }
            
            # 缓存数据
            cache.set(cache_key, news_detail, self.cache_timeout)
            
            return news_detail
            
        except CCTVNews.DoesNotExist:
            logger.warning(f"新闻{news_id}不存在")
            return None
        except Exception as e:
            logger.error(f"获取新闻{news_id}详情失败: {str(e)}")
            return None
    
    def create_news(self, news_data: Dict) -> Optional[Dict]:
        """
        创建新闻
        
        Args:
            news_data: 新闻数据
        
        Returns:
            创建的新闻信息
        """
        try:
            # 验证新闻内容
            title = sanitize_input(news_data.get('title', ''))
            content = sanitize_input(news_data.get('content', ''))
            
            errors = validate_news_content(title, content)
            if errors:
                logger.warning(f"新闻内容验证失败: {errors}")
                return {'errors': errors}
            
            # 创建新闻
            news = CCTVNews.objects.create(
                title=title,
                content=content,
                ai_content=sanitize_input(news_data.get('ai_content', '')),
                publish_date=datetime.fromisoformat(news_data['publish_date']) if news_data.get('publish_date') else datetime.now()
            )
            
            return {
                'id': news.id,
                'title': news.title,
                'content': news.content,
                'ai_content': news.ai_content,
                'summary': news.summary,
                'publish_date': news.publish_date.strftime('%Y-%m-%d') if news.publish_date else None,
                'create_time': news.create_time.strftime('%Y-%m-%d %H:%M:%S') if news.create_time else None
            }
            
        except Exception as e:
            logger.error(f"创建新闻失败: {str(e)}")
            return None
    
    def update_news(self, news_id: int, news_data: Dict) -> Optional[Dict]:
        """
        更新新闻
        
        Args:
            news_id: 新闻ID
            news_data: 更新的新闻数据
        
        Returns:
            更新后的新闻信息
        """
        try:
            news = CCTVNews.objects.get(id=news_id)
            
            # 验证并更新字段
            if 'title' in news_data:
                title = sanitize_input(news_data['title'])
                if title:
                    news.title = title
            
            if 'content' in news_data:
                content = sanitize_input(news_data['content'])
                if content:
                    news.content = content
            
            if 'ai_content' in news_data:
                news.ai_content = sanitize_input(news_data['ai_content'])
            
            if 'publish_date' in news_data:
                news.publish_date = datetime.fromisoformat(news_data['publish_date'])
            
            news.save()
            
            # 清除缓存
            cache.delete(f'news_detail_{news_id}')
            
            return {
                'id': news.id,
                'title': news.title,
                'content': news.content,
                'ai_content': news.ai_content,
                'summary': news.summary,
                'publish_date': news.publish_date.strftime('%Y-%m-%d') if news.publish_date else None,
                'create_time': news.create_time.strftime('%Y-%m-%d %H:%M:%S') if news.create_time else None
            }
            
        except CCTVNews.DoesNotExist:
            logger.warning(f"新闻{news_id}不存在")
            return None
        except Exception as e:
            logger.error(f"更新新闻{news_id}失败: {str(e)}")
            return None
    
    def delete_news(self, news_id: int) -> bool:
        """
        删除新闻
        
        Args:
            news_id: 新闻ID
        
        Returns:
            是否删除成功
        """
        try:
            news = CCTVNews.objects.get(id=news_id)
            news.delete()
            
            # 清除缓存
            cache.delete(f'news_detail_{news_id}')
            
            logger.info(f"删除新闻{news_id}成功")
            return True
            
        except CCTVNews.DoesNotExist:
            logger.warning(f"新闻{news_id}不存在")
            return False
        except Exception as e:
            logger.error(f"删除新闻{news_id}失败: {str(e)}")
            return False
    
    def get_latest_news(self, limit: int = 10) -> Optional[List[Dict]]:
        """
        获取最新新闻
        
        Args:
            limit: 数量限制
        
        Returns:
            最新新闻列表
        """
        cache_key = f'latest_news_{limit}'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存获取最新{limit}条新闻")
            return cached_data
        
        try:
            # 获取最新新闻
            latest_news = CCTVNews.objects.all().order_by('-publish_date')[:limit]
            
            news_list = []
            for news in latest_news:
                news_data = {
                    'id': news.id,
                    'title': news.title,
                    'content': news.content,
                    'ai_content': news.ai_content,
                    'summary': news.summary,
                    'publish_date': news.publish_date.strftime('%Y-%m-%d') if news.publish_date else None,
                    'create_time': news.create_time.strftime('%Y-%m-%d %H:%M:%S') if news.create_time else None
                }
                news_list.append(news_data)
            
            # 缓存数据
            cache.set(cache_key, news_list, self.cache_timeout)
            
            return news_list
            
        except Exception as e:
            logger.error(f"获取最新新闻失败: {str(e)}")
            return None
    
    def search_news(self, keyword: str, page: int = 1, limit: int = 20) -> Optional[List[Dict]]:
        """
        搜索新闻
        
        Args:
            keyword: 搜索关键词
            page: 页码
            limit: 每页数量
        
        Returns:
            搜索结果
        """
        try:
            keyword = sanitize_input(keyword)
            if not keyword:
                return []
            
            offset = (page - 1) * limit
            
            # 在标题和内容中搜索
            news_queryset = CCTVNews.objects.filter(
                Q(title__icontains=keyword) | Q(content__icontains=keyword)
            ).order_by('-publish_date')[offset:offset + limit]
            
            news_list = []
            for news in news_queryset:
                news_data = {
                    'id': news.id,
                    'title': news.title,
                    'content': news.content,
                    'ai_content': news.ai_content,
                    'summary': news.summary,
                    'publish_date': news.publish_date.strftime('%Y-%m-%d') if news.publish_date else None,
                    'create_time': news.create_time.strftime('%Y-%m-%d %H:%M:%S') if news.create_time else None,
                    'relevance_score': self._calculate_relevance(news, keyword)
                }
                news_list.append(news_data)
            
            # 按相关性排序
            news_list.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            return news_list
            
        except Exception as e:
            logger.error(f"搜索新闻失败: {str(e)}")
            return None
    
    def _calculate_relevance(self, news: CCTVNews, keyword: str) -> float:
        """
        计算新闻与关键词的相关性
        
        Args:
            news: 新闻对象
            keyword: 关键词
        
        Returns:
            相关性分数
        """
        score = 0.0
        
        # 标题匹配权重更高
        if keyword.lower() in news.title.lower():
            score += 2.0
        
        # 内容匹配
        content_matches = news.content.lower().count(keyword.lower())
        score += content_matches * 0.1
        
        # 发布时间越近分数越高
        if news.publish_date:
            days_ago = (datetime.now().date() - news.publish_date.date()).days
            score += max(0, 1.0 - days_ago / 30)  # 30天内的新闻有时间加分
        
        return score
    
    def get_news_statistics(self) -> Optional[Dict]:
        """
        获取新闻统计信息
        
        Returns:
            统计信息
        """
        cache_key = 'news_statistics'
        
        # 尝试从缓存获取
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info("从缓存获取新闻统计信息")
            return cached_data
        
        try:
            total_count = CCTVNews.objects.count()
            
            # 最近7天的新闻数量
            week_ago = datetime.now() - timedelta(days=7)
            recent_count = CCTVNews.objects.filter(publish_date__gte=week_ago).count()
            
            # 最新新闻
            latest_news = CCTVNews.objects.order_by('-publish_date').first()
            
            statistics = {
                'total_count': total_count,
                'recent_count': recent_count,
                'latest_news': {
                    'id': latest_news.id,
                    'title': latest_news.title,
                    'content': latest_news.content,
                    'ai_content': latest_news.ai_content,
                    'publish_date': latest_news.publish_date.strftime('%Y-%m-%d') if latest_news.publish_date else None,
                    'create_time': latest_news.create_time.strftime('%Y-%m-%d %H:%M:%S') if latest_news.create_time else None
                } if latest_news else None,
                'timestamp': datetime.now().isoformat()
            }
            
            # 缓存数据
            cache.set(cache_key, statistics, self.cache_timeout)
            
            return statistics
            
        except Exception as e:
            logger.error(f"获取新闻统计信息失败: {str(e)}")
            return None

# 全局服务实例
news_service = CCTVNewsService()