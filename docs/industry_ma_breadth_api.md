# 行业 MA 市场宽度接口文档

## 接口地址

- `GET /django/api/strategy/industry-ma-breadth/`

## 接口说明

- 功能：返回指定日期范围内，各东方财富板块中“收盘价高于 N 日均线”的股票占比。
- 响应格式：统一使用 `success_response` / `error_response` 封装。
- 支持两种模式：
  - **全量模式**（默认，不传 `sector_code`）：计算某个 `idx_type`/`level` 下的**全部板块**，按交易日逐日拉取全市场技术指标再本地过滤。请求次数随交易日数量增长，适合较短区间。
  - **单行业模式**（传入 `sector_code`）：仅计算指定的单个东财板块，按该板块成分股**逐只**拉取整段区间的技术指标。请求次数只与成分股数量相关，与时间跨度无关，适合长区间查询；此时忽略 `idx_type`/`level`。
- 全量模式当前实现优先读取本地板块成分快照文件：
  - `data/dc_board_members_snapshot.json`
- 全量模式查询阶段优先只依赖以下 Tushare 接口：
  - `stk_factor_pro`
- 当本地快照缺失时，才会回退到在线模式：
  - `trade_cal`
  - `dc_index`
  - `dc_member`
  - `stk_factor_pro`
- 单行业模式不读本地快照，直接实时依赖 `trade_cal`、`dc_index`、`dc_member`、`stk_factor_pro`。

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| ----- | ---- | ---- | ------ | ---- |
| `start_date` | string | 否 | 过去90天 | 开始日期，格式 `YYYY-MM-DD` |
| `end_date` | string | 否 | 当天 | 结束日期，格式 `YYYY-MM-DD` |
| `ma_window` | integer | 否 | `20` | 移动平均窗口（交易日），建议优先使用 `5/10/20/30/60/90/250` |
| `idx_type` | string | 否 | `行业板块` | 东方财富板块类型，支持 `行业板块`、`概念板块`、`地域板块` |
| `level` | string | 否 | - | 东财行业层级，仅 `idx_type=行业板块` 时生效，支持 `东财一级行业`、`东财二级行业`、`东财三级行业` |
| `sector_code` | string | 否 | - | 东财板块代码，例如 `BK1462.DC`。传入时进入**单行业模式**，仅计算该板块并按成分股逐只拉取因子数据（请求次数与时间跨度无关），此时忽略 `idx_type`/`level` |

## 请求示例

### 1. 查询东财一级行业近一个月 MA20 宽度

```text
GET /django/api/strategy/industry-ma-breadth/?start_date=2026-06-01&end_date=2026-06-27&ma_window=20&idx_type=行业板块&level=东财一级行业
```

### 2. 查询概念板块近 10 天 MA20 宽度

```text
GET /django/api/strategy/industry-ma-breadth/?start_date=2026-06-15&end_date=2026-06-27&ma_window=20&idx_type=概念板块
```

### 3. 查询地域板块近 7 天 MA15 宽度

```text
GET /django/api/strategy/industry-ma-breadth/?start_date=2026-06-20&end_date=2026-06-27&ma_window=15&idx_type=地域板块
```

### 4. 单行业模式：查询指定板块长区间 MA20 宽度序列

```text
GET /django/api/strategy/industry-ma-breadth/?sector_code=BK1462.DC&start_date=2024-01-01&end_date=2026-07-05&ma_window=20
```

- 传入 `sector_code` 后仅计算该板块，按成分股逐只拉取整段区间数据，请求次数与时间跨度无关，适合长区间查询。
- 此时 `idx_type`/`level` 会被忽略。

## 响应示例

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-06-27T12:00:00",
  "data": {
    "total": 2,
    "data": [
      {
        "date": "2026-06-26",
        "sector_code": "BK0420.DC",
        "sector_name": "消费电子",
        "count_above_ma": 56,
        "eligible_count": 100,
        "breadth_ratio": 0.56
      },
      {
        "date": "2026-06-26",
        "sector_code": "BK0475.DC",
        "sector_name": "半导体",
        "count_above_ma": 60,
        "eligible_count": 102,
        "breadth_ratio": 0.5882
      }
    ],
    "start_date": "2026-06-01",
    "end_date": "2026-06-27",
    "ma_window": 20,
    "idx_type": "行业板块",
    "level": "东财一级行业",
    "sector_code": null,
    "query_time": "2026-06-27T12:00:00"
  }
}
```

单行业模式下，`data` 数组只包含该板块的每日宽度记录，回显字段中 `sector_code` 为传入值、`level` 为 `null`：

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-07-05T12:00:00",
  "data": {
    "total": 1,
    "data": [
      {
        "date": "2026-07-04",
        "sector_code": "BK1462.DC",
        "sector_name": "机器人概念",
        "count_above_ma": 42,
        "eligible_count": 68,
        "breadth_ratio": 0.6176
      }
    ],
    "start_date": "2024-01-01",
    "end_date": "2026-07-05",
    "ma_window": 20,
    "idx_type": "行业板块",
    "level": null,
    "sector_code": "BK1462.DC",
    "query_time": "2026-07-05T12:00:00"
  }
}
```

