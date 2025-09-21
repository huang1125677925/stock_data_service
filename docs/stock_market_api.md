# 股票大盘数据 API 文档

## 股票市场每日概况

### 接口信息

- **接口URL**: `/django/api/market/sse-daily-overview/`
- **请求方式**: GET
- **接口描述**: 获取股票市场每日概况数据，包括上证指数、深证成指、沪深300和上证50的指数值、交易额和涨跌幅数据，以及上海证券交易所每日股票交易概况数据。

### 请求参数

| 参数名 | 类型   | 必填 | 描述                                                                |
|--------|--------|------|---------------------------------------------------------------------|
| date   | string | 否   | 查询日期，格式为YYYYMMDD（如：20230101）。若不传，默认获取最近一个交易日数据 |

### 响应参数

| 参数名  | 类型   | 描述                 |
|---------|--------|----------------------|
| code    | int    | 状态码，200表示成功  |
| message | string | 状态信息             |
| data    | object | 返回的数据           |

#### data 对象结构

| 参数名      | 类型   | 描述                                |
|-------------|--------|-------------------------------------|
| date        | string | 查询日期，格式为YYYYMMDD            |
| shanghai    | object | 上证指数数据                        |
| shenzhen    | object | 深证成指数据                        |
| hs300       | object | 沪深300指数数据                     |
| sz50        | object | 上证50指数数据                      |
| sse_daily_data | array  | 上海证券交易所每日概况数据列表（兼容旧版本） |

#### 指数数据对象结构 (shanghai, shenzhen, hs300, sz50)

| 参数名          | 类型   | 描述                 |
|-----------------|--------|----------------------|
| index_name      | string | 指数名称             |
| index_code      | string | 指数代码             |
| latest_value    | float  | 最新指数值           |
| change_percent  | float  | 涨跌幅（%）          |
| volume          | float  | 成交量               |
| amount          | float  | 成交额               |

### 指标说明

#### 指数数据指标
- **latest_value**: 指数最新收盘值
- **change_percent**: 当日涨跌幅（%）
- **volume**: 成交量
- **amount**: 成交额

### 请求示例

```
GET /django/api/market/sse-daily-overview/
```

或者指定日期：

```
GET /django/api/market/sse-daily-overview/?date=20230101
```

### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "date": "20230101",
    "shanghai": {
      "index_name": "上证指数",
      "index_code": "000001",
      "latest_value": 3089.26,
      "change_percent": 0.51,
      "volume": 237.85,
      "amount": 2856.32
    },
    "shenzhen": {
      "index_name": "深证成指",
      "index_code": "399001",
      "latest_value": 11016.42,
      "change_percent": 0.82,
      "volume": 325.67,
      "amount": 4123.45
    },
    "hs300": {
      "index_name": "沪深300",
      "index_code": "000300",
      "latest_value": 3778.84,
      "change_percent": 0.63,
      "volume": 185.42,
      "amount": 2356.78
    },
    "sz50": {
      "index_name": "上证50",
      "index_code": "000016",
      "latest_value": 2678.53,
      "change_percent": 0.42,
      "volume": 98.76,
      "amount": 1567.89
    },
  }
}
```

### 错误响应示例

```json
{
  "code": 400,
  "message": "获取股市指数数据失败: 无法获取指定日期的数据",
  "data": null
}
```

### 注意事项

1. 当前交易日的数据需要在交易所收盘后才能获取
2. 该接口仅支持获取在 20211227（包含）之后的数据
3. 如果查询的日期是非交易日（如周末或节假日），将返回错误信息
4. 数据来源于上海证券交易所和深圳证券交易所官方网站，通过 akshare 接口获取

### 数据来源

- 数据来源: 上海证券交易所、深圳证券交易所
- 数据链接: 
  - 上海证券交易所: http://www.sse.com.cn/market/stockdata/overview/day/
  - 深圳证券交易所: http://www.szse.cn/market/index/index.html