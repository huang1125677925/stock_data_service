#!/usr/bin/env python3
"""
Django敏感词过滤工具
提供敏感词检测和过滤功能
"""

import re
from typing import List, Set, Optional
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class SensitiveWordFilter:
    """敏感词过滤器"""
    
    def __init__(self):
        self.sensitive_words: Set[str] = set()
        self.load_default_words()
        
        # 从设置中加载自定义敏感词
        custom_words = getattr(settings, 'CUSTOM_SENSITIVE_WORDS', [])
        if custom_words:
            self.add_words(custom_words)
    
    def load_default_words(self):
        """加载默认敏感词库"""
        default_words = [
            # 政治敏感词
            '政治敏感词1', '政治敏感词2',
            # 暴力相关
            '暴力', '恐怖', '杀害',
            # 色情相关
            '色情', '淫秽', '黄色',
            # 赌博相关
            '赌博', '博彩', '彩票诈骗',
            # 诈骗相关
            '诈骗', '骗钱', '传销',
            # 违法药品
            '毒品', '大麻', '冰毒',
            # 其他违法内容
            '枪支', '爆炸物', '假证'
        ]
        
        self.sensitive_words.update(default_words)
        logger.info(f"加载默认敏感词库，共{len(default_words)}个词")
    
    def add_words(self, words: List[str]):
        """添加敏感词
        
        Args:
            words: 敏感词列表
        """
        self.sensitive_words.update(words)
        logger.info(f"添加{len(words)}个敏感词")
    
    def remove_words(self, words: List[str]):
        """移除敏感词
        
        Args:
            words: 要移除的敏感词列表
        """
        for word in words:
            self.sensitive_words.discard(word)
        logger.info(f"移除{len(words)}个敏感词")
    
    def contains_sensitive_word(self, text: str) -> bool:
        """检查文本是否包含敏感词
        
        Args:
            text: 待检查的文本
        
        Returns:
            是否包含敏感词
        """
        if not text:
            return False
        
        text_lower = text.lower()
        
        for word in self.sensitive_words:
            if word.lower() in text_lower:
                return True
        
        return False
    
    def find_sensitive_words(self, text: str) -> List[str]:
        """查找文本中的敏感词
        
        Args:
            text: 待检查的文本
        
        Returns:
            找到的敏感词列表
        """
        if not text:
            return []
        
        found_words = []
        text_lower = text.lower()
        
        for word in self.sensitive_words:
            if word.lower() in text_lower:
                found_words.append(word)
        
        return found_words
    
    def filter_text(self, text: str, replacement: str = '*') -> str:
        """过滤文本中的敏感词
        
        Args:
            text: 待过滤的文本
            replacement: 替换字符
        
        Returns:
            过滤后的文本
        """
        if not text:
            return text
        
        filtered_text = text
        
        for word in self.sensitive_words:
            if word.lower() in text.lower():
                # 使用正则表达式进行不区分大小写的替换
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                filtered_text = pattern.sub(replacement * len(word), filtered_text)
        
        return filtered_text
    
    def validate_content(self, content: str, strict: bool = False) -> dict:
        """验证内容是否符合规范
        
        Args:
            content: 待验证的内容
            strict: 是否严格模式（严格模式下发现敏感词直接拒绝）
        
        Returns:
            验证结果字典
        """
        result = {
            'is_valid': True,
            'sensitive_words': [],
            'filtered_content': content,
            'message': '内容验证通过'
        }
        
        if not content:
            return result
        
        # 查找敏感词
        found_words = self.find_sensitive_words(content)
        
        if found_words:
            result['sensitive_words'] = found_words
            
            if strict:
                result['is_valid'] = False
                result['message'] = f'内容包含敏感词: {", ".join(found_words)}'
            else:
                result['filtered_content'] = self.filter_text(content)
                result['message'] = f'内容包含敏感词已过滤: {", ".join(found_words)}'
        
        return result
    
    def get_word_count(self) -> int:
        """获取敏感词数量
        
        Returns:
            敏感词数量
        """
        return len(self.sensitive_words)
    
    def export_words(self) -> List[str]:
        """导出敏感词列表
        
        Returns:
            敏感词列表
        """
        return list(self.sensitive_words)
    
    def import_words_from_file(self, file_path: str):
        """从文件导入敏感词
        
        Args:
            file_path: 敏感词文件路径（每行一个词）
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                words = [line.strip() for line in f if line.strip()]
                self.add_words(words)
                logger.info(f"从文件{file_path}导入{len(words)}个敏感词")
        except FileNotFoundError:
            logger.error(f"敏感词文件{file_path}不存在")
        except Exception as e:
            logger.error(f"导入敏感词文件失败: {str(e)}")

# 全局敏感词过滤器实例
sensitive_filter = SensitiveWordFilter()

# 便捷函数
def check_sensitive_words(text: str) -> bool:
    """检查文本是否包含敏感词
    
    Args:
        text: 待检查的文本
    
    Returns:
        是否包含敏感词
    """
    return sensitive_filter.contains_sensitive_word(text)

def filter_sensitive_words(text: str, replacement: str = '*') -> str:
    """过滤文本中的敏感词
    
    Args:
        text: 待过滤的文本
        replacement: 替换字符
    
    Returns:
        过滤后的文本
    """
    return sensitive_filter.filter_text(text, replacement)

def validate_text_content(content: str, strict: bool = False) -> dict:
    """验证文本内容
    
    Args:
        content: 待验证的内容
        strict: 是否严格模式
    
    Returns:
        验证结果
    """
    return sensitive_filter.validate_content(content, strict)