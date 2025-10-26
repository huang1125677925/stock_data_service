# 股票策略API文档

## 指数RPS强度排名API

### 获取实时指数RPS强度排名

**接口地址**: `/api/strategy/index-rps/`

**请求方式**: GET

**请求参数**:

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| ----- | --- | ---- | ----- | ---- |
| periods | string | 否 | "5,20,60" | 时间周期，多个周期用逗号分隔 |
| save | boolean | 否 | false | 是否保存到数据库 |

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2024-05-20T12:00:00",
  "data": {
    "total": 100,
    "data": [
      {
        "指数代码": "886001",
        "指数简称": "电子信息",
        "5日涨跌幅": 3.25,
        "RPS_5": 95.5,
        "20日涨跌幅": 5.67,
        "RPS_20": 92.3,
        "60日涨跌幅": 10.45,
        "RPS_60": 88.7
      },
      // 更多数据...
    ],
    "periods": [5, 20, 60],
    "saved_count": 0,
    "errors": [],
    "query_time": "2024-05-20T12:00:00"
  }
}
```

### 获取历史RPS数据

**接口地址**: `/api/strategy/historical-rps/`

**请求方式**: GET

**请求参数**:

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| ----- | --- | ---- | ----- | ---- |
| period | integer | 否 | 20 | 时间周期 |
| limit | integer | 否 | 100 | 返回数量限制 |
| offset | integer | 否 | 0 | 偏移量 |

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2024-05-20T12:00:00",
  "data": {
    "total": 500,
    "data": [
      {
        "index_code": "886001",
        "index_name": "电子信息",
        "period": 20,
        "change_percent": 5.67,
        "rps_value": 92.3,
        "created_at": "2024-05-20T10:00:00"
      },
      // 更多数据...
    ],
    "period": 20,
    "query_time": "2024-05-20T12:00:00"
  }
}
```

## 使用说明

1. 获取指数RPS强度排名数据时，可以通过`periods`参数指定需要计算的时间周期，多个周期用逗号分隔。
2. 如果需要保存数据到数据库，可以设置`save=true`参数。
3. 查询历史RPS数据时，可以通过`period`参数指定需要查询的时间周期。
4. 历史数据支持分页查询，可以通过`limit`和`offset`参数进行控制。

## 数据说明

- RPS (Relative Price Strength) 是相对价格强度指标，用于衡量一个指数相对于其他指数的强弱程度。
- RPS计算公式: RPS = (1 - 排名 / 总板块数) × 100
- RPS值越高，表示该指数的相对强度越高。

---

## 行业MA20市场宽度指标API

### 获取行业MA20市场宽度

**接口地址**: `/api/strategy/industry-ma-breadth/`

**请求方式**: GET

