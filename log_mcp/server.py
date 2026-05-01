#!/usr/bin/env python3
"""
MCP server exposing read-oriented shell tools for log inspection and troubleshooting.

Run (stdio transport, for Cursor / Claude Desktop):
    python3 -m log_mcp.server
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

_REPO_ROOT = Path(__file__).resolve().parent.parent

_DEFAULT_ALLOWLIST = frozenset(
    {
        "grep",
        "egrep",
        "fgrep",
        "zgrep",
        "tail",
        "head",
        "cat",
        "zcat",
        "sort",
        "uniq",
        "wc",
        "cut",
        "ls",
    }
)


def _extra_allowlist_from_env() -> frozenset[str]:
    raw = os.environ.get("MCP_SHELL_ALLOWED_COMMANDS", "")
    if not raw.strip():
        return frozenset()
    return frozenset(x.strip() for x in raw.split(",") if x.strip())


@lru_cache(maxsize=1)
def _allowed_commands() -> frozenset[str]:
    return _DEFAULT_ALLOWLIST | _extra_allowlist_from_env()


def _resolve_work_dir() -> Path:
    override = os.environ.get("MCP_SHELL_WORKDIR")
    if override:
        p = Path(override).expanduser().resolve()
    else:
        p = _REPO_ROOT
    try:
        p.relative_to(_REPO_ROOT)
    except ValueError:
        raise ValueError(
            "working directory must be inside the repository root"
        ) from None
    return p


@lru_cache(maxsize=1)
def _workdir() -> Path:
    return _resolve_work_dir()


def _timeout_seconds() -> float:
    raw = os.environ.get("MCP_SHELL_TIMEOUT_SECONDS", "60")
    try:
        t = float(raw)
    except ValueError:
        return 60.0
    return max(1.0, min(t, 300.0))


def _max_output_bytes() -> int:
    raw = os.environ.get("MCP_SHELL_MAX_OUTPUT_BYTES", str(256 * 1024))
    try:
        n = int(raw)
    except ValueError:
        return 256 * 1024
    return max(4096, min(n, 2 * 1024 * 1024))


mcp = FastMCP(
    "stock-data-service",
    instructions=(
        "辅助查询与分析本地日志：使用 run_shell_command 在仓库目录内执行只读类命令"
        "（白名单：grep/tail/head/cat 等），禁止管道与 shell 元字符。"
    ),
)


@mcp.tool(
    name="run_shell_command",
    description=(
        "在仓库根目录下执行一条 shell 命令（不经 shell 解析），用于查看日志、检索关键字等。"
        "仅允许白名单中的首个可执行文件（如 grep、tail、head、cat、zgrep、wc）；"
        "不支持管道符 |、重定向、命令替换等。输出长度受 MCP_SHELL_MAX_OUTPUT_BYTES 限制。"
    ),
    annotations=ToolAnnotations(
        title="执行只读 Shell 命令",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
    ),
)
def run_shell_command(command: str) -> str:
    """执行单个只读诊断命令并返回合并的标准输出与标准错误（截断时会在末尾注明）。"""
    try:
        workdir = _workdir()
    except ValueError as e:
        return f"错误：工作目录配置无效（{e}）。"

    allowlist = _allowed_commands()
    timeout = _timeout_seconds()
    max_out = _max_output_bytes()

    cmd = (command or "").strip()
    if not cmd:
        return "错误：command 不能为空。"

    if any(c in cmd for c in "\n\r\x00"):
        return "错误：命令中不允许换行或空字符。"

    if any(sep in cmd for sep in ("|", "&", ";", "`", "$", ">", "<")):
        return (
            "错误：不支持管道、重定向、后台执行、多条命令或 shell 替换。"
            "请使用单个白名单命令及其参数。"
        )

    try:
        argv = shlex.split(cmd, posix=True)
    except ValueError as e:
        return f"错误：无法解析命令（{e}）。"

    if not argv:
        return "错误：解析后参数为空。"

    exe_name = argv[0]
    if "/" in exe_name or exe_name.startswith("."):
        return "错误：请只使用命令名（不允许路径或相对路径）。"

    if exe_name not in allowlist:
        allowed = ", ".join(sorted(allowlist))
        return f"错误：命令 `{exe_name}` 不在允许列表中。允许：{allowed}"

    if not shutil.which(exe_name):
        return f"错误：找不到可执行文件 `{exe_name}`。"

    try:
        proc = subprocess.run(
            argv,
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "PYTHONUTF8": "1"},
        )
    except subprocess.TimeoutExpired:
        return f"错误：命令执行超过 {timeout:.0f} 秒已中止。"
    except OSError as e:
        return f"错误：无法运行命令（{e}）。"

    out = proc.stdout or ""
    err = proc.stderr or ""
    merged = out
    if err:
        merged = f"{out}\n--- stderr ---\n{err}" if out else err

    truncated = False
    if len(merged.encode("utf-8", errors="replace")) > max_out:
        merged = merged.encode("utf-8", errors="replace")[:max_out].decode(
            "utf-8", errors="replace"
        )
        truncated = True

    status_line = f"\n--- exit code: {proc.returncode} ---"
    if truncated:
        status_line += f"\n（输出已截断至约 {max_out} 字节）"
    return merged + status_line


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
