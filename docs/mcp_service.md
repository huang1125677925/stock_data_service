# MCP 服务模块（FastMCP + SSE）

本模块提供一个基于 FastMCP 的 MCP 服务器，支持 SSE 传输方式，工具以模块化方式组织，便于后续扩展更多 Tushare 类型数据接口。

## 目录结构

```
mcp_service/
  ├── __init__.py
  ├── server.py               # FastMCP 服务入口（SSE）
  └── tools/
      ├── __init__.py
      └── tushare_docs.py     # 基于本地 Tushare 文档的工具与资源
```

## 依赖安装

在项目根目录执行：

```bash
pip install -r requirements.txt
```

确保安装了 `mcp[cli]` 以支持 FastMCP 运行与调试。

## 启动（SSE）

有两种方式启动 SSE 服务器：

1) 直接运行入口脚本（默认 SSE 传输）：

```bash
python mcp_service/server.py
```

默认监听 `0.0.0.0:8000`，可在 MCP 客户端中以 SSE 方式连接。

2) 使用 MCP CLI 调试（推荐）：

```bash
# 交互开发/调试
mcp dev mcp_service/server.py

# 或运行
mcp run mcp_service/server.py
```

> 注：如果本地使用 `uv`，也可以用 `uv run mcp dev mcp_service/server.py`。

## 提供的工具与资源

- `list_tushare_docs(category="大模型语料专题数据")`：列出指定分类下的 Markdown 文档
- `read_tushare_doc(name, category="大模型语料专题数据")`：读取指定文档内容
- `search_tushare_docs(query, category="大模型语料专题数据", max_results=20)`：全文检索并返回摘要
- `get_tushare_usage_example()`：返回 `data/tushare_docs/tushare接口使用范例.md` 内容
- 资源：`tushare-doc://{category}/{name}` 以资源形式暴露文档内容

所有工具均返回结构化结果，便于客户端处理；资源提供原始文本以便直接加载到上下文。

## 扩展建议

- 新增工具：在 `mcp_service/tools/` 内新增模块，并提供 `register_*_tools(mcp, base_dir)`
- 遵循模块化注册方式：在 `server.py` 中引入并注册新工具集，无需改动现有工具
- 外部数据获取（如直接调用 Tushare API）：按照项目规范，请在 `scheduled_tasks/` 中实现采集逻辑，并将结果入库后由 API 读取；MCP 工具可作为文档/结果访问层。