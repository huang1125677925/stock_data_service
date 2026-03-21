# 会话服务 API 接口文档

## 1. 接口概览

- 基础路径：`/django/api/chat/`
- 认证方式：`Authorization: Bearer <token>`
- 响应格式：统一使用 `code/message/data/timestamp`

| 接口名称 | URL | 方法 | 说明 |
| --- | --- | --- | --- |
| 创建会话 | `/django/api/chat/conversations/` | POST | 创建会话 |
| 会话列表 | `/django/api/chat/conversations/?page=1&page_size=20` | GET | 分页获取当前用户会话 |
| 消息分页 | `/django/api/chat/conversations/{id}/messages/?cursor=0&page_size=50` | GET | 游标分页获取消息 |
| 写入用户消息 | `/django/api/chat/conversations/{id}/messages/` | POST | 新增一条 user 消息 |
| 流式 AI 回复 | `/django/api/chat/conversations/{id}/stream/` | POST | SSE 流式返回并落库 assistant 消息 |
| 更新会话 | `/django/api/chat/conversations/{id}/` | PATCH | 更新标题或置顶 |
| 删除会话 | `/django/api/chat/conversations/{id}/` | DELETE | 软删除会话 |

## 2. 数据模型

### 2.1 conversation

- 表名：`chat_conversation`
- `id`
- `user_id`
- `title`
- `model`
- `is_pinned`
- `created_at`
- `updated_at`
- `deleted_at`

索引：
- `(user_id, updated_at desc)`
- `(user_id, deleted_at)`

### 2.2 message

- 表名：`chat_message`
- `id`
- `conversation_id`
- `role`：`user/assistant/tool/system`
- `content`
- `tool_data`(json)
- `seq`
- `created_at`

索引：
- `(conversation_id, seq asc)`
- 唯一约束：`(conversation_id, seq)`

## 3. 关键请求示例

### 3.1 创建会话

`POST /django/api/chat/conversations/`

```json
{
  "title": "新能源行业分析",
  "model": "deepseek-chat"
}
```

### 3.2 写入用户消息

`POST /django/api/chat/conversations/12/messages/`

```json
{
  "content": "请分析今天的行业轮动",
  "tool_data": null
}
```

### 3.3 流式对话

`POST /django/api/chat/conversations/12/stream/`

```json
{
  "content": "结合最近三天数据给出结论"
}
```

说明：
- 若传 `content`，服务端会先写入一条 user 消息再发起流式生成。
- 流式过程中输出 SSE 数据，结束后自动落库 assistant 消息。

## 4. 隔离与安全

- 所有会话与消息查询均以 `request.user` 为条件过滤。
- 访问不存在或不属于当前用户的会话返回 `code=404`。
- 会话删除采用软删除（`deleted_at` 赋值），默认列表与读取会过滤已删除数据。
