# Skill 技能扩展目录

本目录用于存放 AI Agent 的自定义技能。只要在此目录下按规范建立技能文件夹，系统就会自动加载技能的 Prompt（提示词）和工具（Tools）。

## 技能目录规范

一个典型的技能文件夹结构如下：

```
skill/
└── my_custom_skill/         # 技能名称（目录名）
    ├── SKILL.md             # 【必填】技能的核心指令、设定或工作流描述
    ├── references/          # 【选填】该技能需要参考的文档目录
    │   ├── doc1.md
    │   └── doc2.txt
    └── scripts/             # 【选填】该技能提供的 MCP 工具实现脚本
        └── tools.py
```

## 加载机制

1. **Prompt 注入**: 
   AI 服务启动或处理请求时，会自动遍历所有技能的 `SKILL.md` 以及 `references/` 目录下的 `.md` 和 `.txt` 文件，将其拼接到 Agent 的 System Prompt 中。

2. **MCP 工具注册**:
   如果技能提供了 `scripts/` 目录，MCP Server 会动态导入其中的 Python 文件。如果 Python 文件中定义了 `register_tools(mcp)` 函数，系统将自动调用它来注册工具。

## Python 工具示例 (`scripts/tools.py`)

```python
def register_tools(mcp):
    @mcp.tool()
    def my_custom_tool(param1: str) -> str:
        \"\"\"
        这里是工具的功能描述，供 AI 理解如何使用此工具。
        \"\"\"
        return f"Tool executed with {param1}"
```

参考 DeerFlow 2.0 和 Trae IDE 的实现，这种结构实现了高度模块化的 AI 技能扩展。
