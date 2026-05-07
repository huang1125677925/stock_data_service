"""
股票标记任务模块

功能：提供各种股票标记策略的定时任务，将符合条件的股票自动标记到数据库中
参数：各种策略的参数配置
返回值：标记结果统计信息
事件：标记成功/失败时记录日志
"""

import sys
import os
import json
from pathlib import Path
from tracemalloc import start
import django

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_data_service.settings')
django.setup()

import logging
import hashlib
from datetime import datetime, date
from typing import List, Dict, Optional, Any
from django.core.cache import cache
from django.db import transaction

# 导入相关模型和服务
from indival_stock_data.models import StockTag, IndividualStock
from indival_stock_data.services import StockTagService
from stock_strategy.services import StockScreeningService

logger = logging.getLogger(__name__)


class StockTaggingTaskService:
    """
    股票标记任务服务类
    
    功能：提供各种股票标记策略的执行服务
    参数：无（通过方法参数传递具体策略参数）
    返回值：标记任务执行结果
    事件：任务执行过程中记录详细日志
    """
    
    def __init__(self):
        """
        初始化股票标记任务服务
        
        功能：初始化相关服务实例和配置
        参数：无
        返回值：无
        事件：初始化完成时记录日志
        """
        self.stock_tag_service = StockTagService()
        self.screening_service = StockScreeningService()
        logger.info("股票标记任务服务初始化完成")
    
    def execute_previous_high_breakout_tagging(
        self, 
        window_size: int = 60,
        volume_multiplier: float = 1.5,
        stock_codes: Optional[List[str]] = None,
        limit: int = 50,
        tag_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        执行前高突破策略标记任务
        
        功能：根据前高突破策略筛选股票并自动标记到数据库
        参数：
        - window_size: 分析窗口大小（交易日数量），默认60
        - volume_multiplier: 成交量放大倍数，默认1.5
        - stock_codes: 指定股票代码列表，可选
        - limit: 处理结果数量限制，默认50
        - tag_date: 标记日期，默认为当前日期
        
        返回值：
        - success: 是否成功
        - message: 执行结果消息
        - data: 标记统计信息
        
        事件：
        - 任务开始时记录日志
        - 筛选过程中记录进度
        - 标记成功/失败时记录详细信息
        - 任务完成时记录统计结果
        """
        try:
            logger.info(f"开始执行前高突破策略标记任务: window_size={window_size}, volume_multiplier={volume_multiplier}")
            
            # 设置默认标记日期
            if tag_date is None:
                tag_date = date.today()
            
            # 验证参数
            validation_result = self.screening_service.validate_parameters(window_size, volume_multiplier)
            if not validation_result['valid']:
                error_msg = f"参数验证失败: {', '.join(validation_result['errors'])}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'message': error_msg,
                    'data': None
                }
            
            # 执行股票筛选
            logger.info("开始执行股票筛选...")
            screening_result = self.screening_service.screen_stocks_by_previous_high(
                window_size=window_size,
                volume_multiplier=volume_multiplier,
                stock_codes=stock_codes,
                limit=limit
            )
            
            if not screening_result['success']:
                logger.error(f"股票筛选失败: {screening_result['message']}")
                return {
                    'success': False,
                    'message': f"股票筛选失败: {screening_result['message']}",
                    'data': None
                }
            
            screened_stocks = screening_result['data'].get('candidates', [])
            logger.info(f"筛选到 {len(screened_stocks)} 只股票")
            
            # 批量标记股票
            tagging_result = self._batch_tag_stocks_with_breakout_pattern(
                screened_stocks, 
                tag_date,
                window_size,
                volume_multiplier
            )
            
            logger.info(f"前高突破策略标记任务完成: 成功标记 {tagging_result['success_count']} 只股票")
            
            return {
                'success': True,
                'message': f"前高突破策略标记任务完成，成功标记 {tagging_result['success_count']} 只股票",
                'data': {
                    'screened_count': len(screened_stocks),
                    'success_count': tagging_result['success_count'],
                    'failed_count': tagging_result['failed_count'],
                    'failed_stocks': tagging_result['failed_stocks'],
                    'tag_date': tag_date.strftime('%Y-%m-%d'),
                    'strategy_params': {
                        'window_size': window_size,
                        'volume_multiplier': volume_multiplier
                    }
                }
            }
            
        except Exception as e:
            error_msg = f"前高突破策略标记任务执行失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'message': error_msg,
                'data': None
            }
    
    def _batch_tag_stocks_with_breakout_pattern(
        self, 
        screened_stocks: List[Dict], 
        tag_date: date,
        window_size: int,
        volume_multiplier: float
    ) -> Dict[str, Any]:
        """
        批量标记股票为突破形态
        
        功能：将筛选出的股票批量标记为突破形态
        参数：
        - screened_stocks: 筛选出的股票列表
        - tag_date: 标记日期
        - window_size: 窗口大小（用于备注）
        - volume_multiplier: 成交量倍数（用于备注）
        
        返回值：
        - success_count: 成功标记数量
        - failed_count: 失败标记数量
        - failed_stocks: 失败的股票列表
        
        事件：
        - 每个股票标记成功/失败时记录日志
        """
        success_count = 0
        failed_count = 0
        failed_stocks = []
        
        logger.info(f"开始批量标记 {len(screened_stocks)} 只股票")
        
        for stock_data in screened_stocks:
            try:
                stock_code = stock_data.get('stock_code')
                if not stock_code:
                    logger.warning("股票数据缺少代码信息，跳过")
                    continue
                
                # 创建标记
                with transaction.atomic():
                    stock = IndividualStock.objects.get(code=stock_code)
            
                    # 创建标记
                    stockTag = StockTag(
                        stock=stock,
                        pattern_type='BOX_BREAKOUT',
                    )
                    stockTag.save()

                    success_count += 1
                    # logger.info(f"成功标记股票 {stock_code}，标记ID: {stock_tag.id}")
                    
            except Exception as e:
                failed_count += 1
                failed_stocks.append({
                    'code': stock_code,
                    'error': str(e)
                })
                logger.error(f"标记股票 {stock_code} 失败: {str(e)}")
        
        logger.info(f"批量标记完成: 成功 {success_count} 只，失败 {failed_count} 只")
        
        return {
            'success_count': success_count,
            'failed_count': failed_count,
            'failed_stocks': failed_stocks
        }
    
    def _check_existing_tag(self, stock_code: str, tag_date: date) -> Optional[StockTag]:
        """
        检查股票在指定日期是否已存在标记
        
        功能：避免重复标记同一只股票
        参数：
        - stock_code: 股票代码
        - tag_date: 标记日期
        
        返回值：
        - 存在的标记对象或None
        
        事件：查询过程中记录调试信息
        """
        try:
            stock = IndividualStock.objects.get(code=stock_code)
            existing_tag = StockTag.objects.filter(
                stock=stock,
                tag_date=tag_date
            ).first()
            return existing_tag
        except IndividualStock.DoesNotExist:
            logger.warning(f"股票 {stock_code} 不存在")
            return None
        except Exception as e:
            logger.error(f"检查股票 {stock_code} 标记时出错: {str(e)}")
            return None
    
    def get_tagging_statistics(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        获取指定时间范围内的标记统计信息
        
        功能：统计标记任务的执行情况
        参数：
        - start_date: 开始日期
        - end_date: 结束日期
        
        返回值：
        - 标记统计信息字典
        
        事件：统计过程中记录日志
        """
        try:
            logger.info(f"获取标记统计信息: {start_date} 到 {end_date}")
            
            # 查询指定时间范围内的标记
            tags = StockTag.objects.filter(
                tag_date__gte=start_date,
                tag_date__lte=end_date
            ).select_related('stock')
            
            # 统计各种类型的标记数量
            pattern_stats = {}
            technical_stats = {}
            daily_stats = {}
            
            for tag in tags:
                # 按形态类型统计
                if tag.pattern_type:
                    pattern_stats[tag.pattern_type] = pattern_stats.get(tag.pattern_type, 0) + 1
                
                # 按技术指标类型统计
                if tag.technical_indicator_type:
                    technical_stats[tag.technical_indicator_type] = technical_stats.get(tag.technical_indicator_type, 0) + 1
                
                # 按日期统计
                date_str = tag.tag_date.strftime('%Y-%m-%d')
                daily_stats[date_str] = daily_stats.get(date_str, 0) + 1
            
            result = {
                'total_count': tags.count(),
                'pattern_type_stats': pattern_stats,
                'technical_indicator_stats': technical_stats,
                'daily_stats': daily_stats,
                'date_range': {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d')
                }
            }
            
            logger.info(f"标记统计完成: 总计 {result['total_count']} 条标记")
            return result
            
        except Exception as e:
            logger.error(f"获取标记统计信息失败: {str(e)}")
            raise


# 创建全局服务实例
stock_tagging_service = StockTaggingTaskService()


def execute_previous_high_breakout_tagging_task(
    window_size: int = 60,
    volume_multiplier: float = 1.5,
    stock_codes: Optional[List[str]] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    执行前高突破策略标记任务的便捷函数
    
    功能：提供简单的函数接口来执行前高突破策略标记
    参数：
    - window_size: 分析窗口大小，默认60
    - volume_multiplier: 成交量放大倍数，默认1.5
    - stock_codes: 指定股票代码列表，可选
    - limit: 处理结果数量限制，默认50
    
    返回值：
    - 标记任务执行结果字典
    
    事件：
    - 任务执行过程中记录日志
    """
    return stock_tagging_service.execute_previous_high_breakout_tagging(
        window_size=window_size,
        volume_multiplier=volume_multiplier,
        stock_codes=stock_codes,
        limit=limit
    )

if __name__ == '__main__':
    execute_previous_high_breakout_tagging_task()