"""Tests for MCP log diagnostic shell tool."""

import pytest

from log_mcp.server import run_shell_command


@pytest.mark.parametrize(
    "cmd,fragment",
    [
        ("/bin/grep foo bar", "路径"),
        ("bash -c echo", "不在允许列表"),
        ("grep ERROR logs/foo | wc", "不支持管道"),
        ("tail -n 1 logs/app.log &", "不支持管道"),
    ],
)
def test_run_shell_command_rejects_unsafe_or_disallowed(cmd: str, fragment: str) -> None:
    out = run_shell_command(cmd)
    assert "错误" in out
    assert fragment in out


def test_run_shell_command_success_ls(tmp_path, monkeypatch) -> None:
    from log_mcp import server as srv

    monkeypatch.setattr(srv, "_REPO_ROOT", tmp_path)
    monkeypatch.delenv("MCP_SHELL_WORKDIR", raising=False)
    monkeypatch.delenv("MCP_SHELL_ALLOWED_COMMANDS", raising=False)
    srv._allowed_commands.cache_clear()
    srv._workdir.cache_clear()

    (tmp_path / "a.txt").write_text("x")
    out = run_shell_command("ls -1")
    assert "exit code: 0" in out
    assert "a.txt" in out
