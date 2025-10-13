# 股票数据服务接口文档

## 接口概述

本文档详细描述了股票数据服务提供的所有API接口，包括请求参数、返回值格式及示例。所有接口均遵循RESTful设计规范，返回JSON格式数据。

### 通用返回格式

所有接口统一使用以下格式返回数据：

**成功响应**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": { ... }
}
```

**错误响应**：
```json
{
    "code": 400/404/500,
    "message": "错误信息",
    "timestamp": "2024-01-01T12:00:00"
}
```

## 股票实时行情相关接口

### 1. 获取上证A股实时行情数据

获取当前所有上证A股的实时行情数据，支持分页查询。

**接口URL**：`/django/api/stock/realtime/`

**请求方式**：GET

**请求参数**：

| 参数名 | 类型 | 必选 | 描述 |
| ------ | ---- | ---- | ---- |
| limit | int | 否 | 返回股票数量限制，默认返回全部 |
| offset | int | 否 | 偏移量，默认0 |

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": {
        "total": 500,
        "stocks": [
            {
                "code": "600000",
                "name": "浦发银行",
                "price": 10.25,
                "change": 0.25,
                "change_percent": 2.5,
                "volume": 12345678,
                "turnover_rate": 1.23,
                "market_cap": 123.45
            },
            // 更多股票数据...
        ],
        "query_time": "2024-01-01T12:00:00"
    }
}
```

### 2. 根据条件筛选上证A股股票

根据价格、换手率、市值等条件筛选股票，并支持排序。

**接口URL**：`/django/api/stock/filter/`

**请求方式**：GET

**请求参数**：

| 参数名 | 类型 | 必选 | 描述 |
| ------ | ---- | ---- | ---- |
| min_price | float | 否 | 最低价格，默认0 |
| max_price | float | 否 | 最高价格，默认1000 |
| min_turnover_rate | float | 否 | 最低换手率(%)，默认0 |
| max_turnover_rate | float | 否 | 最高换手率(%)，默认100 |
| min_market_cap | float | 否 | 最低流通市值(亿元)，默认0 |
| max_market_cap | float | 否 | 最高流通市值(亿元)，默认100000 |
| sort_by | string | 否 | 排序字段，默认turnover_rate |
| ascending | bool | 否 | 是否升序，默认true |

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": {
        "total": 50,
        "stocks": [
            {
                "code": "600000",
                "name": "浦发银行",
                "price": 10.25,
                "turnover_rate": 1.23,
                "market_cap": 123.45
            },
            // 更多股票数据...
        ],
        "filters": {
            "min_price": 0,
            "max_price": 1000,
            "min_turnover_rate": 0,
            "max_turnover_rate": 100,
            "min_market_cap": 0,
            "max_market_cap": 100000,
            "sort_by": "turnover_rate",
            "ascending": true
        }
    }
}
```

### 3. 获取单只股票详细信息

获取指定股票代码的详细信息。

**接口URL**：`/django/api/stock/stock/detail/<str:code>/`

**请求方式**：GET

**路径参数**：

| 参数名 | 类型 | 必选 | 描述 |
| ------ | ---- | ---- | ---- |
| code | string | 是 | 股票代码，如"600000" |

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": {
        "code": "600000",
        "name": "浦发银行",
        "price": 10.25,
        "change": 0.25,
        "change_percent": 2.5,
        "open": 10.00,
        "high": 10.30,
        "low": 9.95,
        "close": 10.25,
        "volume": 12345678,
        "turnover_rate": 1.23,
        "market_cap": 123.45,
        "pe_ratio": 15.6,
        "pb_ratio": 1.2
    }
}
```

### 4. 获取市场概况

获取上证A股市场整体概况，包括上涨、下跌、平盘股票数量等信息。

**接口URL**：`/django/api/stock/market-summary/`

**请求方式**：GET

