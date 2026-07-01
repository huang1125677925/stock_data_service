# 股票 RPS 接口文档

## 概述

该接口用于查询全市场股票在不同交易日周期内的相对强弱排名（RPS, Relative Price Strength）。

接口会先使用 Tushare `stock_basic` 构建目标交易日对应的有效股票池，再基于 Tushare `daily` 的单日行情快照计算各周期区间收益率和横向 RPS 排名。

与板块 RPS 不同，该接口的比较对象是“股票对股票”，适合直接观察当前全市场或某个交易所、某个市场板块中的强势个股。

接口基础路径：

```text
/django/api/strategy/
```

接口地址：

```http
GET /django/api/strategy/stock-rps/
```

数据来源：

- `stock_basic`：获取股票基础信息、上市日期、退市日期和市场分类
- `daily`：获取股票在指定交易日的日线快照
- `trade_cal`：通过项目内交易日历工具回推各周期的起始交易日

适用场景：

- 查看全市场短中期相对最强的股票
- 筛选某个交易所或某个市场板块中的强势股
- 为前端强势股榜单、轮动跟踪、选股策略提供基础数据

## 计算逻辑

接口整体逻辑参考 `/django/api/strategy/index-rps/` 和 `/django/api/strategy/dc-board-member-rps/`，但股票池来源改为 Tushare `stock_basic`。

### 1. 股票池构建

接口会分别拉取以下三类股票基础信息：

- `list_status=L`：上市
- `list_status=P`：暂停上市
- `list_status=D`：退市

随后根据目标交易日做历史有效性过滤，仅保留满足以下条件的股票：

- `list_date <= trade_date`
- `delist_date` 为空，或 `delist_date >= trade_date`

这样可以保证历史日期下的股票池与当时真实可交易股票范围尽量一致，避免把尚未上市或已退市股票混入排名。

### 2. 交易日回推

根据请求中的 `trade_date` 作为截止交易日，按交易日历回推每个周期对应的起始交易日。例如：

- `period=5` 表示回看 5 个交易日
- `period=20` 表示回看 20 个交易日
- `period=60` 表示回看 60 个交易日

说明：这里按交易日回推，不按自然日回推。

### 3. 行情快照获取

分别获取：

- 截止交易日的股票日线快照
- 各回看周期起始交易日的股票日线快照

行情来源为 Tushare `daily` 接口，主要使用字段：

- `close`
- `pct_chg`

### 4. 区间涨跌幅计算

对每只股票，按下述公式计算周期收益率：

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
- `total` 为参与排名的股票总数

补充说明：

- `RPS_today`：按截止交易日当天 `pct_change` 横向计算
- `RPS_5`、`RPS_20`、`RPS_60`：分别按对应周期的区间收益率横向计算
- 数值越高，说明该股票在当前股票池内相对更强

### 6. 最近可用交易日回退

当未显式传入 `trade_date` 时，接口会先根据 `trade_cal` 获取最近开市日。

如果该日期在 `daily` 中尚无可用快照数据，则会自动向前回退，直到找到最近一个有数据的可用交易日，并在响应 `errors` 字段中给出提示信息。

这可以避免“交易所已开市，但行情快照尚未更新”时接口直接报错。

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `periods` | string | 否 | `5,20,60` | 回看交易日周期，多个周期用英文逗号分隔，例如 `5,10,20,60` |
| `trade_date` | string | 否 | 最近可用交易日 | 截止交易日，格式 `YYYYMMDD` |
| `exchange` | string | 否 | 全市场 | 交易所筛选，可选值通常为 `SSE`、`SZSE`、`BSE` |
| `market` | string | 否 | 全市场 | 市场类型筛选，例如 `主板`、`创业板`、`科创板`、`北交所` |
| `token` | string | 否 | 环境变量 | Tushare Token，传入后会覆盖环境变量中的配置 |

## 请求示例

默认查询最近可用交易日的全市场股票 RPS：

```bash
curl "http://localhost:8000/django/api/strategy/stock-rps/"
```

指定交易日和周期：

```bash
curl "http://localhost:8000/django/api/strategy/stock-rps/?periods=5,20,60&trade_date=20260630"
```

仅查询深交所股票：

```bash
curl "http://localhost:8000/django/api/strategy/stock-rps/?exchange=SZSE&periods=5,20,60"
```

仅查询创业板股票：

```bash
curl "http://localhost:8000/django/api/strategy/stock-rps/?market=创业板&periods=5,20,60"
```

同时指定交易所和市场：

```bash
curl "http://localhost:8000/django/api/strategy/stock-rps/?exchange=SZSE&market=创业板&periods=5,20,60&trade_date=20260630"
```

