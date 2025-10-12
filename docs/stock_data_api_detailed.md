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