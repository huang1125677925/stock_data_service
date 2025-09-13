# 股票策略API文档

## 指数RPS强度排名API

### 获取实时指数RPS强度排名

**接口地址**: `/api/strategy/index-rps/`

**请求方式**: GET

**请求参数**:

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| ----- | --- | ---- | ----- | ---- |
| periods | string | 否 | "5,20,60" | 时间周期，多个周期用逗号分隔 |
| save | boolean | 否 | false | 是否保存到数据库 |

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2024-05-20T12:00:00",
  "data": {
    "total": 100,
    "data": [
      {
        "指数代码": "886001",
        "指数简称": "电子信息",
        "5日涨跌幅": 3.25,
        "RPS_5": 95.5,
        "20日涨跌幅": 5.67,
        "RPS_20": 92.3,
        "60日涨跌幅": 10.45,
        "RPS_60": 88.7
      },
      // 更多数据...
    ],
    "periods": [5, 20, 60],
    "saved_count": 0,
    "errors": [],
    "query_time": "2024-05-20T12:00:00"
  }
}
```

### 获取历史RPS数据

**接口地址**: `/api/strategy/historical-rps/`

**请求方式**: GET

**请求参数**:

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| ----- | --- | ---- | ----- | ---- |
| period | integer | 否 | 20 | 时间周期 |
| limit | integer | 否 | 100 | 返回数量限制 |
| offset | integer | 否 | 0 | 偏移量 |

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2024-05-20T12:00:00",
  "data": {
    "total": 500,
    "data": [
      {
        "index_code": "886001",
        "index_name": "电子信息",
        "period": 20,
        "change_percent": 5.67,
        "rps_value": 92.3,
        "created_at": "2024-05-20T10:00:00"
      },
      // 更多数据...
    ],
    "period": 20,
    "query_time": "2024-05-20T12:00:00"
  }
}
```

## 使用说明

1. 获取指数RPS强度排名数据时，可以通过`periods`参数指定需要计算的时间周期，多个周期用逗号分隔。
2. 如果需要保存数据到数据库，可以设置`save=true`参数。
3. 查询历史RPS数据时，可以通过`period`参数指定需要查询的时间周期。
4. 历史数据支持分页查询，可以通过`limit`和`offset`参数进行控制。

## 数据说明

- RPS (Relative Price Strength) 是相对价格强度指标，用于衡量一个指数相对于其他指数的强弱程度。
- RPS计算公式: RPS = (1 - 排名 / 总板块数) × 100
- RPS值越高，表示该指数的相对强度越高。