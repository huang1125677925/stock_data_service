# 用户管理 API 接口文档

本文档描述用户注册、登录、登出、重置密码、用户信息、邀请码等接口。

## 1. 接口概览

- 基础路径：`/django/api/user/`
- 请求体：POST 接口使用 JSON（`Content-Type: application/json`）
- 认证方式：Token（Header 传 `Authorization`）
  - 支持：`Authorization: Bearer <token>` 或 `Authorization: <token>`
- 注意：接口统一返回 JSON 响应体，业务成功/失败以响应体中的 `code` 为准

| 接口名称 | URL | 方法 | 认证 | 说明 |
| --- | --- | --- | --- | --- |
| 用户注册 | `/django/api/user/register/` | POST | 否 | 注册新用户（可选邀请码） |
| 用户登录 | `/django/api/user/login/` | POST | 否 | 登录并获取 token |
| 用户登出 | `/django/api/user/logout/` | POST | 是 | token 失效（删除） |
| 重置密码 | `/django/api/user/reset-password/` | POST | 否 | 通过邮箱直接重置密码 |
| 获取用户信息 | `/django/api/user/info/` | GET | 是 | 获取当前 token 对应用户信息 |
| 邀请码（生成/列表） | `/django/api/user/invitation/` | POST / GET | 是 | 生成邀请码、查询自己创建的邀请码 |
| 验证邀请码 | `/django/api/user/invitation/validate/` | POST | 否 | 校验邀请码是否有效 |

## 2. 统一响应格式

项目使用 `success_response / error_response` 返回（业务失败时，HTTP 状态码也固定返回 200；通过 body.code 判断成功或失败）。

### 2.1 成功响应

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-03-21T12:00:00.000000",
  "data": {}
}
```

### 2.2 错误响应

```json
{
  "code": 400,
  "message": "错误信息",
  "timestamp": "2026-03-21T12:00:00.000000",
  "data": null
}
```

## 3. 业务规则摘要

- token 有效期：7 天
- 邀请码有效期：30 天
- 用户名：3-50 字符且唯一
- 密码：6-20 字符，且必须同时包含字母与数字
- 登录：支持用户名或邮箱（包含 `@` 时按邮箱登录）

## 4. 接口详情

### 4.1 用户注册

- **URL**：`/django/api/user/register/`
- **方法**：POST
- **认证**：否
- **说明**：注册新用户；若传 `invitation_code` 且校验通过，会将邀请码标记为已使用

#### 请求参数（JSON Body）

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| username | string | 是 | 用户名（3-50 字符，唯一） |
| password | string | 是 | 密码（6-20 字符，字母+数字） |
| email | string | 是 | 邮箱（唯一） |
| phone | string | 否 | 手机号 |
| invitation_code | string | 否 | 邀请码（未使用且未过期） |

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

#### 成功响应示例

```json
{
  "code": 200,
  "message": "注册成功",
  "timestamp": "2026-03-21T12:00:00.000000",
  "data": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "phone": "13800138000",
    "created_at": "2026-03-21T12:00:00.000000"
  }
}
```

#### 常见错误（code=400）

- `用户名、密码和邮箱不能为空`
- `用户名长度必须在3-50个字符之间`
- `用户名已存在`
- `邮箱格式不正确`
- `邮箱已被注册`
- `密码长度必须在6-20个字符之间`
- `密码必须包含数字和字母`
- `邀请码不存在 / 邀请码已被使用 / 邀请码已过期`

---

### 4.2 用户登录

- **URL**：`/django/api/user/login/`
- **方法**：POST
- **认证**：否
- **说明**：登录成功会返回 `token`，后续需要认证的接口通过 `Authorization` 传递

#### 请求参数（JSON Body）

| 参数名 | 类型 | 必填 | 说明 |
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

#### 成功响应示例

```json
{
  "code": 200,
  "message": "登录成功",
  "timestamp": "2026-03-21T12:00:00.000000",
  "data": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "is_admin": false,
    "token": "0d6c5b3a0a5b4b4e9d7c1d2e3f4a5b6c"
  }
}
```

#### 常见错误（code=400）

- `用户名和密码不能为空`
- `用户不存在`
- `密码错误`
- `账号已被禁用`

---

### 4.3 用户登出

- **URL**：`/django/api/user/logout/`
- **方法**：POST
- **认证**：是
- **说明**：使 token 失效（删除 token 记录）

#### Header

- `Authorization: Bearer <token>` 或 `Authorization: <token>`

#### 成功响应示例

```json
{
  "code": 200,
  "message": "登出成功",
  "timestamp": "2026-03-21T12:00:00.000000",
  "data": null
}
```

#### 常见错误

- code=400：`未提供令牌`、`令牌不存在`

---

### 4.4 获取用户信息

- **URL**：`/django/api/user/info/`
- **方法**：GET
- **认证**：是
- **说明**：根据 token 获取当前用户信息

#### Header

- `Authorization: Bearer <token>` 或 `Authorization: <token>`

#### 成功响应示例

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-03-21T12:00:00.000000",
  "data": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "phone": "13800138000",
    "is_admin": false,
    "last_login": "2026-03-21T11:30:00.000000",
    "created_at": "2026-03-21T12:00:00.000000"
  }
}
```