**请求参数**：无

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": {
        "total_stocks": 1000,
        "rising_stocks": 600,
        "falling_stocks": 300,
        "unchanged_stocks": 100,
        "limit_up_stocks": 50,
        "limit_down_stocks": 20,
        "average_change_percent": 1.5
    }
}
```

### 5. 获取热门股票

获取基于换手率排序的热门股票列表。

**接口URL**：`/django/api/stock/hot-stocks/`

**请求方式**：GET

**请求参数**：

| 参数名 | 类型 | 必选 | 描述 |
| ------ | ---- | ---- | ---- |
| count | int | 否 | 返回股票数量，默认10，最大100 |

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": {
        "count": 10,
        "stocks": [
            {
                "code": "600000",
                "name": "浦发银行",
                "price": 10.25,
                "turnover_rate": 5.67,
                "volume": 12345678,
                "change_percent": 2.5
            },
            // 更多股票数据...
        ]
    }
}
```

### 6. 获取低换手率优质股票

获取符合特定条件的低换手率优质股票列表。

**接口URL**：`/django/api/stock/low-turnover-stocks/`

**请求方式**：GET

**请求参数**：

| 参数名 | 类型 | 必选 | 描述 |
| ------ | ---- | ---- | ---- |
| count | int | 否 | 返回股票数量，默认20，最大100 |

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": {
        "count": 20,
        "stocks": [
            {
                "code": "600000",
                "name": "浦发银行",
                "price": 25.60,
                "turnover_rate": 2.34,
                "market_cap": 256.78
            },
            // 更多股票数据...
        ],
        "criteria": {
            "price_range": "10-60",
            "turnover_range": "1%-5%",
            "min_market_cap": "100亿元",
            "sort_by": "turnover_rate_asc"
        }
    }
}
```

## 股票详细信息接口

### 7. 获取股票类型信息

获取指定股票的类型信息，如是否属于科创板、创业板等。

**接口URL**：`/django/api/stock/stock/type/<str:code>/`

**请求方式**：GET

**路径参数**：

| 参数名 | 类型 | 必选 | 描述 |
| ------ | ---- | ---- | ---- |
| code | string | 是 | 股票代码，如"600000" |

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": {
        "code": "600000",
        "name": "浦发银行",
        "board_type": "主板",
        "industry": "银行",
        "is_st": false,
        "is_hs300": true,
        "is_sz50": false,
        "is_zz500": false
    }
}
```

### 8. 获取股票估值分析信息

获取指定股票的估值分析信息。

**接口URL**：`/django/api/stock/stock/stock-value-em/<str:code>/`

**请求方式**：GET

**路径参数**：

| 参数名 | 类型 | 必选 | 描述 |
| ------ | ---- | ---- | ---- |
| code | string | 是 | 股票代码，如"600000" |

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": [
        {
            "date": "2024-01-01",
            "市盈率": 15.6,
            "市净率": 1.2,
            "市销率": 3.4,
            "市现率": 5.6,
            "股息率": 2.3
        },
        // 更多历史估值数据...
    ]
}
```

### 9. 获取股票资金流向

获取指定股票的资金流向信息。

**接口URL**：`/django/api/stock/stock/fund-flow/<str:code>/`

**请求方式**：GET

**路径参数**：

| 参数名 | 类型 | 必选 | 描述 |
| ------ | ---- | ---- | ---- |
| code | string | 是 | 股票代码，如"600000" |

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": [
        {
            "date": "2024-01-01",
            "主力净流入": 1234.56,
            "小单净流入": -234.56,
            "中单净流入": 345.67,
            "大单净流入": 567.89,
            "超大单净流入": 789.01
        },
        // 更多历史资金流向数据...
    ]
}
```

### 10. 获取股票历史数据

获取指定股票的历史交易数据。

**接口URL**：`/django/api/stock/stock/history/<str:code>/`

**请求方式**：GET

**路径参数**：

| 参数名 | 类型 | 必选 | 描述 |
| ------ | ---- | ---- | ---- |
| code | string | 是 | 股票代码，如"600000" |

**请求参数**：

| 参数名 | 类型 | 必选 | 描述 |
| ------ | ---- | ---- | ---- |
| start_date | string | 否 | 开始日期，格式：YYYYMMDD |
| end_date | string | 否 | 结束日期，格式：YYYYMMDD |
| period | string | 否 | 周期，可选值：daily(日)、weekly(周)、monthly(月)，默认daily |

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": {
        "code": "600000",
        "name": "浦发银行",
        "period": "daily",
        "history": [
            {
                "date": "2024-01-01",
                "open": 10.00,
                "high": 10.30,
                "low": 9.95,
                "close": 10.25,
                "volume": 12345678,
                "amount": 123456789.01
            },
            // 更多历史数据...
        ]
    }
}
```

### 11. 获取股票账户统计信息

获取股票账户统计信息。

**接口URL**：`/django/api/stock/stock/account/statistics/`

**请求方式**：GET

**请求参数**：无

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": {
        "total_accounts": 12345678,
        "active_accounts": 1234567,
        "new_accounts": 12345,
        "statistics_date": "2024-01-01",
        "weekly_change": 1.23,
        "monthly_change": 2.34
    }
}
```

### 12. 获取股票市场活跃度

获取股票市场活跃度指标。

**接口URL**：`/django/api/stock/stock/market-activity/`

**请求方式**：GET

**请求参数**：无

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": {
        "date": "2024-01-01",
        "turnover_rate": 2.34,
        "volume": 12345678901,
        "amount": 1234567890123.45,
        "active_stocks_ratio": 78.9,
        "market_sentiment_index": 56.7
    }
}
```

### 13. 批量获取股票类型

批量获取多只股票的类型信息。

**接口URL**：`/django/api/stock/stock/types/batch/`

**请求方式**：GET

**请求参数**：

| 参数名 | 类型 | 必选 | 描述 |
| ------ | ---- | ---- | ---- |
| codes | string | 是 | 股票代码列表，以逗号分隔，如"600000,600001,600002" |

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": {
        "600000": {
            "name": "浦发银行",
            "board_type": "主板",
            "industry": "银行"
        },
        "600001": {
            "name": "邯郸钢铁",
            "board_type": "主板",
            "industry": "钢铁"
        },
        "600002": {
            "name": "齐鲁石化",
            "board_type": "主板",
            "industry": "化工"
        }
    }
}
```

### 14. 获取行业列表

获取所有行业分类列表。

**接口URL**：`/django/api/stock/industries/`

**请求方式**：GET

**请求参数**：无

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": [
        {
            "industry_code": "BK0001",
            "industry_name": "银行",
            "stock_count": 30
        },
        {
            "industry_code": "BK0002",
            "industry_name": "保险",
            "stock_count": 15
        },
        // 更多行业数据...
    ]
}
```

## 行业板块相关接口

### 15. 获取行业板块列表

获取所有行业板块列表，支持分页查询。

**接口URL**：`/django/api/stock/industry-sectors/`

**请求方式**：GET

**请求参数**：

| 参数名 | 类型 | 必选 | 描述 |
| ------ | ---- | ---- | ---- |
| limit | int | 否 | 返回行业板块数量限制，默认返回全部 |
| offset | int | 否 | 偏移量，默认0 |

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": {
        "total": 100,
        "sectors": [
            {
                "code": "BK0001",
                "name": "农业",
                "stock_count": 50,
                "latest_price": 1234.56,
                "change_percent": 1.23
            },
            // 更多行业板块数据...
        ],
        "query_time": "2024-01-01T12:00:00"
    }
}
```

### 16. 获取行业板块日频数据

获取指定行业板块的日频数据。

**接口URL**：`/django/api/stock/industry-sector/daily/<str:code>/`

**请求方式**：GET

**路径参数**：

| 参数名 | 类型 | 必选 | 描述 |
| ------ | ---- | ---- | ---- |
| code | string | 是 | 行业板块代码，如"BK0001" |

**请求参数**：

| 参数名 | 类型 | 必选 | 描述 |
| ------ | ---- | ---- | ---- |
| start_date | string | 否 | 开始日期，格式：YYYYMMDD |
| end_date | string | 否 | 结束日期，格式：YYYYMMDD |

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": {
        "sector_code": "BK0001",
        "sector_name": "农业",
        "daily_data": [
            {
                "date": "2024-01-01",
                "open": 1230.45,
                "high": 1240.56,
                "low": 1225.67,
                "close": 1234.56,
                "change_percent": 1.23,
                "volume": 12345678,
                "amount": 123456789.01
            },
            // 更多日频数据...
        ],
        "query_time": "2024-01-01T12:00:00"
    }
}
```

### 17. 获取行业板块实时行情

获取指定行业板块的实时行情数据。

**接口URL**：`/django/api/stock/industry-sector/realtime/<str:code>/`

**请求方式**：GET

**路径参数**：

| 参数名 | 类型 | 必选 | 描述 |
| ------ | ---- | ---- | ---- |
| code | string | 是 | 行业板块代码，如"BK0001" |

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": {
        "sector_code": "BK0001",
        "sector_name": "农业",
        "latest_price": 1234.56,
        "change": 15.67,
        "change_percent": 1.23,
        "open": 1230.45,
        "high": 1240.56,
        "low": 1225.67,
        "volume": 12345678,
        "amount": 123456789.01,
        "turnover_rate": 2.34,
        "rising_stocks": 30,
        "falling_stocks": 15,
        "unchanged_stocks": 5
    }
}
```

### 18. 获取行业板块成分股

获取指定行业板块的成分股列表。

**接口URL**：`/django/api/stock/industry-sector/constituents/<str:code>/`

**请求方式**：GET

**路径参数**：

| 参数名 | 类型 | 必选 | 描述 |
| ------ | ---- | ---- | ---- |
| code | string | 是 | 行业板块代码，如"BK0001" |

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": {
        "sector_code": "BK0001",
        "sector_name": "农业",
        "constituents": [
            {
                "code": "600000",
                "name": "浦发银行",
                "price": 10.25,
                "change_percent": 2.5,
                "weight": 5.67
            },
            // 更多成分股数据...
        ],
        "total": 50,
        "query_time": "2024-01-01T12:00:00"
    }
}
```

## 业绩快报相关接口

### 19. 获取行业业绩快报汇聚数据

获取按行业和报告期汇聚的业绩快报数据，支持多种报告类型筛选。

**接口URL**：`/django/api/stock/industry/performance-reports/`

**请求方式**：GET

**请求参数**：

| 参数名 | 类型 | 必选 | 描述 |
| ------ | ---- | ---- | ---- |
| industry | string | 否 | 行业名称，支持模糊匹配，如"软件开发" |
| report_type | string | 否 | 报告类型，可选值：annual(年报)、semi_annual(中报)、q1(一季报)、q3(三季报)、quarterly(季报，包含一季报和三季报) |
| start_date | string | 否 | 开始日期，格式：YYYYMMDD |
| end_date | string | 否 | 结束日期，格式：YYYYMMDD |

**报告类型说明**：
- `annual`: 年报，筛选报告期以1231结尾的数据
- `semi_annual`: 中报，筛选报告期以0630结尾的数据  
- `q1`: 一季报，筛选报告期以0331结尾的数据
- `q3`: 三季报，筛选报告期以0930结尾的数据
- `quarterly`: 季报，包含一季报和三季报数据（向后兼容）

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": {
        "total_records": 11,
        "aggregated_reports": [
            {
                "report_date": "20240331",
                "industry": "软件开发",
                "company_count": 195,
                "total_operating_revenue": 70969077274.93,
                "total_net_profit": -2337025713.16,
                "avg_earnings_per_share": -0.0327,
                "avg_operating_revenue_growth_rate": 7.87,
                "avg_net_profit_growth_rate": -28.39,
                "avg_roe": -1.0688,
                "avg_gross_profit_margin": 44.4228,
                "avg_net_assets_per_share": 7.1994,
                "avg_operating_cash_flow_per_share": -0.3102
            },
            {
                "report_date": "20230331",
                "industry": "软件开发",
                "company_count": 195,
                "total_operating_revenue": 67924252275.68,
                "total_net_profit": -2814793582.1,
                "avg_earnings_per_share": -0.0392,
                "avg_operating_revenue_growth_rate": 11.54,
                "avg_net_profit_growth_rate": -119.3,
                "avg_roe": -1.8956,
                "avg_gross_profit_margin": 43.7821,
                "avg_net_assets_per_share": 7.0234,
                "avg_operating_cash_flow_per_share": -0.2845
            }
            // 更多汇聚数据...
        ],
        "query_params": {
            "industry": "软件开发",
            "report_type": "q1",
            "start_date": null,
            "end_date": null
        }
    }
}
```

**字段说明**：

| 字段名 | 类型 | 描述 |
| ------ | ---- | ---- |
| report_date | string | 报告期，格式YYYYMMDD |
| industry | string | 行业名称 |
| company_count | int | 该行业该报告期的公司数量 |
| total_operating_revenue | float | 总营业收入（元） |
| total_net_profit | float | 总净利润（元） |
| avg_earnings_per_share | float | 平均每股收益（元） |
| avg_operating_revenue_growth_rate | float | 平均营业收入增长率（%） |
| avg_net_profit_growth_rate | float | 平均净利润增长率（%） |
| avg_roe | float | 平均净资产收益率（%） |
| avg_gross_profit_margin | float | 平均毛利率（%） |
| avg_net_assets_per_share | float | 平均每股净资产（元） |
| avg_operating_cash_flow_per_share | float | 平均每股经营现金流（元） |

**使用示例**：

1. 获取软件开发行业一季报数据：
   ```
   GET /django/api/stock/industry/performance-reports/?report_type=q1&industry=软件开发
   ```

2. 获取所有行业年报数据：
   ```
   GET /django/api/stock/industry/performance-reports/?report_type=annual
   ```

3. 获取指定时间范围的季报数据：
   ```
   GET /django/api/stock/industry/performance-reports/?report_type=quarterly&start_date=20230101&end_date=20231231
   ```

### 20. 获取行业热力图数据

获取行业业绩数据的热力图格式，用于可视化展示行业间的对比和时间序列变化。

**接口URL**：`/django/api/stock/industry/heatmap-data/`

**请求方式**：GET

**请求参数**：

| 参数名 | 类型 | 必选 | 描述 |
| ------ | ---- | ---- | ---- |
| industry | string | 否 | 行业名称，支持模糊匹配，如"软件开发" |
| report_type | string | 否 | 报告类型，可选值：annual(年报)、semi_annual(中报)、q1(一季报)、q3(三季报)、quarterly(季报) |
| start_date | string | 否 | 开始日期，格式：YYYYMMDD |
| end_date | string | 否 | 结束日期，格式：YYYYMMDD |

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": {
        "dates": [
            "2023-03-31",
            "2023-06-30",
            "2023-09-30",
            "2023-12-31",
            "2024-03-31"
        ],
        "swCodeNames": [
            {
                "indexCode": "801001.SI",
                "indexName": "软件开发"
            },
            {
                "indexCode": "801002.SI",
                "indexName": "电子设备"
            },
            {
                "indexCode": "801003.SI",
                "indexName": "医药生物"
            }
            // 更多行业...
        ],
        "congestions": {
            "801001.SI": [
                {
                    "avg_operating_revenue_growth_rate": 11.54,
                    "avg_net_profit_growth_rate": -119.3,
                    "total_operating_revenue": 67924252275.68,
                    "total_net_profit": -2814793582.1,
                    "avg_earnings_per_share": -0.0392,
                    "avg_roe": -1.8956,
                    "avg_gross_profit_margin": 43.7821,
                    "avg_net_assets_per_share": 7.0234,
                    "avg_operating_cash_flow_per_share": -0.2845
                },
                // 更多日期数据...
            ],
            "801002.SI": [
                // 电子设备行业各日期数据...
            ],
            "801003.SI": [
                // 医药生物行业各日期数据...
            ]
            // 更多行业数据...
        }
    }
}
```

**字段说明**：

| 字段名 | 类型 | 描述 |
| ------ | ---- | ---- |
| dates | array | 报告期日期列表，格式YYYY-MM-DD |
| swCodeNames | array | 行业代码和名称映射列表 |
| swCodeNames[].indexCode | string | 行业代码 |
| swCodeNames[].indexName | string | 行业名称 |
| congestions | object | 行业热力图数据，键为行业代码，值为该行业在各报告期的指标数据数组 |
| congestions[code][].avg_operating_revenue_growth_rate | float | 平均营业收入增长率（%） |
| congestions[code][].avg_net_profit_growth_rate | float | 平均净利润增长率（%） |
| congestions[code][].total_operating_revenue | float | 总营业收入（元） |
| congestions[code][].total_net_profit | float | 总净利润（元） |
| congestions[code][].avg_earnings_per_share | float | 平均每股收益（元） |
| congestions[code][].avg_roe | float | 平均净资产收益率（%） |
| congestions[code][].avg_gross_profit_margin | float | 平均毛利率（%） |
| congestions[code][].avg_net_assets_per_share | float | 平均每股净资产（元） |
| congestions[code][].avg_operating_cash_flow_per_share | float | 平均每股经营现金流（元） |

**使用示例**：

1. 获取所有行业的热力图数据：
   ```
   GET /django/api/stock/industry/heatmap-data/
   ```

2. 获取软件开发行业的热力图数据：
   ```
   GET /django/api/stock/industry/heatmap-data/?industry=软件开发
   ```

3. 获取指定时间范围的年报热力图数据：
   ```
   GET /django/api/stock/industry/heatmap-data/?report_type=annual&start_date=20230101&end_date=20231231
   ```

## 行业统计数据接口

### 21. 获取行业统计数据

获取基于个股数据汇聚的行业统计信息，包括市值、价格、交易量等各项指标的统计数据。

**接口URL**：`/django/api/stock/industry/statistics/`

**请求方式**：GET

**请求参数**：

| 参数名 | 类型 | 必选 | 描述 |
| ------ | ---- | ---- | ---- |
| industry | string | 否 | 行业名称，如"银行"、"证券"等，不传则返回所有行业 |

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": {
        "statistics": [
            {
                "industry": "银行",
                "stock_count": 42,
                "total_market_cap_sum": 8765432109876.0,
                "circulating_market_cap_sum": 7654321098765.0,
                "avg_latest_price": 8.404,
                "avg_change_percent": -0.84,
                "avg_change_amount": 0.084,
                "total_volume": 58616093,
                "total_amount": 44305567876.89,
                "avg_amplitude": 2.949,
                "avg_turnover_rate": 1.02,
                "avg_pe_ratio": 5.622,
                "avg_pb_ratio": 0.605,
                "avg_volume_ratio": 1.414,
                "avg_price_change_speed": -0.125,
                "avg_change_5min": -0.112,
                "avg_change_60d": -10.676,
                "avg_change_ytd": 6.962,
                "max_high": 40.3,
                "min_low": 1.98,
                "avg_open_price": 8.355,
                "avg_close_price": 8.404,
                "total_shares_sum": 0,
                "circulating_shares_sum": 0,
                "avg_listing_years": 0
            },
            // 更多行业统计数据...
        ],
        "total_industries": 86,
        "timestamp": "2024-01-01T12:00:00"
    }
}
```

**字段说明**：

| 字段名 | 类型 | 描述 |
| ------ | ---- | ---- |
| industry | string | 行业名称 |
| stock_count | int | 该行业股票数量 |
| total_market_cap_sum | float | 总市值合计（元） |
| circulating_market_cap_sum | float | 流通市值合计（元） |
| avg_latest_price | float | 平均最新价格（元） |
| avg_change_percent | float | 平均涨跌幅（%） |
| avg_change_amount | float | 平均涨跌额（元） |
| total_volume | int | 总成交量（手） |
| total_amount | float | 总成交额（元） |
| avg_amplitude | float | 平均振幅（%） |
| avg_turnover_rate | float | 平均换手率（%） |
| avg_pe_ratio | float | 平均市盈率 |
| avg_pb_ratio | float | 平均市净率 |
| avg_volume_ratio | float | 平均量比 |
| avg_price_change_speed | float | 平均价格变化速度 |
| avg_change_5min | float | 平均5分钟涨跌幅（%） |
| avg_change_60d | float | 平均60日涨跌幅（%） |
| avg_change_ytd | float | 平均年初至今涨跌幅（%） |
| max_high | float | 行业内最高价（元） |
| min_low | float | 行业内最低价（元） |
| avg_open_price | float | 平均开盘价（元） |
| avg_close_price | float | 平均收盘价（元） |
| total_shares_sum | int | 总股本合计（股） |
| circulating_shares_sum | int | 流通股本合计（股） |
| avg_listing_years | float | 平均上市年限 |

### 22. 获取行业排名数据

根据指定指标对行业进行排名，支持多种排序指标和排序方向。

**接口URL**：`/django/api/stock/industry/ranking/`

**请求方式**：GET

**请求参数**：

| 参数名 | 类型 | 必选 | 描述 |
| ------ | ---- | ---- | ---- |
| metric | string | 否 | 排序指标，默认为total_market_cap_sum，可选值见下表 |
| order | string | 否 | 排序方向，desc(降序)或asc(升序)，默认desc |
| limit | int | 否 | 返回行业数量，默认10，最大100 |

**可选排序指标**：

| 指标名称 | 描述 |
| -------- | ---- |
| total_market_cap_sum | 总市值合计 |
| circulating_market_cap_sum | 流通市值合计 |
| avg_change_percent | 平均涨跌幅 |
| total_volume | 总成交量 |
| total_amount | 总成交额 |
| avg_turnover_rate | 平均换手率 |
| avg_pe_ratio | 平均市盈率 |
| avg_pb_ratio | 平均市净率 |
| stock_count | 股票数量 |

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": {
        "ranking": [
            {
                "industry": "银行",
                "stock_count": 42,
                "total_market_cap_sum": 8765432109876.0,
                "circulating_market_cap_sum": 7654321098765.0,
                "avg_latest_price": 8.404,
                "avg_change_percent": -0.84,
                "rank": 1
            },
            {
                "industry": "证券",
                "stock_count": 49,
                "total_market_cap_sum": 3765837035771.0,
                "circulating_market_cap_sum": 3098110107424.0,
                "avg_latest_price": 12.582,
                "avg_change_percent": -0.787,
                "rank": 2
            },
            // 更多排名数据...
        ],
        "ranking_params": {
            "metric": "total_market_cap_sum",
            "order": "desc",
            "limit": 10
        }
    }
}
```

### 23. 获取行业比较数据

比较指定多个行业的统计数据，用于行业间的对比分析。

**接口URL**：`/django/api/stock/industry/comparison/`

**请求方式**：POST

**请求参数**：

| 参数名 | 类型 | 必选 | 描述 |
| ------ | ---- | ---- | ---- |
| industries | array | 是 | 要比较的行业名称列表，如["银行", "证券", "保险"] |

**请求体示例**：
```json
{
    "industries": ["银行", "证券", "保险"]
}
```

**返回示例**：
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-01T12:00:00",
    "data": {
        "comparison": [
            {
                "industry": "银行",
                "stock_count": 42,
                "total_market_cap_sum": 8765432109876.0,
                "circulating_market_cap_sum": 7654321098765.0,
                "avg_latest_price": 8.404,
                "avg_change_percent": -0.84,
                "avg_change_amount": 0.084,
                "total_volume": 58616093,
                "total_amount": 44305567876.89,
                "avg_amplitude": 2.949,
                "avg_turnover_rate": 1.02,
                "avg_pe_ratio": 5.622,
                "avg_pb_ratio": 0.605,
                "avg_volume_ratio": 1.414,
                "avg_price_change_speed": -0.125,
                "avg_change_5min": -0.112,
                "avg_change_60d": -10.676,
                "avg_change_ytd": 6.962,
                "max_high": 40.3,
                "min_low": 1.98,
                "avg_open_price": 8.355,
                "avg_close_price": 8.404,
                "total_shares_sum": 0,
                "circulating_shares_sum": 0,
                "avg_listing_years": 0
            },
            {
                "industry": "证券",
                "stock_count": 49,
                "total_market_cap_sum": 3765837035771.0,
                "circulating_market_cap_sum": 3098110107424.0,
                "avg_latest_price": 12.582,
                "avg_change_percent": -0.787,
                "avg_change_amount": -0.093,
                "total_volume": 37611785,
                "total_amount": 48292191390.71,
                "avg_amplitude": 3.167,
                "avg_turnover_rate": 1.874,
                "avg_pe_ratio": 49.65,
                "avg_pb_ratio": 1.825,
                "avg_volume_ratio": 0.884,
                "avg_price_change_speed": -0.009,
                "avg_change_5min": -0.004,
                "avg_change_60d": 8.237,
                "avg_change_ytd": 12.863,
                "max_high": 37.92,
                "min_low": 4.43,
                "avg_open_price": 12.339,
                "avg_close_price": 12.676,
                "total_shares_sum": 0,
                "circulating_shares_sum": 0,
                "avg_listing_years": 0
            },
            {
                "industry": "保险",
                "stock_count": 6,
                "total_market_cap_sum": 2981049146237.0,
                "circulating_market_cap_sum": 2049676155988.0,
                "avg_latest_price": 39.84,
                "avg_change_percent": -0.88,
                "avg_change_amount": -0.336,
                "total_volume": 2191069,
                "total_amount": 7278062381.0,
                "avg_amplitude": 2.076,
                "avg_turnover_rate": 0.415,
                "avg_pe_ratio": 7.99,
                "avg_pb_ratio": 1.592,
                "avg_volume_ratio": 0.754,
                "avg_price_change_speed": -0.066,
                "avg_change_5min": 0.004,
                "avg_change_60d": -7.483,
                "avg_change_ytd": -3.733,
                "max_high": 63.06,
                "min_low": 7.72,
                "avg_open_price": 39.442,
                "avg_close_price": 33.743,
                "total_shares_sum": 0,
                "circulating_shares_sum": 0,
                "avg_listing_years": 0
            }
        ],
        "comparison_count": 3,
        "timestamp": "2024-01-01T12:00:00"
    }
}
```

**使用示例**：

1. 获取所有行业统计数据：
   ```
   GET /django/api/stock/industry/statistics/
   ```

2. 获取银行行业统计数据：
   ```
   GET /django/api/stock/industry/statistics/?industry=银行
   ```

3. 按总市值排名前5的行业：
   ```
   GET /django/api/stock/industry/ranking/?metric=total_market_cap_sum&limit=5
   ```

4. 按平均涨跌幅升序排列：
   ```
   GET /django/api/stock/industry/ranking/?metric=avg_change_percent&order=asc&limit=10
   ```

5. 比较金融相关行业：
   ```
   POST /django/api/stock/industry/comparison/
   Content-Type: application/json
   
   {
       "industries": ["银行", "证券", "保险", "信托"]
   }
   ```

**特性说明**：

1. **数据来源**：基于IndividualStock模型中的个股数据进行实时汇聚计算
2. **统计方式**：比率类指标（如涨跌幅、换手率、市盈率等）使用平均值，数量类指标（如市值、成交量等）使用总和
3. **缓存机制**：统计数据支持缓存，提高查询性能
4. **实时性**：数据基于最新的个股行情数据计算，保证时效性
5. **完整性**：涵盖市值、价格、交易、估值等多维度指标

## 错误码说明

| 错误码 | 描述 |
| ------ | ---- |
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 注意事项

1. 所有接口均支持HTTPS安全访问
2. 接口调用频率限制为每分钟100次
3. 历史数据查询时间范围不应超过1年
4. 股票代码格式应符合中国股市规范，如上交所股票以"6"开头，深交所股票以"0"或"3"开头
5. 行业板块代码格式为"BK"开头加4位数字
6. 业绩快报数据按报告期和行业进行汇聚，提供行业整体财务指标分析
7. 日期参数格式为YYYYMMDD，如20240331表示2024年3月31日