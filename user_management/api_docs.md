# 用户管理API接口文档

## 概述

用户管理模块提供用户注册、登录、登出、获取用户信息、生成邀请码和验证邀请码等功能。所有API返回统一的JSON格式响应。

## 通用响应格式

### 成功响应

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2023-01-01T12:00:00.000000",
  "data": {}
}
```

### 错误响应

```json
{
  "code": 400,  // 错误代码，可能是400、401、403、404、500等
  "message": "错误信息",
  "timestamp": "2023-01-01T12:00:00.000000"
}
```

## 认证方式

除了注册、登录和验证邀请码接口外，其他接口都需要在请求头中携带令牌进行认证：

```
Authorization: Bearer {token}
```

注意：所有API的实际访问路径以 `/django/api/user/` 开头，而不是文档中原先描述的 `/api/user/`。

## 接口列表

### 1. 用户注册

- **URL**: `/django/api/user/register/`
- **方法**: POST
- **描述**: 注册新用户
- **请求参数**:

| 参数名 | 类型 | 必填 | 描述 |
| --- | --- | --- | --- |
| username | string | 是 | 用户名，长度3-20字符 |
| password | string | 是 | 密码，长度8-20字符 |
| email | string | 是 | 邮箱地址 |
| phone | string | 否 | 手机号码 |
| invitation_code | string | 否 | 邀请码 |

- **成功响应**:

```json
{
  "code": 200,
  "message": "注册成功",
  "timestamp": "2023-01-01T12:00:00.000000",
  "data": {
    "id": 1,
    "username": "test_user",
    "email": "test@example.com",
    "phone": "13800138000",
    "created_at": "2023-01-01T12:00:00.000000"
  }
}
```

- **错误响应**:

```json
{
  "code": 400,
  "message": "用户名已存在",
  "timestamp": "2023-01-01T12:00:00.000000"
}
```

### 2. 用户登录

- **URL**: `/django/api/user/login/`
- **方法**: POST
- **描述**: 用户登录获取令牌
- **请求参数**:

| 参数名 | 类型 | 必填 | 描述 |
| --- | --- | --- | --- |
| username | string | 是 | 用户名或邮箱 |
| password | string | 是 | 密码 |

- **成功响应**:

```json
{
  "code": 200,
  "message": "登录成功",
  "timestamp": "2023-01-01T12:00:00.000000",
  "data": {
    "id": 1,
    "username": "test_user",
    "email": "test@example.com",
    "is_admin": false,
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

- **错误响应**:

```json
{
  "code": 401,
  "message": "用户名或密码错误",
  "timestamp": "2023-01-01T12:00:00.000000"
}
```

### 3. 用户登出

- **URL**: `/django/api/user/logout/`
- **方法**: POST
- **描述**: 用户登出，使当前令牌失效
- **请求头**: 需要认证令牌
- **请求参数**: 无
- **成功响应**:

```json
{
  "code": 200,
  "message": "登出成功",
  "timestamp": "2023-01-01T12:00:00.000000"
}
```

- **错误响应**:

```json
{
  "code": 401,
  "message": "未认证",
  "timestamp": "2023-01-01T12:00:00.000000"
}
```

### 4. 获取用户信息

- **URL**: `/django/api/user/info/`
- **方法**: GET
- **描述**: 获取当前登录用户的信息
- **请求头**: 需要认证令牌
- **请求参数**: 无
- **成功响应**:

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2023-01-01T12:00:00.000000",
  "data": {
    "id": 1,
    "username": "test_user",
    "email": "test@example.com",
    "phone": "13800138000",
    "is_admin": false,
    "last_login": "2023-01-01T12:00:00.000000",
    "created_at": "2023-01-01T12:00:00.000000"
  }
}
```

- **错误响应**:

```json
{
  "code": 401,
  "message": "无效的令牌",
  "timestamp": "2023-01-01T12:00:00.000000"
}
```

### 5. 生成邀请码

- **URL**: `/django/api/user/invitation/`
- **方法**: POST
- **描述**: 生成新的邀请码（需要管理员权限）
- **请求头**: 需要认证令牌
- **请求参数**: 无
- **成功响应**:

```json
{
  "code": 200,
  "message": "邀请码生成成功",
  "timestamp": "2023-01-01T12:00:00.000000",
  "data": {
    "code": "ABC123XYZ",
    "expires_at": "2023-02-01T12:00:00.000000",
    "created_at": "2023-01-01T12:00:00.000000"
  }
}
```

- **错误响应**:

```json
{
  "code": 403,
  "message": "权限不足",
  "timestamp": "2023-01-01T12:00:00.000000"
}
```

### 6. 获取邀请码列表

- **URL**: `/django/api/user/invitation/`
- **方法**: GET
- **描述**: 获取当前用户创建的邀请码列表
- **请求头**: 需要认证令牌
- **请求参数**: 无
- **成功响应**:

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2023-01-01T12:00:00.000000",
  "data": [
    {
      "id": 1,
      "code": "ABC123XYZ",
      "is_used": false,
      "used_by": null,
      "expires_at": "2023-02-01T12:00:00.000000",
      "created_at": "2023-01-01T12:00:00.000000"
    },
    {
      "id": 2,
      "code": "DEF456UVW",
      "is_used": true,
      "used_by": "another_user",
      "expires_at": "2023-02-01T12:00:00.000000",
      "created_at": "2023-01-01T12:00:00.000000"
    }
  ]
}
```

### 7. 验证邀请码

- **URL**: `/django/api/user/invitation/validate/`
- **方法**: POST
- **描述**: 验证邀请码是否有效
- **请求参数**:

| 参数名 | 类型 | 必填 | 描述 |
| --- | --- | --- | --- |
| code | string | 是 | 邀请码 |

- **成功响应**:

```json
{
  "code": 200,
  "message": "邀请码有效",
  "timestamp": "2023-01-01T12:00:00.000000"
}
```

- **错误响应**:

```json
{
  "code": 400,
  "message": "邀请码无效或已过期",
  "timestamp": "2023-01-01T12:00:00.000000"
}
```

## 错误代码说明

| 错误代码 | 描述 |
| --- | --- |
| 400 | 请求参数错误 |
| 401 | 未认证或认证失败 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |