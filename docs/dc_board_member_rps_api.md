# 东财板块成分股 RPS 接口文档

## 概述

该接口用于查询指定东方财富板块的成分股，并基于成分股在不同交易日周期内的区间涨跌幅，计算成分股的相对强弱排名（RPS, Relative Price Strength）。

当前接口默认面向 `BK1462.DC` 板块，但也支持通过请求参数传入其他东财板块代码进行复用。

接口基础路径：

```text
/django/api/strategy/
```

接口地址：

```http
GET /django/api/strategy/dc-board-member-rps/
```

数据来源：

- `dc_member`：获取东财板块在指定交易日的成分股列表
- `dc_index`：获取东财板块名称及交易日信息
- `daily`：获取成分股在指定交易日的日线快照
- `trade_cal`：通过项目内交易日历工具回推各周期的起始交易日

适用场景：

- 查看 `BK1462.DC` 板块内哪些成分股最近更强
- 比较板块内部个股在 `5`、`20`、`60` 等不同周期上的强弱分布
- 为板块内龙头识别、轮动跟踪、前端榜单展示提供基础数据

## 计算逻辑

接口计算逻辑与 `/django/api/strategy/index-rps/` 的 RPS 口径保持一致，只是将比较对象从“板块”切换为“指定板块的成分股”。

### 1. 成分股获取

先调用 Tushare `dc_member` 接口，按 `trade_date + ts_code` 获取指定东财板块在该交易日下的成分股列表。

### 2. 交易日回推

根据请求中的 `trade_date` 作为截止交易日，按交易日历回推每个周期对应的起始交易日。例如：

- `period=5` 表示回看 5 个交易日
- `period=20` 表示回看 20 个交易日
- `period=60` 表示回看 60 个交易日

说明：这里按交易日回推，不按自然日回推。

### 3. 行情快照获取

分别获取：

- 截止交易日的成分股日线快照
- 各回看周期起始交易日的成分股日线快照

行情来源为 Tushare `daily` 接口，主要使用字段：

- `close`
- `pct_chg`

### 4. 区间涨跌幅计算

对每只成分股，按下述公式计算周期收益率：

```text
return_p = (close_end / close_start - 1) * 100
```

其中：

- `close_end` 为截止交易日收盘价
- `close_start` 为该周期起始交易日收盘价
- `p` 为周期值，例如 `5`、`20`、`60`

### 5. RPS 计算

RPS 公式如下：

```text
RPS = (1 - rank / total) * 100
```

其中：

- `rank` 为按涨跌幅或区间收益率降序排名后的名次
- `total` 为参与排名的成分股总数

补充说明：

- `RPS_today`：按截止交易日当天 `pct_change` 横向计算
- `RPS_5`、`RPS_20`、`RPS_60`：分别按对应周期的区间涨跌幅横向计算
- 数值越高，说明该股票在板块内部相对更强

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `ts_code` | string | 否 | `BK1462.DC` | 东财板块代码，例如 `BK1462.DC` |
| `periods` | string | 否 | `5,20,60` | 回看交易日周期，多个周期用英文逗号分隔，例如 `5,10,20,60` |
| `trade_date` | string | 否 | 最新交易日 | 截止交易日，格式 `YYYYMMDD` |
| `token` | string | 否 | 环境变量 | Tushare Token，传入后会覆盖环境变量中的配置 |

## 请求示例

默认查询 `BK1462.DC` 最新交易日的成分股 RPS：

```bash
curl "http://localhost:8000/django/api/strategy/dc-board-member-rps/"
```

指定交易日和周期：

```bash
curl "http://localhost:8000/django/api/strategy/dc-board-member-rps/?ts_code=BK1462.DC&periods=5,20,60&trade_date=20260626"
```

查询其他东财板块：

```bash
curl "http://localhost:8000/django/api/strategy/dc-board-member-rps/?ts_code=BK1184.DC&periods=5,10,20&trade_date=20260626"
```

