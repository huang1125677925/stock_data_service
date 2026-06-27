# 行业 MA 市场宽度接口文档

## 接口地址

- `GET /django/api/strategy/industry-ma-breadth/`

## 接口说明

- 功能：返回指定日期范围内，各东方财富板块中“收盘价高于 N 日均线”的股票占比。
- 响应格式：统一使用 `success_response` / `error_response` 封装。
- 当前实现基于以下 Tushare 接口：
  - `dc_index`
  - `dc_member`
  - `stk_factor_pro`

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| ----- | ---- | ---- | ------ | ---- |
| `start_date` | string | 否 | 过去90天 | 开始日期，格式 `YYYY-MM-DD` |
| `end_date` | string | 否 | 当天 | 结束日期，格式 `YYYY-MM-DD` |
| `ma_window` | integer | 否 | `20` | 移动平均窗口（交易日），建议优先使用 `5/10/20/30/60/90/250` |
| `idx_type` | string | 否 | `行业板块` | 东方财富板块类型，支持 `行业板块`、`概念板块`、`地域板块` |
| `level` | string | 否 | - | 东财行业层级，仅 `idx_type=行业板块` 时生效，支持 `东财一级行业`、`东财二级行业`、`东财三级行业` |

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
    "query_time": "2026-06-27T12:00:00"
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

### 1. 板块与交易日获取

- 调用 `dc_index` 获取 `start_date ~ end_date` 区间内的板块数据。
- 根据 `idx_type` 过滤板块类型。
- 如果传入 `level`，则在 `idx_type=行业板块` 的前提下进一步过滤东财行业层级。
- 区间内实际可返回的日期，以 `dc_index` 返回的交易日为准。

### 2. 板块成分获取

- 使用区间内最新交易日调用一次 `dc_member`，获取该交易日全部板块成分。
- 区间内历史日期统一复用这份最新成分映射。

### 3. 技术指标获取

- 对区间内每个交易日调用 `stk_factor_pro` 获取股票技术指标快照。
- 当 `ma_window` 为 `5/10/20/30/60/90/250` 时，直接使用 `stk_factor_pro` 的 `ma_bfq_N` 字段。
- 其他整数窗口会基于 `stk_factor_pro` 返回的 `close` 在本地滚动计算均线。

### 4. 宽度计算

- 对每个板块、每个交易日计算：
  - `count_above_ma`：收盘价严格大于 MA_N 的股票数量
  - `eligible_count`：当日有有效 MA_N 的股票数量
  - `breadth_ratio = count_above_ma / eligible_count`
- 当 `eligible_count = 0` 时，`breadth_ratio` 返回 `0`。

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
