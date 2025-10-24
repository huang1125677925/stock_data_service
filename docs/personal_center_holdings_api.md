# 个人中心持有/关注股票接口文档

本文档描述个人中心模块中与持有/关注股票管理相关的两个接口：列表/新增接口与删除接口。接口统一使用项目通用的 `success_response` 与 `error_response` 返回格式。

## 鉴权说明
- 需在请求头携带令牌：`Authorization: Bearer <token>`
- 令牌通过用户管理模块登录获取，后端中间件会解析令牌并注入 `request.user`
- 未认证或令牌无效时返回 401

## 接口一：获取列表 / 新增记录
- 路径：`GET /django/api/personal/holdings/`、`POST /django/api/personal/holdings/`
- 说明：同一路径，GET 用于查询当前用户的持有/关注记录列表；POST 用于新增一条记录。

### 1. GET 列表
- 请求
  - 方法：`GET`
  - URL：`/django/api/personal/holdings/`
  - Headers：`Authorization: Bearer <token>`
  - Query：无
- 响应（成功示例）
```json
{
  "code": 200,
  "message": "查询成功",
  "timestamp": "2025-10-24T22:10:00",
  "data": {
    "list": [
      {
        "id": 1,
        "stock_code": "600000",
        "stock_name": "浦发银行",
        "industry": "银行",
        "relation_type": "WATCHED",
        "created_at": "2025-10-24T21:59:20"
      }
    ],
    "total": 1
  }
}
```
- 错误示例
```json
{
  "code": 401,
  "message": "未认证",
  "timestamp": "2025-10-24T22:10:00",
  "data": null
}
```

### 2. POST 新增
- 请求
  - 方法：`POST`
  - URL：`/django/api/personal/holdings/`
  - Headers：
    - `Authorization: Bearer <token>`
    - `Content-Type: application/json`
  - Body（JSON）：
    - `stock_code`（string，必填）：股票代码，例如 `600000`、`sz000001`、`AAPL`
    - `relation_type`（string，可选，默认 `WATCHED`）：可选值 `WATCHED`（关注）或 `HELD`（持有）
- 校验与规则
  - `stock_code` 必填且格式需满足校验函数 `validate_stock_symbol`
  - `relation_type` 只能为 `WATCHED` 或 `HELD`
  - `stock_code` 必须在 `IndividualStock` 表中存在
  - `user + stock + relation_type` 唯一约束，重复新增会报错
- 响应（成功示例）
```json
{
  "code": 200,
  "message": "新增成功",
  "timestamp": "2025-10-24T22:12:00",
  "data": {
    "id": 2,
    "stock_code": "600000",
    "stock_name": "浦发银行",
    "industry": "银行",
    "relation_type": "HELD",
    "created_at": "2025-10-24T22:11:58"
  }
}
```
- 错误示例
```json
{
  "code": 400,
  "message": "该记录已存在",
  "timestamp": "2025-10-24T22:12:00",
  "data": null
}
```

## 接口二：删除记录
- 路径：`DELETE /django/api/personal/holdings/{id}/`
- 说明：删除当前用户的一条持有/关注记录。

### DELETE 删除
- 请求
  - 方法：`DELETE`
  - URL：`/django/api/personal/holdings/{id}/`
  - Path 参数：
    - `id`（int，必填）：持有/关注记录的主键ID
  - Headers：`Authorization: Bearer <token>`
- 响应（成功示例）
```json
{
  "code": 200,
  "message": "删除成功",
  "timestamp": "2025-10-24T22:13:00",
  "data": null
}
```
- 错误示例
```json
{
  "code": 404,
  "message": "记录不存在",
  "timestamp": "2025-10-24T22:13:00",
  "data": null
}
```

## 返回格式说明
- 成功：`success_response(data, message)`，`code=200`
- 失败：`error_response(message, code)`，常见：
  - `401 未认证`：令牌缺失或无效
  - `400 参数错误`：缺失或格式不正确
  - `404 未找到`：股票或记录不存在
  - `500 服务器错误`：内部异常

## 业务约束与注意事项
- 所有股票相关数据仅通过数据库 (`IndividualStock`) 获取，不调用外部接口
- 关系类型取值固定为 `WATCHED` 或 `HELD`
- industry 字段在新增时若未提供，将自动冗余填充为 `IndividualStock.industry`
- 接口遵循单一职责：
  - GET/POST /holdings/ 专注列表展示与新增
  - DELETE /holdings/{id}/ 专注删除操作