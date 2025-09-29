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

### 6. 获取观测器数据

**接口地址**: `GET /backtest/<task_id>/observer/`

**功能描述**: 获取回测任务的观测器数据，用于前端可视化展示

**路径参数**:
- `task_id`: 回测任务ID

**请求参数**:
- `observer_type`: 观测器类型过滤（可选）
  - 可选值: `broker`, `trades`, `buysell`, `timereturn`, `drawdown`, `benchmark`
  - 不指定时返回所有观测器数据

**响应格式**:
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "task_info": {
            "task_id": "uuid-string",
            "strategy_name": "ma_cross",
            "stock_code": "000001.SZ",
            "stock_name": "平安银行",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_cash": 100000.0,
            "commission": 0.001
        },
        "observer_data": {
            "broker": [
                {
                    "datetime": "2023-01-01",
                    "cash": 100000.0,
                    "value": 100000.0
                }
            ],
            "trades": [
                {
                    "ref": 1,
                    "size": 1000,
                    "price": 10.50,
                    "value": 10500.0,
                    "commission": 10.5,
                    "pnl": 0.0,
                    "pnlcomm": -10.5
                }
            ],
            "buysell": [
                {
                    "datetime": "2023-01-15",
                    "size": 1000,
                    "price": 10.50,
                    "value": 10500.0,
                    "commission": 10.5
                }
            ],
            "timereturn": [
                {
                    "datetime": "2023-01-01",
                    "timereturn": 0.0
                }
            ],
            "drawdown": [
                {
                    "datetime": "2023-01-01",
                    "len": 0,
                    "drawdown": 0.0,
                    "maxdrawdown": 0.0
                }
            ],
            "benchmark": []
        },
        "statistics": {
            "broker_records": 100,
            "trades_records": 10,
            "buysell_records": 20,
            "timereturn_records": 100,
            "drawdown_records": 100,
            "benchmark_records": 0
        },
        "visualization_hints": {
            "broker": "资金曲线图 - 显示现金和总价值变化",
            "trades": "交易统计表 - 显示每笔交易的盈亏情况",
            "buysell": "买卖信号图 - 在价格图上标记买卖点",
            "timereturn": "收益率曲线 - 显示策略收益率变化",
            "drawdown": "回撤曲线 - 显示最大回撤情况",
            "benchmark": "基准对比图 - 与基准收益率对比"
        }
    }
}
```

### 7. 获取原始数据和指标数据

**接口地址**: `GET /backtest/<task_id>/raw-indicator/`

**功能描述**: 获取回测任务的原始市场数据和技术指标数据，用于前端可视化展示

**路径参数**:
- `task_id`: 回测任务ID

**请求参数**:
- `data_type`: 数据类型过滤（可选）
  - 可选值: `raw`, `indicator`, `all`
  - `raw`: 仅返回原始市场数据（OHLCV）
  - `indicator`: 仅返回技术指标数据
  - `all`: 返回所有数据（默认值）

**响应格式**:
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "task_info": {
            "task_id": "uuid-string",
            "strategy_name": "ma_cross",
            "stock_code": "000001.SZ",
            "stock_name": "平安银行",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_cash": 100000.0,
            "commission": 0.001
        },
        "raw_data": {
            "datetime": [
                "2023-01-01",
                "2023-01-02",
                "2023-01-03"
            ],
            "open": [10.50, 10.60, 10.55],
            "high": [10.80, 10.75, 10.70],
            "low": [10.40, 10.50, 10.45],
            "close": [10.70, 10.65, 10.60],
            "volume": [1000000, 1200000, 950000]
        },
        "indicator_data": {
            "ma_short": [10.60, 10.62, 10.58],
            "ma_long": [10.55, 10.57, 10.56],
            "crossover": [0, 1, 0]
        },
        "statistics": {
            "raw_data_records": 100,
            "indicator_data_records": 100
        },
        "visualization_hints": {
            "raw_data": "K线图 - 显示OHLCV原始市场数据",
            "indicator_data": "技术指标图 - 显示移动平均线、交叉信号等指标数据"
        }
    }
}
```

**数据说明**:
- `raw_data`: 原始市场数据
  - `datetime`: 日期时间数组
  - `open`: 开盘价数组
  - `high`: 最高价数组
  - `low`: 最低价数组
  - `close`: 收盘价数组
  - `volume`: 成交量数组
- `indicator_data`: 技术指标数据（根据策略不同而变化）
  - `ma_short`: 短期移动平均线
  - `ma_long`: 长期移动平均线
  - `crossover`: 交叉信号（1表示金叉，0表示无信号，-1表示死叉）

### 8. 获取回测历史

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

6. **获取观测器数据**:
```bash
curl -X GET "http://localhost:8000/django/api/quant/backtest/{task_id}/observer/"
```

7. **获取原始数据和指标数据**:
```bash
curl -X GET "http://localhost:8000/django/api/quant/backtest/{task_id}/raw-indicator/"
```

**带参数的请求示例**:
```bash
# 只获取原始市场数据
curl -X GET "http://localhost:8000/django/api/quant/backtest/{task_id}/raw-indicator/?data_type=raw"

# 只获取技术指标数据
curl -X GET "http://localhost:8000/django/api/quant/backtest/{task_id}/raw-indicator/?data_type=indicator"

# 只获取特定观测器数据
curl -X GET "http://localhost:8000/django/api/quant/backtest/{task_id}/observer/?observer_type=broker"
```

## 注意事项

1. 所有日期格式均为 `YYYY-MM-DD`
2. 回测任务为异步执行，需要通过状态查询接口监控执行进度
3. 回测结果会保存在数据库中，可以随时查询
4. 策略参数需要根据具体策略的要求进行设置
5. 建议在生产环境中添加适当的认证和权限控制
6. **新增数据接口说明**:
   - `/observer/` 接口用于获取回测过程中的观测器数据，适用于绘制资金曲线、收益率曲线等
   - `/raw-indicator/` 接口用于获取原始市场数据和技术指标数据，适用于绘制K线图、指标图等
   - 两个接口都支持数据类型过滤，可根据前端需求灵活获取所需数据
   - 响应数据包含可视化提示信息，帮助前端选择合适的图表类型

## 技术支持

如有问题，请联系开发团队或查看项目文档。