# 上升通道靠近下轨波段选股接口文档

## 概述

本接口用于筛选 ETF 或股票中“通道线朝上，并且当前价格靠近下通道线”的波段候选标的。接口只返回数据分析结果，不影响其他创建任务或交易流程，也不构成投资建议。

接口地址：

```http
GET /django/api/strategy/swing-channel-candidates/
```

数据来源：

| 标的类型 | 候选池数据 | 行情数据 |
| --- | --- | --- |
| ETF | Tushare `etf_basic` + 最近交易日 `fund_daily` | Tushare `fund_daily` |
| 股票 | Tushare 最近交易日 `bak_daily` | Tushare `daily`；传 `adjust=qfq/hfq` 时使用 `pro_bar` |

## ETF 候选池过滤规则

ETF 默认参考 `/django/api/etf/basic/` 的处理口径，并过滤掉无效 ETF：

| 规则 | 说明 |
| --- | --- |
| 剔除 `.OF` | 只保留交易所 ETF，不返回场外基金代码 |
| 最近交易日有 `fund_daily` 数据 | 过滤停牌、无行情或 Tushare 无最新日线数据的 ETF |
| 上市时间大于 6 个月 | 使用 `list_date` 过滤新上市且数据不足的 ETF |
| 正常上市 | 如果 Tushare 返回 `list_status`，仅保留 `L` |
| 流动性排序 | 按最近交易日 `fund_daily.amount` 从高到低扫描 |

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `target_type` | string | 否 | `etf` | 标的类型，支持 `etf` 或 `stock` |
| `codes` | string | 否 | - | 指定扫描代码，多个用英文逗号分隔。传入后不再使用默认候选池 |
| `start_date` | string | 否 | 最近约 240 天 | 行情开始日期，支持 `YYYYMMDD` 或 `YYYY-MM-DD` |
| `end_date` | string | 否 | 当前日期 | 行情结束日期，支持 `YYYYMMDD` 或 `YYYY-MM-DD` |
| `channel_window` | int | 否 | `60` | 通道计算窗口，最小 20，最大 180 |
| `max_distance_pct` | number | 否 | `3.0` | 当前收盘价距离下通道线的最大百分比 |
| `max_channel_position_pct` | number | 否 | `35.0` | 当前价格在通道内的位置上限，越小越靠近下轨 |
| `min_slope_pct` | number | 否 | `0.0` | 下通道线最小日斜率百分比，用于过滤斜率过弱标的 |
| `universe_limit` | int | 否 | `100` | 默认候选池扫描数量，最大 2000 |
| `limit` | int | 否 | `50` | 返回数量，最大 500 |
| `adjust` | string | 否 | 不复权 | 股票复权类型，可选 `qfq` 或 `hfq`；ETF 忽略 |

## 筛选逻辑

接口会对每个候选标的取最近 `channel_window` 个交易日，对高点序列和低点序列分别做线性拟合，形成上通道线与下通道线，并筛选：

| 条件 | 说明 |
| --- | --- |
| `is_channel_up = true` | 上轨和下轨斜率都大于 0，表示通道整体上移 |
| `distance_to_lower_pct >= 0` | 当前价不低于下轨 |
| `distance_to_lower_pct <= max_distance_pct` | 当前价距离下轨足够近 |
| `channel_position_pct <= max_channel_position_pct` | 当前价处于通道下方区域 |
| `lower_slope_pct_per_day >= min_slope_pct` | 下轨上行速度满足最小要求 |

评分 `score` 仅用于排序参考，主要奖励“离下轨更近、通道位置更低、下轨斜率更强”的标的。

## 请求示例

筛选 ETF：

```bash
curl "http://localhost:8000/django/api/strategy/swing-channel-candidates/?target_type=etf&universe_limit=500&limit=50"
```

筛选股票，使用前复权行情：

```bash
curl "http://localhost:8000/django/api/strategy/swing-channel-candidates/?target_type=stock&universe_limit=1000&limit=100&adjust=qfq"
```

指定 ETF 代码扫描：

