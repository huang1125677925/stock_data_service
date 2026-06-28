# Tushare版ETF与行业热点接口文档

本文档整理最近改造为 Tushare 数据源的接口，覆盖 ETF 最近交易日行情、行业热点分析相关接口。

## 1. 文档范围

本次改造涉及以下接口：

- `GET /django/api/etf/daily/latest/`
- `GET /django/api/strategy/industry-turnover-percentile/`
- `GET /django/api/strategy/industry-ma-breadth/`
- `GET /django/api/strategy/industry-scale-breadth/`
- `GET /django/api/strategy/industry-actual-output/`
- `GET /django/api/stock/industry/heatmap-data/`
- `GET /django/api/stock/industry/fund-flow/data/`

## 2. 总体说明

### 2.1 数据源

上述接口当前统一改为优先或直接从 Tushare 获取数据，不再依赖原先的数据库行情表或 AkShare 作为主链路。

### 2.2 通用响应结构

接口统一通过 `success_response` / `error_response` 返回，成功响应结构通常如下：

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-05-16T10:00:00",
  "data": {}
}
```

失败时通常返回：

```json
{
  "code": 500,
  "message": "获取数据失败: xxx",
  "timestamp": "2026-05-16T10:00:00",
  "data": null
}
```

### 2.3 日期格式

- ETF 接口筛选参数使用 `YYYY-MM-DD`
- 行业宽度、成交额占比分位数等接口使用 `YYYY-MM-DD`
- 财报期参数 `report_date` 使用 `YYYYMMDD`
- 热力图接口的 `start_date` / `end_date` 使用 `YYYYMMDD`

### 2.4 权限与限制

- `industry-actual-output` 和 `industry/heatmap-data` 依赖 `income_vip` / `fina_indicator_vip`
- 如果当前 Tushare Token 没有对应权限，这两个接口可能返回空数据或失败
- 文档中的示例字段为当前实现输出，后续如代码新增字段，应以实际接口返回为准

## 3. ETF接口

### 3.1 ETF最近交易日行情

**接口地址**：`GET /django/api/etf/daily/latest/`

**功能说明**：

- 从 Tushare 交易日历中倒序查找最近一个有 ETF 数据的交易日
- 从 `fund_daily` 拉取该交易日全部 ETF 日线行情
- 补充本地 `EtfBasic` 的 ETF 基础信息
- 支持按跟踪指数的发布机构、类别/主题筛选
- 支持按筛选维度输出聚合分析

**Tushare数据源**：

- `trade_cal`
- `fund_daily`
- `index_basic`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
| ----- | ---- | ---- | ---- |
| index_publisher | string | 否 | 按跟踪指数发布机构筛选，模糊匹配 |
| index_category | string | 否 | 按跟踪指数类别/主题筛选，模糊匹配 `category`、`index_name`、`index_fullname` |
| group_by | string | 否 | 分类分析维度，可选：`index_publisher`、`index_category` |

**响应示例**：

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-05-16T10:00:00",
  "data": [
    {
      "ts_code": "510300.SH",
      "trade_date": "20260515",
      "close": 4.125,
      "pct_chg": 0.83,
      "amount": 3256789.12,
      "csname": "沪深300ETF",
      "index_code": "000300.SH",
      "index_name": "沪深300",
      "mgr_name": "华泰柏瑞基金",
      "index_publisher": "中证指数有限公司",
      "index_category": "规模指数",
      "index_fullname": "沪深300指数"
    }
  ],
  "trade_date": "20260515",
  "total": 1,
  "filters": {
    "index_publisher": "中证指数有限公司",
    "index_category": null,
    "group_by": "index_publisher"
  },
  "analysis": [
    {
      "group_by": "index_publisher",
      "group_value": "中证指数有限公司",
      "etf_count": 24,
      "index_count": 12,
      "avg_pct_chg": 0.4567,
      "up_count": 18,
      "down_count": 6,
      "flat_count": 0,
      "total_amount": 67890123.45,
      "sample_index_names": ["沪深300", "中证500"]
    }
  ]
}
```

**顶层字段说明**：

