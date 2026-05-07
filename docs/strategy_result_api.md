# 策略结果管理接口文档

## 概述

策略结果管理接口提供了对策略选股结果的完整CRUD操作，包括创建、查询、更新和删除策略结果。该接口基于Django REST Framework实现，遵循RESTful API设计规范。

## 基础信息

- **基础URL**: `/api/individual-stock/strategy-results/`
- **认证方式**: 暂无（根据项目需要可添加认证中间件）
- **响应格式**: JSON
- **字符编码**: UTF-8

## 统一响应格式

所有接口均使用统一的响应格式：

### 成功响应格式
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-15T10:30:00.123456",
    "data": {
        // 具体数据内容
    }
}
```

### 错误响应格式
```json
{
    "code": 400,
    "message": "错误描述信息",
    "timestamp": "2024-01-15T10:30:00.123456",
    "data": null
}
```

## 数据模型

### StrategyResult 模型字段说明

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | Integer | 自动生成 | 策略结果唯一标识符 |
| strategy_name | String(100) | 是 | 策略名称 |
| strategy_description | Text | 是 | 策略描述 |
| strategy_result | JSON | 是 | 策略选股结果，JSON格式存储 |
| created_at | DateTime | 自动生成 | 创建时间 |
| updated_at | DateTime | 自动更新 | 更新时间 |

### 策略结果数据示例
```json
{
    "id": 1,
    "strategy_name": "MA均线策略",
    "strategy_description": "基于5日和20日移动平均线的选股策略",
    "strategy_result": {
        "selected_stocks": [
            {
                "code": "000001",
                "name": "平安银行",
                "score": 85.6,
                "reason": "5日均线上穿20日均线"
            },
            {
                "code": "000002", 
                "name": "万科A",
                "score": 78.3,
                "reason": "成交量放大，均线多头排列"
            }
        ],
        "total_count": 2,
        "execution_time": "2024-01-15T09:30:00",
        "parameters": {
            "short_period": 5,
            "long_period": 20,
            "min_score": 70
        }
    },
    "created_at": "2024-01-15T09:30:00.123456Z",
    "updated_at": "2024-01-15T09:30:00.123456Z"
}
```

## 接口详情

### 1. 获取策略结果列表

获取所有策略结果的分页列表，支持按策略名称筛选。

#### 请求信息
- **URL**: `GET /api/individual-stock/strategy-results/`
- **方法**: GET
- **Content-Type**: application/json

#### 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| page | Integer | 否 | 1 | 页码，从1开始 |
| page_size | Integer | 否 | 20 | 每页数量，最大100 |
| strategy_name | String | 否 | - | 策略名称关键词筛选（模糊匹配） |

#### 请求示例
```bash
# 获取第一页数据
GET /api/individual-stock/strategy-results/?page=1&page_size=10

# 按策略名称筛选
GET /api/individual-stock/strategy-results/?strategy_name=MA&page=1&page_size=5
```

#### 响应示例

**成功响应 (200)**
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-15T10:30:00.123456",
    "data": {
        "total": 25,
        "page": 1,
        "page_size": 10,
        "total_pages": 3,
        "results": [
            {
                "id": 1,
                "strategy_name": "MA均线策略",
                "strategy_description": "基于5日和20日移动平均线的选股策略",
                "strategy_result": {
                    "selected_stocks": [...],
                    "total_count": 15,
                    "execution_time": "2024-01-15T09:30:00"
                },
                "created_at": "2024-01-15T09:30:00.123456Z",
                "updated_at": "2024-01-15T09:30:00.123456Z"
            }
        ]
    }
}
```

**错误响应**
```json
{
    "code": 400,
    "message": "参数格式错误: page必须是正整数",
    "timestamp": "2024-01-15T10:30:00.123456",
    "data": null
}
```

### 2. 获取单个策略结果

根据策略结果ID获取详细信息。

#### 请求信息
- **URL**: `GET /api/individual-stock/strategy-results/{result_id}/`
- **方法**: GET
- **Content-Type**: application/json

#### 路径参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| result_id | Integer | 是 | 策略结果ID |

#### 请求示例
```bash
GET /api/individual-stock/strategy-results/1/
```

#### 响应示例

**成功响应 (200)**
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2024-01-15T10:30:00.123456",
    "data": {
        "id": 1,
        "strategy_name": "MA均线策略",
        "strategy_description": "基于5日和20日移动平均线的选股策略",
        "strategy_result": {
            "selected_stocks": [
                {
                    "code": "000001",
                    "name": "平安银行",
                    "score": 85.6,
                    "reason": "5日均线上穿20日均线"
                }
            ],
            "total_count": 1,
            "execution_time": "2024-01-15T09:30:00",
            "parameters": {
                "short_period": 5,
                "long_period": 20
            }
        },
        "created_at": "2024-01-15T09:30:00.123456Z",
        "updated_at": "2024-01-15T09:30:00.123456Z"
    }
}
```

**错误响应 (404)**
```json
{
    "code": 404,
    "message": "策略结果不存在",
    "timestamp": "2024-01-15T10:30:00.123456",
    "data": null
}
```

### 3. 创建策略结果

创建新的策略选股结果。

#### 请求信息
- **URL**: `POST /api/individual-stock/strategy-results/`
- **方法**: POST
- **Content-Type**: application/json

#### 请求体参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| strategy_name | String | 是 | 策略名称，最大100字符 |
| strategy_description | String | 是 | 策略描述 |
| strategy_result | Object | 是 | 策略结果JSON对象 |

#### 请求示例
```bash
POST /api/individual-stock/strategy-results/
Content-Type: application/json

