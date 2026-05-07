# 股票标记接口API文档

## 概述

本文档描述了股票标记相关的API接口，包括股票标记的增删改查、标记因子选择项获取以及根据股票代码获取标记等功能。这些接口支持多种标记因子的单选和多选查询，为股票分析和筛选提供强大的标记功能。

## 基础信息

- **基础URL**: `http://localhost:8000/django/api/individual_stock/`
- **认证方式**: 部分接口需要用户认证
- **数据格式**: JSON
- **字符编码**: UTF-8

## 通用响应格式

### 成功响应
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2025-01-01T12:00:00.000000",
    "data": {
        // 具体数据内容
    }
}
```

### 错误响应
```json
{
    "code": 400,
    "message": "错误描述",
    "timestamp": "2025-01-01T12:00:00.000000",
    "data": null
}
```

## 接口列表

### 1. 股票标记管理

#### 1.1 获取股票标记列表

**接口地址**: `GET /stock-tags/`

**功能描述**: 获取股票标记列表，支持多种查询条件和分页

**请求参数**:
- `stock_codes` (可选): 股票代码列表，支持多选，如: `["000001", "000002"]`
- `pattern_types` (可选): 形态类型列表，支持多选
- `technical_indicator_types` (可选): 技术指标类型列表，支持多选
- `stock_types` (可选): 股票类型列表，支持多选
- `market_cap_types` (可选): 市值大小类型列表，支持多选
- `pe_range_types` (可选): PE区间类型列表，支持多选
- `pb_range_types` (可选): PB区间类型列表，支持多选
- `industry_types` (可选): 行业类型列表，支持多选
- `volume_types` (可选): 成交量类型列表，支持多选
- `volatility_types` (可选): 波动率类型列表，支持多选
- `trend_types` (可选): 趋势类型列表，支持多选
- `start_date` (可选): 开始日期，格式: YYYY-MM-DD（基于创建时间筛选）
- `end_date` (可选): 结束日期，格式: YYYY-MM-DD（基于创建时间筛选）
- `page` (可选): 页码，默认为1
- `page_size` (可选): 每页数量，默认为20，最大100

**响应示例**:
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2025-01-01T12:00:00.000000",
    "data": {
        "total": 100,
        "page": 1,
        "page_size": 20,
        "total_pages": 5,
        "has_next": true,
        "has_previous": false,
        "results": [
            {
                "id": 1,
                "created_at": "2025-01-01T10:00:00.000000Z",
                "updated_at": "2025-01-01T10:00:00.000000Z",
                "stock_code": "000001",
                "stock_name": "平安银行",
                "pattern_type": "BREAKOUT",
                "pattern_type_display": "突破形态",
                "technical_indicator_type": "MACD_GOLDEN_CROSS",
                "technical_indicator_type_display": "MACD金叉",
                "stock_type": "BLUE_CHIP",
                "stock_type_display": "蓝筹股",
                "market_cap_type": "LARGE_CAP",
                "market_cap_type_display": "大盘股(300-1000亿)",
                "pe_range_type": "MODERATE",
                "pe_range_type_display": "适中PE(15-25)",
                "pb_range_type": "LOW",
                "pb_range_type_display": "低PB(1-2)",
                "industry_type": "FINANCE",
                "industry_type_display": "金融行业",
                "volume_type": "VOLUME_SURGE",
                "volume_type_display": "放量",
                "volatility_type": "MODERATE_VOLATILITY",
                "volatility_type_display": "中等波动",
                "trend_type": "STRONG_UPTREND",
                "trend_type_display": "强势上涨",
                "stock": 1
            }
        ]
    }
}
```

#### 1.2 获取单个股票标记

**接口地址**: `GET /stock-tags/{tag_id}/`

**功能描述**: 根据标记ID获取单个股票标记详情

**路径参数**:
- `tag_id`: 标记ID

