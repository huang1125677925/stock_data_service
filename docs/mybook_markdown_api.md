# GitHub mybook Markdown 文档接口

本文档面向前端开发，描述如何通过后端接口展示 GitHub 仓库 `huang1125677925/mybook` 下的 Markdown 文档。

## 配置

后端从 `.env` 读取配置：

```env
GITHUB_TOKEN=...
AI_GITHUB_TOKEN=...
AI_GITHUB_SYNC_REPO=https://github.com/huang1125677925/mybook
AI_GITHUB_SYNC_BRANCH=main
```

前端不需要、也不应该持有 GitHub token。前端只访问本后端接口。

## 统一响应

```json
{
  "code": 200,
  "message": "success",
  "timestamp": "2026-05-16T10:30:00.000000",
  "data": {}
}
```

错误时前端仍以响应体 `code` 判断：

```json
{
  "code": 400,
  "message": "参数格式错误: path 不能为空",
  "timestamp": "2026-05-16T10:30:00.000000",
  "data": null
}
```

## 1. 浏览仓库目录

```http
GET /django/api/tasks/mybook/directory/
```

### 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---:|---:|---:|---|
| `path` | string | 否 | 空 | 仓库内目录路径，空表示根目录 |

### 示例

```bash
curl "http://localhost:8000/django/api/tasks/mybook/directory/?path=notes"
```

### data 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `repo` | string | 仓库，固定类似 `huang1125677925/mybook` |
| `branch` | string | 分支 |
| `path` | string | 当前目录路径 |
| `count` | number | 条目数量 |
| `items` | array | 文件和目录列表 |
| `query_time` | string | 查询时间 |

### item 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | string | 文件或目录名 |
| `path` | string | 仓库内路径 |
| `type` | string | `file` 或 `dir` |
| `size` | number | 文件大小，目录通常为 0 |
| `sha` | string | GitHub 对象 sha |
| `download_url` | string | 原始下载地址，目录为空 |
| `html_url` | string | GitHub 页面地址 |
| `is_markdown` | boolean | 是否为 `.md` / `.markdown` 文件 |

## 2. 获取 Markdown 文件列表

```http
GET /django/api/tasks/mybook/markdown-files/
```

### 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---:|---:|---:|---|
| `prefix` | string | 否 | 空 | 路径前缀，空表示全仓库 |
| `recursive` | boolean | 否 | `true` | 是否递归扫描子目录 |

### 示例

```bash
curl "http://localhost:8000/django/api/tasks/mybook/markdown-files/?prefix=notes&recursive=true"
```

### data 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `repo` | string | 仓库 |
| `branch` | string | 分支 |
| `prefix` | string | 当前过滤前缀 |
| `recursive` | boolean | 是否递归 |
| `count` | number | Markdown 文件数量 |
| `files` | array | Markdown 文件列表 |
| `query_time` | string | 查询时间 |

### file 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | string | 文件名 |
| `path` | string | 仓库内完整路径，读取内容时传这个值 |
| `size` | number | 文件大小 |
| `sha` | string | 文件 sha |
| `html_url` | string | GitHub 文件页面 |

## 3. 读取 Markdown 内容

```http
GET /django/api/tasks/mybook/markdown-content/
```

### 参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---:|---:|---:|---|
| `path` | string | 是 | - | 仓库内 Markdown 文件路径 |
| `max_chars` | integer | 否 | `200000` | 最大返回字符数，最大 `500000` |

### 示例

```bash
curl "http://localhost:8000/django/api/tasks/mybook/markdown-content/?path=README.md"
```

### data 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `repo` | string | 仓库 |
| `branch` | string | 分支 |
| `path` | string | 文件路径 |
| `name` | string | 文件名 |
| `sha` | string | 文件 sha |
| `size` | number | 文件大小 |
| `encoding` | string | 固定 `utf-8` |
| `content` | string | Markdown 文本内容 |
| `truncated` | boolean | 是否被 `max_chars` 截断 |
| `html_url` | string | GitHub 文件页面 |
| `download_url` | string | 原始下载地址 |
| `query_time` | string | 查询时间 |

## 前端建议

推荐流程：

1. 页面初始化调用 `/markdown-files/?recursive=true` 获取文档列表。
2. 左侧用 `files[].path` 构建文档树。
3. 用户点击文件后调用 `/markdown-content/?path=<path>`。
4. 使用前端 Markdown 渲染库渲染 `data.content`。

TypeScript 路径常量示例：

```ts
export const MYBOOK_API = {
  directory: '/django/api/tasks/mybook/directory/',
  markdownFiles: '/django/api/tasks/mybook/markdown-files/',
  markdownContent: '/django/api/tasks/mybook/markdown-content/',
}
```

注意：

- `path` 禁止绝对路径和 `..`，后端会校验。
- 只返回 Markdown 文本，不做 HTML 转换，前端自行渲染。
- token 只在后端 `.env` 中配置，不能暴露给浏览器端。
