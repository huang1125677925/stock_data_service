# 涨停打板组合数据接口文档

本文档面向前端开发，描述涨停、打板、竞价、题材、炸板回封、龙虎榜游资复盘、趋势分析、行业趋势强度相关组合接口。

## 统一响应格式

所有接口均使用统一 JSON 外层结构：

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-05-16T10:30:00.000000",
  "data": {}
}
```

错误时 HTTP 状态码仍通常为 `200`，前端应以响应体 `code` 判断业务成功或失败：

```json
{
  "code": 400,
  "message": "参数格式错误: trade_date 为必填参数，格式为 YYYYMMDD",
  "timestamp": "2026-05-16T10:30:00.000000",
  "data": null
}
```

通用参数：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---:|---:|---:|---|
| `trade_date` | string | 是 | - | 交易日期，格式 `YYYYMMDD` |
| `token` | string | 否 | 环境变量 `TUSHARE_TOKEN` | Tushare Token，传入后覆盖环境变量 |

数据权限说明：

- 接口依赖 Tushare 权限和积分。
- `stk_auction`、`stk_auction_o`、`stk_auction_c` 等竞价数据属于较高权限数据。
- 组合接口会尽量保留可选增强数据；部分非核心源失败或为空时，接口仍可能返回核心结果。

## 1. 每日打板情绪总览

```http
GET /django/api/strategy/limit-board/daily-sentiment/
```

### 功能

聚合以下 Tushare 数据：

- `limit_list_d`：涨停、跌停、炸板数据
- `limit_step`：连板天梯
- `limit_cpt_list`：涨停最强板块

适合前端做市场情绪头部卡片、连板分布图、最强题材列表。

### 请求参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---:|---:|---:|---|
| `trade_date` | string | 是 | - | 交易日期 |
| `token` | string | 否 | - | Tushare Token |

### 示例请求

```bash
curl "http://localhost:8000/django/api/strategy/limit-board/daily-sentiment/?trade_date=20260114"
```

### data 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `trade_date` | string | 查询日期 |
| `summary` | object | 情绪汇总 |
| `board_distribution` | array | 连板高度分布 |
| `top_concepts` | array | 涨停最强题材列表，来自 `limit_cpt_list` |
| `source_counts` | object | 各 Tushare 源返回记录数 |
| `query_time` | string | 查询时间 |

### summary 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `limit_up_count` | number | 涨停家数 |
| `limit_down_count` | number | 跌停家数 |
| `broken_limit_count` | number | 炸板家数 |
| `limit_attempt_count` | number | 冲板总数，涨停 + 炸板 |
| `sealed_rate` | number | 封板率，单位 `%` |
| `broken_rate` | number | 炸板率，单位 `%` |
| `max_board` | number | 最高连板数 |
| `one_board_count` | number | 首板数量 |
| `second_board_or_above_count` | number | 2板及以上数量 |
| `high_board_count` | number | 3板及以上数量 |
| `sentiment_score` | number | 情绪分，0-100 |
| `phase` | string | `attack` / `repair` / `mixed` / `defense` |
| `phase_label` | string | 中文阶段名 |
| `conclusion` | string | 简短结论 |

### 示例响应片段

```json
{
  "code": 200,
  "message": "获取每日打板情绪总览成功",
  "data": {
    "trade_date": "20260114",
    "summary": {
      "limit_up_count": 68,
      "limit_down_count": 8,
      "broken_limit_count": 21,
      "limit_attempt_count": 89,
      "sealed_rate": 76.4,
      "broken_rate": 23.6,
      "max_board": 5,
      "sentiment_score": 72.5,
      "phase": "repair",
      "phase_label": "修复期"
    },
    "board_distribution": [
      {"board": 5, "count": 1},
      {"board": 4, "count": 2},
      {"board": 3, "count": 5}
    ],
    "top_concepts": []
  }
}
```

## 2. 增强版竞价打板候选池

```http
GET /django/api/strategy/limit-board/auction-candidates/
```

### 功能

在现有 `auction-selection` 策略基础上，补充：

- `limit_list_ths`：同花顺涨停原因、标签、涨停状态
- `kpl_list`：开盘啦题材、榜单状态
- `dc_hot`：东方财富热榜
- `ths_hot`：同花顺热榜

适合前端做 9:25 竞价候选股列表、候选股详情抽屉、评分拆解。

### 请求参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---:|---:|---:|---|
| `trade_date` | string | 是 | - | 目标交易日 |
| `top_n` | integer | 否 | 10 | 返回 TOP 数量，最大 100 |
| `auction_max_retries` | integer | 否 | 6 | 竞价数据最大重试次数 |
| `auction_base_wait` | integer | 否 | 2 | 竞价数据基础等待秒数 |
| `token` | string | 否 | - | Tushare Token |

### 示例请求

```bash
curl "http://localhost:8000/django/api/strategy/limit-board/auction-candidates/?trade_date=20260114&top_n=10"
```

### data 字段

继承原 `auction-selection` 返回结构，并增强候选股字段。

| 字段 | 类型 | 说明 |
|---|---|---|
| `summary` | object | 策略摘要 |
| `market_sentiment` | object | 市场情绪判断 |
| `top_candidates` | array | 增强评分后的 TOP 候选 |
| `candidates` | array | 全量候选 |
| `statistics` | object | 统计信息 |
| `params` | object | 查询参数 |

### candidate 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | string | 股票代码 |
| `name` | string | 股票名称 |
| `score` | number | 原竞价策略分 |
| `enhanced_score` | number | 增强分，原评分 + 热榜分 |
| `hot_score` | number | 热榜加分 |
| `auction_price` | number | 竞价价格 |
| `pre_close` | number | 昨收价 |
| `auction_amount` | number | 竞价成交额 |
| `gap_pct` | number | 竞价涨幅 |
| `limit_times` | number | 昨日连板数 |
| `volume_ratio_pct` | number | 竞价额 / 流通市值 |
| `reason` | string | 涨停原因，优先同花顺 |
| `tags` | array | 题材标签 |
| `ths_status` | string | 同花顺状态 |
| `kpl_status` | string | 开盘啦状态 |
| `dc_hot` | object | 东方财富热榜原始记录 |
| `ths_hot` | object | 同花顺热榜原始记录 |
| `score_breakdown` | object | 原竞价策略评分拆解 |
| `raw_sources` | object | 增强源原始记录 |

### 示例响应片段

```json
{
  "code": 200,
  "message": "获取增强版竞价打板候选池成功",
  "data": {
    "top_candidates": [
      {
        "code": "000001.SZ",
        "name": "测试股份",
        "score": 17.2,
        "enhanced_score": 18.4,
        "hot_score": 1.2,
        "gap_pct": 5.6,
        "reason": "机器人概念活跃",
        "tags": ["机器人", "人工智能"]
      }
    ]
  }
}
```

## 3. 涨停题材梯队

```http
GET /django/api/strategy/limit-board/theme-ladder/
```

### 功能

聚合：

- `kpl_list`
- `kpl_concept`
- `kpl_concept_cons`
- `limit_cpt_list`
- `limit_step`

输出每个题材下的涨停数量、最高板、核心股、热度分。适合做题材梯队页。

### 请求参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---:|---:|---:|---|
| `trade_date` | string | 是 | - | 交易日期 |
| `top_n` | integer | 否 | 20 | 返回题材数量，最大 100 |
| `token` | string | 否 | - | Tushare Token |

### 示例请求

```bash
curl "http://localhost:8000/django/api/strategy/limit-board/theme-ladder/?trade_date=20260114&top_n=20"
```

### data 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `trade_date` | string | 查询日期 |
| `total` | number | 题材总数 |
| `themes` | array | 题材列表 |
| `source_counts` | object | 数据源记录数 |
| `query_time` | string | 查询时间 |

### theme 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `concept_code` | string | 题材代码 |
| `concept_name` | string | 题材名称 |
| `limit_up_count` | number | 题材内涨停家数 |
| `max_board` | number | 题材内最高连板 |
| `heat_score` | number | 热度分 |
| `core_stocks` | array | 核心涨停股，最多 10 个 |
| `strongest_concept` | object | `limit_cpt_list` 原始记录 |

### core_stocks 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `ts_code` | string | 股票代码 |
| `name` | string | 股票名称 |
| `board` | number | 连板数 |
| `status` | string | 榜单状态 |
| `theme` | string | 开盘啦题材 |
| `raw` | object | 原始股票记录 |

## 4. 炸板/回封分析

```http
GET /django/api/strategy/limit-board/break-reseal/
```

### 功能

基于：

- `limit_list_d(limit_type=U)`：涨停池，取 `open_times > 0` 判定回封股
- `limit_list_d(limit_type=Z)`：炸板池
- `limit_list_ths(limit_type=炸板池)`：补充炸板原因

适合做炸板率、回封率、开板次数、封单强度排行。

### 请求参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---:|---:|---:|---|
| `trade_date` | string | 是 | - | 交易日期 |
| `top_n` | integer | 否 | 50 | 每类返回数量，最大 200 |
| `token` | string | 否 | - | Tushare Token |

### 示例请求

```bash
curl "http://localhost:8000/django/api/strategy/limit-board/break-reseal/?trade_date=20260114&top_n=50"
```

### data 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `trade_date` | string | 查询日期 |
| `summary` | object | 汇总 |
| `resealed` | array | 开板后回封列表 |
| `failed` | array | 最终炸板列表 |
| `source_counts` | object | 数据源记录数 |
| `query_time` | string | 查询时间 |

### summary 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `limit_up_count` | number | 最终涨停家数 |
| `resealed_count` | number | 开板后回封家数 |
| `failed_break_count` | number | 最终炸板家数 |
| `break_attempt_count` | number | 有开板或炸板行为的数量 |
| `failed_break_rate` | number | 最终炸板率 |
| `reseal_rate_after_break` | number | 开板后回封率 |

### item 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `ts_code` | string | 股票代码 |
| `name` | string | 股票名称 |
| `status` | string | `resealed` 或 `failed` |
| `industry` | string | 行业 |
| `close` | number | 收盘价 |
| `pct_chg` | number | 涨跌幅 |
| `amount` | number | 成交额 |
| `fd_amount` | number | 封单金额 |
| `seal_ratio_pct` | number | 封单额 / 成交额 |
| `first_time` | string | 首次封板时间 |
| `last_time` | string | 最后封板时间 |
| `open_times` | number | 开板次数 |
| `limit_times` | number | 连板数 |
| `reason` | string | 涨停/炸板原因 |
| `break_strength_score` | number | 回封强度分 |
| `raw_sources` | object | 原始记录 |

## 5. 游资打板复盘

```http
GET /django/api/strategy/limit-board/hot-money-review/
```

### 功能

聚合：

- `top_list`：龙虎榜每日统计
- `hm_detail`：游资交易每日明细
- `limit_list_d`：涨停/炸板池

适合做龙虎榜打板复盘、活跃游资排行、上榜股票和涨停状态关联。

### 请求参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---:|---:|---:|---|
| `trade_date` | string | 是 | - | 交易日期 |
| `top_n` | integer | 否 | 100 | 返回股票数量，最大 500 |
| `token` | string | 否 | - | Tushare Token |

### 示例请求

```bash
curl "http://localhost:8000/django/api/strategy/limit-board/hot-money-review/?trade_date=20260114&top_n=100"
```

### data 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `trade_date` | string | 查询日期 |
| `summary` | object | 汇总 |
| `active_hot_money` | array | 活跃游资排行 |
| `records` | array | 上榜股票复盘列表 |
| `source_counts` | object | 数据源记录数 |
| `query_time` | string | 查询时间 |

### summary 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `top_list_count` | number | 龙虎榜股票数量 |
| `hot_money_detail_count` | number | 游资交易明细数量 |
| `top_limit_up_count` | number | 龙虎榜中最终涨停数量 |
| `top_broken_count` | number | 龙虎榜中最终炸板数量 |
| `active_hot_money_count` | number | 活跃游资数量 |

### active_hot_money 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `hm_name` | string | 游资名称 |
| `appear_count` | number | 出现次数 |
| `estimated_net_buy` | number | 估算净买额，按可用字段计算 |

### record 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `ts_code` | string | 股票代码 |
| `name` | string | 股票名称 |
| `board_status` | string | `limit_up` / `broken` / `other` |
| `top_list` | object | 龙虎榜原始记录 |
| `limit_record` | object | 涨停或炸板原始记录 |
| `hot_money_records` | array | 该股相关游资明细 |
| `hot_money_count` | number | 相关游资明细数量 |

## 6. 涨停打板趋势分析

```http
GET /django/api/strategy/limit-board/trend-analysis/
```

### 功能

从时间维度分析打板生态变化，覆盖三条主线：

- 情绪变化：涨停数、跌停数、炸板数、封板率、炸板率、最高板、情绪分。
- 题材变化：题材上榜天数、涨停家数峰值、连板家数峰值、排名变化、热度分。
- 个股生命周期：首板启动、二板确认、主升连板、高位龙头、断板/炸板等阶段。

该接口对支持区间的 Tushare 接口使用 `start_date/end_date` 一次拉取，再按日期聚合。当前默认限制查询区间不超过 90 个自然日，避免一次请求过重。

### 数据源

- `limit_list_d(start_date,end_date,limit_type=U)`：区间涨停池
- `limit_list_d(start_date,end_date,limit_type=D)`：区间跌停池
- `limit_list_d(start_date,end_date,limit_type=Z)`：区间炸板池
- `limit_step(start_date,end_date)`：区间连板天梯
- `limit_cpt_list(start_date,end_date)`：区间涨停最强板块

### 请求参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---:|---:|---:|---|
| `start_date` | string | 是 | - | 开始日期，格式 `YYYYMMDD` |
| `end_date` | string | 是 | - | 结束日期，格式 `YYYYMMDD` |
| `top_n` | integer | 否 | 20 | 题材趋势和个股生命周期返回数量，最大 100 |
| `token` | string | 否 | - | Tushare Token |

### 示例请求

```bash
curl "http://localhost:8000/django/api/strategy/limit-board/trend-analysis/?start_date=20260101&end_date=20260131&top_n=20"
```

### data 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `start_date` | string | 查询开始日期 |
| `end_date` | string | 查询结束日期 |
| `trade_dates` | array | 区间内有打板相关数据的交易日期 |
| `summary` | object | 趋势汇总 |
| `sentiment_series` | array | 每日情绪时间序列 |
| `concept_trends` | array | 题材趋势列表 |
| `stock_lifecycles` | array | 涨停股生命周期列表 |
| `source_counts` | object | 数据源记录数 |
| `query_time` | string | 查询时间 |

### summary 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `trade_day_count` | number | 有数据的交易日数量 |
| `avg_limit_up_count` | number | 区间日均涨停家数 |
| `avg_broken_rate` | number | 区间平均炸板率 |
| `max_board_peak` | number | 区间最高连板峰值 |
| `sentiment_score_start` | number | 区间首日情绪分 |
| `sentiment_score_end` | number | 区间末日情绪分 |
| `sentiment_score_change` | number | 情绪分变化，末日 - 首日 |
| `phase_distribution` | object | 阶段分布，如 `{ "repair": 5, "mixed": 3 }` |
| `dominant_phase` | string | 区间出现最多的阶段 |

### sentiment_series 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `trade_date` | string | 交易日期 |
| `limit_up_count` | number | 涨停家数 |
| `limit_down_count` | number | 跌停家数 |
| `broken_limit_count` | number | 炸板家数 |
| `limit_attempt_count` | number | 冲板总数 |
| `sealed_rate` | number | 封板率 |
| `broken_rate` | number | 炸板率 |
| `max_board` | number | 当日最高连板 |
| `high_board_count` | number | 3板及以上数量 |
| `sentiment_score` | number | 情绪分 |
| `phase` | string | `attack` / `repair` / `mixed` / `defense` |
| `phase_label` | string | 中文阶段 |
| `board_distribution` | array | 连板分布 |
| `top_concepts` | array | 当日排名前 10 的强势题材 |
| `changes` | object | 相比前一个交易日的变化 |

### changes 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `limit_up_count` | number | 涨停家数变化 |
| `broken_limit_count` | number | 炸板家数变化 |
| `max_board` | number | 最高板变化 |
| `sentiment_score` | number | 情绪分变化 |

### concept_trends 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `concept_code` | string | 题材代码 |
| `concept_name` | string | 题材名称 |
| `active_days` | number | 区间上榜天数 |
| `first_date` | string | 首次上榜日期 |
| `last_date` | string | 最后上榜日期 |
| `peak_rank` | number | 区间最好排名，数值越小越强 |
| `max_up_nums` | number | 区间最大涨停家数 |
| `max_cons_nums` | number | 区间最大连板家数 |
| `max_board` | number | 区间题材最高连板 |
| `avg_pct_chg` | number | 区间平均题材涨幅 |
| `heat_score` | number | 题材热度分 |
| `rank_change` | number | 末次排名 - 首次排名；负数代表排名提升 |
| `series` | array | 题材每日变化序列 |

### stock_lifecycles 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `ts_code` | string | 股票代码 |
| `name` | string | 股票名称 |
| `industry` | string | 行业 |
| `first_limit_date` | string | 区间首次涨停日期 |
| `last_limit_date` | string | 区间最后涨停日期 |
| `limit_up_days` | number | 区间涨停天数 |
| `broken_days` | number | 区间炸板天数 |
| `max_board` | number | 区间最高连板 |
| `current_status` | string | 最后事件，`limit_up` 或 `broken` |
| `lifecycle_stage` | string | 生命周期阶段 |
| `strength_score` | number | 强度分 |
| `events` | array | 股票逐日事件 |

### lifecycle_stage 枚举

| 值 | 说明 |
|---|---|
| `首板启动` | 区间内首板，尚未形成连续性 |
| `二板确认` | 进入二板或区间内多次涨停 |
| `主升连板` | 3-4 板区间 |
| `高位龙头` | 5 板及以上 |
| `断板/炸板` | 最新事件为炸板 |
| `试错回封` | 曾炸板但最终仍有回封或涨停事件 |

### 示例响应片段

```json
{
  "code": 200,
  "message": "获取涨停打板趋势分析成功",
  "data": {
    "start_date": "20260101",
    "end_date": "20260131",
    "summary": {
      "trade_day_count": 20,
      "avg_limit_up_count": 66.4,
      "avg_broken_rate": 24.8,
      "max_board_peak": 6,
      "sentiment_score_change": 8.5,
      "dominant_phase": "repair"
    },
    "sentiment_series": [
      {
        "trade_date": "20260105",
        "limit_up_count": 58,
        "broken_limit_count": 19,
        "max_board": 4,
        "sentiment_score": 63.5,
        "phase": "repair",
        "changes": {
          "limit_up_count": 0,
          "broken_limit_count": 0,
          "max_board": 0,
          "sentiment_score": 0
        }
      }
    ],
    "concept_trends": [
      {
        "concept_code": "885001.TI",
        "concept_name": "机器人",
        "active_days": 8,
        "peak_rank": 1,
        "max_up_nums": 18,
        "heat_score": 92.5
      }
    ],
    "stock_lifecycles": [
      {
        "ts_code": "000001.SZ",
        "name": "示例股份",
        "limit_up_days": 3,
        "broken_days": 1,
        "max_board": 3,
        "current_status": "limit_up",
        "lifecycle_stage": "主升连板"
      }
    ]
  }
}
```

## 7. 行业涨停趋势强度分析

```http
GET /django/api/strategy/limit-board/industry-trend-strength/
```

### 功能

以区间 `limit_list_ths(limit_type=涨停池)` 同花顺涨停池数据为基础，从 `limit_list_d(limit_type=U)` 获取每只涨停股所属行业，按交易日聚合输出「整体、行业、个股」三个维度的数据，适合前端做行业热度趋势表、行业轮动看板、逐日涨停股下钻。

统计范围会剔除以下个股（不计入任何维度）：

- ST/退市类股票（名称含 `ST`、`*ST` 或 `退`）。
- 无法归类到具体行业（未知行业）的个股。

### 数据源

- `limit_list_ths(start_date,end_date,limit_type=涨停池)`：区间同花顺涨停池，作为涨停个股基础数据（含涨停原因、标签等全部字段）
- `limit_list_d(start_date,end_date,limit_type=U)`：区间涨停池，仅用于构建 `(交易日, 股票代码) -> 所属行业` 映射

### 请求参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---:|---:|---:|---|
| `start_date` | string | 是 | - | 开始日期，格式 `YYYYMMDD` |
| `end_date` | string | 是 | - | 结束日期，格式 `YYYYMMDD` |
| `token` | string | 否 | - | Tushare Token |

### 示例请求

```bash
curl "http://localhost:8000/django/api/strategy/limit-board/industry-trend-strength/?start_date=20260114&end_date=20260131"
```

### data 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `start_date` | string | 查询开始日期 |
| `end_date` | string | 查询结束日期 |
| `summary` | object | 汇总信息 |
| `data` | object | 以交易日 `YYYYMMDD` 为 key 的日度明细，value 为该日三维数据 |
| `source_counts` | object | 数据源记录数 |
| `query_time` | string | 查询时间 |

### summary 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `trade_day_count` | number | 区间内出现涨停数据的交易日数量 |
| `industry_count` | number | 区间内涉及的行业数量 |
| `total_limit_up_count` | number | 剔除 ST 与未知行业后，纳入统计的涨停个股总数 |
| `industry_matched_count` | number | 成功从 `limit_list_d` 匹配到行业的个股记录数 |
| `excluded_st_count` | number | 因 ST/退市被剔除的个股数 |
| `excluded_unknown_industry_count` | number | 因无法归类到具体行业被剔除的个股数 |
| `top_industries` | array | 按区间累计涨停家数排序的行业汇总，最多 20 条 |

### top_industries 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `industry` | string | 行业名称 |
| `trade_day_count` | number | 该行业在区间内上榜交易日数 |
| `total_limit_up_count` | number | 区间累计涨停家数 |
| `avg_daily_limit_up_count` | number | 日均涨停家数 |

### data[trade_date] 字段（按交易日 key）

`data` 是一个对象，key 为交易日 `YYYYMMDD`，每个交易日包含整体、行业、个股三个维度：

| 字段 | 类型 | 说明 |
|---|---|---|
| `trade_date` | string | 交易日期 |
| `overall` | object | 整体维度：该日涨停总数与涉及行业数量 |
| `industries` | array | 行业维度：该日涨停股细分到的各行业及每个行业的涨停数量，按涨停数量倒序 |
| `stocks` | object | 个股维度：以行业名称为 key，value 为该行业内涨停股列表 |

#### overall 字段（整体维度）

| 字段 | 类型 | 说明 |
|---|---|---|
| `limit_up_count` | number | 该日涨停股总数 |
| `industry_count` | number | 该日涨停股涉及的行业数量 |

#### industries 字段（行业维度）

| 字段 | 类型 | 说明 |
|---|---|---|
| `industry` | string | 行业名称 |
| `limit_up_count` | number | 该日该行业涨停家数 |
| `status_counts` | object | 该日该行业涨停股按涨停状态（`limit_list_ths` 的 `status` 字段）分类的数量统计 |

#### status_counts 字段（涨停状态统计）

固定包含以下三种涨停状态的数量，未出现的状态计为 `0`，其它状态不纳入统计：

| 字段 | 类型 | 说明 |
|---|---|---|
| `T字板` | number | 该行业当日 T 字板涨停股数量 |
| `一字板` | number | 该行业当日一字板涨停股数量 |
| `换手板` | number | 该行业当日换手板涨停股数量 |

#### stocks 字段（个股维度）

- `stocks` 是一个对象，key 为行业名称，value 为该行业内的涨停股数组。
- 每只个股保留 `limit_list_ths` 中该日该股票的全部原始字段（接口已通过 `fields` 显式声明完整字段，含默认不返回的 `N` 字段），并额外补充 `industry` 字段标识所属行业。字段如下：

| 字段 | 类型 | 说明 |
|---|---|---|
| `trade_date` | string | 交易日期 |
| `ts_code` | string | 股票代码 |
| `name` | string | 股票名称 |
| `price` | number | 收盘价(元) |
| `pct_chg` | number | 涨跌幅% |
| `open_num` | number | 打开次数 |
| `lu_desc` | string | 涨停原因 |
| `limit_type` | string | 板单类别 |
| `tag` | string | 涨停标签 |
| `status` | string | 涨停状态（如 `T字板`、`一字板`、`换手板`、`N连板`） |
| `first_lu_time` | string | 首次涨停时间 |
| `last_lu_time` | string | 最后涨停时间 |
| `first_ld_time` | string | 首次跌停时间 |
| `last_ld_time` | string | 最后跌停时间 |
| `limit_order` | number | 封单量(元) |
| `limit_amount` | number | 封单额(元) |
| `turnover_rate` | number | 换手率% |
| `free_float` | number | 实际流通(元) |
| `lu_limit_order` | number | 最大封单(元) |
| `limit_up_suc_rate` | number | 近一年涨停封板率 |
| `turnover` | number | 成交额 |
| `rise_rate` | number | 涨速 |
| `sum_float` | number | 总市值(亿元) |
| `market_type` | string | 股票类型：`HS` 沪深主板、`GEM` 创业板、`STAR` 科创板 |
| `industry` | string | 所属行业（本接口补充，来自 `limit_list_d` 映射） |

- ST/退市股票（名称含 `ST` 或 `退`）不计入统计范围。
- 无法归类到具体行业（既无法从 `limit_list_d` 匹配、`limit_list_ths` 也无 `industry` 字段）的个股不计入统计范围，即不存在 `未知行业` 分组。
- 某交易日经上述过滤后若无有效涨停个股，则该交易日不会出现在 `data` 中。

### 示例响应片段

```json
{
  "code": 200,
  "message": "获取行业涨停趋势强度分析成功",
  "data": {
    "start_date": "20260114",
    "end_date": "20260115",
    "summary": {
      "trade_day_count": 2,
      "industry_count": 2,
      "total_limit_up_count": 5,
      "industry_matched_count": 5,
      "excluded_st_count": 1,
      "excluded_unknown_industry_count": 1,
      "top_industries": [
        {
          "industry": "机器人",
          "trade_day_count": 2,
          "total_limit_up_count": 4,
          "avg_daily_limit_up_count": 2.0
        }
      ]
    },
    "data": {
      "20260114": {
        "trade_date": "20260114",
        "overall": {
          "limit_up_count": 2,
          "industry_count": 1
        },
        "industries": [
          {
            "industry": "机器人",
            "limit_up_count": 2,
            "status_counts": { "T字板": 0, "一字板": 1, "换手板": 1 }
          }
        ],
        "stocks": {
          "机器人": [
            {
              "trade_date": "20260114",
              "ts_code": "000001.SZ",
              "name": "一板股",
              "price": 12.5,
              "pct_chg": 10.0,
              "lu_desc": "机器人概念",
              "limit_type": "涨停池",
              "tag": "首板",
              "status": "一字板",
              "open_num": 0,
              "turnover_rate": 10.0,
              "limit_up_suc_rate": 0.85,
              "turnover": 100000000,
              "first_lu_time": "093000",
              "rise_rate": 12.5,
              "market_type": "HS",
              "industry": "机器人"
            }
          ]
        }
      }
    }
  }
}
```

## 前端页面建议

建议拆成 7 个模块：

| 页面模块 | 推荐接口 | 展示方式 |
|---|---|---|
| 情绪总览 | `/daily-sentiment/` | 指标卡、连板柱状图、最强题材表 |
| 竞价候选 | `/auction-candidates/` | 候选股表格、评分拆解、题材标签 |
| 题材梯队 | `/theme-ladder/` | 题材分组、核心股列表、热度排序 |
| 炸板回封 | `/break-reseal/` | 回封/炸板双列表、开板次数排行 |
| 游资复盘 | `/hot-money-review/` | 活跃游资排行、龙虎榜股票表 |
| 趋势分析 | `/trend-analysis/` | 情绪折线图、题材热度趋势、个股生命周期表 |
| 行业趋势强度 | `/industry-trend-strength/` | 按日行业热度表、行业轮动趋势、逐日涨停股下钻 |

## 注意事项

- `trade_date` 必须传交易日；非交易日通常会返回空数据或 Tushare 错误。
- 趋势分析接口使用 `start_date/end_date`，当前限制最大 90 个自然日。
- 行业趋势强度接口同样使用 `start_date/end_date`，当前限制最大 90 个自然日；`data` 以交易日为 key，个股维度保留 `limit_list_ths` 原始字段，行业由 `limit_list_d` 补充映射。
- 前端应展示 `source_counts`，便于判断是否某个增强数据源为空。
- 组合接口中部分增强源为空不一定代表接口失败，核心字段仍可使用。
- `raw_sources`、`top_list`、`limit_record` 等对象保留 Tushare 原始字段，前端可以按需展示详情。