| 字段名 | 类型 | 说明 |
| ----- | ---- | ---- |
| data | array | ETF 行情明细列表 |
| trade_date | string | 实际返回的数据交易日，格式 `YYYYMMDD` |
| total | integer | 返回的 ETF 条数 |
| filters | object | 本次请求使用的筛选条件回显 |
| analysis | array | 分组分析结果 |

**使用示例**：

```http
GET /django/api/etf/daily/latest/
GET /django/api/etf/daily/latest/?index_category=半导体
GET /django/api/etf/daily/latest/?index_publisher=中证指数有限公司
GET /django/api/etf/daily/latest/?index_category=消费&group_by=index_publisher
```

## 4. 行业热点接口

### 4.1 板块成交额百分位

**接口地址**：`GET /django/api/strategy/industry-turnover-percentile/`

**功能说明**：

- 基于东方财富板块快照计算每日板块成交额
- 支持 `行业板块`、`概念板块`、`地域板块`
- 当 `idx_type=行业板块` 时，支持按 `东财一级行业`、`东财二级行业`、`东财三级行业` 过滤
- 对目标板块集合按日计算成交额占总额比例与成交额百分位

**Tushare数据源**：

- `trade_cal`
- `dc_index`
- `dc_daily`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
| ----- | ---- | ---- | ---- |
| start_date | string | 否 | 开始日期，格式 `YYYY-MM-DD` |
| end_date | string | 否 | 结束日期，格式 `YYYY-MM-DD` |
| idx_type | string | 否 | 东方财富板块类型，支持 `行业板块`、`概念板块`、`地域板块`，默认 `行业板块` |
| level | string | 否 | 东财行业层级，仅 `idx_type=行业板块` 时生效，支持 `东财一级行业`、`东财二级行业`、`东财三级行业` |

**响应示例**：

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-05-16T10:00:00",
  "data": {
    "total": 1,
    "data": [
      {
        "date": "2026-05-15",
        "sector_code": "BK0475.DC",
        "sector_name": "有色金属",
        "idx_type": "行业板块",
        "level": "东财一级行业",
        "amount": 321456789.12,
        "daily_total_amount": 5681234567.89,
        "amount_ratio": 0.0566,
        "amount_percentile": 94
      }
    ],
    "start_date": "2026-04-01",
    "end_date": "2026-05-15",
    "actual_end_date": "2026-05-15",
    "idx_type": "行业板块",
    "level": "东财一级行业",
    "query_time": "2026-05-16T10:00:00"
  }
}
```


### 4.2 行业MA市场宽度

**接口地址**：`GET /django/api/strategy/industry-ma-breadth/`

**功能说明**：

- 优先使用本地 JSON 快照文件提供东方财富板块与成分数据
- 查询阶段主要使用 `stk_factor_pro` 计算各板块中收盘价高于 N 日均线的股票占比
- 当本地快照缺失时，再回退到 `trade_cal` + `dc_index` + `dc_member` + `stk_factor_pro`

**Tushare数据源**：

- 查询主链路：`stk_factor_pro`
- 快照导出：`dc_index` + `dc_member`
- 回退链路：
- `trade_cal`
- `dc_index`
- `dc_member`
- `stk_factor_pro`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
| ----- | ---- | ---- | ---- |
| start_date | string | 否 | 开始日期，格式 `YYYY-MM-DD`，默认过去90天 |
| end_date | string | 否 | 结束日期，格式 `YYYY-MM-DD`，默认当天 |
| ma_window | integer | 否 | 均线窗口，默认 `20` |
| idx_type | string | 否 | 东方财富板块类型，支持 `行业板块`、`概念板块`、`地域板块`，默认 `行业板块` |
| level | string | 否 | 东财行业层级，仅 `idx_type=行业板块` 时生效，支持 `东财一级行业`、`东财二级行业`、`东财三级行业` |

**响应示例**：

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-05-16T10:00:00",
  "data": {
    "total": 1,
    "data": [
      {
        "date": "2026-05-15",
        "sector_code": "BK0420.DC",
        "sector_name": "消费电子",
        "count_above_ma": 87,
        "eligible_count": 142,
        "breadth_ratio": 0.6127
      }
    ],
    "start_date": "2026-03-01",
    "end_date": "2026-05-15",
    "ma_window": 20,
    "idx_type": "行业板块",
    "level": "东财一级行业",
    "query_time": "2026-05-16T10:00:00"
  }
}
```