## 成功响应示例

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-06-26T23:15:30.123456",
  "data": {
    "total": 3,
    "data": [
      {
        "ts_code": "300024.SZ",
        "name": "机器人",
        "pct_change": 6.52,
        "RPS_today": 66.67,
        "return_5": 12.48,
        "RPS_5": 66.67,
        "return_20": 24.31,
        "RPS_20": 66.67,
        "return_60": 38.95,
        "RPS_60": 66.67
      },
      {
        "ts_code": "002472.SZ",
        "name": "双环传动",
        "pct_change": 3.15,
        "RPS_today": 33.33,
        "return_5": 8.02,
        "RPS_5": 33.33,
        "return_20": 18.47,
        "RPS_20": 33.33,
        "return_60": 22.64,
        "RPS_60": 33.33
      },
      {
        "ts_code": "601727.SH",
        "name": "上海电气",
        "pct_change": -1.08,
        "RPS_today": 0.0,
        "return_5": -2.63,
        "RPS_5": 0.0,
        "return_20": 5.32,
        "RPS_20": 0.0,
        "return_60": 7.96,
        "RPS_60": 0.0
      }
    ],
    "periods": [5, 20, 60],
    "board_ts_code": "BK1462.DC",
    "board_name": "示例板块",
    "trade_date": "20260626",
    "member_count": 3,
    "errors": [],
    "query_time": "2026-06-26T23:15:30.123456"
  }
}
```

## 响应字段说明

### 顶层字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | integer | 业务状态码，`200` 表示成功 |
| `message` | string | 响应消息，成功时通常为 `success` |
| `timestamp` | string | 服务端响应时间，ISO 格式 |
| `data` | object/null | 成功时为对象，失败时为 `null` |

### data 对象字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `total` | integer | 当前返回记录数 |
| `data` | array | 成分股 RPS 结果列表 |
| `periods` | integer[] | 实际参与计算的周期列表 |
| `board_ts_code` | string | 本次查询的东财板块代码 |
| `board_name` | string | 板块名称 |
| `trade_date` | string | 实际使用的截止交易日，格式 `YYYYMMDD` |
| `member_count` | integer | 成分股数量 |
| `errors` | string[] | 非致命错误或告警列表 |
| `query_time` | string | 本次查询生成时间，ISO 格式 |

### data.data[] 字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `ts_code` | string | 成分股 Tushare 股票代码 |
| `name` | string | 成分股名称 |
| `pct_change` | number/null | 截止交易日当天涨跌幅，对应 Tushare `pct_chg` |
| `RPS_today` | number | 按当天涨跌幅横向计算得到的 RPS |
| `return_{period}` | number/null | 某周期的区间收益率，例如 `return_5` |
| `RPS_{period}` | number/null | 某周期区间收益率对应的 RPS，例如 `RPS_5` |

说明：

- `return_{period}` 和 `RPS_{period}` 的列名由请求参数 `periods` 动态生成
- 排序默认按第一个周期对应的 `RPS_{period}` 倒序排列
- 若个别股票在某个起始交易日无有效收盘价，则该周期字段可能为空字符串或空值

## 错误响应示例

### 周期参数格式错误

```json
{
  "code": 400,
  "message": "周期参数格式错误，应为逗号分隔的整数",
  "timestamp": "2026-06-26T23:15:30.123456",
  "data": null
}
```

### 未获取到成分股或行情数据

```json
{
  "code": 500,
  "message": "获取板块成分股RPS排名失败: 未获取到板块成分股列表或 trade_date 无数据",
  "timestamp": "2026-06-26T23:15:30.123456",
  "data": null
}
```

## 常见错误说明

| code | 场景 | 说明 |
| --- | --- | --- |
| `400` | 参数错误 | 例如 `periods` 不是逗号分隔整数 |
| `500` | 数据获取失败 | 例如板块无成分股数据、日线快照缺失、交易日历不足 |

说明：项目统一采用响应体中的 `code` 作为业务状态码判断依据，错误响应在 HTTP 层通常仍返回 `200`。

## 使用建议

- 建议优先使用默认周期 `5,20,60`，分别观察短线、波段和中期强弱
- 如果前端只展示榜单，建议按返回顺序直接渲染，接口已按首个周期 RPS 倒序排序
- 若用于日内观察，建议在收盘后使用，避免当天行情尚未完整落库导致数据不完整
- 若需扩展到更多东财板块，可直接传不同的 `ts_code`，无需新增接口

## 与相关接口的区别

### `/django/api/strategy/index-rps/`

- 比较对象：东财板块之间的强弱排名
- 输出主体：板块
- 适合用途：判断当前强势板块、题材轮动方向

### `/django/api/strategy/dc-board-member-rps/`

- 比较对象：某一个东财板块内部成分股之间的强弱排名
- 输出主体：个股
- 适合用途：在某个重点板块内部筛选相对强势个股

## 相关源码

- 视图入口：`stock_strategy/views.py`
- 路由配置：`stock_strategy/urls.py`
- 计算逻辑：`scheduled_tasks/stock_data_query_tasks/dc_board_member_rps.py`
