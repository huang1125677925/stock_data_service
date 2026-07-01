# 股票市场API接口文档

本文档详细描述了股票市场相关的API接口，包括指数基础数据、指数涨跌统计、涨跌比数据、大盘资金流数据查询接口，以及基于 Tushare 的大盘资金流趋势接口。

## 接口概览

| 接口名称 | URL路径 | 请求方法 | 功能描述 |
|---------|---------|----------|----------|
| 指数基础数据接口 | `/django/api/market/index-basic-data/` | GET, POST, PUT, DELETE | 指数基础信息的增删改查 |
| 指数涨跌统计接口 | `/django/api/market/index-high-low-statistics/` | GET | 查询指数涨跌统计数据 |
| 涨跌比数据接口 | `/django/api/market/rise-fall-ratio/` | GET | 查询指数涨跌比历史数据 |
| 大盘资金流接口 | `/django/api/market/fund-flow/` | GET | 查询大盘资金流数据 |
| 大盘资金流趋势接口 | `/django/api/market/fund-flow/trend/` | GET | 查询指定区间内的大盘资金变化、收盘价变化和涨跌幅变化 |

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

## 5. 大盘资金流趋势接口

### 接口信息
- **URL**: `/django/api/market/fund-flow/trend/`
- **请求方法**: GET
- **功能描述**: 基于 Tushare `moneyflow_mkt_dc` 接口，查询指定交易日或日期区间内的大盘资金流趋势数据，供前端展示资金变化曲线、上证/深证收盘价变化和涨跌幅变化

### 数据来源
- 实时调用 Tushare `moneyflow_mkt_dc`
- 主要用于前端趋势图、区间变化卡片等可视化展示

### GET 请求 - 查询大盘资金流趋势数据

#### 请求参数
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| trade_date | string | 否 | - | 单个交易日，格式支持 `YYYY-MM-DD` 或 `YYYYMMDD` |
| start_date | string | 否 | - | 开始日期，格式支持 `YYYY-MM-DD` 或 `YYYYMMDD` |
| end_date | string | 否 | - | 结束日期，格式支持 `YYYY-MM-DD` 或 `YYYYMMDD` |

#### 参数说明
- `trade_date` 与 `start_date`、`end_date` 不能同时传入
- `trade_date`、`start_date`、`end_date` 三者至少传入一种查询方式
- 当同时传入 `start_date` 和 `end_date` 时，`start_date` 不能晚于 `end_date`

#### 请求示例
```bash
# 查询单个交易日数据
GET /django/api/market/fund-flow/trend/?trade_date=2026-06-30

# 查询指定区间的大盘资金流趋势
GET /django/api/market/fund-flow/trend/?start_date=2026-06-01&end_date=2026-06-30

# 使用 YYYYMMDD 格式查询
GET /django/api/market/fund-flow/trend/?start_date=20260601&end_date=20260630
```

#### 响应参数
| 参数名 | 类型 | 说明 |
|--------|------|------|
| code | int | 响应状态码，200表示成功 |
| message | string | 响应消息 |
| data | object | 响应数据 |
| data.interface | string | 数据源接口标识，固定为 `moneyflow_mkt_dc` |
| data.count | int | 返回记录数量 |
| data.records | array | 趋势明细列表，按交易日升序返回 |
| data.records[].trade_date | string | 交易日期，格式为 `YYYYMMDD` |
| data.records[].close_sh | float | 上证收盘价 |
| data.records[].pct_change_sh | float | 上证涨跌幅（%） |
| data.records[].close_sz | float | 深证收盘价 |
| data.records[].pct_change_sz | float | 深证涨跌幅（%） |
| data.records[].net_amount | float | 主力净流入净额（元） |
| data.records[].net_amount_rate | float | 主力净流入净占比（%） |
| data.records[].buy_elg_amount | float | 超大单净流入净额（元） |
| data.records[].buy_elg_amount_rate | float | 超大单净流入净占比（%） |
| data.records[].buy_lg_amount | float | 大单净流入净额（元） |
| data.records[].buy_lg_amount_rate | float | 大单净流入净占比（%） |
| data.records[].buy_md_amount | float | 中单净流入净额（元） |
| data.records[].buy_md_amount_rate | float | 中单净流入净占比（%） |
| data.records[].buy_sm_amount | float | 小单净流入净额（元） |
| data.records[].buy_sm_amount_rate | float | 小单净流入净占比（%） |
| data.records[].net_amount_change | float | 相对区间首个有效交易日的主力净流入变化值 |
| data.records[].close_sh_change | float | 相对区间首个有效交易日的上证收盘价变化值 |
| data.records[].close_sz_change | float | 相对区间首个有效交易日的深证收盘价变化值 |
| data.summary | object | 区间变化摘要 |
| data.summary.start_date | string | 区间起始交易日 |
| data.summary.end_date | string | 区间结束交易日 |
| data.summary.record_count | int | 区间记录数 |
| data.summary.net_amount_change | float | 区间主力净流入变化值 |
| data.summary.shanghai_close_change | float | 区间上证收盘价变化值 |
| data.summary.shenzhen_close_change | float | 区间深证收盘价变化值 |
| data.summary.shanghai_change_rate_span | float | 区间上证涨跌幅变化值 |
| data.summary.shenzhen_change_rate_span | float | 区间深证涨跌幅变化值 |
| data.query | object | 本次查询条件 |
| data.query.trade_date | string | 单日查询条件 |
| data.query.start_date | string | 区间开始日期 |
| data.query.end_date | string | 区间结束日期 |

