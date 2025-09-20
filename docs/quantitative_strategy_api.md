# 量化策略API接口文档

## 概述

量化策略API提供了完整的量化交易策略回测功能，包括策略管理、回测任务创建与执行、结果查询等功能。

**基础URL**: `http://localhost:8000/django/api/quant/`

## 接口列表

### 1. 获取策略列表

**接口地址**: `GET /strategies/`

**功能描述**: 获取系统中所有可用的量化策略信息

**请求参数**: 无

**响应格式**:
```json
{
    "code": 200,
    "message": "success",
    "data": [
        {
            "name": "ma_cross",
            "description": "双均线交叉策略",
            "params": {
                "fast_period": {
                    "type": "int",
                    "default": 10,
                    "description": "快速均线周期"
                },
                "slow_period": {
                    "type": "int",
                    "default": 30,
                    "description": "慢速均线周期"
                }
            }
        }
    ]
}
```

### 2. 创建回测任务

**接口地址**: `POST /backtest/create/`

**功能描述**: 创建新的回测任务

**请求参数**:
```json
{
    "strategy_name": "ma_cross",
    "symbol": "000001.SZ",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "initial_cash": 100000,
    "strategy_params": {
        "fast_period": 10,
        "slow_period": 30
    }
}
```

**参数说明**:
- `strategy_name`: 策略名称（必填）
- `symbol`: 股票代码（必填）
- `start_date`: 回测开始日期，格式YYYY-MM-DD（必填）
- `end_date`: 回测结束日期，格式YYYY-MM-DD（必填）
- `initial_cash`: 初始资金，默认100000（可选）
- `strategy_params`: 策略参数（可选）

**响应格式**:
```json
{
    "code": 200,
    "message": "回测任务创建成功",
    "data": {
        "task_id": "uuid-string",
        "status": "created",
        "created_at": "2024-01-01T10:00:00Z"
    }
}
```

### 3. 运行回测任务

**接口地址**: `POST /backtest/<task_id>/run/`

**功能描述**: 启动指定的回测任务

**路径参数**:
- `task_id`: 回测任务ID

**请求参数**: 无

**响应格式**:
```json
{
    "code": 200,
    "message": "回测任务已启动",
    "data": {
        "task_id": "uuid-string",
        "status": "running",
        "started_at": "2024-01-01T10:01:00Z"
    }
}
```

### 4. 查询任务状态

**接口地址**: `GET /backtest/<task_id>/status/`

**功能描述**: 查询回测任务的执行状态

**路径参数**:
- `task_id`: 回测任务ID

**请求参数**: 无

**响应格式**:
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "task_id": "uuid-string",
        "status": "completed",
        "progress": 100,
        "created_at": "2024-01-01T10:00:00Z",
        "started_at": "2024-01-01T10:01:00Z",
        "completed_at": "2024-01-01T10:05:00Z",
        "error_message": null
    }
}
```

**状态说明**:
- `created`: 已创建
- `running`: 运行中
- `completed`: 已完成
- `failed`: 执行失败

### 5. 获取回测结果

**接口地址**: `GET /backtest/<task_id>/result/`

**功能描述**: 获取回测任务的详细结果

**路径参数**:
- `task_id`: 回测任务ID

**请求参数**: 无

**响应格式**:
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "task_id": "uuid-string",
        "strategy_name": "ma_cross",
        "symbol": "000001.SZ",
        "period": {
            "start_date": "2023-01-01",
            "end_date": "2023-12-31"
        },
        "performance": {
            "total_return": 0.15,
            "annual_return": 0.15,
            "max_drawdown": -0.08,
            "sharpe_ratio": 1.25,
            "win_rate": 0.65,
            "total_trades": 45,
            "winning_trades": 29,
            "losing_trades": 16
        },
        "portfolio_value": [
            {
                "date": "2023-01-01",
                "value": 100000
            },
            {
                "date": "2023-01-02",
                "value": 100500
            }
        ],
        "trades": [
            {
                "date": "2023-01-15",
                "action": "buy",
                "price": 10.50,
                "quantity": 1000,
                "amount": 10500
            },
            {
                "date": "2023-02-10",
                "action": "sell",
                "price": 11.20,
                "quantity": 1000,
                "amount": 11200
            }
        ]
    }
}
```

### 6. 获取回测历史

**接口地址**: `GET /backtest/history/`

**功能描述**: 获取用户的回测任务历史记录

**请求参数**:
- `page`: 页码，默认1（可选）
- `page_size`: 每页数量，默认20（可选）
- `strategy_name`: 策略名称过滤（可选）
- `symbol`: 股票代码过滤（可选）
- `status`: 状态过滤（可选）

**响应格式**:
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "total": 100,
        "page": 1,
        "page_size": 20,
        "results": [
            {
                "task_id": "uuid-string",
                "strategy_name": "ma_cross",
                "symbol": "000001.SZ",
                "status": "completed",
                "total_return": 0.15,
                "max_drawdown": -0.08,
                "created_at": "2024-01-01T10:00:00Z",
                "completed_at": "2024-01-01T10:05:00Z"
            }
        ]
    }
}
```

## 错误响应格式

所有接口在出现错误时都会返回统一的错误格式：

```json
{
    "code": 400,
    "message": "错误描述信息",
    "data": null
}
```

**常见错误码**:
- `400`: 请求参数错误
- `404`: 资源不存在
- `500`: 服务器内部错误

## 使用示例

### 完整的回测流程示例

1. **获取可用策略**:
```bash
curl -X GET "http://localhost:8000/django/api/quant/strategies/"
```

2. **创建回测任务**:
```bash
curl -X POST "http://localhost:8000/django/api/quant/backtest/create/" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "ma_cross",
    "symbol": "000001.SZ",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "initial_cash": 100000,
    "strategy_params": {
      "fast_period": 10,
      "slow_period": 30
    }
  }'
```

3. **启动回测任务**:
```bash
curl -X POST "http://localhost:8000/django/api/quant/backtest/{task_id}/run/"
```

4. **查询任务状态**:
```bash
curl -X GET "http://localhost:8000/django/api/quant/backtest/{task_id}/status/"
```

5. **获取回测结果**:
```bash
curl -X GET "http://localhost:8000/django/api/quant/backtest/{task_id}/result/"
```

## 注意事项

1. 所有日期格式均为 `YYYY-MM-DD`
2. 回测任务为异步执行，需要通过状态查询接口监控执行进度
3. 回测结果会保存在数据库中，可以随时查询
4. 策略参数需要根据具体策略的要求进行设置
5. 建议在生产环境中添加适当的认证和权限控制

## 技术支持

如有问题，请联系开发团队或查看项目文档。