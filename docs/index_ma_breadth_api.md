# 指数 MA 市场宽度接口文档

## 接口地址

- `GET /django/api/strategy/index-ma-breadth/`

## 接口说明

- 功能：返回指定日期范围内，各大盘指数中“收盘价高于 N 日均线”的成分股占比（市场宽度）。
- 分析的指数列表与 `major-index-rps` 接口一致（国内 + 国际大盘指数）。
- 计算逻辑与 `industry-ma-breadth` 接口一致，仅将“行业板块”维度替换为“指数”维度。
- 指数成分股通过 Tushare `index_weight` 接口获取（取回溯窗口内最新一期的成分与权重）。
- 响应格式：统一使用 `success_response` / `error_response` 封装。
- 依赖的 Tushare 接口：
  - `index_weight`（指数成分股）
  - `stk_factor_pro`（成分股技术指标 / 均线）
  - `trade_cal`（交易日历，通过内部工具获取）

> 说明：`index_weight` 仅提供境内指数（如 `000300.SH`、`000905.SH` 等）的成分股。默认指数列表中的国际指数（如 `HSI`、`SPX`、`N225` 等）在 Tushare 无成分股数据，会被自动跳过，并在 `errors` 字段中给出提示，不影响其他指数结果。

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| ----- | ---- | ---- | ------ | ---- |
| `start_date` | string | 否 | 过去90天 | 开始日期，格式 `YYYY-MM-DD` |
| `end_date` | string | 否 | 当天 | 结束日期，格式 `YYYY-MM-DD` |
| `ma_window` | integer | 否 | `20` | 移动平均窗口（交易日），建议优先使用 `5/10/20/30/60/90/250` |
| `index_codes` | string | 否 | 默认指数列表 | 指数代码列表（逗号分隔），例如 `000300.SH,000905.SH`；为空则使用与 `major-index-rps` 一致的默认指数列表 |

### 默认指数列表（与 major-index-rps 一致）

- 国内：`000001.SH`（上证综指）、`000016.SH`（上证50）、`000300.SH`（沪深300）、`000905.SH`（中证500）、`000688.SH`（科创50）、`399001.SZ`（深证成指）、`399006.SZ`（创业板指）
- 国际：`XIN9`、`HSI`、`HKTECH`、`HKAH`、`DJI`、`SPX`、`IXIC`、`FTSE`、`FCHI`、`GDAXI`、`N225`、`KS11`、`AS51`、`SENSEX`、`IBOVESPA`、`RTS`、`TWII`、`CKLSE`、`SPTSX`、`CSX5P`、`RUT`

> 国际指数无 `index_weight` 成分股数据，实际计算仅覆盖境内指数。如需只分析境内指数，可显式传入 `index_codes`。

## 请求示例

### 1. 查询默认指数近一个月 MA20 宽度

```text
GET /django/api/strategy/index-ma-breadth/?start_date=2026-06-01&end_date=2026-06-27&ma_window=20
```

### 2. 只查询沪深300与中证500 MA20 宽度

```text
GET /django/api/strategy/index-ma-breadth/?start_date=2026-06-01&end_date=2026-06-27&ma_window=20&index_codes=000300.SH,000905.SH
```

### 3. 查询沪深300近 10 天 MA60 宽度

```text
GET /django/api/strategy/index-ma-breadth/?start_date=2026-06-15&end_date=2026-06-27&ma_window=60&index_codes=000300.SH
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
        "index_code": "000300.SH",
        "index_name": "沪深300",
        "count_above_ma": 168,
        "eligible_count": 300,
        "breadth_ratio": 0.56
      },
      {
        "date": "2026-06-26",
        "index_code": "000905.SH",
        "index_name": "中证500",
        "count_above_ma": 294,
        "eligible_count": 500,
        "breadth_ratio": 0.588
      }
    ],
    "start_date": "2026-06-01",
    "end_date": "2026-06-27",
    "ma_window": 20,
    "index_codes": ["000300.SH", "000905.SH"],
    "errors": [],
    "query_time": "2026-06-27T12:00:00"
  }
}
```

