#!/usr/bin/env python3
"""
测试原始数据和指标数据收集与返回功能
验证回测系统是否正确收集和返回原始市场数据和技术指标数据
"""

import os
import sys
import django
from datetime import datetime, timedelta

# 配置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_data_service.settings')
django.setup()

from quantitative_strategy.services import BacktestService
from quantitative_strategy.models import BacktestTask, BacktestResult


def test_raw_indicator_data_collection():
    """测试原始数据和指标数据的收集功能"""
    print("=" * 60)
    print("测试原始数据和指标数据收集功能")
    print("=" * 60)
    
    # 创建回测服务实例
    service = BacktestService()
    
    # 设置回测参数
    backtest_params = {
        'strategy_name': 'ma_cross',
        'stock_code': '000001',
        'start_date': '2024-01-01',
        'end_date': '2024-03-31',
        'initial_cash': 100000,
        'commission': 0.001,
        'strategy_params': {
            'short_period': 5,
            'long_period': 20
        }
    }
    
    try:
        # 创建回测任务
        print("1. 创建回测任务...")
        task_id = service.create_backtest_task(**backtest_params)
        print(f"   任务ID: {task_id}")
        
        # 运行回测
        print("2. 运行回测...")
        result = service.run_backtest(task_id)
        
        if result.get('status') == 'completed':
            print("   回测完成成功！")
            
            # 获取回测结果
            print("3. 检查数据收集情况...")
            task = BacktestTask.objects.get(task_id=task_id)
            backtest_result = BacktestResult.objects.get(task=task)
            
            # 检查原始数据
            raw_data = backtest_result.raw_data
            print(f"   原始数据类型: {type(raw_data)}")
            if raw_data:
                print("   原始数据字段:")
                for key, value in raw_data.items():
                    if isinstance(value, list):
                        print(f"     - {key}: {len(value)} 条记录")
                    else:
                        print(f"     - {key}: {type(value)}")
            else:
                print("   ❌ 原始数据为空！")
            
            # 检查指标数据
            indicator_data = backtest_result.indicator_data
            print(f"   指标数据类型: {type(indicator_data)}")
            if indicator_data:
                print("   指标数据字段:")
                for key, value in indicator_data.items():
                    if isinstance(value, list):
                        print(f"     - {key}: {len(value)} 条记录")
                    else:
                        print(f"     - {key}: {type(value)}")
            else:
                print("   ❌ 指标数据为空！")
            
            # 检查观测器数据
            observer_data = backtest_result.observer_data
            print(f"   观测器数据类型: {type(observer_data)}")
            if observer_data:
                print("   观测器数据字段:")
                for key, value in observer_data.items():
                    if isinstance(value, list):
                        print(f"     - {key}: {len(value)} 条记录")
                    else:
                        print(f"     - {key}: {type(value)}")
            else:
                print("   ❌ 观测器数据为空！")
            
            # 验证数据完整性
            print("4. 验证数据完整性...")
            success = True
            
            # 检查原始数据完整性
            if not raw_data:
                print("   ❌ 原始数据缺失")
                success = False
            else:
                required_raw_fields = ['datetime', 'open', 'high', 'low', 'close', 'volume']
                for field in required_raw_fields:
                    if field not in raw_data or not raw_data[field]:
                        print(f"   ❌ 原始数据缺少字段: {field}")
                        success = False
                
                # 检查数据长度一致性
                if raw_data:
                    lengths = [len(v) for v in raw_data.values() if isinstance(v, list)]
                    if lengths and len(set(lengths)) > 1:
                        print(f"   ❌ 原始数据长度不一致: {lengths}")
                        success = False
                    elif lengths:
                        print(f"   ✅ 原始数据长度一致: {lengths[0]} 条记录")
            
            # 检查指标数据完整性
            if not indicator_data:
                print("   ❌ 指标数据缺失")
                success = False
            else:
                expected_indicator_fields = ['ma_short', 'ma_long', 'crossover']
                for field in expected_indicator_fields:
                    if field not in indicator_data or not indicator_data[field]:
                        print(f"   ❌ 指标数据缺少字段: {field}")
                        success = False
                
                # 检查指标数据长度一致性
                if indicator_data:
                    lengths = [len(v) for v in indicator_data.values() if isinstance(v, list)]
                    if lengths and len(set(lengths)) > 1:
                        print(f"   ❌ 指标数据长度不一致: {lengths}")
                        success = False
                    elif lengths:
                        print(f"   ✅ 指标数据长度一致: {lengths[0]} 条记录")
            
            # 检查观测器数据完整性
            if not observer_data:
                print("   ❌ 观测器数据缺失")
                success = False
            else:
                expected_observer_fields = ['broker', 'buysell', 'trades', 'timereturn', 'drawdown', 'benchmark']
                for field in expected_observer_fields:
                    if field not in observer_data:
                        print(f"   ❌ 观测器数据缺少字段: {field}")
                        success = False
                    elif not observer_data[field]:
                        print(f"   ⚠️  观测器数据字段为空: {field}")
                    else:
                        print(f"   ✅ 观测器数据字段正常: {field} ({len(observer_data[field])} 条记录)")
            
            # 输出测试结果
            print("5. 测试结果:")
            if success:
                print("   ✅ 所有数据收集功能正常！")
                print("   ✅ 原始数据、指标数据和观测器数据都已正确收集")
            else:
                print("   ❌ 数据收集存在问题，请检查上述错误信息")
            
            return success
            
        else:
            print(f"   ❌ 回测失败: {result.get('error', '未知错误')}")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_api_data_return():
    """测试API接口数据返回功能"""
    print("\n" + "=" * 60)
    print("测试API接口数据返回功能")
    print("=" * 60)
    
    try:
        # 获取最近的一个已完成任务
        completed_task = BacktestTask.objects.filter(status='completed').order_by('-completed_at').first()
        
        if not completed_task:
            print("❌ 没有找到已完成的回测任务，无法测试API返回功能")
            return False
        
        print(f"使用任务ID: {completed_task.task_id}")
        
        # 获取回测结果
        backtest_result = BacktestResult.objects.get(task=completed_task)
        
        # 模拟API返回数据
        print("1. 测试get_performance_summary方法...")
        performance_summary = backtest_result.get_performance_summary()
        
        # 检查返回数据是否包含新增字段
        required_fields = ['raw_data', 'indicator_data', 'observer_data']
        success = True
        
        for field in required_fields:
            if field in performance_summary:
                print(f"   ✅ {field} 字段存在")
                if performance_summary[field]:
                    print(f"      数据类型: {type(performance_summary[field])}")
                    if isinstance(performance_summary[field], dict):
                        print(f"      包含字段: {list(performance_summary[field].keys())}")
                else:
                    print(f"      ⚠️  {field} 字段为空")
            else:
                print(f"   ❌ {field} 字段缺失")
                success = False
        
        print("2. 测试结果:")
        if success:
            print("   ✅ API数据返回功能正常！")
            print("   ✅ 所有新增字段都已正确包含在API响应中")
        else:
            print("   ❌ API数据返回存在问题")
        
        return success
        
    except Exception as e:
        print(f"❌ API测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("开始测试原始数据和指标数据功能...")
    
    # 测试数据收集功能
    collection_success = test_raw_indicator_data_collection()
    
    # 测试API返回功能
    api_success = test_api_data_return()
    
    # 总结测试结果
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    if collection_success and api_success:
        print("🎉 所有测试通过！")
        print("✅ 原始数据和指标数据收集功能正常")
        print("✅ API接口数据返回功能正常")
        print("✅ 系统已成功集成原始数据和指标数据功能")
    else:
        print("❌ 部分测试失败！")
        if not collection_success:
            print("❌ 数据收集功能存在问题")
        if not api_success:
            print("❌ API返回功能存在问题")
        print("请检查上述错误信息并进行修复")