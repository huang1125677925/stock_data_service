#!/usr/bin/env python3
"""
配置文件
集中管理所有配置项
"""

import os
from pathlib import Path

class Config:
    """基础配置类"""
    
    # 应用配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-this'
    
    # Flask配置
    JSON_AS_ASCII = False
    JSON_SORT_KEYS = False
    
    # 数据库配置（预留）
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///stock_data.db'
    
    # Redis配置（预留）
    # REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # 缓存配置
    CACHE_TYPE = os.environ.get('CACHE_TYPE') or 'simple'
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', 300))
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE') or 'logs/app.log'
    
    # API配置
    API_RATE_LIMIT = os.environ.get('API_RATE_LIMIT') or '100/hour'
    
    # 股票数据API配置
    STOCK_API_KEY = os.environ.get('STOCK_API_KEY')
    STOCK_API_BASE_URL = os.environ.get('STOCK_API_BASE_URL') or 'https://api.example.com'
    
    # 数据更新频率（秒）
    DATA_UPDATE_INTERVAL = int(os.environ.get('DATA_UPDATE_INTERVAL', 60))
    
    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        # 创建日志目录
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # 创建数据目录
        data_dir = Path('data')
        data_dir.mkdir(exist_ok=True)

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    CACHE_TYPE = 'simple'

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    CACHE_TYPE = 'redis'

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    CACHE_TYPE = 'null'

# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}