# 行业涨停趋势强度接口功能增强

## 更新日期
2026-07-05

## 更新内容

### 1. 新增昨日涨停股今日溢价数据

在行业层面增加昨日该行业涨停股今日的开盘溢价数据。

#### 新增字段（在 `industries` 数组中）

- **`yesterday_limit_up_count`** (number): 昨日该行业涨停股数量
- **`yesterday_limit_up_stocks`** (array): 昨日涨停股的今日溢价详情列表
  - `ts_code` (string): 股票代码
  - `name` (string): 股票名称
  - `prev_close` (number): 昨日收盘价（元）
  - `today_open` (number): 今日开盘价（元）
  - `premium_pct` (number): 今日开盘溢价百分比
- **`avg_premium_pct`** (number): 该行业昨日涨停股的平均溢价百分比

#### 计算公式

```
溢价百分比 = (今日开盘价 - 昨日收盘价) / 昨日收盘价 × 100
```

#### 数据来源

- **Tushare `daily` 接口**: 获取股票日线行情数据（开盘价、收盘价）

#### 注意事项

- 仅当存在前一交易日数据时，才会返回这些字段
- 查询区间的第一个交易日不会有昨日溢价数据（因为没有前一日数据）
- ST股票在昨日涨停股中也会被过滤掉
- 支持所有行业映射方式

### 2. 新增行业涨跌幅数据

在行业层面增加该行业当日的涨跌幅数据（仅东财板块映射方式可用）。

#### 新增字段（在 `industries` 数组中）

- **`industry_pct_change`** (number): 该行业当日涨跌幅百分比

#### 数据来源

- **Tushare `dc_daily` 接口**: 东方财富板块日线行情

#### 适用范围

仅在使用以下行业映射方式时返回：
- `dc_concept` - 东财概念板块
- `dc_region` - 东财地域板块
- `dc_l1` - 东财一级行业板块
- `dc_l2` - 东财二级行业板块
- `dc_l3` - 东财三级行业板块

使用 `default` 映射方式时，此字段不返回。

### 3. 更新 source_counts 字段

新增数据源统计字段：

- **`dc_daily`** (number): 区间 `dc_daily` 板块行情记录数；仅在使用东财板块映射方式时有值

## 修改文件清单

### 后端代码
- `stock_strategy/limit_board_service.py`
  - 修改 `get_industry_trend_strength()` 方法，添加昨日溢价和行业涨跌幅计算逻辑
  - 新增 `_fetch_stock_daily()` 方法，用于获取股票日线行情

### API文档
- `docs/limit_board_strategy_api.md`
  - 更新数据源说明，添加 `dc_daily` 和 `daily` 接口说明
  - 更新 `industries` 字段说明，添加新增字段
  - 新增 `yesterday_limit_up_stocks` 字段详细说明
  - 更新 `source_counts` 字段说明
  - 更新示例响应，展示完整数据结构

## API 使用示例

### 示例1: 使用默认映射（包含昨日溢价，不含行业涨跌幅）

```bash
curl "http://localhost:8000/django/api/strategy/limit-board/industry-trend-strength/?start_date=20260101&end_date=20260110"
```

响应示例：
```json
{
  "code": 200,
  "message": "获取行业涨停趋势强度分析成功",
  "data": {
    "data": {
      "20260102": {
        "industries": [
          {
            "industry": "机器人",
            "limit_up_count": 5,
            "status_counts": { "T字板": 1, "一字板": 2, "换手板": 2 },
            "yesterday_limit_up_count": 3,
            "avg_premium_pct": 2.5,
            "yesterday_limit_up_stocks": [
              {
                "ts_code": "000001.SZ",
                "name": "示例股",
                "prev_close": 10.0,
                "today_open": 10.3,
                "premium_pct": 3.0
              }
            ]
          }
        ]
      }
    }
  }
}
```

### 示例2: 使用东财板块映射（包含昨日溢价和行业涨跌幅）

```bash
curl "http://localhost:8000/django/api/strategy/limit-board/industry-trend-strength/?start_date=20260101&end_date=20260110&industry_mapping=dc_l2"
```

响应示例：
```json
{
  "code": 200,
  "message": "获取行业涨停趋势强度分析成功",
  "data": {
    "summary": {
      "industry_mapping": "dc_l2",
      "industry_mapping_label": "东财二级行业板块"
    },
    "data": {
      "20260102": {
        "industries": [
          {
            "industry": "机器人",
            "limit_up_count": 5,
            "status_counts": { "T字板": 1, "一字板": 2, "换手板": 2 },
            "industry_pct_change": 5.23,
            "yesterday_limit_up_count": 3,
            "avg_premium_pct": 2.5,
            "yesterday_limit_up_stocks": [
              {
                "ts_code": "000001.SZ",
                "name": "示例股",
                "prev_close": 10.0,
                "today_open": 10.3,
                "premium_pct": 3.0
              }
            ]
          }
        ]
      }
    },
    "source_counts": {
      "limit_list_ths": 250,
      "limit_list_d_up": 230,
      "dc_board_snapshot_stocks": 5613,
      "dc_daily": 180
    }
  }
}
```

## 技术细节

### 性能优化

1. **批量数据获取**: 使用 `start_date` 和 `end_date` 一次性获取区间内所有数据，避免逐日请求
2. **最小化字段请求**: 只请求必要的字段以减少数据传输量
   - `daily` 接口仅请求: `ts_code,trade_date,open,close`
   - `dc_daily` 接口仅请求: `trade_date,ts_code,name,pct_change`
3. **条件加载**: 仅在使用东财板块映射方式时才调用 `dc_daily` 接口

### 数据过滤

- ST股票在计算昨日溢价时也会被过滤
- 只有能匹配到行情数据的股票才会计入溢价统计
- 如果某行业所有昨日涨停股都没有匹配到今日行情，则不返回昨日溢价相关字段

### 兼容性

- 向后兼容：新增字段为可选字段，老版本客户端忽略新字段即可
- 如果某个交易日不包含新字段，表示该日期是查询区间的第一个交易日（无前一日数据）

## 测试

已创建测试脚本 `test_industry_trend_premium.py`，验证：
1. 默认映射方式的昨日溢价功能
2. 东财板块映射方式的行业涨跌幅功能
3. source_counts 字段的正确性

运行测试：
```bash
python3 test_industry_trend_premium.py
```

## 后续优化建议

1. **缓存优化**: 考虑缓存 `dc_daily` 板块行情数据，减少重复请求
2. **异步加载**: 对于大区间查询，可以考虑将溢价计算异步化
3. **更多统计指标**: 可以添加溢价的中位数、最大值、最小值等统计信息
4. **涨停后续表现**: 可以扩展到计算昨日涨停股的今日收盘涨跌幅，评估涨停效应
