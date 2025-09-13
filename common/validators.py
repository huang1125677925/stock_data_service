#!/usr/bin/env python3
"""
Django数据验证工具
提供常用的数据验证函数
"""

import re
from typing import List, Optional
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from datetime import datetime

def validate_stock_symbol(symbol: str) -> bool:
    """
    验证股票代码格式
    
    Args:
        symbol: 股票代码
    
    Returns:
        是否有效
    """
    if not symbol or not isinstance(symbol, str):
        return False
    
    # 支持A股和美股格式
    pattern = r'^[A-Z]{1,6}$|^\d{6}$'
    return bool(re.match(pattern, symbol.upper()))

def validate_date_range(start_date: str, end_date: str) -> bool:
    """
    验证日期范围
    
    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
    
    Returns:
        是否有效
    """
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        return start <= end
    except ValueError:
        return False

def validate_period(period: str) -> bool:
    """
    验证时间周期
    
    Args:
        period: 时间周期
    
    Returns:
        是否有效
    """
    valid_periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max']
    return period in valid_periods

def validate_interval(interval: str) -> bool:
    """
    验证时间间隔
    
    Args:
        interval: 时间间隔
    
    Returns:
        是否有效
    """
    valid_intervals = ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo']
    return interval in valid_intervals

def validate_symbols_list(symbols: List[str], max_count: int = 100) -> bool:
    """
    验证股票代码列表
    
    Args:
        symbols: 股票代码列表
        max_count: 最大数量限制
    
    Returns:
        是否有效
    """
    if not isinstance(symbols, list):
        return False
    
    if len(symbols) > max_count:
        return False
    
    return all(validate_stock_symbol(symbol) for symbol in symbols)

def sanitize_input(input_str: str) -> str:
    """
    清理输入字符串，防止注入攻击
    
    Args:
        input_str: 输入字符串
    
    Returns:
        清理后的字符串
    """
    if not isinstance(input_str, str):
        return str(input_str)
    
    # 移除潜在的危险字符
    dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '|', '`']
    cleaned = input_str
    
    for char in dangerous_chars:
        cleaned = cleaned.replace(char, '')
    
    return cleaned.strip()

def validate_pagination_params(limit: int, offset: int) -> tuple:
    """
    验证分页参数
    
    Args:
        limit: 每页数量，可以为None
        offset: 偏移量
    
    Returns:
        验证后的参数元组 (limit, offset)
    """
    # 限制每页最大数量
    max_limit = 1000
    min_limit = 1
    
    # 处理limit为None的情况
    if limit is None:
        # 如果limit为None，保持为None，表示不限制
        pass
    elif limit > max_limit:
        limit = max_limit
    elif limit < min_limit:
        limit = min_limit
    
    if offset < 0:
        offset = 0
    
    return limit, offset

def validate_chinese_text(text: str) -> bool:
    """
    验证是否包含中文字符
    
    Args:
        text: 待验证文本
    
    Returns:
        是否包含中文
    """
    if not text:
        return False
    
    chinese_pattern = r'[\u4e00-\u9fff]+'
    return bool(re.search(chinese_pattern, text))

def validate_news_content(title: str, content: str) -> List[str]:
    """
    验证新闻内容
    
    Args:
        title: 新闻标题
        content: 新闻内容
    
    Returns:
        错误信息列表
    """
    errors = []
    
    if not title or len(title.strip()) == 0:
        errors.append('新闻标题不能为空')
    elif len(title) > 200:
        errors.append('新闻标题不能超过200个字符')
    
    if not content or len(content.strip()) == 0:
        errors.append('新闻内容不能为空')
    elif len(content) < 10:
        errors.append('新闻内容不能少于10个字符')
    elif len(content) > 50000:
        errors.append('新闻内容不能超过50000个字符')
    
    return errors

class ValidationError(Exception):
    """自定义验证错误"""
    
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)

# Django表单验证器
def stock_code_validator(value):
    """
    Django表单股票代码验证器
    
    Args:
        value: 股票代码
    
    Raises:
        DjangoValidationError: 验证失败时抛出
    """
    if not validate_stock_symbol(value):
        raise DjangoValidationError('无效的股票代码格式')

def chinese_text_validator(value):
    """
    Django表单中文文本验证器
    
    Args:
        value: 文本内容
    
    Raises:
        DjangoValidationError: 验证失败时抛出
    """
    if not validate_chinese_text(value):
        raise DjangoValidationError('内容必须包含中文字符')