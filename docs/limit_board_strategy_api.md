# 涨停打板组合数据接口文档

本文档面向前端开发，描述涨停打板趋势分析、行业趋势强度相关组合接口。

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
  "message": "参数格式错误: start_date 为必填参数，格式为 YYYYMMDD",
  "timestamp": "2026-05-16T10:30:00.000000",
  "data": null
}
```

通用参数：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---:|---:|---:|---|
| `start_date` | string | 是 | - | 开始日期，格式 `YYYYMMDD` |
| `end_date` | string | 是 | - | 结束日期，格式 `YYYYMMDD` |
| `token` | string | 否 | 环境变量 `TUSHARE_TOKEN` | Tushare Token，传入后覆盖环境变量 |

数据权限说明：

- 接口依赖 Tushare 权限和积分。
- 组合接口会尽量保留可选增强数据；部分非核心源失败或为空时，接口仍可能返回核心结果。

## 1. 涨停打板趋势分析

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

## 2. 行业涨停趋势强度分析

```http
GET /django/api/strategy/limit-board/industry-trend-strength/
```

### 功能

以区间 `limit_list_ths(limit_type=涨停池)` 同花顺涨停池数据为基础，按 `industry_mapping` 指定的方式获取每只涨停股所属行业，按交易日聚合输出「整体、行业、个股」三个维度的数据，适合前端做行业热度趋势表、行业轮动看板、逐日涨停股下钻。

统计范围会剔除以下个股（不计入任何维度）：

- ST/退市类股票（名称含 `ST`、`*ST` 或 `退`）。
- 无法归类到具体行业（未知行业）的个股。

### 数据源

- `limit_list_ths(start_date,end_date,limit_type=涨停池)`：区间同花顺涨停池，作为涨停个股基础数据（含涨停原因、标签等全部字段）
- 每日整体数据中的情绪字段复用以下区间数据按交易日计算：
  - `limit_list_d(start_date,end_date,limit_type=U)`：涨停数据，同时用于 `default` 行业映射。
  - `limit_list_d(start_date,end_date,limit_type=D)`：跌停数据。
  - `limit_list_d(start_date,end_date,limit_type=Z)`：炸板数据。
  - `limit_step(start_date,end_date)`：连板天梯数据。
- 行业映射来源随 `industry_mapping` 变化：
  - `default`：`limit_list_d(start_date,end_date,limit_type=U)`，按交易日构建 `(交易日, 股票代码) -> 所属行业` 的动态映射。
  - `dc_concept` / `dc_region` / `dc_l1` / `dc_l2` / `dc_l3`：本地东方财富板块成分快照 `data/dc_board_members_snapshot.json`，按 `股票代码 -> 板块名称` 映射。快照为单一时点的静态成分，全区间一致，不随交易日变化。

### 行业映射方式（`industry_mapping`）

| 取值 | 行业来源 | 映射关系 | 说明 |
|---|---|---|---|
| `default` | `limit_list_d` 的 `industry` 字段 | 一对一 | 默认方式，按交易日动态映射 |
| `dc_concept` | 东财概念板块（快照） | 多对多 | 同一只个股可同时归入多个概念板块 |
| `dc_region` | 东财地域板块（快照） | 一对一 | |
| `dc_l1` | 东财一级行业板块（快照） | 一对一 | |
| `dc_l2` | 东财二级行业板块（快照） | 一对一 | |
| `dc_l3` | 东财三级行业板块（快照） | 一对一 | |

> `dc_concept` 为多对多映射：同一只涨停股会同时出现在多个概念行业分组中。因此各行业维度的涨停数量（`industries[].limit_up_count`、`top_industries[].total_limit_up_count`）按成分归属分别计入，而整体/汇总的涨停总数（`overall.limit_up_count`、`summary.total_limit_up_count`）按去重个股计，避免重复计数。其余映射方式为一对一，两类计数一致。

### 请求参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---:|---:|---:|---|
| `start_date` | string | 是 | - | 开始日期，格式 `YYYYMMDD` |
| `end_date` | string | 是 | - | 结束日期，格式 `YYYYMMDD` |
| `industry_mapping` | string | 否 | `default` | 行业映射方式，取值见上表：`default`、`dc_concept`、`dc_region`、`dc_l1`、`dc_l2`、`dc_l3`；非法值返回 400 |
| `token` | string | 否 | - | Tushare Token |

### 示例请求

```bash
# 默认行业映射（limit_list_d）
curl "http://localhost:8000/django/api/strategy/limit-board/industry-trend-strength/?start_date=20260114&end_date=20260131"