{
    "strategy_name": "RSI超卖策略",
    "strategy_description": "基于RSI指标识别超卖股票的选股策略",
    "strategy_result": {
        "selected_stocks": [
            {
                "code": "000001",
                "name": "平安银行",
                "rsi_value": 25.6,
                "score": 88.5,
                "reason": "RSI低于30，处于超卖状态"
            }
        ],
        "total_count": 1,
        "execution_time": "2024-01-15T14:30:00",
        "parameters": {
            "rsi_period": 14,
            "oversold_threshold": 30
        }
    }
}
```

#### 响应示例

**成功响应 (200)**
```json
{
    "code": 200,
    "message": "策略结果创建成功",
    "timestamp": "2024-01-15T10:30:00.123456",
    "data": {
        "id": 2,
        "strategy_name": "RSI超卖策略",
        "strategy_description": "基于RSI指标识别超卖股票的选股策略",
        "strategy_result": {
            "selected_stocks": [...],
            "total_count": 1,
            "execution_time": "2024-01-15T14:30:00"
        },
        "created_at": "2024-01-15T10:30:00.123456Z",
        "updated_at": "2024-01-15T10:30:00.123456Z"
    }
}
```

**错误响应 (400)**
```json
{
    "code": 400,
    "message": "数据验证失败: {'strategy_name': ['该字段是必填项。']}",
    "timestamp": "2024-01-15T10:30:00.123456",
    "data": null
}
```

### 4. 完整更新策略结果

使用PUT方法完整更新策略结果的所有字段。

#### 请求信息
- **URL**: `PUT /api/individual-stock/strategy-results/{result_id}/`
- **方法**: PUT
- **Content-Type**: application/json

#### 路径参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| result_id | Integer | 是 | 策略结果ID |

#### 请求体参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| strategy_name | String | 是 | 策略名称 |
| strategy_description | String | 是 | 策略描述 |
| strategy_result | Object | 是 | 策略结果JSON对象 |

#### 请求示例
```bash
PUT /api/individual-stock/strategy-results/1/
Content-Type: application/json

{
    "strategy_name": "MA均线策略v2.0",
    "strategy_description": "优化后的移动平均线选股策略，增加成交量确认",
    "strategy_result": {
        "selected_stocks": [
            {
                "code": "000001",
                "name": "平安银行",
                "score": 90.2,
                "reason": "均线多头排列且成交量放大"
            }
        ],
        "total_count": 1,
        "execution_time": "2024-01-15T15:30:00",
        "parameters": {
            "short_period": 5,
            "long_period": 20,
            "volume_factor": 1.5
        }
    }
}
```

#### 响应示例

**成功响应 (200)**
```json
{
    "code": 200,
    "message": "策略结果更新成功",
    "timestamp": "2024-01-15T10:30:00.123456",
    "data": {
        "id": 1,
        "strategy_name": "MA均线策略v2.0",
        "strategy_description": "优化后的移动平均线选股策略，增加成交量确认",
        "strategy_result": {
            "selected_stocks": [...],
            "total_count": 1,
            "execution_time": "2024-01-15T15:30:00"
        },
        "created_at": "2024-01-15T09:30:00.123456Z",
        "updated_at": "2024-01-15T15:35:00.789012Z"
    }
}
```

### 5. 部分更新策略结果

使用PATCH方法部分更新策略结果的指定字段。

#### 请求信息
- **URL**: `PATCH /api/individual-stock/strategy-results/{result_id}/`
- **方法**: PATCH
- **Content-Type**: application/json

#### 路径参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| result_id | Integer | 是 | 策略结果ID |

#### 请求体参数

支持部分更新，只需提供要更新的字段：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| strategy_name | String | 否 | 策略名称 |
| strategy_description | String | 否 | 策略描述 |
| strategy_result | Object | 否 | 策略结果JSON对象 |

#### 请求示例
```bash
PATCH /api/individual-stock/strategy-results/1/
Content-Type: application/json

