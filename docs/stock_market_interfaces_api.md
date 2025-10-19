# 股票市场API接口文档

本文档详细描述了股票市场相关的API接口，包括指数基础数据、指数涨跌统计、涨跌比数据和大盘资金流数据的查询接口。

## 接口概览

| 接口名称 | URL路径 | 请求方法 | 功能描述 |
|---------|---------|----------|----------|
| 指数基础数据接口 | `/django/api/market/index-basic-data/` | GET, POST, PUT, DELETE | 指数基础信息的增删改查 |
| 指数涨跌统计接口 | `/django/api/market/index-high-low-statistics/` | GET | 查询指数涨跌统计数据 |
| 涨跌比数据接口 | `/django/api/market/rise-fall-ratio/` | GET | 查询指数涨跌比历史数据 |
| 大盘资金流接口 | `/django/api/market/fund-flow/` | GET | 查询大盘资金流数据 |

---

## 1. 指数基础数据接口

### 接口信息
- **URL**: `/django/api/market/index-basic-data/`
- **请求方法**: GET, POST, PUT, DELETE
- **功能描述**: 提供指数基础数据的增删改查操作，支持分页查询和搜索功能

### 数据模型
指数基础数据包含以下字段：
- `id`: 主键ID
- `code`: 指数代码
- `name`: 指数名称
- `created_at`: 创建时间
- `updated_at`: 更新时间

### GET 请求 - 查询指数列表

#### 请求参数
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| page | int | 否 | 1 | 页码 |
| page_size | int | 否 | 20 | 每页数量，最大100 |
| search | string | 否 | - | 搜索关键词，支持按代码或名称搜索 |
| code | string | 否 | - | 精确匹配指数代码 |

#### 请求示例
```bash
# 查询第一页数据
GET /django/api/market/index-basic-data/?page=1&page_size=10

# 搜索包含"沪深"的指数
GET /django/api/market/index-basic-data/?search=沪深

# 精确查询指数代码
GET /django/api/market/index-basic-data/?code=000001
```

#### 响应参数
| 参数名 | 类型 | 说明 |
|--------|------|------|
| code | int | 响应状态码，200表示成功 |
| message | string | 响应消息 |
| data | object | 响应数据 |
| data.list | array | 指数数据列表 |
| data.list[].id | int | 指数ID |
| data.list[].code | string | 指数代码 |
| data.list[].name | string | 指数名称 |
| data.list[].created_at | string | 创建时间（ISO格式） |
| data.list[].updated_at | string | 更新时间（ISO格式） |
| data.pagination | object | 分页信息 |
| data.pagination.current_page | int | 当前页码 |
| data.pagination.total_pages | int | 总页数 |
| data.pagination.total_count | int | 总记录数 |
| data.pagination.page_size | int | 每页数量 |
| data.pagination.has_next | boolean | 是否有下一页 |
| data.pagination.has_previous | boolean | 是否有上一页 |

#### 成功响应示例
```json
{
    "code": 200,
    "message": "查询成功",
    "data": {
        "list": [
            {
                "id": 1,
                "code": "000001",
                "name": "上证指数",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        ],
        "pagination": {
            "current_page": 1,
            "total_pages": 5,
            "total_count": 50,
            "page_size": 10,
            "has_next": true,
            "has_previous": false
        }
    }
}
```

### POST 请求 - 创建指数记录

#### 请求参数
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| code | string | 是 | 指数代码 |
| name | string | 是 | 指数名称 |

#### 请求示例
```json
POST /django/api/market/index-basic-data/
Content-Type: application/json

{
    "code": "000002",
    "name": "深证成指"
}
```

### PUT 请求 - 更新指数信息

#### 请求参数
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | int | 是 | 指数ID |
| code | string | 否 | 指数代码 |
| name | string | 否 | 指数名称 |

### DELETE 请求 - 删除指数记录

#### 请求参数
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | int | 是 | 指数ID |

---

## 2. 指数涨跌统计接口