当使用默认指数列表时，国际指数会因无成分股数据被跳过，并在 `errors` 中给出提示：

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-06-27T12:00:00",
  "data": {
    "total": 7,
    "data": [ "..." ],
    "start_date": "2026-06-01",
    "end_date": "2026-06-27",
    "ma_window": 20,
    "index_codes": null,
    "errors": [
      "HSI 在最近 45 天内无 index_weight 成分数据",
      "SPX 在最近 45 天内无 index_weight 成分数据"
    ],
    "query_time": "2026-06-27T12:00:00"
  }
}
```

## 响应字段说明

### 顶层 `data` 字段

| 字段名 | 类型 | 说明 |
| ----- | ---- | ---- |
| `total` | integer | `data` 数组的记录数 |
| `data` | array | 每日每指数的宽度记录数组，见下表 |
| `start_date` / `end_date` | string | 请求日期范围回显 |
| `ma_window` | integer | 移动平均窗口回显 |
| `index_codes` | array/null | 请求的指数代码列表回显；未传时为 `null` |
| `errors` | array | 提示 / 部分失败信息（例如国际指数无成分股） |
| `query_time` | string | 查询时间 |

### `data` 数组元素字段

| 字段名 | 类型 | 说明 |
| ----- | ---- | ---- |
| `date` | string | 交易日期，格式 `YYYY-MM-DD` |
| `index_code` | string | 指数代码 |
| `index_name` | string | 指数名称 |
| `count_above_ma` | integer | 当日指数成分股中收盘价高于 MA_N 的股票数量 |
| `eligible_count` | integer | 当日有有效 MA_N 值、可参与统计的成分股数量 |
| `breadth_ratio` | number | 宽度比例，计算公式为 `count_above_ma / eligible_count`，范围 `[0,1]`，保留 4 位小数 |

## 计算逻辑

### 1. 指数与交易日获取

- 指数列表来自 `index_codes` 参数；未传时使用与 `major-index-rps` 一致的默认指数列表。
- 通过交易日历获取区间内的实际交易日；当 `ma_window` 不在预计算窗口内时，起始日会自动向前扩展 `ma_window * 2` 个自然日以保证首日均线可算。

### 2. 指数成分获取

- 对每个指数调用 `index_weight`，回溯窗口为 `end_date` 前 45 个自然日（覆盖至少一次成分调整）。
- 取窗口内最新一期 `trade_date` 的成分股 `con_code` 列表，套用到整个查询区间（口径与行业接口一致）。
- 国际指数无成分股数据时跳过，并在 `errors` 中记录提示。

### 3. 技术指标获取

- 汇总所有目标指数成分股的并集，按交易日调用 `stk_factor_pro` 拉取全市场技术指标快照后在本地过滤，因子快照每个交易日只请求一次并被所有指数复用。
- 当 `ma_window` 为 `5/10/20/30/60/90/250` 时，直接使用 `stk_factor_pro` 的 `ma_bfq_N` 字段。
- 其他整数窗口会基于 `stk_factor_pro` 返回的 `close` 在本地滚动计算均线。

### 4. 宽度计算

- 对每个指数、每个交易日计算：
  - `count_above_ma`：收盘价严格大于 MA_N 的成分股数量
  - `eligible_count`：当日有有效 MA_N 的成分股数量
  - `breadth_ratio = count_above_ma / eligible_count`
- 当 `eligible_count = 0` 时，`breadth_ratio` 返回 `0`。

## 参数约束

- `ma_window` 必须为整数（`<= 1` 时按 `2` 处理）。
- `index_codes` 为逗号分隔的指数代码；未知代码仍会尝试请求 `index_weight`，无数据则跳过并在 `errors` 中提示。

## 错误响应示例

```json
{
  "code": 400,
  "message": "参数格式错误：ma_window应为整数",
  "timestamp": "2026-06-27T12:00:00"
}
```

```json
{
  "code": 500,
  "message": "获取指数MA市场宽度数据失败: 未获取到任何指数的成分股数据",
  "timestamp": "2026-06-27T12:00:00"
}
```

## 使用建议

- 如果优先考虑性能，建议优先使用 `ma_window=20` 或其他 `stk_factor_pro` 已内置的均线窗口。
- 由于国际指数无成分股数据，若只关心境内指数宽度，建议显式传入 `index_codes`（如 `000300.SH,000905.SH,000016.SH`）以减少无效请求。
