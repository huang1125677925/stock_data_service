# CCTV新闻API接口文档

## 基本信息

- 基础URL: `/api/cctv_news`
- 响应格式: JSON

## 通用响应格式

### 成功响应

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

### 错误响应

```json
{
  "code": 错误码,
  "message": "错误信息"
}
```

## 接口列表

### 1. 获取新闻列表

- **URL**: `/api/cctv_news/`
- **方法**: GET
- **描述**: 获取新闻列表，支持分页和关键词搜索

#### 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 描述 |
|-------|-----|------|-------|------|
| limit | int | 否 | 10 | 返回结果数量限制 |
| offset | int | 否 | 0 | 分页偏移量 |
| keyword | string | 否 | 无 | 搜索关键词 |

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 100,
    "items": [
      {
        "id": 1,
        "title": "新闻标题",
        "content": "新闻内容",
        "ai_content": "AI处理后的内容",
        "publish_date": "2024-01-01",
        "created_at": "2024-01-01 12:00:00",
        "updated_at": "2024-01-01 12:00:00"
      },
      // 更多新闻项...
    ],
    "limit": 10,
    "offset": 0
  }
}
```

### 2. 获取新闻详情

- **URL**: `/api/cctv_news/<int:news_id>`
- **方法**: GET
- **描述**: 获取指定ID的新闻详情

#### 路径参数

| 参数名 | 类型 | 描述 |
|-------|-----|------|
| news_id | int | 新闻ID |

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "title": "新闻标题",
    "content": "新闻内容",
    "ai_content": "AI处理后的内容",
    "publish_date": "2024-01-01",
    "created_at": "2024-01-01 12:00:00",
    "updated_at": "2024-01-01 12:00:00"
  }
}
```

### 3. 创建新闻

- **URL**: `/api/cctv_news/`
- **方法**: POST
- **描述**: 创建新的新闻记录

#### 请求体

```json
{
  "title": "新闻标题",
  "content": "新闻内容",
  "ai_content": "AI处理后的内容", // 可选
  "publish_date": "2024-01-01" // 可选，默认为当前日期
}
```

#### 请求参数说明

| 参数名 | 类型 | 必填 | 描述 |
|-------|-----|------|------|
| title | string | 是 | 新闻标题 |
| content | string | 是 | 新闻内容 |
| ai_content | string | 否 | AI处理后的内容 |
| publish_date | string | 否 | 发布日期，格式为YYYY-MM-DD |

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "message": "新闻创建成功",
    "news": {
      "id": 1,
      "title": "新闻标题",
      "content": "新闻内容",
      "ai_content": "AI处理后的内容",
      "publish_date": "2024-01-01",
      "created_at": "2024-01-01 12:00:00",
      "updated_at": "2024-01-01 12:00:00"
    }
  }
}
```

### 4. 更新新闻

- **URL**: `/api/cctv_news/<int:news_id>`
- **方法**: PUT
- **描述**: 更新指定ID的新闻记录

#### 路径参数

| 参数名 | 类型 | 描述 |
|-------|-----|------|
| news_id | int | 新闻ID |

#### 请求体

```json
{
  "title": "更新的标题", // 可选
  "content": "更新的内容", // 可选
  "ai_content": "更新的AI内容", // 可选
  "publish_date": "2024-01-01" // 可选
}
```

#### 请求参数说明

| 参数名 | 类型 | 必填 | 描述 |
|-------|-----|------|------|
| title | string | 否 | 更新的新闻标题 |
| content | string | 否 | 更新的新闻内容 |
| ai_content | string | 否 | 更新的AI处理后内容 |
| publish_date | string | 否 | 更新的发布日期，格式为YYYY-MM-DD |

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "message": "新闻更新成功",
    "news": {
      "id": 1,
      "title": "更新的标题",
      "content": "更新的内容",
      "ai_content": "更新的AI内容",
      "publish_date": "2024-01-01",
      "created_at": "2024-01-01 12:00:00",
      "updated_at": "2024-01-02 12:00:00"
    }
  }
}
```

### 5. 删除新闻

- **URL**: `/api/cctv_news/<int:news_id>`
- **方法**: DELETE
- **描述**: 删除指定ID的新闻记录

#### 路径参数

| 参数名 | 类型 | 描述 |
|-------|-----|------|
| news_id | int | 新闻ID |

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "message": "新闻删除成功",
    "id": 1
  }
}
```

### 6. 获取最新新闻

- **URL**: `/api/cctv_news/latest`
- **方法**: GET
- **描述**: 获取最新的新闻列表

#### 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 描述 |
|-------|-----|------|-------|------|
| limit | int | 否 | 5 | 返回结果数量限制 |

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 5,
    "items": [
      {
        "id": 1,
        "title": "新闻标题",
        "content": "新闻内容",
        "ai_content": "AI处理后的内容",
        "publish_date": "2024-01-01",
        "created_at": "2024-01-01 12:00:00",
        "updated_at": "2024-01-01 12:00:00"
      },
      // 更多新闻项...
    ]
  }
}
```

### 7. 搜索新闻

- **URL**: `/api/cctv_news/search`
- **方法**: GET
- **描述**: 根据关键词搜索新闻

#### 请求参数

| 参数名 | 类型 | 必填 | 默认值 | 描述 |
|-------|-----|------|-------|------|
| keyword | string | 是 | 无 | 搜索关键词 |
| limit | int | 否 | 20 | 返回结果数量限制 |

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 3,
    "keyword": "搜索关键词",
    "items": [
      {
        "id": 1,
        "title": "包含关键词的新闻标题",
        "content": "包含关键词的新闻内容",
        "ai_content": "AI处理后的内容",
        "publish_date": "2024-01-01",
        "created_at": "2024-01-01 12:00:00",
        "updated_at": "2024-01-01 12:00:00"
      },
      // 更多新闻项...
    ]
  }
}
```

## 错误码说明

| 错误码 | 描述 |
|-------|------|
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 注意事项

1. 所有日期格式均为`YYYY-MM-DD`
2. 创建和更新操作会返回完整的新闻对象
3. 搜索功能支持在标题和内容中查找关键词
4. 获取新闻列表默认按发布日期倒序排列