## 响应字段说明

| 字段名 | 类型 | 说明 |
| ----- | ---- | ---- |
| `date` | string | 交易日期，格式 `YYYY-MM-DD` |
| `sector_code` | string | 东方财富板块代码 |
| `sector_name` | string | 东方财富板块名称 |
| `count_above_ma` | integer | 当日板块内收盘价高于 MA_N 的股票数量 |
| `eligible_count` | integer | 当日有有效 MA_N 值、可参与统计的股票数量 |
| `breadth_ratio` | number | 宽度比例，计算公式为 `count_above_ma / eligible_count`，范围 `[0,1]`，保留 4 位小数 |

## 计算逻辑

### 全量模式（不传 `sector_code`）

#### 1. 板块与交易日获取

- 优先从本地快照文件加载板块列表和成分数据。
- 根据 `idx_type` 过滤板块类型。
- 如果传入 `level`，则在 `idx_type=行业板块` 的前提下进一步过滤东财行业层级。
- 查询阶段按自然日遍历请求 `stk_factor_pro`，仅保留有返回数据的交易日结果。

#### 2. 板块成分获取

- 板块成分来自本地快照文件中的 `members` 数组。
- 快照生成时会使用最新交易日的 `dc_index` 与 `dc_member` 导出全量板块及成分。
- 查询阶段不再实时调用 `dc_member`。

#### 3. 技术指标获取

- 对区间内每个交易日调用 `stk_factor_pro` 获取股票技术指标快照。
- 当 `ma_window` 为 `5/10/20/30/60/90/250` 时，直接使用 `stk_factor_pro` 的 `ma_bfq_N` 字段。
- 其他整数窗口会基于 `stk_factor_pro` 返回的 `close` 在本地滚动计算均线。

### 单行业模式（传入 `sector_code`）

#### 1. 板块与成分获取

- 忽略 `idx_type`/`level`，直接以 `sector_code` 唯一确定目标板块。
- 取区间内最新交易日，用 `dc_index` 查该板块名称、用 `dc_member` 查该板块成分股（沿用最新交易日的成分定义，套用到整个区间，与全量模式口径一致）。
- 不读本地快照文件。

#### 2. 技术指标获取（逐成分股）

- 对每个成分股调用一次 `stk_factor_pro`，用 `ts_code` + `start_date` + `end_date` 一次性拉取整段区间序列。
- 请求次数等于成分股数量，与时间跨度无关，因此适合长区间查询。
- 均线来源与全量模式一致：`5/10/20/30/60/90/250` 直接用 `ma_bfq_N`；其他窗口取 `close` 后本地滚动计算（起始日会自动前推 `ma_window * 2` 个自然日以保证首日均线可算）。

### 宽度计算（两种模式共用）

- 对每个板块、每个交易日计算：
  - `count_above_ma`：收盘价严格大于 MA_N 的股票数量
  - `eligible_count`：当日有有效 MA_N 的股票数量
  - `breadth_ratio = count_above_ma / eligible_count`
- 当 `eligible_count = 0` 时，`breadth_ratio` 返回 `0`。
- 输出字段 schema 两种模式完全一致，单行业模式的结果即该板块的宽度时间序列。

## 参数约束

- `ma_window` 必须为整数。
- `level` 仅在 `idx_type=行业板块` 时生效。
- `level` 可选值仅支持：
  - `东财一级行业`
  - `东财二级行业`
  - `东财三级行业`

## 错误响应示例

```json
{
  "code": 400,
  "message": "level参数错误，仅支持：东财一级行业、东财二级行业、东财三级行业",
  "timestamp": "2026-06-27T12:00:00"
}
```

## 使用建议

- 如果优先考虑性能，建议优先使用 `ma_window=20` 或其他 `stk_factor_pro` 已内置的均线窗口。
- 如果只需要看行业分层结果，推荐搭配：
  - `idx_type=行业板块`
  - `level=东财一级行业` / `东财二级行业` / `东财三级行业`
- 如果查看概念板块或地域板块，只传 `idx_type` 即可，不需要传 `level`。