## 成功响应示例

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-07-01T11:30:00.123456",
  "data": {
    "total": 3,
    "data": [
      {
        "ts_code": "300750.SZ",
        "symbol": "300750",
        "name": "宁德时代",
        "industry": "电气设备",
        "market": "创业板",
        "list_date": "20180611",
        "delist_date": "",
        "list_status": "L",
        "trade_date": "20260630",
        "pct_change": 4.82,
        "RPS_today": 66.67,
        "return_5": 11.34,
        "RPS_5": 66.67,
        "return_20": 18.56,
        "RPS_20": 66.67,
        "return_60": 35.21,
        "RPS_60": 66.67
      },
      {
        "ts_code": "002594.SZ",
        "symbol": "002594",
        "name": "比亚迪",
        "industry": "汽车整车",
        "market": "主板",
        "list_date": "20110630",
        "delist_date": "",
        "list_status": "L",
        "trade_date": "20260630",
        "pct_change": 2.13,
        "RPS_today": 33.33,
        "return_5": 7.85,
        "RPS_5": 33.33,
        "return_20": 12.47,
        "RPS_20": 33.33,
        "return_60": 24.18,
        "RPS_60": 33.33
      },
      {
        "ts_code": "600519.SH",
        "symbol": "600519",
        "name": "贵州茅台",
        "industry": "白酒",
        "market": "主板",
        "list_date": "20010827",
        "delist_date": "",
        "list_status": "L",
        "trade_date": "20260630",
        "pct_change": -0.56,
        "RPS_today": 0.0,
        "return_5": 1.42,
        "RPS_5": 0.0,
        "return_20": 4.88,
        "RPS_20": 0.0,
        "return_60": 9.17,
        "RPS_60": 0.0
      }
    ],
    "periods": [5, 20, 60],
    "trade_date": "20260630",
    "exchange": null,
    "market": null,
    "errors": [],
    "query_time": "2026-07-01T11:30:00.123456"
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
| `data` | array | 股票 RPS 结果列表 |
| `periods` | integer[] | 实际参与计算的周期列表 |
| `trade_date` | string | 实际使用的截止交易日，格式 `YYYYMMDD` |
| `exchange` | string/null | 本次查询使用的交易所筛选条件 |
| `market` | string/null | 本次查询使用的市场类型筛选条件 |
| `errors` | string[] | 非致命错误或告警列表 |
| `query_time` | string | 本次查询生成时间，ISO 格式 |

### data.data[] 字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `ts_code` | string | 股票 Tushare 代码 |
| `symbol` | string | 不带后缀的股票代码 |
| `name` | string | 股票名称 |
| `industry` | string | 股票所属行业，来源于 `stock_basic` |
| `market` | string | 股票所属市场板块，来源于 `stock_basic` |
| `list_date` | string | 上市日期，格式 `YYYYMMDD` |
| `delist_date` | string | 退市日期，未退市时通常为空字符串 |
| `list_status` | string | 当前记录来源状态，常见为 `L`、`P`、`D` |
| `trade_date` | string | 本条记录对应的截止交易日，格式 `YYYYMMDD` |
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
  "timestamp": "2026-07-01T11:30:00.123456",
  "data": null
}
```

### 未获取到股票基础信息

```json
{
  "code": 500,
  "message": "获取股票RPS排名失败: 未获取到股票基础信息",
  "timestamp": "2026-07-01T11:30:00.123456",
  "data": null
}
```

### 未获取到股票行情数据

```json
{
  "code": 500,
  "message": "获取股票RPS排名失败: daily返回空数据: trade_date=20260630",
  "timestamp": "2026-07-01T11:30:00.123456",
  "data": null
}
```

## 常见错误说明

| code | 场景 | 说明 |
| --- | --- | --- |
| `400` | 参数错误 | 例如 `periods` 不是逗号分隔整数 |
| `500` | 数据获取失败 | 例如 `stock_basic` 无数据、`daily` 快照缺失、交易日历不足 |

说明：项目统一采用响应体中的 `code` 作为业务状态码判断依据，错误响应在 HTTP 层通常仍返回 `200`。

## 使用建议

- 建议优先使用默认周期 `5,20,60`，分别观察短线、波段和中期强弱
- 如果只关注特定市场风格，可结合 `exchange` 或 `market` 缩小股票池范围
- 若用于收盘复盘，建议在当日行情快照更新完成后调用，避免最新交易日数据尚未落地
- 若前端只展示排行榜，建议直接按返回顺序渲染，接口已按首个周期 RPS 倒序排列

## 与相关接口的区别

### `/django/api/strategy/index-rps/`

- 比较对象：东财板块之间的强弱排名
- 输出主体：板块
- 适合用途：判断当前强势题材和板块轮动方向

### `/django/api/strategy/dc-board-member-rps/`

- 比较对象：某一个东财板块内部成分股之间的强弱排名
- 输出主体：个股
- 适合用途：在重点板块内部寻找龙头和强势股

### `/django/api/strategy/stock-rps/`

- 比较对象：当前股票池内全部股票之间的强弱排名
- 输出主体：个股
- 适合用途：做全市场强势股扫描，或按交易所/市场板块筛选强势股

## 相关源码

- 视图入口：`stock_strategy/views.py`
- 路由配置：`stock_strategy/urls.py`
- 计算逻辑：`scheduled_tasks/stock_data_query_tasks/stock_rps.py`