# 使用东财二级行业板块映射
curl "http://localhost:8000/django/api/strategy/limit-board/industry-trend-strength/?start_date=20260114&end_date=20260131&industry_mapping=dc_l2"
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
| `total_limit_up_count` | number | 剔除 ST 与未知行业后，纳入统计的涨停个股总数（按交易日内去重个股累加；`dc_concept` 多对多下不重复计数） |
| `industry_matched_count` | number | 成功匹配到行业的个股记录数（`default` 来自 `limit_list_d`，其余来自快照；多对多映射下同一个股的多个成分计为一次） |
| `excluded_st_count` | number | 因 ST/退市被剔除的个股数 |
| `excluded_unknown_industry_count` | number | 因无法归类到具体行业被剔除的个股数 |
| `industry_mapping` | string | 本次使用的行业映射方式（`default`/`dc_concept`/`dc_region`/`dc_l1`/`dc_l2`/`dc_l3`） |
| `industry_mapping_label` | string | 行业映射方式的中文标签 |
| `top_industries` | array | 按区间累计涨停家数排序的行业汇总，最多 20 条 |

### top_industries 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `industry` | string | 行业名称 |
| `trade_day_count` | number | 该行业在区间内上榜交易日数 |
| `total_limit_up_count` | number | 区间累计涨停家数 |
| `avg_daily_limit_up_count` | number | 日均涨停家数 |

### source_counts 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `limit_list_ths` | number | 区间同花顺涨停池记录数 |
| `limit_list_d_up` | number | 区间 `limit_list_d(limit_type=U)` 记录数；用于每日情绪统计，且 `default` 映射下同时作为行业动态映射来源 |
| `limit_list_d_down` | number | 区间 `limit_list_d(limit_type=D)` 记录数；用于每日情绪统计 |
| `limit_list_d_broken` | number | 区间 `limit_list_d(limit_type=Z)` 记录数；用于每日情绪统计 |
| `limit_step` | number | 区间 `limit_step` 记录数；用于每日情绪统计 |
| `dc_board_snapshot_stocks` | number | 本地板块快照中命中该映射方式的股票数；`default` 映射为 0 |

### data[trade_date] 字段（按交易日 key）

`data` 是一个对象，key 为交易日 `YYYYMMDD`，每个交易日包含整体、行业、个股三个维度：

| 字段 | 类型 | 说明 |
|---|---|---|
| `trade_date` | string | 交易日期 |
| `overall` | object | 整体维度：该日涨停总数、涉及行业数量，以及同口径情绪汇总字段 |
| `industries` | array | 行业维度：该日涨停股细分到的各行业及每个行业的涨停数量，按涨停数量倒序 |
| `stocks` | object | 个股维度：以行业名称为 key，value 为该行业内涨停股列表 |

#### overall 字段（整体维度）

`overall` 中的情绪字段按交易日合并到行业趋势接口的日级整体数据中。

