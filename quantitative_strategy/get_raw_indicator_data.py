#!/usr/bin/env python3
"""
获取原始数据和指标数据的API接口
专门用于前端获取原始市场数据和技术指标数据
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import logging

from common.response import success_response, error_response
from .models import BacktestTask, BacktestResult

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET"])
def get_raw_indicator_data(request, task_id):
    """
    获取原始数据和指标数据，专门用于前端可视化
    
    Args:
        task_id: 任务ID
        data_type: 可选，指定数据类型 (raw, indicator, all)
    
    Returns:
        {
            "code": 200,
            "message": "success",
            "data": {
                "task_info": {
                    "task_id": "xxx",
                    "strategy_name": "xxx",
                    "stock_code": "xxx",
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31"
                },
                "raw_data": {
                    "datetime": [...],
                    "open": [...],
                    "high": [...],
                    "low": [...],
                    "close": [...],
                    "volume": [...]
                },
                "indicator_data": {
                    "ma_short": [...],
                    "ma_long": [...],
                    "crossover": [...]
                },
                "statistics": {
                    "raw_data_records": 100,
                    "indicator_data_records": 100
                }
            }
        }
    """
    try:
        # 获取任务
        try:
            task = BacktestTask.objects.get(task_id=task_id)
        except BacktestTask.DoesNotExist:
            return error_response("任务不存在", 404)
        
        # 检查任务状态
        if task.status != 'completed':
            return error_response("任务未完成", 400)
        
        # 获取结果
        try:
            result = BacktestResult.objects.get(task=task)
        except BacktestResult.DoesNotExist:
            return error_response("回测结果不存在", 404)
        
        # 获取原始数据和指标数据
        raw_data = result.raw_data or {}
        indicator_data = result.indicator_data or {}
        
        # 获取可选的数据类型过滤参数
        data_type = request.GET.get('data_type', 'all')
        
        # 根据数据类型过滤返回数据
        response_data_content = {}
        if data_type == 'raw':
            response_data_content['raw_data'] = raw_data
        elif data_type == 'indicator':
            response_data_content['indicator_data'] = indicator_data
        else:  # data_type == 'all' or any other value
            response_data_content['raw_data'] = raw_data
            response_data_content['indicator_data'] = indicator_data
        
        # 计算统计信息
        statistics = {}
        if 'datetime' in raw_data and isinstance(raw_data['datetime'], list):
            statistics['raw_data_records'] = len(raw_data['datetime'])
        else:
            statistics['raw_data_records'] = 0
            
        # 计算指标数据记录数（以第一个指标的长度为准）
        if indicator_data:
            first_indicator = next(iter(indicator_data.values()), [])
            if isinstance(first_indicator, list):
                statistics['indicator_data_records'] = len(first_indicator)
            else:
                statistics['indicator_data_records'] = 0
        else:
            statistics['indicator_data_records'] = 0
        
        # 构建响应数据
        response_data = {
            'task_info': {
                'task_id': task.task_id,
                'strategy_name': task.strategy_name,
                'stock_code': task.stock_code,
                'stock_name': task.stock_name,
                'start_date': task.start_date.strftime('%Y-%m-%d'),
                'end_date': task.end_date.strftime('%Y-%m-%d'),
                'initial_cash': float(task.initial_cash),
                'commission': float(task.commission)
            },
            'statistics': statistics,
            'visualization_hints': {
                'raw_data': 'K线图 - 显示OHLCV原始市场数据',
                'indicator_data': '技术指标图 - 显示移动平均线、交叉信号等指标数据'
            }
        }
        
        # 添加过滤后的数据内容
        response_data.update(response_data_content)
        
        return success_response(response_data)
        
    except Exception as e:
        logger.error(f"获取原始数据和指标数据失败: {str(e)}")
        return error_response(f"获取原始数据和指标数据失败: {str(e)}", 500)