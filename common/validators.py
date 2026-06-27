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

def _infer_stock_market(code: str) -> Optional[str]:
    """
    功能：根据 A 股数字代码推断交易所后缀。
    参数：
    - code(str): 六位数字股票代码。
    返回值：
    - Optional[str]: 识别成功时返回 `SH`、`SZ` 或 `BJ`，否则返回 None。
    异常情况：
    - 本函数不抛出异常；当输入为空、格式不合法或无法识别时返回 None。
    """
    if not code or not re.fullmatch(r'\d{6}', code):
        return None

    if code.startswith(('6', '9')):
        return 'SH'
    if code.startswith(('0', '2', '3')):
        return 'SZ'
    if code.startswith(('4', '8')):
        return 'BJ'
    return None

def normalize_stock_symbol(symbol: str, output_format: str = 'plain') -> Optional[str]:
    """
    功能：规范化股票代码，兼容 plain、前缀式与 Tushare ts_code 格式。
    参数：
    - symbol(str): 原始股票代码，支持 `600909`、`sh600909`、`600909.SH` 等格式。
    - output_format(str): 输出格式，`plain` 返回纯六位代码，`ts` 返回 Tushare `ts_code` 格式。
    返回值：
    - Optional[str]: 规范化后的股票代码；无法识别时返回 None。
    异常情况：
    - 当 `output_format` 非法时抛出 ValueError。
    - 其他非法输入不抛出异常，统一返回 None。
    """
    if output_format not in {'plain', 'ts'}:
        raise ValueError(f'不支持的股票代码输出格式: {output_format}')

    if not symbol or not isinstance(symbol, str):
        return None

    normalized = symbol.strip().upper()
    if not normalized:
        return None

    ts_match = re.fullmatch(r'(\d{6})\.(SH|SZ|BJ)', normalized)
    if ts_match:
        code, market = ts_match.groups()
        return code if output_format == 'plain' else f'{code}.{market}'

    prefixed_match = re.fullmatch(r'(SH|SZ|BJ)(\d{6})', normalized)
    if prefixed_match:
        market, code = prefixed_match.groups()
        return code if output_format == 'plain' else f'{code}.{market}'

    if re.fullmatch(r'\d{6}', normalized):
        market = _infer_stock_market(normalized)
        if market is None:
            return None
        return normalized if output_format == 'plain' else f'{normalized}.{market}'

    if re.fullmatch(r'[A-Z]{1,6}', normalized):
        return normalized

    return None

def validate_stock_symbol(symbol: str, allow_market_suffix: bool = False) -> bool:
    """
    功能：验证股票代码格式，并按需放行 Tushare `ts_code` 格式。
    参数：
    - symbol(str): 待验证的股票代码。
    - allow_market_suffix(bool): 是否允许 `600909.SH` 这类带交易所后缀的格式。
    返回值：
    - bool: 股票代码格式是否有效。
    异常情况：
    - 本函数不抛出异常；任意非法输入均返回 False。
    """
    if not symbol or not isinstance(symbol, str):
        return False

    normalized = symbol.strip().upper()
    if not normalized:
        return False

    if allow_market_suffix and normalize_stock_symbol(normalized, output_format='ts'):
        return True

    # 默认保持原有兼容性，仅接受纯字母代码、六位数字代码与前缀式代码。
    pattern = r'^[A-Z]{1,6}$|^\d{6}$|^(SH|SZ|BJ)\d{6}$'
    return bool(re.fullmatch(pattern, normalized))

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
