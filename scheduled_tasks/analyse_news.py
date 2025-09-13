"""
新闻联播新闻分析器 - 使用大模型分析新闻内容
提供经济利好行业和股票推荐
"""
import requests
import logging
import sys, os
import re
from typing import List, Dict, Set

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsAnalyzer:
    """新闻大模型分析器"""
    
    def __init__(self):
        """
        初始化分析器
        
        Args:
            api_key: API密钥，如果为None则从环境变量或配置文件读取
            base_url: API基础URL
            config_path: 配置文件路径
        """
        self.api_key = "sk-6dbcf817918149cb96cbbd933dcc80bb"
        self.base_url = "https://api.deepseek.com/v1"
        
        # 支持的模型配置
        self.models = {
                'url': f'{self.base_url}/chat/completions',
                'headers': {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                'model_name': 'deepseek-chat'
        }
    
    def _build_prompt(self, news_content: str) -> str:
        """构建分析提示词"""
        return f"""请分析以下新闻联播内容，从经济角度判断利好的行业
新闻内容：
{news_content}
"""
    
    def analyze_news(self, news_content: str) -> str:
        """
        分析新闻内容
        Args:
            news_content: 新闻内容文本
        Returns:
            str: 分析结果
        """
        
        payload = {
            "model": self.models['model_name'],
            "messages": [
                {"role": "system", "content": "你是一个专业的财经分析师，擅长从新闻联播等官方媒体中提取经济相关信息，分析对股市的影响。请基于中国A股市场给出专业建议。"},
                {"role": "user", "content": self._build_prompt(news_content)}
            ],
            "temperature": 0.3,
        }
        
        try:
            response = requests.post(
                self.models['url'],
                headers=self.models['headers'],
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            return content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API请求失败: {e}")
            raise RuntimeError(f"大模型API调用失败: {e}")
        except Exception as e:
            logger.error(f"解析响应失败: {e}")
            raise RuntimeError(f"分析结果解析失败: {e}")



class SensitiveWordFilter:
    """敏感词过滤器"""
    
    def __init__(self, config_file: str = None):
        self.sensitive_words = []
        self.compiled_patterns = {}
        
        # 优先从配置文件加载，否则使用默认词库
        if config_file and self.load_from_file(config_file):
            pass
        else:
            # 尝试从默认配置文件加载
            if not self.load_from_file('sensitive_words.txt'):
                self.sensitive_words = self._load_default_words()
        
        self._compile_patterns()
    
    def _load_default_words(self) -> List[str]:
        """加载默认敏感词"""
        return [
            # 政治敏感词
            '领导人', '政治局', '常委', '总理', '主席', '总书记', '习近平',
            '部长', '局长', '主任', '委员', '书记',
            
            # 负面事件词汇
            '暴乱', '抗议', '示威', '罢工', '冲突', '暴力',
            '骚乱', '动乱', '政变', '革命', '叛乱', '颠覆',
            
            # 敏感机构
            '中南海', '国务院', '中央军委', '公安部', '国安部',
            
            # 敏感信息
            '机密', '绝密', '内部文件', '未公开', '保密',
            '内部消息', '小道消息', '内幕', '爆料',
            
            # 宗教相关
            '邪教', '异端', '极端组织', '恐怖组织',
            
            # 社会敏感
            '种族歧视', '性别歧视', '地域歧视', '仇恨言论',
            
            # 其他
            '腐败', '贪污', '受贿', '滥用职权', '渎职'
        ]
    
    def add_words(self, words: List[str]):
        """添加新的敏感词"""
        self.sensitive_words.extend(words)
        self.sensitive_words = list(set(self.sensitive_words))  # 去重
        self._compile_patterns()
    
    def remove_words(self, words: List[str]):
        """移除敏感词"""
        for word in words:
            if word in self.sensitive_words:
                self.sensitive_words.remove(word)
        self._compile_patterns()
    
    def _compile_patterns(self):
        """编译正则表达式模式"""
        self.compiled_patterns = {}
        for word in self.sensitive_words:
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            self.compiled_patterns[word] = pattern
    
    def filter_text(self, text: str, replacement: str = '*') -> str:
        """
        过滤文本中的敏感词
        
        Args:
            text: 要过滤的文本
            replacement: 替换字符，默认为'*'
            
        Returns:
            过滤后的文本
        """
        filtered_text = text
        
        for word, pattern in self.compiled_patterns.items():
            # 用等长的替换字符替换敏感词
            replacement_str = replacement * len(word)
            filtered_text = pattern.sub(replacement_str, filtered_text)
        
        return filtered_text
    
    def has_sensitive_words(self, text: str) -> bool:
        """检测文本是否包含敏感词"""
        for word, pattern in self.compiled_patterns.items():
            if pattern.search(text):
                return True
        return False
    
    def find_sensitive_words(self, text: str) -> Dict[str, List[int]]:
        """找出文本中的所有敏感词及其位置"""
        found_words = {}
        
        for word, pattern in self.compiled_patterns.items():
            matches = list(pattern.finditer(text))
            if matches:
                positions = [match.start() for match in matches]
                found_words[word] = positions
        
        return found_words
    
    def load_from_file(self, filepath: str):
        """从文件加载敏感词"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                words = [line.strip() for line in f if line.strip()]
                self.add_words(words)
        except FileNotFoundError:
            print(f"敏感词文件 {filepath} 不存在，使用默认词库")
    
    def save_to_file(self, filepath: str):
        """保存敏感词到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            for word in sorted(self.sensitive_words):
                f.write(word + '\n')

def analyze_and_save_latest_news():
    """
    分析最新的新闻并保存结果到数据库（线程安全方式）
    """
    try:
        from cctv_news.models import CCTVNews
        from django.db import close_old_connections
        import threading
        import sys

        exception_container = []

        def do_analyze_and_save():
            # 确保线程独立数据库连接
            close_old_connections()
            try:
                # 从数据库中获取最新的新闻
                latest_news_list = CCTVNews.objects.filter(ai_content__isnull=True).order_by('-publish_date')[:1]
                
                if not latest_news_list:
                    print("没有需要分析的新闻")
                    return
                    
                latest_news = latest_news_list[0]
                test_news = latest_news.content
                
                # 过滤敏感词
                test_news = SensitiveWordFilter().filter_text(test_news)
                
                # 分析新闻
                analyzer = NewsAnalyzer()
                result = analyzer.analyze_news(test_news)
                
                # 保存分析结果
                latest_news.ai_content = result
                latest_news.save()
                
                print(f"✅ 已成功分析并保存新闻: {latest_news.title}")
            except Exception as e:
                exception_container.append(e)
            finally:
                # 结束前清理旧连接
                close_old_connections()

        # 在独立线程中执行数据库操作
        t = threading.Thread(target=do_analyze_and_save, daemon=True)
        t.start()
        t.join()

        if exception_container:
            raise exception_container[0]

    except Exception as e:
        print(f"❌ 分析新闻失败: {e}")


if __name__ == "__main__":
    # 简单的测试示例
    analyze_and_save_latest_news()