**请求参数**:

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| ----- | --- | ---- | ----- | ---- |
| start_date | string | 否 | - | 开始日期，格式YYYY-MM-DD，默认过去90天 |
| end_date | string | 否 | - | 结束日期，格式YYYY-MM-DD，默认当天 |
| ma_window | integer | 否 | 20 | 移动平均窗口大小（交易日），建议≥2 |
| sector_codes | string | 否 | - | 行业板块代码列表，逗号分隔；为空则计算所有板块 |

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2024-05-20T12:00:00",
  "data": {
    "total": 2,
    "data": [
      {
        "date": "2024-05-17",
        "sector_code": "BK001",
        "sector_name": "电子信息",
        "count_above_ma": 56,
        "eligible_count": 100,
        "breadth_ratio": 0.56
      },
      {
        "date": "2024-05-18",
        "sector_code": "BK001",
        "sector_name": "电子信息",
        "count_above_ma": 60,
        "eligible_count": 102,
        "breadth_ratio": 0.5882
      }
    ],
    "start_date": "2024-05-10",
    "end_date": "2024-05-18",
    "ma_window": 20,
    "sector_codes": ["BK001"],
    "query_time": "2024-05-20T12:00:00"
  }
}
```

**字段含义说明（patterns项）**:
- date: 交易日期，格式 YYYY-MM-DD。
- hammer（TA-Lib: CDLHAMMER）: 锤子线，常见于下跌末期的看涨反转形态；信号取值：100=识别到锤子线，0=无信号。
- morning_star（TA-Lib: CDLMORNINGSTAR）: 早晨之星，三根K线构成的看涨反转形态；信号取值：100=识别到，0=无信号。
- piercing（TA-Lib: CDLPIERCING）: 刺透形态，两根K线构成的看涨反转；信号取值：100=识别到，0=无信号。
- kicking（TA-Lib: CDLKICKING）: 踢击形态，由两根跳空实体K线构成；信号取值：100=看涨踢击，-100=看跌踢击，0=无信号。
- inverted_hammer（TA-Lib: CDLINVERTEDHAMMER）: 倒锤头，常见于下跌末期的看涨反转提示；信号取值：100=识别到，0=无信号。
- engulfing（TA-Lib: CDLENGULFING）: 吞没形态，两根K线构成；信号取值：100=看涨吞没，-100=看跌吞没，0=无信号。
- harami（TA-Lib: CDLHARAMI）: 孕线，两根K线构成；信号取值：100=看涨孕线，-100=看跌孕线，0=无信号。
- hanging_man（TA-Lib: CDLHANGINGMAN）: 上吊线，常见于上涨末期的看跌反转提示；信号取值：-100=识别到，0=无信号。
- evening_star（TA-Lib: CDLEVENINGSTAR）: 黄昏之星，三根K线构成的看跌反转形态；信号取值：-100=识别到，0=无信号。
- dark_cloud_cover（TA-Lib: CDLDARKCLOUDCOVER）: 乌云盖顶，两根K线构成的看跌反转；信号取值：-100=识别到，0=无信号。
- three_black_crows（TA-Lib: CDL3BLACKCROWS）: 三只黑乌鸦，连续三根阴线的看跌延续/反转信号；信号取值：-100=识别到，0=无信号。
- identical_three_crows（TA-Lib: CDLIDENTICAL3CROWS）: 同样三乌鸦，三根近似实体的阴线；信号取值：-100=识别到，0=无信号。
- doji（TA-Lib: CDLDOJI）: 十字星，开收盘几乎相等的中性形态；信号取值：100=识别到，0=无信号。
- long_legged_doji（TA-Lib: CDLLONGLEGGEDDOJI）: 长脚十字星，影线很长、实体极小的十字星；信号取值：100=识别到，0=无信号。
- gravestone_doji（TA-Lib: CDLGRAVESTONEDOJI）: 墓碑十字星，上影线长、下影线短或无的十字星；信号取值：100=识别到，0=无信号。
- two_crows（TA-Lib: CDL2CROWS）: 两只乌鸦，连续两根阴线的看跌延续/反转；信号取值：-100=识别到，0=无信号。
- three_inside（TA-Lib: CDL3INSIDE）: 三内部上涨/下跌，孕线组合的延续/反转形态；信号取值：±100，0=无信号。
- three_line_strike（TA-Lib: CDL3LINESTRIKE）: 三线打击，三根同向K线后出现反向强实体；信号取值：±100，0=无信号。
- three_outside（TA-Lib: CDL3OUTSIDE）: 三外部上涨/下跌，孕线的外部扩展；信号取值：±100，0=无信号。
- three_stars_in_south（TA-Lib: CDL3STARSINSOUTH）: 南方三星，低位三根星线形态；信号取值：±100，0=无信号。
- three_white_soldiers（TA-Lib: CDL3WHITESOLDIERS）: 三个白兵，连续三根阳线的看涨延续；信号取值：100=识别到，0=无信号。
- abandoned_baby（TA-Lib: CDLABANDONEDBABY）: 弃婴，跳空的三烛线反转形态；信号取值：±100，0=无信号。
- advance_block（TA-Lib: CDLADVANCEBLOCK）: 大敌当前，多头推进但力度衰减的形态；信号取值：-100=识别到，0=无信号。
- belt_hold（TA-Lib: CDLBELTHOLD）: 捉腰带线，开盘即为实体端的长实体；信号取值：±100，0=无信号。
- breakaway（TA-Lib: CDLBREAKAWAY）: 脱离形态，五根K线的趋势脱离；信号取值：±100，0=无信号。
- closing_marubozu（TA-Lib: CDLCLOSINGMARUBOZU）: 收盘秃线，收盘在极端的秃线；信号取值：±100，0=无信号。
- conceal_baby_swallow（TA-Lib: CDLCONCEALBABYSWALL）: 藏婴吞没，影线与实体组合的吞没；信号取值：-100=识别到，0=无信号。
- counterattack（TA-Lib: CDLCOUNTERATTACK）: 反击线，收盘价相同的对立实体；信号取值：±100，0=无信号。
- doji_star（TA-Lib: CDLDOJISTAR）: 十字星形态，星位的十字线；信号取值：±100，0=无信号。
- dragonfly_doji（TA-Lib: CDLDRAGONFLYDOJI）: 蜻蜓十字，下影线很长的十字；信号取值：100=识别到，0=无信号。
- evening_doji_star（TA-Lib: CDLEVENINGDOJISTAR）: 十字暮星，三烛线看跌反转；信号取值：-100=识别到，0=无信号。
- gap_side_by_side_white（TA-Lib: CDLGAPSIDESIDEWHITE）: 并列阳线，上/下跳空并列阳线；信号取值：±100，0=无信号。
- homing_pigeon（TA-Lib: CDLHOMINGPIGEON）: 家鸽，小实体包裹的看涨组合；信号取值：100=识别到，0=无信号。
- in_neck（TA-Lib: CDLINNECK）: 颈内线，阴线后次日收盘接近前日最低；信号取值：-100=识别到，0=无信号。
- kicking_by_length（TA-Lib: CDLKICKINGBYLENGTH）: 由较长秃线决定的反冲；信号取值：±100，0=无信号。
- ladder_bottom（TA-Lib: CDLLADDERBOTTOM）: 梯底，低位多头反攻形态；信号取值：100=识别到，0=无信号。
- long_line（TA-Lib: CDLLONGLINE）: 长线，极长实体的K线；信号取值：±100，0=无信号。
- marubozu（TA-Lib: CDLMARUBOZU）: 秃线/缺影线，实体无影线；信号取值：±100，0=无信号。
- matching_low（TA-Lib: CDLMATCHINGLOW）: 相同低价，连续两根最低价相同的看涨形态；信号取值：100=识别到，0=无信号。
- mat_hold（TA-Lib: CDLMATHOLD）: 垫脚石，五根K线的看涨延续形态；信号取值：100=识别到，0=无信号。
- morning_doji_star（TA-Lib: CDLMORNINGDOJISTAR）: 十字晨星，三烛线看涨反转；信号取值：100=识别到，0=无信号。
- on_neck（TA-Lib: CDLONNECK）: 颈上线，阴线后次日收盘与前日最低相同；信号取值：-100=识别到，0=无信号。
- rickshaw_man（TA-Lib: CDLRICKSHAWMAN）: 黄包车夫，带长影线的十字；信号取值：100=识别到，0=无信号。
- rise_fall_three_methods（TA-Lib: CDLRISEFALL3METHODS）: 上升/下降三法，中继形态；信号取值：±100，0=无信号。
- separating_lines（TA-Lib: CDLSEPARATINGLINES）: 分离线，趋势延续形态；信号取值：±100，0=无信号。
- shooting_star（TA-Lib: CDLSHOOTINGSTAR）: 射击之星，高位看跌反转；信号取值：-100=识别到，0=无信号。
- short_line（TA-Lib: CDLSHORTLINE）: 短线，极短实体的K线；信号取值：±100，0=无信号。
- spinning_top（TA-Lib: CDLSPINNINGTOP）: 纺锤线，小实体上下影线均较长；信号取值：±100，0=无信号。
- stalled_pattern（TA-Lib: CDLSTALLEDPATTERN）: 停顿形态，上涨趋势中的停顿；信号取值：-100=识别到，0=无信号。
- stick_sandwich（TA-Lib: CDLSTICKSANDWICH）: 条形三明治，三根K线构成的看涨反转；信号取值：100=识别到，0=无信号。
- takuri（TA-Lib: CDLTAKURI）: 探水杆，极长下影线的反转提示；信号取值：100=识别到，0=无信号。
- tasuki_gap（TA-Lib: CDLTASUKIGAP）: 跳空并列线，跳空后的并列线；信号取值：±100，0=无信号。
- thrusting（TA-Lib: CDLTHRUSTING）: 插入形态，下跌中的弱反弹；信号取值：-100=识别到，0=无信号。
- tristar（TA-Lib: CDLTRISTAR）: 三星，三根十字线的反转形态；信号取值：±100，0=无信号。
- unique_three_river（TA-Lib: CDLUNIQUE3RIVER）: 独特三河，低位三烛线形态；信号取值：100=识别到，0=无信号。
- upside_gap_two_crows（TA-Lib: CDLUPSIDEGAP2CROWS）: 向上跳空两只乌鸦，看跌延续/反转；信号取值：-100=识别到，0=无信号。
- xside_gap_three_methods（TA-Lib: CDLXSIDEGAP3METHODS）: 向上/向下跳空三法，中继形态；信号取值：±100，0=无信号。

> 通用说明：TA-Lib CDL 系列的信号取值统一为 +100（看涨）、-100（看跌）、0（无信号）。部分形态仅有正向或负向信号（如 CDLHAMMER 仅有 +100，CDLDARKCLOUDCOVER 仅有 -100）。

**错误响应示例**:

```json
{
  "code": 400,
  "message": "参数格式错误：ma_window应为整数",
  "timestamp": "2024-05-20T12:00:00"
}
```

**说明**:
- 宽度定义为“收盘价高于MA_N”的股票在行业内的占比，breadth_ratio范围为[0,1]，结果四舍五入到4位小数。
- 行业与个股映射通过 IndividualStock.industry 与 IndustrySector.name 对应，仅使用数据库数据。
- 接口返回统一使用 success_response/error_response 封装。

---

## 行业规模宽度指标API

### 获取行业规模宽度

**接口地址**: `/api/strategy/industry-scale-breadth/`

**请求方式**: GET

**请求参数**:

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| ----- | --- | ---- | ----- | ---- |
| sector_codes | string | 否 | - | 行业板块代码列表，逗号分隔；为空则计算所有板块 |

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2024-05-20T12:00:00",
  "data": {
    "total": 1,
    "data": [
      {
        "sector_code": "BK001",
        "sector_name": "电子信息",
        "industry_total_market_value": 1234567890.12,
        "market_total_market_value": 9876543210.98,
        "industry_company_count": 120,
        "market_total_company_count": 4000,
        "market_cap_ratio": 0.1249,
        "company_ratio": 0.03,
        "scale_breadth": 0.0037
      }
    ],
    "sector_codes": ["BK001"],
    "query_time": "2024-05-20T12:00:00"
  }
}
```