#### 常见错误（code=401）

- `未提供令牌`
- `无效的令牌`
- `令牌已过期`
- `用户已被禁用`

---

### 4.5 邀请码（生成）

- **URL**：`/django/api/user/invitation/`
- **方法**：POST
- **认证**：是
- **说明**：生成一个新的邀请码（默认 30 天过期）

#### Header

- `Authorization: Bearer <token>` 或 `Authorization: <token>`

#### 成功响应示例

```json
{
  "code": 200,
  "message": "邀请码生成成功",
  "timestamp": "2026-03-21T12:00:00.000000",
  "data": {
    "code": "ABC123DEF456",
    "expires_at": "2026-04-20T12:00:00.000000",
    "created_at": "2026-03-21T12:00:00.000000"
  }
}
```

#### 常见错误

- code=401：未提供令牌 / token 无效或过期
- code=400：业务校验失败（例如用户状态异常等）

---

### 4.6 邀请码（列表）

- **URL**：`/django/api/user/invitation/`
- **方法**：GET
- **认证**：是
- **说明**：获取当前用户创建的邀请码列表（按创建时间倒序）

#### Header

- `Authorization: Bearer <token>` 或 `Authorization: <token>`

#### 成功响应示例

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-03-21T12:00:00.000000",
  "data": [
    {
      "id": 1,
      "code": "ABC123DEF456",
      "is_used": false,
      "used_by": null,
      "expires_at": "2026-04-20T12:00:00.000000",
      "created_at": "2026-03-21T12:00:00.000000"
    }
  ]
}
```

#### 常见错误（code=401）

- `未提供令牌`
- `无效的令牌`
- `令牌已过期`
- `用户已被禁用`

---

### 4.7 验证邀请码

- **URL**：`/django/api/user/invitation/validate/`
- **方法**：POST
- **认证**：否
- **说明**：验证邀请码是否存在、是否已使用、是否过期

#### 请求参数（JSON Body）

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| code | string | 是 | 邀请码 |

#### 请求示例

```json
{
  "code": "ABC123DEF456"
}
```

#### 成功响应示例

```json
{
  "code": 200,
  "message": "邀请码有效",
  "timestamp": "2026-03-21T12:00:00.000000",
  "data": null
}
```

#### 常见错误（code=400）

- `邀请码不能为空`
- `邀请码不存在`
- `邀请码已被使用`
- `邀请码已过期`

---

### 4.8 重置密码

- **URL**：`/django/api/user/reset-password/`
- **方法**：POST
- **认证**：否
- **说明**：通过邮箱直接重置密码（当前实现不包含验证码校验流程）

#### 请求参数（JSON Body）

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| email | string | 是 | 注册邮箱 |
| new_password | string | 是 | 新密码（6-20 字符，字母+数字） |

#### 请求示例

```json
{
  "email": "test@example.com",
  "new_password": "NewTest123456"
}
```

#### 成功响应示例

```json
{
  "code": 200,
  "message": "密码重置成功",
  "timestamp": "2026-03-21T12:00:00.000000",
  "data": null
}
```

#### 常见错误（code=400）

- `邮箱和新密码不能为空`
- `用户不存在`
- `密码长度必须在6-20个字符之间`
- `密码必须包含数字和字母`

## 5. 错误码说明（body.code）

| code | 说明 |
| --- | --- |
| 200 | 成功 |
| 400 | 参数错误或业务校验失败 |
| 401 | 未认证或 token 无效/过期 |
| 403 | 权限不足（本模块暂未使用） |
| 404 | 资源不存在（本模块暂未使用） |
| 500 | 服务器内部错误 |
