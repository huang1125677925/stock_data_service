# 用户管理 API 文档

## 基本信息

- 基础路径: `/django/api/user/`
- 所有请求和响应均使用 JSON 格式
- 认证方式: Bearer Token (在请求头中添加 `Authorization: Bearer {token}`)

## 通用响应格式

### 成功响应

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2023-01-01T12:00:00.000000",
  "data": { ... }
}
```

### 错误响应

```json
{
  "code": 400,  // 错误代码
  "message": "错误信息",  // 错误描述
  "timestamp": "2023-01-01T12:00:00.000000"
}
```

## 接口列表

### 1. 用户注册

- **URL**: `/register/`
- **方法**: POST
- **描述**: 注册新用户

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 |
| --- | --- | --- | --- |
| username | string | 是 | 用户名，3-50个字符 |
| password | string | 是 | 密码，6-20个字符，必须包含数字和字母 |
| email | string | 是 | 邮箱地址 |
| phone | string | 否 | 手机号码 |
| invitation_code | string | 否 | 邀请码 |

#### 请求示例

```json
{
  "username": "testuser",
  "password": "Test123456",
  "email": "test@example.com",
  "phone": "13800138000",
  "invitation_code": "ABC123DEF456"
}
```

#### 成功响应

```json
{
  "code": 200,
  "message": "注册成功",
  "timestamp": "2023-01-01T12:00:00.000000",
  "data": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "phone": "13800138000",
    "created_at": "2023-01-01T12:00:00.000000"
  }
}
```

#### 错误响应

```json
{
  "code": 400,
  "message": "用户名已存在",
  "timestamp": "2023-01-01T12:00:00.000000"
}
```

### 2. 用户登录

- **URL**: `/login/`
- **方法**: POST
- **描述**: 用户登录并获取令牌

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 |
| --- | --- | --- | --- |
| username | string | 是 | 用户名或邮箱 |
| password | string | 是 | 密码 |

#### 请求示例

```json
{
  "username": "testuser",
  "password": "Test123456"
}
```

#### 成功响应

```json
{
  "code": 200,
  "message": "登录成功",
  "timestamp": "2023-01-01T12:00:00.000000",
  "data": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "is_admin": false,
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

#### 错误响应

```json
{
  "code": 401,
  "message": "密码错误",
  "timestamp": "2023-01-01T12:00:00.000000"
}
```

### 3. 用户登出

- **URL**: `/logout/`
- **方法**: POST
- **描述**: 用户登出，使当前令牌失效
- **认证**: 需要

#### 请求参数

无请求体参数，令牌通过请求头 `Authorization` 传递

#### 成功响应

```json
{
  "code": 200,
  "message": "登出成功",
  "timestamp": "2023-01-01T12:00:00.000000",
  "data": {}
}
```

#### 错误响应

```json
{
  "code": 400,
  "message": "令牌不存在",
  "timestamp": "2023-01-01T12:00:00.000000"
}
```

### 4. 获取用户信息

- **URL**: `/info/`
- **方法**: GET
- **描述**: 获取当前登录用户的详细信息
- **认证**: 需要

#### 请求参数

无请求体参数，令牌通过请求头 `Authorization` 传递

#### 成功响应

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2023-01-01T12:00:00.000000",
  "data": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "phone": "13800138000",
    "is_admin": false,
    "last_login": "2023-01-01T12:00:00.000000",
    "created_at": "2023-01-01T12:00:00.000000"
  }
}
```

#### 错误响应

```json
{
  "code": 401,
  "message": "无效的令牌",
  "timestamp": "2023-01-01T12:00:00.000000"
}
```

### 5. 生成邀请码

- **URL**: `/invitation/`
- **方法**: POST
- **描述**: 生成新的邀请码
- **认证**: 需要

#### 请求参数

无请求体参数，令牌通过请求头 `Authorization` 传递

#### 成功响应

```json
{
  "code": 200,
  "message": "邀请码生成成功",
  "timestamp": "2023-01-01T12:00:00.000000",
  "data": {
    "code": "ABC123DEF456",
    "expires_at": "2023-02-01T12:00:00.000000",
    "created_at": "2023-01-01T12:00:00.000000"
  }
}
```

#### 错误响应

```json
{
  "code": 401,
  "message": "用户已被禁用",
  "timestamp": "2023-01-01T12:00:00.000000"
}
```

### 6. 获取邀请码列表

- **URL**: `/invitation/`
- **方法**: GET
- **描述**: 获取当前用户创建的所有邀请码
- **认证**: 需要

#### 请求参数

无请求体参数，令牌通过请求头 `Authorization` 传递

#### 成功响应

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2023-01-01T12:00:00.000000",
  "data": [
    {
      "id": 1,
      "code": "ABC123DEF456",
      "is_used": false,
      "used_by": null,
      "expires_at": "2023-02-01T12:00:00.000000",
      "created_at": "2023-01-01T12:00:00.000000"
    },
    {
      "id": 2,
      "code": "GHI789JKL012",
      "is_used": true,
      "used_by": "newuser",
      "expires_at": "2023-02-01T12:00:00.000000",
      "created_at": "2023-01-01T12:00:00.000000"
    }
  ]
}
```

### 7. 验证邀请码

- **URL**: `/invitation/validate/`
- **方法**: POST
- **描述**: 验证邀请码是否有效

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 |
| --- | --- | --- | --- |
| code | string | 是 | 邀请码 |

#### 请求示例

```json
{
  "code": "ABC123DEF456"
}
```

#### 成功响应

```json
{
  "code": 200,
  "message": "邀请码有效",
  "timestamp": "2023-01-01T12:00:00.000000",
  "data": {}
}
```

#### 错误响应

```json
{
  "code": 400,
  "message": "邀请码已过期",
  "timestamp": "2023-01-01T12:00:00.000000"
}
```

### 8. 重置密码

- **URL**: `/reset-password/`
- **方法**: POST
- **描述**: 重置用户密码

#### 请求参数

| 参数名 | 类型 | 必填 | 描述 |
| --- | --- | --- | --- |
| email | string | 是 | 用户邮箱 |
| new_password | string | 是 | 新密码，6-20个字符，必须包含数字和字母 |

#### 请求示例

```json
{
  "email": "test@example.com",
  "new_password": "NewTest123456"
}
```

#### 成功响应

```json
{
  "code": 200,
  "message": "密码重置成功",
  "timestamp": "2023-01-01T12:00:00.000000",
  "data": {}
}
```

#### 错误响应

```json
{
  "code": 400,
  "message": "用户不存在",
  "timestamp": "2023-01-01T12:00:00.000000"
}
```

或

```json
{
  "code": 400,
  "message": "密码格式不正确，密码必须包含数字和字母，长度在6-20个字符之间",
  "timestamp": "2023-01-01T12:00:00.000000"
}
```

## 错误代码说明

| 错误代码 | 描述 |
| --- | --- |
| 400 | 请求参数错误或业务逻辑错误 |
| 401 | 未认证或认证失败 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 认证说明

1. 用户登录成功后，服务器会返回一个令牌（token）
2. 客户端需要在后续请求的请求头中添加 `Authorization: Bearer {token}`
3. 令牌有效期为7天，过期后需要重新登录获取新令牌
4. 用户登出后，当前令牌将失效