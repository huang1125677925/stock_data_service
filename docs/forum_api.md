# 论坛应用API文档

## 概述

论坛应用提供了一套完整的API，用于管理帖子和评论。所有API路径均以`/django/api/forum/`开头。

## 认证

部分API需要用户登录才能访问，这些API会在文档中标注为"需要认证"。

## API列表

### 1. 获取帖子列表

- **URL**: `/django/api/forum/posts/`
- **方法**: GET
- **认证**: 不需要
- **描述**: 获取所有帖子的列表，支持分页

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 |
| ------ | ---- | ---- | ---- |
| page | int | 否 | 页码，默认为1 |
| per_page | int | 否 | 每页显示的帖子数量，默认为10 |

#### 响应示例

```json
{
  "posts": [
    {
      "id": 1,
      "title": "帖子标题",
      "author": "用户名",
      "created_at": "2023-01-01T12:00:00Z",
      "comment_count": 5
    },
    // 更多帖子...
  ],
  "page": {
    "current": 1,
    "total_pages": 5,
    "total_items": 50,
    "has_next": true,
    "has_previous": false
  }
}
```

### 2. 获取帖子详情

- **URL**: `/django/api/forum/posts/{post_id}/`
- **方法**: GET
- **认证**: 不需要
- **描述**: 获取指定ID的帖子详情及其评论

#### 路径参数

| 参数名 | 类型 | 描述 |
| ------ | ---- | ---- |
| post_id | int | 帖子ID |

#### 响应示例

```json
{
  "post": {
    "id": 1,
    "title": "帖子标题",
    "content": "帖子内容...",
    "author": "用户名",
    "created_at": "2023-01-01T12:00:00Z",
    "updated_at": "2023-01-02T12:00:00Z"
  },
  "comments": [
    {
      "id": 1,
      "content": "评论内容...",
      "author": "评论者用户名",
      "created_at": "2023-01-01T13:00:00Z"
    },
    // 更多评论...
  ]
}
```

### 3. 创建帖子

- **URL**: `/django/api/forum/posts/create/`
- **方法**: POST
- **认证**: 需要
- **描述**: 创建新帖子

#### 请求体

| 字段名 | 类型 | 必填 | 描述 |
| ------ | ---- | ---- | ---- |
| title | string | 是 | 帖子标题 |
| content | string | 是 | 帖子内容 |

#### 请求示例

```json
{
  "title": "新帖子标题",
  "content": "新帖子内容..."
}
```

#### 响应示例

```json
{
  "message": "帖子创建成功",
  "post": {
    "id": 2,
    "title": "新帖子标题",
    "content": "新帖子内容...",
    "author": "当前登录用户名",
    "created_at": "2023-01-03T12:00:00Z"
  }
}
```

### 4. 删除帖子

- **URL**: `/django/api/forum/posts/{post_id}/delete/`
- **方法**: DELETE 或 POST
- **认证**: 需要
- **描述**: 删除指定ID的帖子（仅帖子作者可操作）

#### 路径参数

| 参数名 | 类型 | 描述 |
| ------ | ---- | ---- |
| post_id | int | 帖子ID |

#### 响应示例

```json
{
  "message": "帖子删除成功"
}
```

#### 错误响应

```json
{
  "error": "您没有权限删除此帖子"
}
```

### 5. 添加评论

- **URL**: `/django/api/forum/posts/{post_id}/comment/`
- **方法**: POST
- **认证**: 需要
- **描述**: 为指定ID的帖子添加评论

#### 路径参数

| 参数名 | 类型 | 描述 |
| ------ | ---- | ---- |
| post_id | int | 帖子ID |

#### 请求体

| 字段名 | 类型 | 必填 | 描述 |
| ------ | ---- | ---- | ---- |
| content | string | 是 | 评论内容 |

#### 请求示例

```json
{
  "content": "这是一条评论..."
}
```

#### 响应示例

```json
{
  "message": "评论添加成功",
  "comment": {
    "id": 3,
    "content": "这是一条评论...",
    "author": "当前登录用户名",
    "created_at": "2023-01-03T13:00:00Z"
  }
}
```

## 错误码说明

| 状态码 | 描述 |
| ------ | ---- |
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 数据模型

### 帖子(Post)

| 字段 | 类型 | 描述 |
| ---- | ---- | ---- |
| id | int | 帖子ID |
| title | string | 帖子标题 |
| content | string | 帖子内容 |
| author | User | 帖子作者 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### 评论(Comment)

| 字段 | 类型 | 描述 |
| ---- | ---- | ---- |
| id | int | 评论ID |
| post | Post | 所属帖子 |
| content | string | 评论内容 |
| author | User | 评论作者 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |