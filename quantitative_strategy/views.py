#!/usr/bin/env python3
"""
量化策略API视图
提供策略回测相关的API接口
"""

import os
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from django.conf import settings

from common.response import success_response, error_response
from common.validators import validate_pagination_params
from .services import backtest_service
from .models import BacktestTask, BacktestResult
from user_management.decorators import jwt_login_required

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET"])
def get_strategies(request):
    """
    获取可用策略列表
    
    Returns:
        {
            "code": 200,
            "message": "success",
            "data": {
                "strategies": {
                    "ma_cross": {
                        "name": "ma_cross",
                        "description": "移动平均线交叉策略",
                        "params": {...}
                    },
                    ...
                }
            }
        }
    """
    try:
        strategies = backtest_service.get_available_strategies()
        
        return success_response({
            'strategies': strategies,
            'total': len(strategies)
        })
        
    except Exception as e:
        logger.error(f"获取策略列表失败: {str(e)}")
        return error_response(f"获取策略列表失败: {str(e)}", 500)


@csrf_exempt
@jwt_login_required
@require_http_methods(["POST"])
def create_backtest(request):
    """
    创建回测任务
    
    Request Body:
        {
            "strategy_name": "ma_cross",
            "stock_code": "000001",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_cash": 100000,
            "commission": 0.001,
            "strategy_params": {
                "short_period": 5,
                "long_period": 20
            }
        }
    
    Returns:
        {
            "code": 200,
            "message": "success",
            "data": {
                "task_id": "uuid-string"
            }
        }
    """
    try:
        # 解析请求数据
        data = json.loads(request.body)
        
        # 验证必需参数
        required_fields = ['strategy_name', 'stock_code', 'start_date', 'end_date']
        for field in required_fields:
            if field not in data:
                return error_response(f"缺少必需参数: {field}", 400)
        
        strategy_name = data['strategy_name']
        stock_code = data['stock_code']
        start_date = data['start_date']
        end_date = data['end_date']
        
        # 验证日期格式
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            if start_dt >= end_dt:
                return error_response("开始日期必须早于结束日期", 400)
            
            if end_dt > datetime.now():
                return error_response("结束日期不能超过当前日期", 400)
                
        except ValueError:
            return error_response("日期格式错误，请使用YYYY-MM-DD格式", 400)
        
        # 验证股票代码格式
        if not stock_code or len(stock_code) != 6 or not stock_code.isdigit():
            return error_response("股票代码格式错误，请输入6位数字代码", 400)
        
        # 获取可选参数
        initial_cash = float(data.get('initial_cash', 100000))
        commission = float(data.get('commission', 0.001))
        strategy_params = data.get('strategy_params', {})
        
        # 验证参数范围
        if initial_cash <= 0:
            return error_response("初始资金必须大于0", 400)
        
        if commission < 0 or commission > 0.1:
            return error_response("手续费率必须在0-0.1之间", 400)
        
        # 验证策略是否存在
        available_strategies = backtest_service.get_available_strategies()
        strategy_names = [strategy['name'] for strategy in available_strategies]
        if strategy_name not in strategy_names:
            return error_response(f"策略 {strategy_name} 不存在", 400)
        
        # 创建回测任务
        task_id = backtest_service.create_backtest_task(
            strategy_name=strategy_name,
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            initial_cash=initial_cash,
            commission=commission,
            strategy_params=strategy_params,
            user=request.user
        )
        
        return success_response({
            'task_id': task_id
        })
        
    except json.JSONDecodeError:
        return error_response("请求数据格式错误", 400)
    except Exception as e:
        logger.error(f"创建回测任务失败: {str(e)}")
        return error_response(f"创建回测任务失败: {str(e)}", 500)


@csrf_exempt
@require_http_methods(["POST"])
def run_backtest(request, task_id):
    """
    执行回测任务
    
    Args:
        task_id: 任务ID
    
    Returns:
        {
            "code": 200,
            "message": "success",
            "data": {
                "task_id": "uuid-string",
                "status": "completed",
                "result": {
                    "total_return": 15.25,
                    "annual_return": 12.8,
                    "sharpe_ratio": 1.25,
                    "max_drawdown": -8.5,
                    "total_trades": 25,
                    "win_rate": 60.0
                }
            }
        }
    """
    try:
        # 验证任务是否存在
        try:
            task = BacktestTask.objects.get(task_id=task_id)
        except BacktestTask.DoesNotExist:
            return error_response("任务不存在", 404)
        
        # 检查任务状态
        if task.status == 'completed':
            return error_response("任务已完成，无需重复执行", 400)
        
        if task.status == 'running':
            return error_response("任务正在运行中", 400)
        
        # 执行回测
        result = backtest_service.run_backtest(task_id)
        
        return success_response(result)
        
    except Exception as e:
        logger.error(f"执行回测任务失败: {str(e)}")
        return error_response(f"执行回测任务失败: {str(e)}", 500)


@csrf_exempt
@require_http_methods(["GET"])
def get_task_status(request, task_id):
    """
    获取任务状态
    
    Args:
        task_id: 任务ID
    
    Returns:
        {
            "code": 200,
            "message": "success",
            "data": {
                "task_id": "uuid-string",
                "status": "completed",
                "strategy_name": "ma_cross",
                "stock_code": "000001",
                "result": {...}
            }
        }
    """
    try:
        result = backtest_service.get_task_status(task_id)
        
        if result['status'] == 'not_found':
            return error_response("任务不存在", 404)
        
        return success_response(result)
        
    except Exception as e:
        logger.error(f"获取任务状态失败: {str(e)}")
        return error_response(f"获取任务状态失败: {str(e)}", 500)


