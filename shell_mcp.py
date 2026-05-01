#!/usr/bin/env python3
"""
在 Cursor / Claude Desktop 等客户端里作为 MCP 服务运行，暴露一个执行 shell 的工具（适合查日志）。

启动（stdio）:
    python3 shell_mcp.py

客户端示例配置把 command 设为 python3，args 设为 ["shell_mcp.py"]，cwd 设为项目根目录。
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

_REPO_ROOT = Path(__file__).resolve().parent

mcp = FastMCP(
    "stock-data-service",
    instructions="可通过 run_shell_command 在项目根目录执行 shell 命令，用于 tail/grep/journalctl 等日志排查。",
)


@mcp.tool()
def run_shell_command(command: str) -> str:
    """在项目根目录执行一条 shell 命令，返回标准输出与标准错误合并文本（含退出码）。"""
    cmd = (command or "").strip()
    if not cmd:
        return "错误：命令为空。"

    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            executable="/bin/bash",
            env={**os.environ},
        )
    except subprocess.TimeoutExpired:
        return "错误：命令执行超过 120 秒。"

    out = (proc.stdout or "") + (
        f"\n--- stderr ---\n{proc.stderr}" if proc.stderr else ""
    )
    return out.rstrip() + f"\n--- exit code: {proc.returncode} ---"


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
