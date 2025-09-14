# -*- coding: utf-8 -*-
import json
import os
import re
import sys
import textwrap
import time
from datetime import datetime
import requests
from lxml import etree

# 设置环境编码
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 重新配置标准输出编码
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# 新闻联播相关配置
NEWS_URL = 'https://tv.cctv.com/lm/xwlb/'
cookies_path = "./cctv_cookies.json"
default_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}
DEBUG = False

# 设置Django环境
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置Django设置
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_data_service.settings')
import django
django.setup()


class Print:
    @staticmethod
    def red(text):
        print("\033[31m" + text + "\033[0m")

    @staticmethod
    def green(text):
        print("\033[32m" + text + "\033[0m")

    @staticmethod
    def yellow(text):
        print("\033[33m" + text + "\033[0m")

    @staticmethod
    def blue(text):
        print("\033[34m" + text + "\033[0m")

    @staticmethod
    def magenta(text):
        print("\033[35m" + text + "\033[0m")

    @staticmethod
    def cyan(text):
        print("\033[36m" + text + "\033[0m")

    @staticmethod
    def print2(*args, **kwargs):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{current_time}]", *args, **kwargs)


class Cookies:
    def __init__(self, cookie_path):
        self.cookie_path = cookie_path
        self.cookies = self._load_cookies()

    def _load_cookies(self):
        try:
            with open(self.cookie_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(e)
            Print.red("Failed to load cookies file")
            Print.red(e.args[0])
            return None

    def convert_to_http_header(self, cookies=None, filter_dict=None):
        if cookies:
            input_list = cookies
        elif self.cookies:
            input_list = self.cookies['cookies']
        else:
            return ''
        
        header_string = ''
        for item in input_list:
            if filter_dict and all(item.get(key) == value for key, value in filter_dict.items()):
                if 'name' in item and 'value' in item:
                    header_string += f"{item['name']}={item['value']};"
            elif not filter_dict:
                if 'name' in item and 'value' in item:
                    header_string += f"{item['name']}={item['value']};"
        return header_string


class HttpUtils:
    @staticmethod
    def get(url, params=None, headers=None, timeout=30):
        try:
            # 合并默认headers和自定义headers
            final_headers = default_headers.copy()
            if headers:
                final_headers.update(headers)
            
            response = requests.get(url=url, params=params, headers=final_headers, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            Print.print2(f'Error in GET request: {e}')
            return None
        except Exception as e:
            Print.print2(f'Error in GET request: {e}')
            return None

    @staticmethod
    def post(url, *args, **kwargs):
        try:
            # 合并默认headers
            if 'headers' in kwargs:
                final_headers = default_headers.copy()
                final_headers.update(kwargs['headers'])
                kwargs['headers'] = final_headers
            else:
                kwargs['headers'] = default_headers
            
            response = requests.post(url, *args, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            Print.print2(f'Error in POST request: {e}')
            return None
        except Exception as e:
            Print.print2(f'Error in POST request: {e}')
            return None

    @staticmethod
    def get_header_cookies(cookies_path):
        cookie = Cookies(cookies_path)
        if cookie.cookies:
            cookies = cookie.cookies['cookies']
            return cookie.convert_to_http_header(cookies=cookies)
        return ''

    @staticmethod
    def get_by_cookies(url, params=None, cookies_path=None):
        headers = {}
        if cookies_path and os.path.exists(cookies_path):
            cookie_header = HttpUtils.get_header_cookies(cookies_path)
            if cookie_header:
                headers['Cookie'] = cookie_header
        
        response = HttpUtils.get(url, headers=headers, params=params)
        return response

    @staticmethod
    def post_by_cookies(url, cookies_path, params=None, payload=None):
        headers = {}
        if cookies_path and os.path.exists(cookies_path):
            cookie_header = HttpUtils.get_header_cookies(cookies_path)
            if cookie_header:
                headers['Cookie'] = cookie_header
        
        response = HttpUtils.post(url=url, headers=headers, params=params, json=payload)
        return response


def create_table():
    """创建数据表 - 使用Django的迁移系统，此函数已不再需要"""
    Print.print2("Django会自动创建和管理数据表，无需手动创建")


def print_disclaimer():
    message = """
    ######################################################################################################################
                                                   免责声明                                                               
    此工具仅限于学习研究，用户需自己承担因使用此工具而导致的所有法律和相关责任！作者不承担任何法律责任！               
    ######################################################################################################################
    """
    print(textwrap.dedent(message))
    while True:
        user_input = input("如果您同意本协议, 请输入Y继续: (y/n) ")
        if user_input.lower() == "y":
            return True
        elif user_input.lower() == "n":
            sys.exit(0)


def get_news_list(url):
    """获取新闻联播新闻列表 - 使用requests替代playwright"""
    final_result = []
    
    try:
        # 使用requests获取页面内容
        response = HttpUtils.get(url)
        if not response:
            Print.print2("获取新闻列表页面失败")
            return final_result
        
        # 解析HTML
        tree = etree.HTML(response.content)
        
        # 查找新闻列表元素
        news_elements = tree.xpath('//div[@class="con"]/ul/li')
        
        for news in news_elements:
            try:
                # 获取链接和标题
                link_elements = news.xpath('.//a[@href]')
                if not link_elements:
                    continue
                    
                news_url = link_elements[0].get('href')
                if not news_url:
                    continue
                
                # 从title属性获取完整标题，如果没有则从链接文本获取
                title = link_elements[0].get('title', '').strip()
                if not title:
                    # 从链接文本获取标题，去除"完整版"前缀
                    title_text = news.xpath('.//a/text()')
                    if title_text:
                        title = title_text[0].strip()
                        # 去除"完整版"前缀
                        if title.startswith('完整版'):
                            title = title[3:].strip()
                        elif '完整版' in title:
                            title = title.replace('完整版', '').strip()
                
                # 从URL中提取发布日期
                publish_date = ""
                if '/2025/' in news_url:
                    date_match = re.search(r'/2025/(\d{2})/(\d{2})/', news_url)
                    if date_match:
                        month, day = date_match.groups()
                        publish_date = f"2025-{month}-{day}"
                
                final_result.append({
                    "title": title,
                    "news_url": news_url,
                    "publish_date": publish_date
                })
            except Exception as e:
                Print.print2(f"解析新闻列表项时出错: {e}")
                continue
        
    except Exception as e:
        Print.print2(f"获取新闻列表时出错: {e}")
    
    return final_result


def get_news_detail(url):
    """获取单条新闻的详细内容 - 使用requests替代playwright"""
    try:
        # 使用requests获取页面内容
        response = HttpUtils.get(url)
        if not response:
            Print.print2(f"获取新闻详情页面失败: {url}")
            return None
        
        # 解析HTML
        tree = etree.HTML(response.content)
        
        # 获取新闻标题 - 从内容区域第一个p标签的文本中提取标题
        title = ""
        content_area = tree.xpath('//div[@class="content_area" and @id="content_area"]')
        if content_area:
            first_p = content_area[0].xpath('.//p[1]//text()')
            if first_p:
                title_text = ''.join(first_p).strip()
                # 从"央视网消息（新闻联播）："后面提取标题
                if '新闻联播）：' in title_text:
                    title = title_text.split('新闻联播）：')[1].split('。')[0].strip()
                else:
                    title = title_text
        
        # 获取发布日期 - 从URL中提取
        publish_date = ""
        if '/2025/' in url:
            date_match = re.search(r'/2025/(\d{2})/(\d{2})/', url)
            if date_match:
                month, day = date_match.groups()
                publish_date = f"2025-{month}-{day}"
        
        # 获取新闻内容 - 从content_area中的所有p标签
        content = ""
        if content_area:
            content_elements = content_area[0].xpath('.//p')
            content_parts = []
            for p in content_elements:
                text_parts = p.xpath('.//text()')
                if text_parts:
                    paragraph = ''.join(text_parts).strip()
                    if paragraph:
                        content_parts.append(paragraph)
            content = '\n'.join(content_parts)
        
        return {
            "title": title,
            "content": content,
            "publish_date": publish_date
        }
    except Exception as e:
        Print.print2(f"获取新闻详情时出错: {e}")
        return None


def save_combined_news_to_db(all_news_content, publish_date):
    """将合并后的新闻保存到数据库，使用Django的CCTVNews模型（通过专用线程执行，避免异步事件循环冲突）"""
    try:
        from cctv_news.models import CCTVNews
        from django.db import close_old_connections
        import threading

        exception_container = []

        def do_save():
            # 确保线程独立数据库连接
            close_old_connections()
            try:
                # 检查是否已存在相同publish_date的新闻
                if CCTVNews.objects.filter(publish_date=publish_date).exists():
                    print(f"⚠️ {publish_date} 的新闻联播内容已存在，跳过保存")
                    return
                # 创建新的CCTVNews对象并保存
                news = CCTVNews(
                    title=f"{publish_date}新闻联播",
                    content=all_news_content,
                    publish_date=publish_date
                )
                news.save()
                print(f"✅ 已保存 {publish_date} 的新闻联播内容到数据库")
            except Exception as e:
                exception_container.append(e)
            finally:
                # 结束前清理旧连接
                close_old_connections()

        t = threading.Thread(target=do_save, daemon=True)
        t.start()
        t.join()

        if exception_container:
            raise exception_container[0]

    except Exception as e:
        Print.print2(f"❌ 保存数据失败: {e}")


def main():
    """主函数 - 使用requests替代playwright"""
    # print_disclaimer()
    
    # 初始化数据库
    # create_table()
    
    try:
        Print.print2("开始获取新闻联播新闻列表...")
        news_list = get_news_list(NEWS_URL)
        Print.print2(f"获取到 {len(news_list)} 条新闻")
        
        if not news_list:
            Print.print2("未获取到任何新闻")
            return
        
        # 获取所有新闻的详细内容
        all_news_content = []
        publish_date = None
        
        Print.print2("开始获取新闻详细内容...")
        for news in news_list:
            Print.print2(f"正在获取: {news['title']}")
            detail = get_news_detail(news['news_url'])
            if detail and detail['content']:
                all_news_content.append(detail['content'])
                if not publish_date and detail['publish_date']:
                    publish_date = detail['publish_date']
                Print.print2(f"已获取: {news['title']}")
            else:
                Print.print2(f"获取详情失败: {news['title']}")
            
            # 避免请求过快
            time.sleep(1)
        
        # 保存合并后的内容到数据库
        if all_news_content and publish_date:
            combined_content = '\n\n'.join(all_news_content)
            Print.print2(f"合并内容长度: {len(combined_content)} 字符")
            save_combined_news_to_db(combined_content, publish_date)
            Print.print2(f"成功保存 {len(all_news_content)} 条新闻的合并内容")
        else:
            Print.print2("没有可保存的内容")
        
    except Exception as e:
        Print.print2(f"执行过程中出错: {e}")


if __name__ == "__main__":
    main()