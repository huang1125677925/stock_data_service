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
        self.api_key = "sk-901c17c669a241f098b25144957667ec"
        self.base_url = "https://api.deepseek.com/v1"
        
        # 支持的模型配置
        self.models = {
                'url': f'{self.base_url}/chat/completions',
                'headers': {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                'model_name': 'deepseek-v4-flash'
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
                {"role": "system", "content": '你是一个专业的财经分析师，擅长从新闻联播等官方媒体中提取经济相关信息，分析对股市的影响。请基于中国A股市场，仅从以下行业列表中选择利好行业并给出原因。行业列表：【航空机场 铁路公路 物流行业 水泥建材 工程建设 公用事业 电力行业 交运设备 农牧饲渔 纺织服装 煤炭行业 食品饮料 家用轻工 互联网服务 通信设备 航运港口 房地产开发 塑料制品 家电行业 电网设备 仪器仪表 电子元件 石油行业 化学制药 造纸印刷 化纤行业 证券 保险 银行 装修建材 酿酒行业 有色金属 钢铁行业 航天航空 汽车零部件 商业百货 贸易行业 旅游酒店 文化传媒 化学制品 综合行业 通用设备 玻璃玻纤 装修装饰 工程咨询服务 医疗服务 环保行业 船舶制造 农药兽药 化肥行业 贵金属 包装材料 珠宝首饰 计算机设备 通信服务 软件开发 多元金融 工程机械 教育 专用设备 能源金属 汽车服务 采掘行业 橡胶制品 化学原料 非金属材料 小金属 燃气 汽车整车 电机 光伏设备 风电设备 电池 电源设备 美容护理 半导体 消费电子 光学光电子 电子化学品 中药 医疗器械 医药商业 专业服务 生物制品 房地产服务 游戏】。输出要求：仅输出一个JSON对象，不要附加任何说明文字；键为行业名称（必须与列表完全一致），值为简短中文原因。例如：{"中药": "国家大力发展该行业，政策支持", "半导体": "科技导向等等"}；如未发现利好行业，返回{}。'},
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
                latest_news_list = CCTVNews.objects.filter(ai_content__isnull=True).order_by('-publish_date')[:7]
                
                if not latest_news_list:
                    print("没有需要分析的新闻")
                    return
                
                analyzer = NewsAnalyzer()
                
                # 遍历所有新闻
                for latest_news in latest_news_list:
                    if latest_news.ai_content:
                        continue
                    test_news = latest_news.content
                    
                    # 过滤敏感词
                    test_news = SensitiveWordFilter().filter_text(test_news)
                    
                    # 分析新闻
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