{
    "strategy_description": "更新后的策略描述：增加了风险控制模块"
}
```

#### 响应示例

**成功响应 (200)**
```json
{
    "code": 200,
    "message": "策略结果更新成功",
    "timestamp": "2024-01-15T10:30:00.123456",
    "data": {
        "id": 1,
        "strategy_name": "MA均线策略",
        "strategy_description": "更新后的策略描述：增加了风险控制模块",
        "strategy_result": {
            // 原有数据保持不变
        },
        "created_at": "2024-01-15T09:30:00.123456Z",
        "updated_at": "2024-01-15T16:00:00.123456Z"
    }
}
```

### 6. 删除策略结果

删除指定的策略结果。

#### 请求信息
- **URL**: `DELETE /api/individual-stock/strategy-results/{result_id}/`
- **方法**: DELETE

#### 路径参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| result_id | Integer | 是 | 策略结果ID |

#### 请求示例
```bash
DELETE /api/individual-stock/strategy-results/1/
```

#### 响应示例

**成功响应 (200)**
```json
{
    "code": 200,
    "message": "策略结果删除成功",
    "timestamp": "2024-01-15T10:30:00.123456",
    "data": {
        "deleted_id": 1,
        "strategy_name": "MA均线策略"
    }
}
```

**错误响应 (404)**
```json
{
    "code": 404,
    "message": "策略结果不存在",
    "timestamp": "2024-01-15T10:30:00.123456",
    "data": null
}
```

## 错误码说明

| 错误码 | 说明 | 常见原因 |
|--------|------|----------|
| 200 | 请求成功 | - |
| 400 | 请求参数错误 | 参数格式不正确、必填参数缺失、数据验证失败 |
| 404 | 资源不存在 | 策略结果ID不存在 |
| 500 | 服务器内部错误 | 数据库连接失败、系统异常 |

## 数据验证规则

### 策略名称 (strategy_name)
- 必填字段
- 最大长度：100字符
- 不能为空字符串

### 策略描述 (strategy_description)
- 必填字段
- 文本类型，无长度限制
- 不能为空字符串

### 策略结果 (strategy_result)
- 必填字段
- 必须是有效的JSON格式
- 支持嵌套对象和数组
- 序列化时自动转换为JSON字符串存储
- 反序列化时自动解析为JSON对象

## 使用示例

### Python requests示例

```python
import requests
import json

base_url = "http://localhost:8000/api/individual-stock/strategy-results/"

# 1. 创建策略结果
create_data = {
    "strategy_name": "MACD策略",
    "strategy_description": "基于MACD指标的选股策略",
    "strategy_result": {
        "selected_stocks": [
            {
                "code": "000001",
                "name": "平安银行",
                "macd_signal": "金叉",
                "score": 85.6
            }
        ],
        "total_count": 1,
        "execution_time": "2024-01-15T14:30:00"
    }
}

response = requests.post(base_url, json=create_data)
result = response.json()
strategy_id = result['data']['id']

# 2. 获取策略结果列表
response = requests.get(f"{base_url}?page=1&page_size=10")
print(response.json())

# 3. 获取单个策略结果
response = requests.get(f"{base_url}{strategy_id}/")
print(response.json())

# 4. 更新策略结果
update_data = {
    "strategy_description": "优化后的MACD策略，增加成交量确认"
}
response = requests.patch(f"{base_url}{strategy_id}/", json=update_data)
print(response.json())

# 5. 删除策略结果
response = requests.delete(f"{base_url}{strategy_id}/")
print(response.json())
```

### JavaScript fetch示例

```javascript
const baseUrl = 'http://localhost:8000/api/individual-stock/strategy-results/';

// 创建策略结果
async function createStrategy() {
    const data = {
        strategy_name: 'KDJ策略',
        strategy_description: '基于KDJ指标的超买超卖策略',
        strategy_result: {
            selected_stocks: [
                {
                    code: '000002',
                    name: '万科A',
                    kdj_signal: '超卖',
                    score: 78.9
                }
            ],
            total_count: 1,
            execution_time: '2024-01-15T16:30:00'
        }
    };

    try {
        const response = await fetch(baseUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        console.log('创建成功:', result);
        return result.data.id;
    } catch (error) {
        console.error('创建失败:', error);
    }
}

// 获取策略结果列表
async function getStrategies(page = 1, pageSize = 10) {
    try {
        const response = await fetch(`${baseUrl}?page=${page}&page_size=${pageSize}`);
        const result = await response.json();
        console.log('获取列表成功:', result);
        return result.data;
    } catch (error) {
        console.error('获取列表失败:', error);
    }
}
```

## 注意事项

1. **JSON格式**: `strategy_result` 字段必须是有效的JSON格式，系统会自动进行验证和转换。

2. **分页限制**: 为了性能考虑，建议每页数量不超过100条记录。

3. **数据大小**: `strategy_result` 字段存储的JSON数据建议不超过1MB，以确保良好的性能。

4. **并发更新**: 系统使用 `updated_at` 字段记录最后更新时间，建议在更新前检查该字段以避免并发冲突。

5. **软删除**: 当前实现为硬删除，如需要软删除功能，可以考虑添加 `is_deleted` 字段。

6. **权限控制**: 当前接口未实现权限控制，生产环境建议添加适当的认证和授权机制。

## 更新日志

- **v1.0.0** (2024-01-15): 初始版本，实现基础CRUD功能
- 支持策略结果的创建、查询、更新、删除
- 支持分页和筛选功能
- 统一响应格式和错误处理