@csrf_exempt
@require_http_methods(["GET"])
@jwt_login_required
def get_backtest_history(request):
    """
    获取回测历史记录
    
    Query Parameters:
        limit (int): 返回记录数量限制，默认20
        offset (int): 偏移量，默认0
        strategy_name (str): 策略名称过滤
        stock_code (str): 股票代码过滤
        status (str): 状态过滤
    
    Returns:
        {
            "code": 200,
            "message": "success",
            "data": {
                "total": 100,
                "tasks": [...]
            }
        }
    """
    try:
        # 获取查询参数
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))
        strategy_name = request.GET.get('strategy_name')
        stock_code = request.GET.get('stock_code')
        status = request.GET.get('status')
        
        # 验证分页参数
        limit, offset = validate_pagination_params(limit, offset)
        
        # 构建查询
        queryset = BacktestTask.objects.all()
        
        # 如果用户已登录，只显示该用户的任务
        queryset = queryset.filter(user=request.user)
        
        # 应用过滤条件
        if strategy_name:
            queryset = queryset.filter(strategy_name=strategy_name)
        
        if stock_code:
            queryset = queryset.filter(stock_code=stock_code)
        
        if status:
            queryset = queryset.filter(status=status)
        
        # 获取总数
        total = queryset.count()
        
        # 分页查询
        tasks = queryset[offset:offset + limit]
        
        # 构建响应数据
        task_list = []
        for task in tasks:
            task_data = {
                'task_id': task.task_id,
                'strategy_name': task.strategy_name,
                'stock_code': task.stock_code,
                'stock_name': task.stock_name,
                'start_date': task.start_date.strftime('%Y-%m-%d'),
                'end_date': task.end_date.strftime('%Y-%m-%d'),
                'initial_cash': float(task.initial_cash),
                'commission': float(task.commission),
                'status': task.status,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat()
            }
            
            # 如果任务完成，添加结果摘要
            if task.status == 'completed':
                try:
                    result = BacktestResult.objects.get(task=task)
                    task_data['result_summary'] = {
                        'total_return': float(result.total_return),
                        'annual_return': float(result.annual_return),
                        'sharpe_ratio': float(result.sharpe_ratio) if result.sharpe_ratio else None,
                        'max_drawdown': float(result.max_drawdown) if result.max_drawdown else None,
                        'total_trades': result.total_trades,
                        'win_rate': float(result.win_rate) if result.win_rate else None
                    }
                    task_data['completed_at'] = task.completed_at.isoformat() if task.completed_at else None
                except BacktestResult.DoesNotExist:
                    pass
            elif task.status == 'failed':
                task_data['error'] = task.error_message
                task_data['completed_at'] = task.completed_at.isoformat() if task.completed_at else None
            
            task_list.append(task_data)
        
        return success_response({
            'total': total,
            'tasks': task_list,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"获取回测历史失败: {str(e)}")
        return error_response(f"获取回测历史失败: {str(e)}", 500)


@csrf_exempt
@require_http_methods(["GET"])
def get_backtest_result(request, task_id):
    """
    获取详细回测结果
    
    Args:
        task_id: 任务ID
    
    Returns:
        {
            "code": 200,
            "message": "success",
            "data": {
                "task_info": {...},
                "performance": {...},
                "trades": [...]
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
                'commission': float(task.commission),
                'strategy_params': task.strategy_params,
                'created_at': task.created_at.isoformat(),
                'completed_at': task.completed_at.isoformat() if task.completed_at else None
            },
            'performance': {
                'initial_value': float(result.initial_value),
                'final_value': float(result.final_value),
                'total_return': float(result.total_return),
                'annual_return': float(result.annual_return),
                'sharpe_ratio': float(result.sharpe_ratio) if result.sharpe_ratio else None,
                'max_drawdown': float(result.max_drawdown) if result.max_drawdown else None,
                'volatility': float(result.volatility) if result.volatility else None,
                'total_trades': result.total_trades,
                'winning_trades': result.winning_trades,
                'losing_trades': result.losing_trades,
                'win_rate': float(result.win_rate) if result.win_rate else None
            },
            'detailed_data': {
                'daily_returns': result.daily_returns,
                'portfolio_values': result.portfolio_values,
                'trade_records': result.trade_records
            }
        }
        
        return success_response(response_data)
        
    except Exception as e:
        logger.error(f"获取回测结果失败: {str(e)}")
        return error_response(f"获取回测结果失败: {str(e)}", 500)


@csrf_exempt
@require_http_methods(["GET"])
def get_backtest_chart(request, task_id):
    """
    获取回测图表
    
    参数:
        task_id: 回测任务ID
        
    返回:
        图表文件或错误信息
        
    事件:
        - 返回PNG格式的回测图表文件
        - 如果图表不存在返回404错误
    """
    try:
        # 获取回测结果
        result = BacktestResult.objects.filter(task_id=task_id).first()
        if not result:
            return error_response("回测结果不存在", 404)
        
        # 检查图表文件是否存在
        if not result.chart_image:
            return error_response("图表文件不存在", 404)
        
        # 构建完整的文件路径
        chart_path = os.path.join(settings.BASE_DIR, result.chart_image)
        
        # 检查文件是否存在
        if not os.path.exists(chart_path):
            return error_response("图表文件不存在", 404)
        
        # 读取并返回图表文件
        with open(chart_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='image/png')
            response['Content-Disposition'] = f'inline; filename="backtest_chart_{task_id}.png"'
            return response
            
    except Exception as e:
        logger.error(f"获取回测图表失败: {str(e)}")
        return error_response(f"获取回测图表失败: {str(e)}", 500)
