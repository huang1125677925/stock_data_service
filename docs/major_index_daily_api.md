# 国内 + 国际主要指数日线行情 API

## 接口信息
- URL: `/django/api/index/major-index-daily/`
- Method: `GET`
- 功能：聚合获取国内主要指数（Tushare `index_daily`）与国际主要指数（Tushare `index_global`）的日线行情。
- 响应封装：统一使用 `success_response` / `error_response`。

## 请求参数（Query）
- scope (string, optional): 返回范围，取值 `domestic` / `global` / `all`，默认 `all`
- trade_date (string, optional): 交易日期，格式 `YYYYMMDD`
- start_date (string, optional): 开始日期，格式 `YYYYMMDD`
- end_date (string, optional): 结束日期，格式 `YYYYMMDD`
- domestic_codes (string, optional): 国内指数代码列表（逗号分隔），默认服务端内置主要指数集合（如 `000001.SH,000300.SH`）
- global_codes (string, optional): 国际指数代码列表（逗号分隔），默认服务端内置主要指数集合（如 `SPX,IXIC,HSI`）
- token (string, optional): Tushare Token（覆盖环境变量）
- domestic_fields (string, optional): 传给 `index_daily` 的字段列表（逗号分隔）
- global_fields (string, optional): 传给 `index_global` 的字段列表（逗号分隔）

## 默认主要指数集合

### 国内（index_daily）
- `000001.SH` 上证综指
- `000300.SH` 沪深300
- `000905.SH` 中证500
- `000016.SH` 上证50
- `399001.SZ` 深证成指
- `399006.SZ` 创业板指
- `399107.SZ` 深证A指

### 国际（index_global）
- `SPX` 标普500指数
- `IXIC` 纳斯达克指数
- `DJI` 道琼斯工业指数
- `HSI` 恒生指数
- `HKTECH` 恒生科技指数
- `XIN9` 富时中国A50指数
- `N225` 日经225指数
- `FTSE` 富时100指数
- `GDAXI` 德国DAX指数
- `TWII` 台湾加权指数

## 请求示例

### 1) 同时获取国内+国际主要指数最近行情
```bash
GET /django/api/index/major-index-daily/
```

### 2) 只获取国内主要指数，按日期区间
```bash
GET /django/api/index/major-index-daily/?scope=domestic&start_date=20260601&end_date=20260628
```

### 3) 自定义指数列表
```bash
GET /django/api/index/major-index-daily/?scope=all&domestic_codes=000300.SH,399006.SZ&global_codes=SPX,IXIC
```

## 响应结构

### 成功响应（success_response）
```json
{
  "code": 200,
  "message": "查询主要指数日线行情成功",
  "timestamp": "2026-06-28T17:20:00.000000",
  "data": {
    "interface": "major_index_daily",
    "count": 2,
    "records": [
      {
        "source": "domestic",
        "name": "沪深300",
        "ts_code": "000300.SH",
        "trade_date": "20260628",
        "open": 3500.12,
        "close": 3510.34,
        "high": 3520.56,
        "low": 3490.78,
        "pre_close": 3498.12,
        "change": 12.22,
        "pct_chg": 0.3492,
        "vol": 123456.0,
        "amount": 987654.0
      },
      {
        "source": "global",
        "name": "标普500指数",
        "ts_code": "SPX",
        "trade_date": "20260628",
        "open": 5500.12,
        "close": 5510.34,
        "high": 5520.56,
        "low": 5490.78,
        "pre_close": 5498.12,
        "change": 12.22,
        "pct_chg": 0.2222,
        "swing": 1.2345,
        "vol": null,
        "amount": null
      }
    ],
    "meta": {
      "scope": "all",
      "domestic_codes": ["000001.SH", "000300.SH"],
      "global_codes": ["SPX", "IXIC"],
      "errors": []
    }
  }
}
```

### 失败响应（error_response）
```json
{
  "code": 400,
  "message": "start_date 必须为 YYYYMMDD 格式",
  "timestamp": "2026-06-28T17:20:00.000000",
  "data": null
}
```

## 说明与注意事项
- `index_daily` 的 `ts_code` 为国内指数 TS 代码（例如 `000300.SH`）；`index_global` 的 `ts_code` 为国际指数代码（例如 `SPX`）。
- 国际指数的 `vol/amount` 字段在部分指数上可能为空，属于 Tushare 数据特性。
- 如需扩展“主要指数集合”，可在服务端的默认列表中增加代码映射。