**说明**:
- 规模宽度公式：`(行业总市值 / 市场总市值) × (行业公司数量 / 市场总公司数量)`。
- 市值数据来自 IndustrySector.total_market_value；公司数量来自 IndividualStock（按行业名称聚合）。
- 结果按 scale_breadth 降序排序；统一使用 success_response/error_response 封装；仅从数据库获取数据。

---

## 行业实际产出规模估算API

### 获取行业实际产出规模（估算）

**接口地址**: `/api/strategy/industry-actual-output/`

**请求方式**: GET

**请求参数**:

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| ----- | --- | ---- | ----- | ---- |
| sector_codes | string | 否 | - | 行业板块代码列表，逗号分隔；为空则计算所有板块 |
| top_n | integer | 否 | 3 | 前N企业数量，必须为正整数 |
| report_date | string | 否 | - | 报告期，格式YYYYMMDD；为空时使用最新业绩快报 |

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2024-05-20T12:00:00",
  "data": {
    "total": 1,
    "data": [
      {
        "sector_code": "BK001",
        "sector_name": "电子信息",
        "top_n": 3,
        "report_date": "20231231",
        "top_n_revenue_sum": 450000000.00,
        "crn_ratio": 0.375,
        "estimated_industry_output": 1200000000.00,
        "industry_total_revenue": 1200000000.00,
        "company_count_with_reports": 85
      }
    ],
    "sector_codes": ["BK001"],
    "top_n": 3,
    "report_date": "20231231",
    "query_time": "2024-05-20T12:00:00"
  }
}
```

**错误响应示例**:

```json
{
  "code": 400,
  "message": "参数格式错误：top_n应为整数",
  "timestamp": "2024-05-20T12:00:00"
}
```

**说明**:
- 估算公式：`行业实际产出 ≈ 前N企业营业总收入之和 / 行业集中度（CRn）`，其中 `CRn = Σ(Top N 企业营业收入 / 行业总营业收入)`（0-1）。
- 若以数据库计算 CRn，则估算值等于行业总营业收入；仅从数据库获取数据（IndividualStock、PerformanceReport、IndustrySector）。
- 接口返回统一使用 success_response/error_response 封装；结果按 estimated_industry_output 降序排序。

---

## 行业资金流相关坐标点API

### 获取行业资金流二维坐标点（按净流入排序）

**接口地址**: `/django/api/strategy/industry-fund-flow-correlation/`

**请求方式**: GET

**请求参数**:

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| ----- | --- | ---- | ----- | ---- |
| sector_code | string | 是 | - | 行业板块代码 |
| start_date | string | 是 | - | 开始日期，格式YYYY-MM-DD |
| end_date | string | 是 | - | 结束日期，格式YYYY-MM-DD |
| x_axis | string | 否 | `change_percent` | 横轴指标，支持 `change_percent`（涨跌幅）、`turnover_rate`（换手率）、`amplitude`（振幅） |
| y_axis | string | 否 | `main` | 纵轴净流入类型，支持 `main`、`super_large`、`large`、`medium`、`small`、`all`；其中 `all` 表示“全部净流入”，为四类净流入之和（super_large + large + medium + small） |
| sort_order | string | 否 | `desc` | 排序方向，`asc` 或 `desc`（按 y 值排序） |

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2024-05-20T12:00:00",
  "data": {
    "sector_code": "BK001",
    "sector_name": "电子信息",
    "filters": {
      "start_date": "2024-05-10",
      "end_date": "2024-05-18",
      "x_axis": "change_percent",
      "y_axis": "all",
      "sort_order": "desc"
    },
    "total": 3,
    "points": [
      { "date": "2024-05-16", "x": 1.23, "y": 345678.9 },
      { "date": "2024-05-15", "x": -0.56, "y": 123456.7 },
      { "date": "2024-05-14", "x": 0.78, "y": 98765.4 }
    ],
    "x_label": "change_percent",
    "y_label": "all_net_inflow_amount"
  }
}
```