### 接口信息
- **URL**: `/django/api/market/index-high-low-statistics/`
- **请求方法**: GET
- **功能描述**: 查询指数涨跌统计数据，仅从数据库获取数据

### GET 请求 - 查询涨跌统计数据

#### 请求参数
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| index_code | string | 否 | - | 指数代码，可选值：'all', 'sz50', 'hs300', 'zz500' |
| start_date | string | 否 | - | 开始日期，格式：YYYY-MM-DD |
| end_date | string | 否 | - | 结束日期，格式：YYYY-MM-DD |
| limit | int | 否 | 30 | 返回记录数量限制 |

#### 请求示例
```bash
# 查询沪深300指数最近30条数据
GET /django/api/market/index-high-low-statistics/?index_code=hs300&limit=30

# 查询指定日期范围的数据
GET /django/api/market/index-high-low-statistics/?start_date=2024-01-01&end_date=2024-01-31
```

#### 响应参数
| 参数名 | 类型 | 说明 |
|--------|------|------|
| code | int | 响应状态码，200表示成功 |
| message | string | 响应消息 |
| timestamp | string | 响应时间戳（ISO格式） |
| data | array | 涨跌统计数据列表 |
| data[].id | int | 记录ID |
| data[].date | string | 日期 |
| data[].index_code | string | 指数代码 |
| data[].index_name | string | 指数名称 |
| data[].close | float | 收盘价 |
| data[].high20 | int | 20日新高数量 |
| data[].low20 | int | 20日新低数量 |
| data[].high60 | int | 60日新高数量 |
| data[].low60 | int | 60日新低数量 |
| data[].high120 | int | 120日新高数量 |
| data[].low120 | int | 120日新低数量 |
| data[].rise_fall_ratio_20 | float | 20日涨跌比 |
| data[].rise_fall_ratio_60 | float | 60日涨跌比 |
| data[].rise_fall_ratio_120 | float | 120日涨跌比 |
| data[].created_at | string | 创建时间 |
| data[].updated_at | string | 更新时间 |

#### 成功响应示例
```json
{
    "code": 200,
    "message": "查询指数涨跌统计数据成功",
    "timestamp": "2025-10-19T20:40:59.938882",
    "data": [
        {
            "id": 1,
            "date": "2025-10-17",
            "index_code": "all",
            "index_name": "全部A股",
            "close": 3839.76,
            "high20": 185,
            "low20": 2115,
            "high60": 102,
            "low60": 1037,
            "high120": 87,
            "low120": 211,
            "rise_fall_ratio_20": 0.0804,
            "rise_fall_ratio_60": 0.0896,
            "rise_fall_ratio_120": 0.2919,
            "created_at": "2025-10-19 05:54:28",
            "updated_at": "2025-10-19 05:54:29"
        }
    ]
}
```

---

## 3. 涨跌比数据接口

### 接口信息
- **URL**: `/django/api/market/rise-fall-ratio/`
- **请求方法**: GET
- **功能描述**: 查询指数的涨跌比历史数据

### GET 请求 - 查询涨跌比数据

#### 请求参数
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| index_code | string | 否 | - | 指数代码，不指定则查询所有 |
| start_date | string | 否 | - | 开始日期，格式：YYYY-MM-DD |
| end_date | string | 否 | - | 结束日期，格式：YYYY-MM-DD |
| limit | int | 否 | 500 | 返回记录数限制，范围：1-1000 |

#### 请求示例
```bash
# 查询所有指数最近500条涨跌比数据
GET /django/api/market/rise-fall-ratio/?limit=500

# 查询特定指数和日期范围的数据
GET /django/api/market/rise-fall-ratio/?index_code=sz50&start_date=2024-01-01&end_date=2024-01-31
```