```bash
curl "http://localhost:8000/django/api/strategy/swing-channel-candidates/?target_type=etf&codes=510300.SH,159919.SZ&channel_window=60&max_distance_pct=2"
```

## 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "target_type": "etf",
    "data_source": "Tushare",
    "universe_trade_date": "2026-05-18",
    "start_date": "2025-09-20",
    "end_date": "2026-05-18",
    "filters": {
      "channel_window": 60,
      "max_distance_pct": 3.0,
      "max_channel_position_pct": 35.0,
      "min_slope_pct": 0.0,
      "universe_limit": 500,
      "limit": 50,
      "adjust": null,
      "codes": []
    },
    "total": 2,
    "matched_total": 2,
    "scanned_total": 500,
    "skipped_total": 8,
    "data": [
      {
        "target_type": "etf",
        "ts_code": "510300.SH",
        "code": "510300.SH",
        "name": "沪深300ETF",
        "index_code": "000300.SH",
        "index_name": "沪深300",
        "exchange": "SSE",
        "list_date": "2012-05-28",
        "etf_type": "股票型",
        "amount": 1234567.89,
        "analysis": {
          "latest_trade_date": "2026-05-18",
          "latest_close": 4.123,
          "channel_window": 60,
          "lower_line_latest": 4.04,
          "upper_line_latest": 4.42,
          "channel_width_pct": 9.2166,
          "distance_to_lower_pct": 2.0131,
          "channel_position_pct": 21.8421,
          "lower_slope": 0.0012,
          "upper_slope": 0.0015,
          "lower_slope_pct_per_day": 0.029105,
          "upper_slope_pct_per_day": 0.036381,
          "is_channel_up": true
        },
        "score": 4.8123
      }
    ],
    "skipped_sample": [
      {
        "ts_code": "xxxxxx.SH",
        "reason": "行情数据不足或通道无法计算"
      }
    ],
    "theory": [
      "上升通道由不断抬高的高点与低点构成，代表资金愿意在更高位置承接。",
      "靠近下通道线通常对应趋势内回调区，理论上比追高更便于设置止损。",
      "筛选结果仍需要结合量能、市场环境与个股/ETF 基本面确认，不构成交易建议。"
    ],
    "query_time": "2026-05-18T10:30:00.000000"
  }
}
```

## 关键字段说明

| 字段 | 说明 |
| --- | --- |
| `universe_trade_date` | 默认候选池使用的最近交易日 |
| `scanned_total` | 实际扫描候选数量 |
| `matched_total` | 满足条件的总数量，可能大于本次返回数量 |
| `total` | 本次返回数量 |
| `latest_close` | 最新收盘价 |
| `lower_line_latest` | 最新下通道线价格，基于低点序列线性拟合后的窗口末端值 |
| `upper_line_latest` | 最新上通道线价格，基于高点序列线性拟合后的窗口末端值 |
| `distance_to_lower_pct` | 当前收盘价距离下通道线百分比，越小越靠近下轨 |
| `channel_position_pct` | 当前价格在上下轨之间的位置，0 表示下轨，100 表示上轨 |
| `lower_slope_pct_per_day` | 下轨每日上行幅度占当前价格的百分比 |
| `upper_slope_pct_per_day` | 上轨每日上行幅度占当前价格的百分比 |
| `is_channel_up` | 上轨和下轨是否同时向上 |
| `skipped_sample` | 因行情不足或 Tushare 返回异常被跳过的样例，最多返回 20 条 |

## 使用建议

- ETF 默认扫描建议先用 `universe_limit=300~1000`，避免一次请求触发过多 Tushare 调用。
- 如果只关注少量标的，优先使用 `codes` 参数，响应更快且不会依赖候选池。
- `max_distance_pct` 越小，筛选越严格；常用范围可设为 `1.5~5`。
- `channel_window` 越长，越偏中期趋势；常用范围可设为 `40~90`。
- 接口不判断买点有效性，建议结合成交量、市场趋势、支撑跌破止损等规则二次确认。
