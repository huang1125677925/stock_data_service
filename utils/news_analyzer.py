"""
新闻联播新闻分析器 - 使用大模型分析新闻内容
提供经济利好行业和股票推荐
"""
import requests
import logging
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.cctv_news_model import CCTVNewsModel
from utils.sensitive_words import SensitiveWordFilter

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

if __name__ == "__main__":
    # 简单的测试示例
    try:
        analyzer = NewsAnalyzer()
        
        # 从数据库中获取最新的新闻
        latest_news_list = CCTVNewsModel.objects.get_latest_news(limit=1)
        if latest_news_list:
            latest_news = latest_news_list[0]  # get_latest_news返回列表，取第一个元素
            if latest_news.ai_content:
                print("已经分析，无须再分析")
                sys.exit(0)
            test_news = latest_news.content
        else:
            print("没有最新的新闻")
            sys.exit(0)

        test_news = SensitiveWordFilter().filter_text(test_news)
        
        result = analyzer.analyze_news(test_news)

        latest_news.ai_content = result
        latest_news.save()
        
        print(result)
        
    except Exception as e:
        print(f"错误: {e}")