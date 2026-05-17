# 股票股息率接口文档

## 接口说明

用于从 Tushare `daily_basic` 获取 A 股股票股息率数据，适合价值股分析、红利股筛选和股息率横向对比。

- 接口地址：`GET /django/api/stock/dividend-yield/`
- 请求方式：`GET`
- 数据源：Tushare `daily_basic`

## 适用场景

- 查询单只股票最近交易日的股息率
- 查询某一交易日全市场股息率排行
- 按 `dv_ttm` 或 `dv_ratio` 筛选高股息股票
- 联合 `PE/PB/市值` 做价值股观察

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| ----- | ---- | ---- | ----- | ---- |
| `ts_code` | string | 否 | - | 股票代码，支持 `000001`、`sz000001`、`000001.SZ` |
| `trade_date` | string | 否 | 最近交易日 | 交易日期，支持 `YYYYMMDD` 或 `YYYY-MM-DD` |
| `limit` | integer | 否 | `50` | 返回条数，最大 `500` |
| `offset` | integer | 否 | `0` | 偏移量 |
| `sort_by` | string | 否 | `dv_ttm` | 排序字段，支持 `dv_ttm`、`dv_ratio`、`pe`、`pe_ttm`、`pb`、`ps_ttm`、`total_mv`、`circ_mv`、`close` |
| `order` | string | 否 | `desc` | 排序方向，支持 `asc`、`desc` |
| `min_dv_ttm` | float | 否 | - | 最低 TTM 股息率筛选 |
| `min_dv_ratio` | float | 否 | - | 最低股息率筛选 |

## 说明

- 如果不传 `trade_date`，后端会自动取最近交易日。
- 如果传了 `ts_code` 但没传 `trade_date`，默认查该股票最近交易日快照。
- 返回中的 `name`、`industry` 优先从本地 `IndividualStock` 表补充。
- 返回中的数值字段会清洗 `NaN` 和无穷值，保证符合 JSON 规范。

## 返回字段

顶层返回：

| 字段名 | 类型 | 说明 |
| ----- | ---- | ---- |
| `code` | integer | 业务状态码，成功为 `200` |
| `message` | string | 状态消息 |
| `timestamp` | string | 响应时间 |
| `data.total` | integer | 过滤后总记录数 |
| `data.items` | array | 股票股息率明细 |
| `data.filters` | object | 请求参数回显 |

`data.items[]` 字段：

| 字段名 | 类型 | 说明 |
| ----- | ---- | ---- |
| `ts_code` | string | Tushare 股票代码 |
| `code` | string | 6位股票代码 |
| `name` | string/null | 股票名称 |
| `industry` | string/null | 所属行业 |
| `trade_date` | string | 交易日，格式 `YYYYMMDD` |
| `close` | float/null | 收盘价 |
| `pe` | float/null | 市盈率 |
| `pe_ttm` | float/null | 市盈率TTM |
| `pb` | float/null | 市净率 |
| `ps` | float/null | 市销率 |
| `ps_ttm` | float/null | 市销率TTM |
| `dv_ratio` | float/null | 股息率（%） |
| `dv_ttm` | float/null | 股息率TTM（%） |
| `total_mv` | float/null | 总市值（万元） |
| `circ_mv` | float/null | 流通市值（万元） |

## 返回示例

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-05-17T14:20:00",
  "data": {
    "total": 2,
    "items": [
      {
        "ts_code": "600000.SH",
        "code": "600000",
        "name": "浦发银行",
        "industry": "银行",
        "trade_date": "20260515",
        "close": 10.52,
        "pe": 5.21,
        "pe_ttm": 5.08,
        "pb": 0.62,
        "ps": 1.95,
        "ps_ttm": 1.88,
        "dv_ratio": 4.26,
        "dv_ttm": 4.31,
        "total_mv": 30876543.21,
        "circ_mv": 30876543.21
      },
      {
        "ts_code": "601398.SH",
        "code": "601398",
        "name": "工商银行",
        "industry": "银行",
        "trade_date": "20260515",
        "close": 6.91,
        "pe": 5.87,
        "pe_ttm": 5.73,
        "pb": 0.59,
        "ps": 2.21,
        "ps_ttm": 2.15,
        "dv_ratio": 4.85,
        "dv_ttm": 4.92,
        "total_mv": 245678901.23,
        "circ_mv": 186543210.45
      }
    ],
    "filters": {
      "ts_code": null,
      "trade_date": "20260515",
      "sort_by": "dv_ttm",
      "order": "desc",
      "min_dv_ttm": 4.0,
      "min_dv_ratio": null,
      "limit": 50,
      "offset": 0
    }
  }
}
```

## 示例用法

查询单只股票最近交易日股息率：

```http
GET /django/api/stock/dividend-yield/?ts_code=600000
```

查询指定交易日全市场高股息排行：

```http
GET /django/api/stock/dividend-yield/?trade_date=20260515&sort_by=dv_ttm&order=desc&limit=100
```

筛选股息率 TTM 大于 3% 的股票：

```http
GET /django/api/stock/dividend-yield/?trade_date=20260515&min_dv_ttm=3
```

按静态股息率升序查看：

```http
GET /django/api/stock/dividend-yield/?trade_date=20260515&sort_by=dv_ratio&order=asc
```

## 错误场景

- `trade_date` 格式错误时返回 `400`
- `sort_by` 不在允许列表中时返回 `400`
- `order` 不是 `asc/desc` 时返回 `400`
- `ts_code` 无法识别时返回 `400`
- Tushare 调用失败时返回 `500`

## 实现位置

- 路由：[industry_stock_data/urls.py](/Users/huangchuang/stock_data_service/industry_stock_data/urls.py)
- 视图：[industry_stock_data/views.py](/Users/huangchuang/stock_data_service/industry_stock_data/views.py)