### 4.3 行业规模宽度

**接口地址**：`GET /django/api/strategy/industry-scale-breadth/`

**功能说明**：

- 基于 Tushare 快照计算行业总市值和公司数
- 指标公式：
  `(行业总市值 / 市场总市值) × (行业公司数量 / 市场总公司数量)`

**Tushare数据源**：

- `bak_daily`
- `index_classify`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
| ----- | ---- | ---- | ---- |
| sector_codes | string | 否 | 行业代码列表，逗号分隔 |

**响应示例**：

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-05-16T10:00:00",
  "data": {
    "total": 1,
    "data": [
      {
        "sector_code": "801120.SI",
        "sector_name": "食品饮料",
        "industry_total_market_value": 125678901234.56,
        "market_total_market_value": 9876543210987.65,
        "industry_company_count": 128,
        "market_total_company_count": 5380,
        "market_cap_ratio": 0.012722,
        "company_ratio": 0.023792,
        "scale_breadth": 0.000303
      }
    ],
    "sector_codes": ["801120.SI"],
    "query_time": "2026-05-16T10:00:00"
  }
}
```

### 4.4 行业实际产出规模估算

**接口地址**：`GET /django/api/strategy/industry-actual-output/`

**功能说明**：

- 基于股票行业映射与财报营收数据，估算行业实际产出规模
- 估算公式：
  `估算产出 ≈ 前N企业营业总收入之和 / CRn`
- 当 `report_date` 不传时，默认使用最近一个已完整披露的年报期

**Tushare数据源**：

- `bak_daily`
- `index_classify`
- `income_vip`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
| ----- | ---- | ---- | ---- |
| sector_codes | string | 否 | 行业代码列表，逗号分隔 |
| top_n | integer | 否 | 前 N 家企业数量，默认 `3` |
| report_date | string | 否 | 报告期，格式 `YYYYMMDD` |

**响应示例**：

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-05-16T10:00:00",
  "data": {
    "total": 1,
    "data": [
      {
        "sector_code": "801150.SI",
        "sector_name": "医药生物",
        "top_n": 3,
        "report_date": "20251231",
        "top_n_revenue_sum": 235678901234.12,
        "crn_ratio": 0.318765,
        "estimated_industry_output": 739430124567.88,
        "industry_total_revenue": 739430124567.88,
        "company_count_with_reports": 186
      }
    ],
    "sector_codes": ["801150.SI"],
    "top_n": 3,
    "report_date": "20251231",
    "query_time": "2026-05-16T10:00:00"
  }
}
```

### 4.5 行业业绩热力图

**接口地址**：`GET /django/api/stock/industry/heatmap-data/`

**功能说明**：

- 基于财务数据按行业聚合输出热力图数据结构
- 支持年报、中报、一季报、三季报、季度维度
- 未传时间范围时，默认回看近几年且只取截至当前日期可用的完整报告期

**Tushare数据源**：

- `bak_daily`
- `index_classify`
- `income_vip`
- `fina_indicator_vip`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
| ----- | ---- | ---- | ---- |
| industry | string | 否 | 行业名称，模糊匹配 |
| report_type | string | 否 | `annual`、`semi_annual`、`q1`、`q3`、`quarterly`，默认 `annual` |
| start_date | string | 否 | 开始日期，格式 `YYYYMMDD` |
| end_date | string | 否 | 结束日期，格式 `YYYYMMDD` |

