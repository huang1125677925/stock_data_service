# 行业涨跌比例接口文档

## 接口地址

- `GET /django/api/strategy/industry-up-down-ratio/`

## 接口说明

- 功能：返回指定日期范围内，各东方财富板块每日的上涨家数、下跌家数及对应比例。
- 响应格式：统一使用 `success_response` / `error_response` 封装。
- 当前实现依赖以下 Tushare 接口：
  - `trade_cal`
  - `dc_index`
- 该接口统计口径为“板块自身快照中的上涨家数 / 下跌家数”，不是板块成分股逐只回溯计算结果。

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| ----- | ---- | ---- | ------ | ---- |
| `start_date` | string | 否 | 过去90天 | 开始日期，格式 `YYYY-MM-DD` |
| `end_date` | string | 否 | 当天 | 结束日期，格式 `YYYY-MM-DD` |
| `idx_type` | string | 否 | `行业板块` | 东方财富板块类型，支持 `行业板块`、`概念板块`、`地域板块` |
| `level` | string | 否 | - | 东财行业层级，仅 `idx_type=行业板块` 时生效，支持 `东财一级行业`、`东财二级行业`、`东财三级行业` |

## 请求示例

### 1. 查询东财二级行业近一段时间每日涨跌比例

```text
GET /django/api/strategy/industry-up-down-ratio/?start_date=2026-06-11&end_date=2026-07-01&idx_type=行业板块&level=东财二级行业
```

### 2. 查询概念板块近 10 天涨跌比例

```text
GET /django/api/strategy/industry-up-down-ratio/?start_date=2026-06-20&end_date=2026-07-01&idx_type=概念板块
```

### 3. 查询地域板块近 7 天涨跌比例

```text
GET /django/api/strategy/industry-up-down-ratio/?start_date=2026-06-25&end_date=2026-07-01&idx_type=地域板块
```

## 响应示例

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-07-01T16:30:00",
  "data": {
    "total": 2,
    "data": [
      {
        "date": "2026-07-01",
        "sector_code": "BK0420.DC",
        "sector_name": "消费电子",
        "idx_type": "行业板块",
        "level": "东财二级行业",
        "up_count": 58,
        "down_count": 42,
        "total_count": 100,
        "up_ratio": 0.58,
        "down_ratio": 0.42
      },
      {
        "date": "2026-07-01",
        "sector_code": "BK0475.DC",
        "sector_name": "半导体",
        "idx_type": "行业板块",
        "level": "东财二级行业",
        "up_count": 61,
        "down_count": 39,
        "total_count": 100,
        "up_ratio": 0.61,
        "down_ratio": 0.39
      }
    ],
    "start_date": "2026-06-11",
    "end_date": "2026-07-01",
    "idx_type": "行业板块",
    "level": "东财二级行业",
    "query_time": "2026-07-01T16:30:00"
  }
}
```

## 响应字段说明

| 字段名 | 类型 | 说明 |
| ----- | ---- | ---- |
| `date` | string | 交易日期，格式 `YYYY-MM-DD` |
| `sector_code` | string | 东方财富板块代码 |
| `sector_name` | string | 东方财富板块名称 |
| `idx_type` | string | 东方财富板块类型 |
| `level` | string | 东财行业层级；当 `idx_type` 不为 `行业板块` 时通常为空字符串 |
| `up_count` | integer | 当日板块上涨家数 |
| `down_count` | integer | 当日板块下跌家数 |
| `total_count` | integer | 参与比例计算的总家数，计算公式为 `up_count + down_count` |
| `up_ratio` | number | 上涨比例，计算公式为 `up_count / total_count`，范围 `[0,1]`，保留 4 位小数 |
| `down_ratio` | number | 下跌比例，计算公式为 `down_count / total_count`，范围 `[0,1]`，保留 4 位小数 |

## 计算逻辑

### 1. 交易日获取

- 使用 `trade_cal` 获取 `start_date` 到 `end_date` 区间内的实际交易日。
- 只对有效交易日发起后续板块快照查询。

### 2. 板块快照获取

- 对每个交易日调用 `dc_index` 拉取对应 `idx_type` 的东方财富板块快照。
- 如果传入 `level`，则在 `idx_type=行业板块` 的前提下进一步过滤东财行业层级。

### 3. 涨跌比例计算

- 对每个板块、每个交易日读取：
  - `up_num`：上涨家数
  - `down_num`：下跌家数
- 进一步计算：
  - `total_count = up_count + down_count`
  - `up_ratio = up_count / total_count`
  - `down_ratio = down_count / total_count`
- 当 `total_count = 0` 时，`up_ratio` 和 `down_ratio` 均返回 `0`。

## 参数约束

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
  "timestamp": "2026-07-01T16:30:00",
  "data": null
}
```

## 使用建议

- 如果只关注行业分层结果，推荐搭配：
  - `idx_type=行业板块`
  - `level=东财一级行业` / `东财二级行业` / `东财三级行业`
- 如果查看概念板块或地域板块，只传 `idx_type` 即可，不需要传 `level`。
- 如果后续前端只展示单边强弱，可以直接使用 `up_ratio` 作为强度指标，`down_ratio` 作为补充信息。