| 字段 | 类型 | 说明 |
|---|---|---|
| `limit_up_count` | number | 该日涨停股总数（按去重个股计；`dc_concept` 多对多下同一个股不重复计数） |
| `industry_count` | number | 该日涨停股涉及的行业数量 |
| `limit_down_count` | number | 该日跌停家数 |
| `broken_limit_count` | number | 该日炸板家数 |
| `limit_attempt_count` | number | 该日冲板总数，涨停 + 炸板 |
| `sealed_rate` | number | 该日封板率，单位 `%` |
| `broken_rate` | number | 该日炸板率，单位 `%` |
| `max_board` | number | 该日最高连板数 |
| `one_board_count` | number | 该日首板数量 |
| `second_board_or_above_count` | number | 该日 2 板及以上数量 |
| `high_board_count` | number | 该日 3 板及以上数量 |
| `sentiment_score` | number | 该日情绪分，0-100 |
| `phase` | string | `attack` / `repair` / `mixed` / `defense` |
| `phase_label` | string | 中文阶段名 |
| `conclusion` | string | 简短结论 |

#### industries 字段（行业维度）

| 字段 | 类型 | 说明 |
|---|---|---|
| `industry` | string | 行业名称 |
| `limit_up_count` | number | 该日该行业涨停家数（按成分归属计；`dc_concept` 下各行业分别计入同一个股） |
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
| `industry` | string | 所属行业/板块名称（本接口补充，来源随 `industry_mapping` 而定） |

- ST/退市股票（名称含 `ST` 或 `退`）不计入统计范围。
- 无法归类到具体行业（未知行业）的个股不计入统计范围，即不存在 `未知行业` 分组。`default` 方式下指既无法从 `limit_list_d` 匹配、`limit_list_ths` 也无 `industry` 字段；快照方式下指该股票代码不在对应板块成分快照中。
- `dc_concept`（多对多）方式下，同一只涨停股会同时出现在其所属的多个概念行业分组中；此时 `stocks`/`industries` 各分组按成分归属分别列出，而 `overall.limit_up_count` 与 `summary.total_limit_up_count` 按去重个股计。
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
          "industry_count": 1,
          "limit_down_count": 1,
          "broken_limit_count": 1,
          "limit_attempt_count": 3,
          "sealed_rate": 66.7,
          "broken_rate": 33.3,
          "max_board": 3,
          "one_board_count": 0,
          "second_board_or_above_count": 2,
          "high_board_count": 1,
          "sentiment_score": 61.3,
          "phase": "repair",
          "phase_label": "修复期",
          "conclusion": "情绪处于修复或温和活跃状态，关注换手充分的强势股。"
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

建议拆成 2 个模块：

| 页面模块 | 推荐接口 | 展示方式 |
|---|---|---|
| 趋势分析 | `/trend-analysis/` | 情绪折线图、题材热度趋势、个股生命周期表 |
| 行业趋势强度 | `/industry-trend-strength/` | 按日行业热度表、行业轮动趋势、逐日涨停股下钻；每日整体数据已内嵌同口径情绪字段 |

## 注意事项

- 趋势分析接口使用 `start_date/end_date`，当前限制最大 90 个自然日。
- 行业趋势强度接口同样使用 `start_date/end_date`，当前限制最大 90 个自然日；`data` 以交易日为 key，个股维度保留 `limit_list_ths` 原始字段，行业由 `industry_mapping` 指定的映射方式补充。
- 行业趋势强度接口的 `industry_mapping` 支持 6 种映射方式：`default`（`limit_list_d` 行业字段，按日动态）与 5 种基于本地东财板块成分快照的方式（`dc_concept`/`dc_region`/`dc_l1`/`dc_l2`/`dc_l3`）；不传参使用 `default`，非法值返回 400。快照方式的成分为单一时点静态数据，全区间一致，需定期更新快照文件才能反映最新板块成分。
- `dc_concept` 为多对多映射，同一只涨停股会同时归入多个概念行业，此时 `overall.limit_up_count`、`summary.total_limit_up_count` 按去重个股计，而 `industries[].limit_up_count`、`top_industries[].total_limit_up_count` 按成分归属分别计入，两者可能不相等。
- 前端应展示 `source_counts`，便于判断是否某个增强数据源为空。
- 组合接口中部分增强源为空不一定代表接口失败，核心字段仍可使用。