#### 响应参数
| 参数名 | 类型 | 说明 |
|--------|------|------|
| code | int | 响应状态码，200表示成功 |
| message | string | 响应消息 |
| timestamp | string | 响应时间戳（ISO格式） |
| data | object | 响应数据 |
| data.count | int | 返回记录数量 |
| data.results | array | 涨跌比数据列表 |
| data.results[].id | int | 记录ID |
| data.results[].date | string | 日期 |
| data.results[].index_code | string | 指数代码 |
| data.results[].index_name | string | 指数名称 |
| data.results[].close | float | 收盘价 |
| data.results[].high20 | int | 20日新高数量 |
| data.results[].low20 | int | 20日新低数量 |
| data.results[].high60 | int | 60日新高数量 |
| data.results[].low60 | int | 60日新低数量 |
| data.results[].high120 | int | 120日新高数量 |
| data.results[].low120 | int | 120日新低数量 |
| data.results[].rise_fall_ratio_20 | float | 20日涨跌比 |
| data.results[].rise_fall_ratio_60 | float | 60日涨跌比 |
| data.results[].rise_fall_ratio_120 | float | 120日涨跌比 |
| data.results[].created_at | string | 创建时间 |
| data.results[].updated_at | string | 更新时间 |

#### 成功响应示例
```json
{
    "code": 200,
    "message": "查询涨跌比数据成功",
    "timestamp": "2025-10-19T20:41:17.306486",
    "data": {
        "count": 3,
        "results": [
            {
                "id": 1,
                "date": "2025-10-17",
                "index_code": "all",
                "index_name": "全部A股",
                "close": 3839.76,
                "high20": 185,
                "low20": 2115,
                "high60": 102,
                "low60": 1037,
                "high120": 87,
                "low120": 211,
                "rise_fall_ratio_20": 0.0804,
                "rise_fall_ratio_60": 0.0896,
                "rise_fall_ratio_120": 0.2919,
                "created_at": "2025-10-19 05:54:28",
                "updated_at": "2025-10-19 05:54:29"
            }
        ]
    }
}
```

---

## 4. 大盘资金流接口

### 接口信息
- **URL**: `/django/api/market/fund-flow/`
- **请求方法**: GET
- **功能描述**: 查询大盘资金流数据，支持分页和日期范围查询

### 数据模型
大盘资金流数据包含以下字段：
- `id`: 主键ID
- `date`: 日期
- `main_net_inflow_amount`: 主力净流入金额
- `small_net_inflow_amount`: 小单净流入金额
- `medium_net_inflow_amount`: 中单净流入金额
- `large_net_inflow_amount`: 大单净流入金额
- `super_large_net_inflow_amount`: 超大单净流入金额
- `main_net_inflow_ratio`: 主力净流入比例
- `small_net_inflow_ratio`: 小单净流入比例
- `medium_net_inflow_ratio`: 中单净流入比例
- `large_net_inflow_ratio`: 大单净流入比例
- `super_large_net_inflow_ratio`: 超大单净流入比例
- `shanghai_close_price`: 上证收盘价
- `shanghai_change_rate`: 上证涨跌幅
- `shenzhen_close_price`: 深证收盘价
- `shenzhen_change_rate`: 深证涨跌幅
- `created_at`: 创建时间
- `updated_at`: 更新时间

### GET 请求 - 查询资金流数据

#### 请求参数
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| start_date | string | 否 | - | 开始日期，格式：YYYY-MM-DD |
| end_date | string | 否 | - | 结束日期，格式：YYYY-MM-DD |
| page | int | 否 | 1 | 页码，必须大于0 |
| page_size | int | 否 | 20 | 每页数量，最大100 |
| order_by | string | 否 | -date | 排序字段，可选值：date, -date, created_at, -created_at |

#### 请求示例
```bash
# 查询第一页数据，每页5条
GET /django/api/market/fund-flow/?page=1&page_size=5

# 查询指定日期范围的数据
GET /django/api/market/fund-flow/?start_date=2024-01-01&end_date=2024-01-31&page=1&page_size=10

# 按日期正序排列
GET /django/api/market/fund-flow/?order_by=date&page=1&page_size=20
```