**响应示例**：

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-05-16T10:00:00",
  "data": {
    "dates": ["2023-12-31", "2024-12-31", "2025-12-31"],
    "swCodeNames": [
      {
        "indexCode": "801750.SI",
        "indexName": "计算机"
      }
    ],
    "congestions": {
      "801750.SI": [
        {
          "avg_operating_revenue_growth_rate": 11.54,
          "avg_net_profit_growth_rate": -8.32,
          "total_operating_revenue": 67924252275.68,
          "total_net_profit": 5814793582.1,
          "avg_earnings_per_share": 0.2392,
          "avg_roe": 8.8956,
          "avg_gross_profit_margin": 43.7821,
          "avg_net_assets_per_share": 7.0234,
          "avg_operating_cash_flow_per_share": 0.2845
        }
      ]
    }
  }
}
```

### 4.6 行业资金流向

**接口地址**：`GET /django/api/stock/industry/fund-flow/data/`

**功能说明**：

- 基于最新交易日的东方财富板块快照锁定目标板块
- 按交易日拉取目标板块的资金流数据
- 支持日度序列和按周平均后的周度序列
- 不再从数据库读取主数据，也不再从 AkShare 回补

**Tushare数据源**：

- `trade_cal`
- `dc_index`
- `moneyflow_ind_dc`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
| ----- | ---- | ---- | ---- |
| start_date | string | 否 | 开始日期，格式 `YYYY-MM-DD` |
| end_date | string | 否 | 结束日期，格式 `YYYY-MM-DD` |
| week_flag | boolean | 否 | 是否按周汇聚，默认 `false` |
| idx_type | string | 否 | 东方财富板块类型，支持 `行业板块`、`概念板块`、`地域板块`，默认 `行业板块` |
| level | string | 否 | 东财行业层级，仅 `idx_type=行业板块` 时生效，支持 `东财一级行业`、`东财二级行业`、`东财三级行业` |

**响应示例**：

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-05-16T10:00:00",
  "data": {
    "dates": ["2026-05-12", "2026-05-13", "2026-05-14", "2026-05-15"],
    "swCodeNames": [
      {
        "indexCode": "BK1036",
        "indexName": "半导体"
      }
    ],
    "congestions": {
      "BK1036": [
        {
          "main_net_inflow_amount": 123456.78,
          "main_net_inflow_ratio": 1.23,
          "super_large_net_inflow_amount": 223456.78,
          "super_large_net_inflow_ratio": 2.23,
          "large_net_inflow_amount": 323456.78,
          "large_net_inflow_ratio": 3.23,
          "medium_net_inflow_amount": -12345.67,
          "medium_net_inflow_ratio": -0.12,
          "small_net_inflow_amount": -23456.78,
          "small_net_inflow_ratio": -0.23,
          "total_net_inflow_amount": 633111.89,
          "total_net_inflow_ratio": 6.34
        }
      ]
    }
  }
}
```

当 `week_flag=true` 时：

- `dates` 格式为 `YYYY-Www`
- `congestions[code]` 中每个对象表示该周平均值
- `level` 仅在 `idx_type=行业板块` 时参与过滤

## 5. 接口与数据源对照表

| 接口 | 当前主数据源 |
| ----- | ---- |
| `/django/api/etf/daily/latest/` | `trade_cal` + `fund_daily` + `index_basic` |
| `/django/api/strategy/industry-turnover-percentile/` | `trade_cal` + `dc_index` + `dc_daily` |
| `/django/api/strategy/industry-ma-breadth/` | `trade_cal` + `dc_index` + `dc_member` + `stk_factor_pro` |
| `/django/api/strategy/industry-scale-breadth/` | `bak_daily` + `index_classify` |
| `/django/api/strategy/industry-actual-output/` | `bak_daily` + `index_classify` + `income_vip` |
| `/django/api/stock/industry/heatmap-data/` | `bak_daily` + `index_classify` + `income_vip` + `fina_indicator_vip` |
| `/django/api/stock/industry/fund-flow/data/` | `trade_cal` + `dc_index` + `moneyflow_ind_dc` |

## 6. 已知注意事项

### 6.1 财报类接口

以下接口依赖财报类 VIP 接口：

- `/django/api/strategy/industry-actual-output/`
- `/django/api/stock/industry/heatmap-data/`

如果 Token 权限不足，可能出现：

- 返回空列表
- 返回空热力图结构
- 接口直接报错

### 6.2 行业名称映射

部分接口使用 `bak_daily.industry` 作为股票到行业的映射来源，再与申万一级行业名称做匹配。若 Tushare 某些股票快照行业名与申万名称不完全一致，个别股票可能不会计入行业汇总。

### 6.3 最新交易日回退

ETF 最近交易日接口不是简单取当天，而是：

1. 先查最近若干个交易日
2. 倒序尝试 `fund_daily`
3. 返回最近一个真正有数据的交易日

这可以避免节假日、盘后延迟或 Tushare 某日未落数时直接返回空结果。
