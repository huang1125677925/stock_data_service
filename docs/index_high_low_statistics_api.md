# 指数涨跌统计API文档

## 概述

指数涨跌统计功能基于akshare的`stock_a_high_low_statistics`接口，提供不同指数（全部A股、上证50、沪深300、中证500）的涨跌统计数据，包括创新高、新低的股票数量以及涨跌比计算。

## 数据模型

### IndexHighLowStatistics 模型字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| date | DateField | 统计日期 |
| index_code | CharField | 指数代码（all/sz50/hs300/zz500） |
| close | DecimalField | 收盘价 |
| high20 | IntegerField | 20日新高数量 |
| low20 | IntegerField | 20日新低数量 |
| high60 | IntegerField | 60日新高数量 |
| low60 | IntegerField | 60日新低数量 |
| high120 | IntegerField | 120日新高数量 |
| low120 | IntegerField | 120日新低数量 |
| rise_fall_ratio | DecimalField | 涨跌比（涨的数量/涨+跌数量） |

## API接口

### 1. 获取指数涨跌统计数据

**接口地址：** `GET /stock-market/index-high-low-statistics/`

**功能：** 获取指定指数或所有指数的涨跌统计数据

**请求参数：**
- `symbol` (可选): 指数代码，可选值：'all', 'sz50', 'hs300', 'zz500'
- `save_to_db` (可选): 是否保存到数据库，默认为false

**请求示例：**
```bash
# 获取全部A股数据并保存到数据库
GET /stock-market/index-high-low-statistics/?symbol=all&save_to_db=true

# 获取所有指数数据
GET /stock-market/index-high-low-statistics/
```

**响应示例：**
```json
{
    "code": 200,
    "message": "获取all涨跌统计数据成功",
    "timestamp": "2025-10-19T13:54:28.397102",
    "data": {
        "date": "2025-10-17",
        "index_code": "all",
        "close": "3839.76",
        "high20": 185,
        "low20": 2115,
        "high60": 102,
        "low60": 1037,
        "high120": 87,
        "low120": 211,
        "rise_fall_ratio": "0.0804",
        "created": true,
        "id": 1
    }
}
```

### 2. 更新指数涨跌统计数据

**接口地址：** `POST /stock-market/index-high-low-statistics/`

**功能：** 强制更新指定指数或所有指数的涨跌统计数据

**请求参数：**
- `symbol` (可选): 指数代码，不指定则更新所有指数

**请求示例：**
```bash
# 更新全部A股数据
POST /stock-market/index-high-low-statistics/
Content-Type: application/json

{
    "symbol": "all"
}

# 更新所有指数数据
POST /stock-market/index-high-low-statistics/
Content-Type: application/json

{}
```

### 3. 查询涨跌比历史数据

**接口地址：** `GET /stock-market/rise-fall-ratio/`

**功能：** 查询指数的涨跌比历史数据

**请求参数：**
- `index_code` (可选): 指数代码，不指定则查询所有
- `start_date` (可选): 开始日期，格式YYYY-MM-DD
- `end_date` (可选): 结束日期，格式YYYY-MM-DD
- `limit` (可选): 返回记录数限制，默认30条，最大1000条

**请求示例：**
```bash
# 查询全部A股最近10条涨跌比数据
GET /stock-market/rise-fall-ratio/?index_code=all&limit=10

# 查询指定日期范围的数据
GET /stock-market/rise-fall-ratio/?start_date=2025-10-01&end_date=2025-10-17
```

**响应示例：**
```json
{
    "code": 200,
    "message": "查询涨跌比数据成功",
    "timestamp": "2025-10-19T13:54:28.397102",
    "data": {
        "count": 4,
        "results": [
            {
                "id": 1,
                "date": "2025-10-17",
                "index_code": "all",
                "index_name": "全部A股",
                "close": 3839.76,
                "high20": 185,
                "low20": 2115,
                "high60": 102,
                "low60": 1037,
                "high120": 87,
                "low120": 211,
                "rise_fall_ratio": 0.0804,
                "created_at": "2025-10-19 13:54:28",
                "updated_at": "2025-10-19 13:54:28"
            }
        ]
    }
}
```

## 指数代码说明

| 代码 | 名称 | 说明 |
|------|------|------|
| all | 全部A股 | 包含所有A股市场股票 |
| sz50 | 上证50 | 上证50指数成分股 |
| hs300 | 沪深300 | 沪深300指数成分股 |
| zz500 | 中证500 | 中证500指数成分股 |

## 涨跌比计算说明

当前涨跌比计算采用简化方式：
- 涨跌比 = high20 / (high20 + low20)
- 其中 high20 表示创20日新高的股票数量，low20 表示创20日新低的股票数量
- 实际应用中建议使用真实的涨跌家数数据进行计算

## 错误码说明

| 错误码 | 说明 |
|--------|------|
| 400 | 参数格式错误 |
| 404 | 资源未找到 |
| 500 | 服务器内部错误 |

## 使用示例

### Python 示例

```python
import requests

# 获取全部A股涨跌统计数据
response = requests.get('http://localhost:8000/stock-market/index-high-low-statistics/?symbol=all&save_to_db=true')
data = response.json()
print(f"涨跌比: {data['data']['rise_fall_ratio']}")

# 查询历史涨跌比数据
response = requests.get('http://localhost:8000/stock-market/rise-fall-ratio/?index_code=all&limit=5')
data = response.json()
for record in data['data']['results']:
    print(f"{record['date']}: {record['rise_fall_ratio']}")
```

### JavaScript 示例

```javascript
// 获取所有指数数据
fetch('/stock-market/index-high-low-statistics/')
  .then(response => response.json())
  .then(data => {
    console.log('所有指数数据:', data.data);
  });

// 查询涨跌比数据
fetch('/stock-market/rise-fall-ratio/?limit=10')
  .then(response => response.json())
  .then(data => {
    data.data.results.forEach(record => {
      console.log(`${record.date}: ${record.index_name} - ${record.rise_fall_ratio}`);
    });
  });
```

## 注意事项

1. 数据来源于akshare的`stock_a_high_low_statistics`接口，数据更新频率取决于数据源
2. 涨跌比计算为简化版本，实际应用中建议使用更准确的涨跌家数数据
3. 建议在交易时间结束后获取当日数据，以确保数据完整性
4. 数据库中使用`unique_together`约束确保同一天同一指数只有一条记录
5. 所有接口都遵循统一的响应格式，使用`success_response`和`error_response`