#### 成功响应示例
```json
{
    "code": 200,
    "message": "查询大盘资金流趋势数据成功",
    "data": {
        "interface": "moneyflow_mkt_dc",
        "count": 2,
        "records": [
            {
                "trade_date": "20260627",
                "close_sh": 3400.0,
                "pct_change_sh": 0.5,
                "close_sz": 10000.0,
                "pct_change_sz": 0.8,
                "net_amount": 100000000.0,
                "net_amount_rate": 1.1,
                "buy_elg_amount": 25000000.0,
                "buy_elg_amount_rate": 0.6,
                "buy_lg_amount": 18000000.0,
                "buy_lg_amount_rate": 0.4,
                "buy_md_amount": -8000000.0,
                "buy_md_amount_rate": -0.2,
                "buy_sm_amount": -4000000.0,
                "buy_sm_amount_rate": -0.1,
                "net_amount_change": 0.0,
                "close_sh_change": 0.0,
                "close_sz_change": 0.0
            },
            {
                "trade_date": "20260630",
                "close_sh": 3450.0,
                "pct_change_sh": 1.2,
                "close_sz": 10200.0,
                "pct_change_sz": 1.5,
                "net_amount": 150000000.0,
                "net_amount_rate": 2.1,
                "buy_elg_amount": 30000000.0,
                "buy_elg_amount_rate": 0.8,
                "buy_lg_amount": 20000000.0,
                "buy_lg_amount_rate": 0.5,
                "buy_md_amount": -10000000.0,
                "buy_md_amount_rate": -0.3,
                "buy_sm_amount": -5000000.0,
                "buy_sm_amount_rate": -0.1,
                "net_amount_change": 50000000.0,
                "close_sh_change": 50.0,
                "close_sz_change": 200.0
            }
        ],
        "summary": {
            "start_date": "20260627",
            "end_date": "20260630",
            "record_count": 2,
            "net_amount_change": 50000000.0,
            "shanghai_close_change": 50.0,
            "shenzhen_close_change": 200.0,
            "shanghai_change_rate_span": 0.7,
            "shenzhen_change_rate_span": 0.7
        },
        "query": {
            "trade_date": null,
            "start_date": "20260627",
            "end_date": "20260630"
        }
    }
}
```

#### 错误响应示例
```json
{
    "code": 400,
    "message": "开始日期不能晚于结束日期",
    "data": null
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

1. **数据来源**: 大部分股票市场接口从数据库读取；`/django/api/market/fund-flow/trend/` 会实时调用 Tushare `moneyflow_mkt_dc`
2. **响应格式**: 所有接口统一使用 `success_response` 和 `error_response` 返回数据
3. **日期格式**: 数据库类接口通常使用 ISO 8601 格式；`fund-flow/trend` 接口的查询参数兼容 `YYYY-MM-DD` 与 `YYYYMMDD`，返回交易日字段为 `YYYYMMDD`
4. **分页限制**: 为了性能考虑，分页查询的每页最大数量限制为100条
5. **数据精度**: 金额和比例数据保持原始精度，以浮点数形式返回
6. **时区**: 所有时间数据均为服务器本地时区

---

## 联系信息

如有问题或建议，请联系开发团队。