#### 响应参数
| 参数名 | 类型 | 说明 |
|--------|------|------|
| code | int | 响应状态码，200表示成功 |
| message | string | 响应消息 |
| data | object | 响应数据 |
| data.list | array | 资金流数据列表 |
| data.list[].id | int | 记录ID |
| data.list[].date | string | 日期（ISO格式） |
| data.list[].main_net_inflow_amount | float | 主力净流入金额 |
| data.list[].small_net_inflow_amount | float | 小单净流入金额 |
| data.list[].medium_net_inflow_amount | float | 中单净流入金额 |
| data.list[].large_net_inflow_amount | float | 大单净流入金额 |
| data.list[].super_large_net_inflow_amount | float | 超大单净流入金额 |
| data.list[].main_net_inflow_ratio | float | 主力净流入比例 |
| data.list[].small_net_inflow_ratio | float | 小单净流入比例 |
| data.list[].medium_net_inflow_ratio | float | 中单净流入比例 |
| data.list[].large_net_inflow_ratio | float | 大单净流入比例 |
| data.list[].super_large_net_inflow_ratio | float | 超大单净流入比例 |
| data.list[].shanghai_close_price | float | 上证收盘价 |
| data.list[].shanghai_change_rate | float | 上证涨跌幅 |
| data.list[].shenzhen_close_price | float | 深证收盘价 |
| data.list[].shenzhen_change_rate | float | 深证涨跌幅 |
| data.list[].created_at | string | 创建时间（ISO格式） |
| data.list[].updated_at | string | 更新时间（ISO格式） |
| data.pagination | object | 分页信息 |
| data.pagination.current_page | int | 当前页码 |
| data.pagination.total_pages | int | 总页数 |
| data.pagination.total_count | int | 总记录数 |
| data.pagination.page_size | int | 每页数量 |
| data.pagination.has_next | boolean | 是否有下一页 |
| data.pagination.has_previous | boolean | 是否有上一页 |

#### 成功响应示例
```json
{
    "code": 200,
    "message": "查询大盘资金流数据成功",
    "data": {
        "list": [
            {
                "id": 1,
                "date": "2024-01-15",
                "main_net_inflow_amount": 1234567890.12,
                "small_net_inflow_amount": -234567890.12,
                "medium_net_inflow_amount": 345678901.23,
                "large_net_inflow_amount": 456789012.34,
                "super_large_net_inflow_amount": 567890123.45,
                "main_net_inflow_ratio": 0.15,
                "small_net_inflow_ratio": -0.05,
                "medium_net_inflow_ratio": 0.08,
                "large_net_inflow_ratio": 0.12,
                "super_large_net_inflow_ratio": 0.18,
                "shanghai_close_price": 3456.78,
                "shanghai_change_rate": 1.25,
                "shenzhen_close_price": 12345.67,
                "shenzhen_change_rate": -0.85,
                "created_at": "2024-01-15T09:30:00",
                "updated_at": "2024-01-15T15:00:00"
            }
        ],
        "pagination": {
            "current_page": 1,
            "total_pages": 10,
            "total_count": 100,
            "page_size": 10,
            "has_next": true,
            "has_previous": false
        }
    }
}
```

---

## 错误响应

所有接口在发生错误时都会返回统一的错误响应格式：

### 错误响应格式
```json
{
    "code": 400,
    "message": "参数格式错误: 页码必须大于0",
    "data": null
}
```

### 常见错误码
| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 重要说明

1. **数据来源**: 所有股票相关功能模块的API代码只从数据库获取数据，不直接调用外部数据源
2. **响应格式**: 所有接口统一使用 `success_response` 和 `error_response` 返回数据
3. **日期格式**: 所有日期参数和返回值均使用 ISO 8601 格式（YYYY-MM-DD 或 YYYY-MM-DDTHH:MM:SS）
4. **分页限制**: 为了性能考虑，分页查询的每页最大数量限制为100条
5. **数据精度**: 金额和比例数据保持原始精度，以浮点数形式返回
6. **时区**: 所有时间数据均为服务器本地时区

---

## 联系信息

如有问题或建议，请联系开发团队。