**错误响应示例**:

```json
{
  "code": 400,
  "message": "x_axis 参数不合法，应为 change_percent/turnover_rate/amplitude",
  "timestamp": "2024-05-20T12:00:00"
}
```

```json
{
  "code": 404,
  "message": "行业板块不存在: BK999",
  "timestamp": "2024-05-20T12:00:00"
}
```

**说明**:
- 仅使用数据库数据，横轴字段来自 IndustrySectorDaily：`change_percent`（涨跌幅）、`turnover_rate`（换手率）、`amplitude`（振幅）。
- 纵轴净流入来自 IndustrySectorFundFlow：`main_net_inflow_amount`、`super_large_net_inflow_amount`、`large_net_inflow_amount`、`medium_net_inflow_amount`、`small_net_inflow_amount`；当 y_axis=`all` 时，表示“全部净流入”= 超大+大+中+小四类净流入金额之和。
- 返回统一使用 success_response/error_response 封装；结果按 y 值排序（默认降序）。
- 日期格式为 YYYY-MM-DD；时区为 Asia/Shanghai；数据精度以数据库为准。

---

## 个股K线形态识别API

### 分析指定股票的K线形态（TA-Lib）

**接口地址**: `/django/api/strategy/individual-analysis/candlestick/<stock_code>/`

