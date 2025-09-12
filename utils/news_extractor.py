#!/usr/bin/env python3
"""
新闻联播文字内容获取器
用于获取指定日期的新闻联播文字版内容
"""

import requests
from bs4 import BeautifulSoup
import datetime
import re
import json
from typing import Dict, List, Optional

class NewsExtractor:
    """新闻联播文字内容提取器"""
    
    def __init__(self):
        self.base_url = "http://mrxwlb.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'http://mrxwlb.com/',
        }
        self.cookies = {
            'security_session_verify': '70354a6071922de17ed3e03772b40ba8'
        }
    
    def format_date_url(self, date: datetime.date) -> str:
        """格式化日期为URL格式，使用用户提供的成功格式"""
        year = date.strftime('%Y')
        month = date.strftime('%m')
        day = date.strftime('%d')
        
        # 使用用户提供的成功URL格式
        url = f"{self.base_url}/{year}/{month}/{day}/{year}%e5%b9%b4{month}%e6%9c%88{day}%e6%97%a5%e6%96%b0%e9%97%bb%e8%81%94%e6%92%ad%e6%96%87%e5%ad%97%e7%89%88/"
        
        return url
    
    def get_news_content(self, date: datetime.date) -> Dict[str, any]:
        """获取指定日期的新闻联播内容"""
        url = self.format_date_url(date)
        
        try:
            response = requests.get(url, headers=self.headers, cookies=self.cookies, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')

            # 提取标题
            title = soup.find('title')
            title_text = title.get_text().strip() if title else f"{date.strftime('%Y年%m月%d日')}新闻联播"

            # 提取主要内容 - 针对mrxwlb.com的结构优化
            content_div = None
            for selector in ['.entry-content', 'article', 'main', '.content', '.post-content']:
                content_div = soup.select_one(selector)
                if content_div:
                    break

            if not content_div:
                content_div = soup.find('body')

            content_text = self.extract_text_from_html(content_div)
            
            # 提取新闻条目
            news_items = self.parse_news_items(content_text)
            
            return {
                'date': date.strftime('%Y-%m-%d'),
                'title': title_text,
                'url': url,
                'content': content_text,
                'news_items': news_items,
                'status': 'success'
            }
            
        except requests.RequestException as e:
            return {
                'date': date.strftime('%Y-%m-%d'),
                'title': f"{date.strftime('%Y年%m月%d日')}新闻联播",
                'url': url,
                'content': '',
                'news_items': [],
                'status': 'error',
                'error': str(e)
            }
    
    def extract_text_from_html(self, content_div) -> str:
        """从HTML中提取纯文本"""
        if not content_div:
            return ""
        
        # 移除脚本和样式标签
        for script in content_div(["script", "style"]):
            script.decompose()
        
        # 获取文本并清理
        text = content_div.get_text()
        
        # 清理空白字符
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        cleaned_text = '\n'.join(lines)
        
        return cleaned_text
    
    def parse_news_items(self, content: str) -> List[Dict[str, str]]:
        """解析新闻内容为条目"""
        if not content:
            return []
        
        # 按段落分割
        paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
        
        news_items = []
        current_item = ""
        
        for para in paragraphs:
            # 识别新闻条目（通常以时间或特定关键词开头）
            if re.match(r'^\d{2}:\d{2}', para) or re.match(r'^【.*?】', para):
                if current_item:
                    news_items.append({
                        'title': current_item.strip(),
                        'content': ''
                    })
                current_item = para
            else:
                if current_item:
                    current_item += " " + para
        
        if current_item:
            news_items.append({
                'title': current_item.strip(),
                'content': ''
            })
        
        return news_items
    
    def get_latest_news(self) -> Dict[str, any]:
        """获取最新的新闻联播内容"""
        today = datetime.date.today()
        return self.get_news_content(today)
    
    def get_news_by_date_str(self, date_str: str) -> Dict[str, any]:
        """通过日期字符串获取新闻联播"""
        try:
            date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            return self.get_news_content(date)
        except ValueError:
            return {
                'status': 'error',
                'error': '日期格式错误，请使用YYYY-MM-DD格式'
            }

def main():
    """主函数示例"""
    extractor = NewsExtractor()
    
    # 获取今天的新闻联播
    print("正在获取今天的新闻联播内容...")
    news = extractor.get_latest_news()
    
    if news['status'] == 'success':
        print(f"\n📺 {news['title']}")
        print(f"🔗 URL: {news['url']}")
        print("=" * 80)
        print("新闻内容:")
        print(news['content'])
        
        if news['news_items']:
            print("\n📋 新闻条目:")
            for i, item in enumerate(news['news_items'], 1):
                print(f"{i}. {item['title']}")
    else:
        print(f"❌ 获取失败: {news['error']}")

if __name__ == "__main__":
    main()