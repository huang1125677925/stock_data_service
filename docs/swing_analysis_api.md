# 波段分析接口文档

## 概述

波段分析接口用于对股票或 ETF 生成中短期波段交易参考数据。接口只做数据分析和风险提示，不构成买卖建议。

基础路径：

```text
/django/api/strategy/
```

接口地址：

```http
GET /django/api/strategy/swing-analysis/
```

数据来源：

- 股票不复权行情：Tushare `daily`
- 股票前复权/后复权行情：Tushare `pro_bar`
- ETF 行情：Tushare `fund_daily`

## 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `target_type` | string | 否 | `stock` | 标的类型，支持 `stock` 或 `etf` |
| `code` | string | 是 | - | 标的代码。股票可传 `600519` 或 `600519.SH`；ETF 传 `510300.SH` |
| `start_date` | string | 否 | 最近约 240 天 | 开始日期，支持 `YYYYMMDD` 或 `YYYY-MM-DD` |
| `end_date` | string | 否 | 当前日期 | 结束日期，支持 `YYYYMMDD` 或 `YYYY-MM-DD` |
| `adjust` | string | 否 | 不复权 | 股票复权类型，可选 `qfq` 前复权、`hfq` 后复权；ETF 忽略该参数 |

## 请求示例

股票不复权：

```bash
curl "http://localhost:8000/django/api/strategy/swing-analysis/?target_type=stock&code=600519&start_date=20250101&end_date=20251231"
```

股票前复权：

```bash
curl "http://localhost:8000/django/api/strategy/swing-analysis/?target_type=stock&code=600519&start_date=20250101&end_date=20251231&adjust=qfq"
```

ETF：

```bash
curl "http://localhost:8000/django/api/strategy/swing-analysis/?target_type=etf&code=510300.SH&start_date=20250101&end_date=20251231"
```

## 响应示例

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-05-17T18:30:00.000000",
  "data": {
    "target_type": "stock",
    "ts_code": "600519.SH",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "adjust": "qfq",
    "data_source": "Tushare",
    "data_interface": "pro_bar",
    "data_points": 120,
    "analysis": {
      "latest_trade_date": "2025-12-31",
      "latest_close": 1520.12,
      "period_return_pct": 12.35,
      "period_high": 1688.0,
      "period_high_date": "2025-10-20",
      "period_low": 1280.0,
      "period_low_date": "2025-02-05",
      "position_percentile": 58.85,
      "pullback_from_high_pct": -9.95,
      "rebound_from_low_pct": 18.76,
      "ma": {
        "ma5": 1518.22,
        "ma10": 1502.51,
        "ma20": 1488.33,
        "ma60": 1450.26
      },
      "momentum": {
        "momentum_5d_pct": 1.12,
        "momentum_20d_pct": 4.88
      },
      "volatility": {
        "atr14": 32.51,
        "atr14_pct": 2.1384
      },
      "volume": {
        "latest_vol": 51234.0,
        "avg_vol20": 48600.0,
        "volume_ratio_20": 1.0542
      },
      "levels": {
        "support_20d": 1456.0,
        "resistance_20d": 1548.0
      },
      "wave_stage": "uptrend",
      "decision_hint": {
        "bias": "trend_follow",
        "reasons": [
          "收盘价位于 MA20 与 MA60 上方，且 MA20 高于 MA60，趋势结构偏强。"
        ],
        "risk_flags": []
      }
    },
    "theory": [
      {
        "name": "趋势跟随",
        "basis": "波段交易优先顺着中期趋势操作，MA20 与 MA60 用于识别中短期趋势结构。",
        "related_fields": ["ma", "wave_stage"]
      }
    ]
  }
}
```

## 关键字段说明

| 字段 | 说明 |
| --- | --- |
| `period_return_pct` | 查询区间首尾收盘价涨跌幅 |
| `period_high` / `period_low` | 查询区间内最高价和最低价 |
| `position_percentile` | 当前收盘价在区间高低点中的位置，越接近 100 越靠近区间高位 |
| `pullback_from_high_pct` | 当前价相对区间最高价的回撤幅度 |
| `rebound_from_low_pct` | 当前价相对区间最低价的反弹幅度 |
| `ma.ma5/ma10/ma20/ma60` | 均线，用于判断短中期趋势结构 |
| `momentum_5d_pct` / `momentum_20d_pct` | 近 5 日和 20 日动量 |
| `atr14_pct` | 14 日 ATR 占当前价格比例，用于衡量波动风险 |
| `volume_ratio_20` | 当前成交量相对 20 日均量的倍数 |
| `support_20d` / `resistance_20d` | 近 20 日低点/高点，作为短期支撑压力参考 |
| `wave_stage` | 波段阶段判断：`uptrend`、`downtrend`、`high_zone_with_volume`、`low_zone_repair`、`range_bound` |
| `decision_hint.bias` | 分析倾向：趋势跟随、区间交易、观察反转、规避等待等 |
| `decision_hint.risk_flags` | 风险提示，例如高位追涨、波动过大、量能不足 |

## 波段理论口径

### 1. 趋势跟随

波段交易通常优先识别主要趋势，再在趋势方向上寻找回调或突破机会。接口使用 `MA20` 和 `MA60` 判断中短期趋势结构：

- `close > MA20 > MA60` 通常表示趋势结构偏强。
- `close < MA20 < MA60` 通常表示趋势结构偏弱。

### 2. 支撑压力

价格在一段区间内反复形成高低点，高点附近常形成压力，低点附近常形成支撑。接口使用：

- 查询区间最高价/最低价
- 近 20 日最高价/最低价
- 当前价格在区间中的百分位

这些数据用于判断当前标的是在低位修复、中位震荡，还是高位突破/滞涨区域。

### 3. 波动率风控

ATR 反映最近价格真实波动幅度。波段交易中，ATR 可用于估算止损距离和仓位风险。`atr14_pct` 越高，说明相对价格的波动越大，仓位和止损应更谨慎。

### 4. 量价确认

突破、反转和趋势延续通常需要成交量确认。接口使用 `volume_ratio_20` 判断当前成交量相对 20 日均量是否放大：

- 大于 `1` 表示成交量高于 20 日均量。
- 小于 `0.7` 表示量能明显不足，价格信号确认度下降。

## 注意事项

- 本接口只提供数据分析，不提供买卖建议。
- ETF 只支持不复权行情，`adjust` 参数对 ETF 无效。
- 股票传 `adjust=qfq` 或 `adjust=hfq` 时使用 Tushare `pro_bar`，需要本地 Tushare SDK 和相应权限。
- 如果 Tushare 未返回数据，`analysis` 会返回 `null`，并在 `message` 中说明原因。