**请求方式**: GET

**请求参数**:

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| ----- | --- | ---- | ----- | ---- |
| stock_code | string | 是 | - | 股票代码，路径参数 |
| start_date | string | 否 | - | 开始日期，格式YYYY-MM-DD |
| end_date | string | 否 | - | 结束日期，格式YYYY-MM-DD |

**响应示例**:

```json
{
  "code": 200,
  "message": "识别K线形态成功",
  "timestamp": "2024-10-26T12:00:00",
  "data": {
    "stock_code": "600519",
    "stock_name": "贵州茅台",
    "total": 3,
    "patterns": [
      {
        "date": "2024-10-23",
        "hammer": 0,
        "morning_star": 100,
        "piercing": 0,
        "kicking": 0,
        "inverted_hammer": 0,
        "engulfing": -100,
        "harami": 0,
        "hanging_man": 0,
        "evening_star": 0,
        "dark_cloud_cover": 0,
        "three_black_crows": -100,
        "identical_three_crows": 0,
        "doji": 0,
        "long_legged_doji": 0,
        "gravestone_doji": 0
      },
      {
        "date": "2024-10-24",
        "hammer": 100,
        "morning_star": 0,
        "piercing": 0,
        "kicking": 0,
        "inverted_hammer": 0,
        "engulfing": 0,
        "harami": 100,
        "hanging_man": 0,
        "evening_star": 0,
        "dark_cloud_cover": 0,
        "three_black_crows": 0,
        "identical_three_crows": 0,
        "doji": 0,
        "long_legged_doji": 0,
        "gravestone_doji": 0
      }
    ]
  }
}
```

**错误响应示例**:

```json
{
  "code": 404,
  "message": "股票代码不存在: 000000",
  "timestamp": "2024-10-26T12:00:00"
}
```

```json
{
  "code": 404,
  "message": "无日频数据",
  "timestamp": "2024-10-26T12:00:00"
}
```

**说明**:
- 识别形态使用 TA-Lib 的 CDL 系列函数，信号值定义：+100 看涨，-100 看跌，0 无信号。
- 仅从数据库获取数据（IndividualStock、IndividualStockDaily），不进行外部数据拉取。
- 输入数据按“日期”升序排列并转换为 numpy 数组后传入 TA-Lib。
- 返回统一使用 success_response/error_response 封装；日期格式为 YYYY-MM-DD。