**响应示例**:
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2025-01-01T12:00:00.000000",
    "data": {
        "id": 1,
        "created_at": "2025-01-01T10:00:00.000000Z",
        "updated_at": "2025-01-01T10:00:00.000000Z",
        "stock_code": "000001",
        "stock_name": "平安银行",
        "pattern_type": "BREAKOUT",
        "pattern_type_display": "突破形态"
    }
}
```

#### 1.3 创建股票标记

**接口地址**: `POST /stock-tags/`

**功能描述**: 创建新的股票标记

**请求体示例**:
```json
{
    "stock_code": "000001",
    "pattern_type": "BREAKOUT",
    "technical_indicator_type": "MACD_GOLDEN_CROSS",
    "stock_type": "BLUE_CHIP",
    "market_cap_type": "LARGE_CAP",
    "pe_range_type": "MODERATE",
    "pb_range_type": "LOW",
    "industry_type": "FINANCE",
    "volume_type": "VOLUME_SURGE",
    "volatility_type": "MODERATE_VOLATILITY",
    "trend_type": "STRONG_UPTREND"
}
```

**注意**: 至少需要设置一个标记因子

#### 1.4 更新股票标记

**接口地址**: `PUT /stock-tags/{tag_id}/`

**功能描述**: 更新指定的股票标记

**路径参数**:
- `tag_id`: 标记ID

**请求体**: 与创建接口相同，支持部分更新

#### 1.5 删除股票标记

**接口地址**: `DELETE /stock-tags/{tag_id}/`

**功能描述**: 删除指定的股票标记

**路径参数**:
- `tag_id`: 标记ID

### 2. 标记因子选择项

#### 2.1 获取所有标记因子选择项

**接口地址**: `GET /stock-tags/choices/`

**功能描述**: 获取所有标记因子的可选值，用于前端下拉框等组件

**响应示例**:
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2025-01-01T12:00:00.000000",
    "data": {
        "pattern_types": [
            ["BREAKOUT", "突破形态"],
            ["REVERSAL", "反转形态"],
            ["CONSOLIDATION", "整理形态"]
        ],
        "technical_indicator_types": [
            ["MACD_GOLDEN_CROSS", "MACD金叉"],
            ["MACD_DEAD_CROSS", "MACD死叉"]
        ],
        "stock_types": [
            ["BLUE_CHIP", "蓝筹股"],
            ["GROWTH", "成长股"]
        ]
    }
}
```

### 3. 根据股票代码获取标记

#### 3.1 获取指定股票的所有标记

**接口地址**: `GET /stocks/{stock_code}/tags/`

**功能描述**: 获取指定股票代码的所有标记记录

**路径参数**:
- `stock_code`: 股票代码，如 "000001"

**查询参数**:
- `start_date` (可选): 开始日期，格式: YYYY-MM-DD（基于创建时间筛选）
- `end_date` (可选): 结束日期，格式: YYYY-MM-DD（基于创建时间筛选）

**认证要求**: 需要用户认证

**响应示例**:
```json
{
    "code": 200,
    "message": "success",
    "timestamp": "2025-01-01T12:00:00.000000",
    "data": [
        {
            "id": 1,
            "created_at": "2025-01-01T10:00:00.000000Z",
            "updated_at": "2025-01-01T10:00:00.000000Z",
            "stock_code": "000001",
            "stock_name": "平安银行",
            "pattern_type": "BREAKOUT",
            "pattern_type_display": "突破形态"
        }
    ]
}
```

## 错误处理

### 常见错误码

- `400`: 请求参数错误
- `401`: 未认证（需要登录）
- `404`: 资源不存在
- `500`: 服务器内部错误

### 错误示例

```json
{
    "code": 400,
    "message": "查询参数错误: {'stock_codes': ['该字段是必需的。']}",
    "timestamp": "2025-01-01T12:00:00.000000",
    "data": null
}
```

## 数据模型说明

### StockTag 模型

股票标记模型包含以下主要字段：

- `id`: 主键ID
- `stock`: 关联的股票对象
- `created_at`: 创建时间
- `updated_at`: 更新时间
- `pattern_type`: 形态类型
- `technical_indicator_type`: 技术指标类型
- `stock_type`: 股票类型
- `market_cap_type`: 市值大小类型
- `pe_range_type`: PE区间类型
- `pb_range_type`: PB区间类型
- `industry_type`: 行业类型
- `volume_type`: 成交量类型
- `volatility_type`: 波动率类型
- `trend_type`: 趋势类型

### 标记因子类型说明

#### 形态类型 (pattern_type)
- `BREAKOUT`: 突破形态
- `REVERSAL`: 反转形态
- `CONSOLIDATION`: 整理形态
- `HEAD_SHOULDERS`: 头肩形态
- `DOUBLE_TOP`: 双顶形态
- `DOUBLE_BOTTOM`: 双底形态
- `TRIANGLE`: 三角形态
- `FLAG`: 旗形形态
- `WEDGE`: 楔形形态
- `CHANNEL`: 通道形态
- `BOX_BREAKOUT`: 箱型突破
- `OTHER`: 其他形态

#### 技术指标类型 (technical_indicator_type)
- `MACD_GOLDEN_CROSS`: MACD金叉
- `MACD_DEAD_CROSS`: MACD死叉
- `KDJ_GOLDEN_CROSS`: KDJ金叉
- `KDJ_DEAD_CROSS`: KDJ死叉
- `RSI_OVERSOLD`: RSI超卖
- `RSI_OVERBOUGHT`: RSI超买
- `BOLL_UPPER`: 布林上轨
- `BOLL_LOWER`: 布林下轨
- `MA_GOLDEN_CROSS`: 均线金叉
- `MA_DEAD_CROSS`: 均线死叉
- `VOLUME_PRICE_DIVERGENCE`: 量价背离
- `OTHER`: 其他指标

#### 股票类型 (stock_type)
- `BLUE_CHIP`: 蓝筹股
- `GROWTH`: 成长股
- `VALUE`: 价值股
- `CYCLICAL`: 周期股
- `DEFENSIVE`: 防御股
- `SPECULATIVE`: 投机股
- `PENNY`: 仙股
- `SMALL_CAP`: 小盘股
- `MID_CAP`: 中盘股
- `LARGE_CAP`: 大盘股
- `CONCEPT`: 概念股
- `THEME`: 题材股
- `ST`: ST股票
- `NEW_STOCK`: 次新股
- `DIVIDEND`: 高股息
- `OTHER`: 其他类型

#### 市值大小类型 (market_cap_type)
- `MEGA_CAP`: 超大盘股(>1000亿)
- `LARGE_CAP`: 大盘股(300-1000亿)
- `MID_CAP`: 中盘股(100-300亿)
- `SMALL_CAP`: 小盘股(50-100亿)
- `MICRO_CAP`: 微盘股(<50亿)

#### PE区间类型 (pe_range_type)
- `NEGATIVE`: 负PE
- `LOW`: 低PE(0-15)
- `MODERATE`: 适中PE(15-25)
- `HIGH`: 高PE(25-50)
- `VERY_HIGH`: 极高PE(>50)

#### PB区间类型 (pb_range_type)
- `VERY_LOW`: 极低PB(<1)
- `LOW`: 低PB(1-2)
- `MODERATE`: 适中PB(2-3)
- `HIGH`: 高PB(3-5)
- `VERY_HIGH`: 极高PB(>5)

#### 行业类型 (industry_type)
- `TECHNOLOGY`: 科技行业
- `FINANCE`: 金融行业
- `HEALTHCARE`: 医疗健康
- `CONSUMER`: 消费行业
- `INDUSTRIAL`: 工业制造
- `ENERGY`: 能源行业
- `MATERIALS`: 原材料
- `UTILITIES`: 公用事业
- `REAL_ESTATE`: 房地产
- `TELECOM`: 电信服务
- `OTHER`: 其他行业

#### 成交量类型 (volume_type)
- `VOLUME_SURGE`: 放量
- `VOLUME_NORMAL`: 正常量
- `VOLUME_SHRINK`: 缩量
- `VOLUME_EXTREME`: 极量

#### 波动率类型 (volatility_type)
- `LOW_VOLATILITY`: 低波动
- `MODERATE_VOLATILITY`: 中等波动
- `HIGH_VOLATILITY`: 高波动
- `EXTREME_VOLATILITY`: 极端波动

#### 趋势类型 (trend_type)
- `STRONG_UPTREND`: 强势上涨
- `WEAK_UPTREND`: 弱势上涨
- `SIDEWAYS`: 横盘整理
- `WEAK_DOWNTREND`: 弱势下跌
- `STRONG_DOWNTREND`: 强势下跌

## 使用建议

1. **查询优化**: 使用具体的查询条件可以提高查询效率
2. **分页处理**: 对于大量数据，建议使用分页参数
3. **错误处理**: 客户端应该妥善处理各种错误响应
4. **认证管理**: 部分接口需要用户认证，请确保正确处理认证状态
5. **日期筛选**: 日期范围筛选基于标记的创建时间，而非原有的标记日期

## 更新说明

- **2025-01-01**: 移除了 `tag_date` 字段，日期筛选改为基于 `created_at` 字段
- **2025-01-01**: 修复了相关代码中的字段引用问题
- **2025-01-01**: 更新了序列化器以适配新的模型结构