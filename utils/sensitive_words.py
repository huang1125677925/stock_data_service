#!/usr/bin/env python3
"""
敏感词过滤模块
提供敏感词检测和替换功能
"""

import re
from typing import List, Dict, Set

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

# 全局过滤器实例
filter_instance = SensitiveWordFilter()

def filter_sensitive_words(text: str, replacement: str = '*') -> str:
    """快速过滤函数"""
    return filter_instance.filter_text(text, replacement)

def test_filter():
    """测试过滤功能"""
    test_text = "这是一条包含机密信息的消息，涉及领导人和内部文件"
    
    print("原始文本:", test_text)
    print("过滤后:", filter_sensitive_words(test_text))
    print("检测敏感词:", filter_instance.has_sensitive_words(test_text))
    print("找到的敏感词:", filter_instance.find_sensitive_words(test_text))

if __name__ == "__main__":
    test_filter()