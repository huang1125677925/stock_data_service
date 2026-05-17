# 价值股选取策略接口文档

## 概述

价值股选取策略接口用于从 Tushare 财报数据中筛选营收保持正增长、净利润水平较高的股票，并支持查询这些股票过去一段时间的营收和净利润历史。

接口基础路径：

```text
/django/api/strategy/
```

数据来源：

- `income_vip`: 利润表数据，主要使用营业收入、净利润、归母净利润。
- `fina_indicator_vip`: 财务指标数据，主要使用营收同比、净利润同比、ROE、毛利率。
- 本地 `individual_stock` 表：用于补充股票名称。

说明：Tushare 财报 VIP 接口通常需要对应积分权限。如果权限不足，接口会在 `errors` 字段返回 Tushare 调用错误。

## 1. 获取价值股候选列表

### 接口地址

```http
GET /django/api/strategy/value-stocks/
```

### 功能说明

从最新可用财报期中筛选股票，筛选条件为：

- 营收同比增长率大于 `min_revenue_growth`，默认大于 `0`。
- 净利润大于等于 `min_net_profit`，默认大于等于 `0`。
- 结果按净利润降序排序，净利润相同时按营收同比增长率降序排序。

如果未传 `report_period`，接口会从当前日期开始向前查找最近可用财报期，默认最多回看 8 个季度。

### 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `report_period` | string | 否 | 自动查找 | 财报期，格式 `YYYYMMDD`，例如 `20240331`、`20231231` |
| `min_revenue_growth` | number | 否 | `0` | 最低营收同比增长率，单位 `%` |
| `min_net_profit` | number | 否 | `0` | 最低净利润，单位元 |
| `limit` | integer | 否 | `50` | 返回数量，最大 `2000` |
| `lookback_periods` | integer | 否 | `8` | 未指定财报期时最多向前查找的季度数，最大 `16` |

### 请求示例

```bash
curl "http://localhost:8000/django/api/strategy/value-stocks/?min_revenue_growth=10&min_net_profit=1000000000&limit=30"
```

指定财报期：

```bash
curl "http://localhost:8000/django/api/strategy/value-stocks/?report_period=20240331&min_revenue_growth=0&limit=50"
```

### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-05-17T10:20:30.123456",
  "data": {
    "report_period": "20240331",
    "total": 2,
    "matched_total": 128,
    "filters": {
      "min_revenue_growth": 10.0,
      "min_net_profit": 1000000000.0,
      "limit": 2,
      "lookback_periods": 8
    },
    "data": [
      {
        "ts_code": "600519.SH",
        "stock_code": "600519",
        "stock_name": "贵州茅台",
        "report_period": "20240331",
        "ann_date": "20240403",
        "f_ann_date": "20240403",
        "total_revenue": 46484700000.0,
        "net_profit": 24065000000.0,
        "revenue_growth_rate": 18.11,
        "net_profit_growth_rate": 15.73,
        "roe": 9.2345,
        "gross_profit_margin": 91.2312
      }
    ],
    "errors": [],
    "query_time": "2026-05-17T10:20:30.123456"
  }
}
```

### 响应字段说明

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `report_period` | string | 实际使用的财报期 |
| `total` | integer | 当前返回记录数 |
| `matched_total` | integer | 满足筛选条件的总记录数 |
| `filters` | object | 本次请求实际使用的筛选条件 |
| `data[].ts_code` | string | Tushare 股票代码 |
| `data[].stock_code` | string | 6 位股票代码 |
| `data[].stock_name` | string/null | 股票名称，来自本地 `individual_stock` 表 |
| `data[].ann_date` | string/null | 公告日期 |
| `data[].f_ann_date` | string/null | 实际公告日期 |
| `data[].total_revenue` | number/null | 营业总收入，单位元 |
| `data[].net_profit` | number/null | 净利润，优先使用归母净利润 `n_income_attr_p`，缺失时使用 `n_income` |
| `data[].revenue_growth_rate` | number/null | 营收同比增长率，优先使用 `or_yoy`，缺失时使用 `q_sales_yoy` |
| `data[].net_profit_growth_rate` | number/null | 净利润同比增长率，优先使用 `netprofit_yoy`，缺失时使用 `q_profit_yoy` |
| `data[].roe` | number/null | ROE |
| `data[].gross_profit_margin` | number/null | 毛利率 |
| `errors` | array | 自动回看财报期或调用 Tushare 时产生的错误信息 |

## 2. 获取营收历史

### 接口地址

```http
GET /django/api/strategy/value-stocks/revenue-history/
```

### 功能说明

根据一个或多个 Tushare 股票代码，查询最近若干个财报期的营业收入和净利润数据。该接口适合前端在价值股列表中选中股票后绘制营收趋势图。

### 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `ts_codes` | string | 是 | - | Tushare 股票代码，多个用英文逗号分隔，例如 `600519.SH,000333.SZ` |
| `periods` | integer | 否 | `8` | 返回最近财报期数量，最大 `16` |

### 请求示例

```bash
curl "http://localhost:8000/django/api/strategy/value-stocks/revenue-history/?ts_codes=600519.SH,000333.SZ&periods=8"
```

### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-05-17T10:20:30.123456",
  "data": {
    "total": 2,
    "periods": [
      "20260331",
      "20251231",
      "20250930",
      "20250630",
      "20250331",
      "20241231",
      "20240930",
      "20240630"
    ],
    "data": [
      {
        "ts_code": "600519.SH",
        "stock_code": "600519",
        "stock_name": "贵州茅台",
        "history": [
          {
            "report_period": "20251231",
            "ann_date": "20260330",
            "f_ann_date": "20260330",
            "total_revenue": 174500000000.0,
            "net_profit": 86000000000.0
          }
        ]
      }
    ],
    "errors": [],
    "query_time": "2026-05-17T10:20:30.123456"
  }
}
```

### 响应字段说明

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `total` | integer | 查询股票数量 |
| `periods` | string[] | 本次尝试查询的财报期列表 |
| `data[].ts_code` | string | Tushare 股票代码 |
| `data[].stock_code` | string | 6 位股票代码 |
| `data[].stock_name` | string/null | 股票名称，来自本地 `individual_stock` 表 |
| `data[].history` | array | 该股票的财报历史数据 |
| `data[].history[].report_period` | string | 财报期 |
| `data[].history[].ann_date` | string/null | 公告日期 |
| `data[].history[].f_ann_date` | string/null | 实际公告日期 |
| `data[].history[].total_revenue` | number/null | 营业总收入，单位元 |
| `data[].history[].net_profit` | number/null | 净利润，优先使用归母净利润，缺失时使用净利润 |
| `errors` | array | Tushare 调用错误列表 |

## 错误响应

项目统一错误响应结构如下：

```json
{
  "code": 400,
  "message": "report_period 参数格式错误，应为 YYYYMMDD",
  "timestamp": "2026-05-17T10:20:30.123456",
  "data": null
}
```

常见错误：

| code | 场景 |
| --- | --- |
| `400` | 参数格式错误，例如 `report_period` 不是 `YYYYMMDD`，或 `ts_codes` 为空 |
| `500` | Tushare 调用异常、服务内部异常 |

## 数据口径

- 营收使用 `income_vip.total_revenue`，缺失时使用 `income_vip.revenue`。
- 净利润优先使用 `income_vip.n_income_attr_p`，缺失时使用 `income_vip.n_income`。
- 营收同比增长率优先使用 `fina_indicator_vip.or_yoy`，缺失时使用 `fina_indicator_vip.q_sales_yoy`。
- 净利润同比增长率优先使用 `fina_indicator_vip.netprofit_yoy`，缺失时使用 `fina_indicator_vip.q_profit_yoy`。
- 候选列表排序规则为净利润降序，其次营收同比增长率降序。
