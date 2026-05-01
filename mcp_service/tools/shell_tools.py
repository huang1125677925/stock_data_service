"""
在 MCP 服务进程所在主机上执行 shell 命令（用于部署环境、运维脚本等）。

默认关闭，避免误用或暴露风险。启用方式：

    export SERVER_SHELL_TOOL_ENABLED=true

可选环境变量：

- SERVER_SHELL_TOOL_WORKDIR_ROOT：若设置，则 cwd 必须在该目录之下（防止任意路径执行）。
- SERVER_SHELL_TOOL_DEFAULT_TIMEOUT：默认超时秒数（默认 300）。
"""

from __future__ import annotations

import concurrent.futures
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from mcp_service.tools.tushare._registry import error_payload, safe_tool


def _shell_enabled() -> bool:
    raw = os.environ.get("SERVER_SHELL_TOOL_ENABLED", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _default_timeout() -> int:
    raw = os.environ.get("SERVER_SHELL_TOOL_DEFAULT_TIMEOUT", "300").strip()
    try:
        return max(1, min(int(raw), 86400))
    except ValueError:
        return 300


def _resolve_workdir_root() -> Optional[Path]:
    raw = os.environ.get("SERVER_SHELL_TOOL_WORKDIR_ROOT", "").strip()
    if not raw:
        return None
    try:
        return Path(raw).expanduser().resolve()
    except OSError:
        return None


def _cwd_allowed(cwd: Path, root: Optional[Path]) -> bool:
    if root is None:
        return True
    try:
        resolved = cwd.resolve()
        return resolved == root or root in resolved.parents
    except OSError:
        return False


def register_shell_tools(mcp: FastMCP) -> None:
    @safe_tool(
        mcp,
        name="server.shell.run",
        description=(
            "在 MCP 服务所在服务器上执行一条 shell 命令（非交互）。"
            "用于安装依赖、systemd/docker、数据库迁移等部署与运维场景。"
            "需在服务端设置 SERVER_SHELL_TOOL_ENABLED=true 才会真正执行；未启用时调用会返回说明。"
            "支持可选 working_directory 与超时；stdout/stderr 合并截断返回。"
        ),
    )
    def server_shell_run(
        command: str,
        working_directory: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        max_output_chars: int = 24000,
    ) -> Dict[str, Any]:
        if not _shell_enabled():
            return error_payload(
                "Shell tool is disabled. On the server, set environment variable "
                "SERVER_SHELL_TOOL_ENABLED=true (and optionally SERVER_SHELL_TOOL_WORKDIR_ROOT) "
                "then restart the MCP service.",
                403,
            )

        cmd = (command or "").strip()
        if not cmd:
            return error_payload("command must be non-empty", 400)

        try:
            argv = shlex.split(cmd)
        except ValueError as e:
            return error_payload(f"Invalid command (shell quoting): {e}", 400)

        if not argv:
            return error_payload("command parses to empty argv", 400)

        timeout = timeout_seconds if timeout_seconds is not None else _default_timeout()
        try:
            timeout = max(1, min(int(timeout), 86400))
        except (TypeError, ValueError):
            timeout = _default_timeout()

        try:
            max_out = max(256, min(int(max_output_chars), 500_000))
        except (TypeError, ValueError):
            max_out = 24000

        cwd_path: Optional[Path] = None
        if working_directory and str(working_directory).strip():
            try:
                cwd_path = Path(str(working_directory).strip()).expanduser().resolve()
            except OSError as e:
                return error_payload(f"Invalid working_directory: {e}", 400)
            if not cwd_path.is_dir():
                return error_payload(
                    f"working_directory is not a directory: {cwd_path}",
                    400,
                )

        root = _resolve_workdir_root()
        if cwd_path is not None and not _cwd_allowed(cwd_path, root):
            return error_payload(
                f"working_directory must be under SERVER_SHELL_TOOL_WORKDIR_ROOT ({root})",
                403,
            )
        if cwd_path is None and root is not None:
            cwd_path = root

        run_kwargs: Dict[str, Any] = {
            "args": argv,
            "capture_output": True,
            "text": True,
            "timeout": timeout,
            "shell": False,
        }
        if cwd_path is not None:
            run_kwargs["cwd"] = str(cwd_path)

        def _run() -> subprocess.CompletedProcess[str]:
            return subprocess.run(**run_kwargs)

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_run)
                proc = future.result(timeout=timeout + 10)
        except subprocess.TimeoutExpired:
            return error_payload(f"Command timed out after {timeout} seconds", 408)
        except Exception as e:
            return error_payload(f"Execution failed: {e}", 500)

        out_parts = []
        if proc.stdout:
            out_parts.append(proc.stdout)
        if proc.stderr:
            if out_parts:
                out_parts.append("\n--- stderr ---\n")
            out_parts.append(proc.stderr)
        combined = "".join(out_parts)
        truncated = False
        if len(combined) > max_out:
            combined = combined[:max_out] + "\n... [truncated]"
            truncated = True

        return {
            "code": 200,
            "message": "success",
            "data": {
                "exit_code": proc.returncode,
                "stdout_stderr": combined,
                "truncated": truncated,
                "cwd": str(cwd_path) if cwd_path is not None else None,
                "timeout_seconds": timeout,
            },
        }
