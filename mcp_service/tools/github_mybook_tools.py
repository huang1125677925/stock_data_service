"""
GitHub mybook 记忆库：通过 Contents API 在配置仓库中追加/读取 Markdown 记忆文件。

与 ai_service 中「问答结束自动同步到 GitHub」独立；供对话 Agent 主动存取个人记忆。

环境变量与 Django settings 一致：AI_GITHUB_TOKEN、AI_GITHUB_SYNC_REPO、
AI_GITHUB_SYNC_BRANCH；可选 AI_GITHUB_MEMORY_PREFIX（默认 memories）。
"""

from __future__ import annotations

import base64
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

from mcp.server.fastmcp import FastMCP

from mcp_service.tools.tushare._registry import error_payload, safe_tool


def _django_str(name: str, default: str = "") -> str:
    try:
        from django.conf import settings

        if hasattr(settings, name):
            v = getattr(settings, name, None)
            if v is not None and str(v).strip():
                return str(v).strip()
    except Exception:
        pass
    return (os.getenv(name, "") or default).strip()


def _github_token() -> str:
    t = _django_str("AI_GITHUB_TOKEN", "") or os.getenv("GITHUB_TOKEN", "").strip()
    return t


def _github_repo() -> str:
    return _django_str("AI_GITHUB_SYNC_REPO", "") or "huang1125677925/mybook"


def _github_branch() -> str:
    return _django_str("AI_GITHUB_SYNC_BRANCH", "") or "main"


def _memory_prefix() -> str:
    return _django_str("AI_GITHUB_MEMORY_PREFIX", "memories").strip().strip("/")


def _normalize_owner_repo(repo: str) -> str:
    r = repo.strip().strip("/")
    if r.startswith("https://github.com/"):
        r = r.replace("https://github.com/", "").strip("/")
    return r


def _reject_unsafe_path_fragment(path: str) -> Optional[str]:
    """Return error message if path is unsafe; else None."""
    p = (path or "").strip().replace("\\", "/")
    if not p:
        return "path 不能为空"
    if p.startswith("/") or ".." in p.split("/"):
        return "path 不合法：禁止绝对路径与 .. 段"
    if "\x00" in p:
        return "path 不合法"
    return None


def _full_path(relative_path: str, prefix: str) -> str:
    rel = relative_path.strip().lstrip("/")
    if not prefix:
        return rel
    return f"{prefix}/{rel}"


def _github_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }


def _contents_get(
    owner_repo: str,
    path: str,
    branch: str,
    token: str,
) -> requests.Response:
    # path segments must be URL-encoded per segment for GitHub API
    parts = path.strip("/").split("/")
    encoded = "/".join(quote(p, safe="") for p in parts)
    url = f"https://api.github.com/repos/{owner_repo}/contents/{encoded}"
    return requests.get(
        url,
        headers=_github_headers(token),
        params={"ref": branch},
        timeout=20,
    )


def _decode_file_content(payload: Dict[str, Any]) -> str:
    enc = payload.get("content") or ""
    if not isinstance(enc, str) or not enc.strip():
        return ""
    try:
        return base64.b64decode(enc.encode("utf-8")).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _append_entry_markdown(title: str, body: str) -> str:
    now = datetime.now()
    ts = now.strftime("%Y-%m-%d %H:%M:%S")
    entry_id = uuid.uuid4().hex[:8]
    t = (title or "").strip()
    b = (body or "").strip()
    head = f"### {ts} · {entry_id}"
    if t:
        head += f"\n\n**{t}**\n"
    else:
        head += "\n"
    return f"\n\n{head}\n{b}\n"


def register_github_mybook_tools(mcp: FastMCP) -> None:
    """注册 GitHub mybook 记忆读写工具。"""

    @safe_tool(
        mcp,
        name="append_github_mybook_memory",
        description=(
            "向配置的 GitHub mybook 仓库中的 Markdown 记忆文件追加一条记录。"
            "relative_path 为仓库内相对路径（位于 memories/ 等业务前缀下，见环境变量 AI_GITHUB_MEMORY_PREFIX）。"
            "首次写入会创建文件并带简单标题。需要 AI_GITHUB_TOKEN 与仓库写权限。"
        ),
    )
    def append_github_mybook_memory(
        relative_path: str,
        body: str,
        entry_title: str = "",
    ) -> Dict[str, Any]:
        err = _reject_unsafe_path_fragment(relative_path)
        if err:
            return error_payload(err, 400)
        token = _github_token()
        if not token:
            return error_payload("未配置 AI_GITHUB_TOKEN（或 GITHUB_TOKEN），无法写入 GitHub。", 503)
        repo = _normalize_owner_repo(_github_repo())
        branch = _github_branch()
        prefix = _memory_prefix()
        path = _full_path(relative_path, prefix)
        path_parts = path.strip("/").split("/")
        url = f"https://api.github.com/repos/{repo}/contents/" + "/".join(
            quote(p, safe="") for p in path_parts
        )

        append_block = _append_entry_markdown(entry_title, body)
        headers = _github_headers(token)

        r = requests.get(url, headers=headers, params={"ref": branch}, timeout=20)
        existing_text = ""
        existing_sha = None
        if r.status_code == 200:
            payload = r.json()
            if isinstance(payload, dict) and payload.get("type") == "file":
                existing_sha = payload.get("sha")
                existing_text = _decode_file_content(payload)
        elif r.status_code == 404:
            pass
        else:
            return error_payload(
                f"读取仓库文件失败: HTTP {r.status_code} {r.text[:500]}",
                502,
            )

        if not (existing_text or "").strip():
            title_line = (entry_title or "Memory").strip() or "Memory"
            existing_text = f"# {title_line}\n\n_个人记忆库 · {datetime.now().strftime('%Y-%m-%d')}_\n"

        new_text = (existing_text or "") + append_block
        encoded_new = base64.b64encode(new_text.encode("utf-8")).decode("utf-8")
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        put_body: Dict[str, Any] = {
            "message": f"memory: append {now_ts} {path}",
            "content": encoded_new,
            "branch": branch,
        }
        if existing_sha:
            put_body["sha"] = existing_sha

        r2 = requests.put(url, headers=headers, json=put_body, timeout=25)
        if r2.status_code not in (200, 201):
            return error_payload(
                f"写入 GitHub 失败: HTTP {r2.status_code} {r2.text[:800]}",
                502,
            )
        return {
            "code": 200,
            "message": "success",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "repo": repo,
                "branch": branch,
                "path": path,
                "bytes_written": len(append_block.encode("utf-8")),
            },
        }

    @safe_tool(
        mcp,
        name="read_github_mybook_file",
        description=(
            "读取 GitHub mybook 仓库中指定相对路径的文本文件内容（UTF-8）。"
            "路径相对于记忆前缀（默认 memories/）。大文件会截断并返回 truncated 标记。"
        ),
    )
    def read_github_mybook_file(
        relative_path: str,
        max_chars: int = 60000,
    ) -> Dict[str, Any]:
        err = _reject_unsafe_path_fragment(relative_path)
        if err:
            return error_payload(err, 400)
        token = _github_token()
        if not token:
            return error_payload("未配置 AI_GITHUB_TOKEN，无法读取 GitHub。", 503)
        repo = _normalize_owner_repo(_github_repo())
        branch = _github_branch()
        prefix = _memory_prefix()
        path = _full_path(relative_path, prefix)

        r = _contents_get(repo, path, branch, token)
        if r.status_code == 404:
            return error_payload(f"文件不存在: {path}", 404)
        if r.status_code != 200:
            return error_payload(f"读取失败: HTTP {r.status_code} {r.text[:500]}", 502)
        payload = r.json()
        if not isinstance(payload, dict) or payload.get("type") != "file":
            return error_payload(f"路径不是文件（可能是目录）: {path}", 400)
        text = _decode_file_content(payload)
        truncated = False
        limit = max(1000, min(int(max_chars) if max_chars else 60000, 500000))
        if len(text) > limit:
            text = text[:limit] + "\n\n…(已截断)"
            truncated = True
        return {
            "code": 200,
            "message": "success",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "repo": repo,
                "branch": branch,
                "path": path,
                "content": text,
                "truncated": truncated,
                "encoding": "utf-8",
            },
        }

    @safe_tool(
        mcp,
        name="list_github_mybook_directory",
        description=(
            "列出 GitHub mybook 仓库中记忆目录下的文件与子目录（相对路径，默认记忆前缀根目录）。"
            "用于查找已有记忆文件名后再读取。"
        ),
    )
    def list_github_mybook_directory(
        relative_path: str = "",
    ) -> Dict[str, Any]:
        token = _github_token()
        if not token:
            return error_payload("未配置 AI_GITHUB_TOKEN，无法访问 GitHub。", 503)
        sub = (relative_path or "").strip().replace("\\", "/").strip("/")
        if sub and (".." in sub.split("/")):
            return error_payload("relative_path 不合法", 400)
        prefix = _memory_prefix()
        if sub:
            path = f"{prefix}/{sub}" if prefix else sub
        else:
            path = prefix or ""
        if not path:
            return error_payload("未配置 AI_GITHUB_MEMORY_PREFIX 且路径为空", 400)

        repo = _normalize_owner_repo(_github_repo())
        branch = _github_branch()
        r = _contents_get(repo, path, branch, token)
        if r.status_code == 404:
            return error_payload(f"路径不存在: {path}", 404)
        if r.status_code != 200:
            return error_payload(f"列出目录失败: HTTP {r.status_code} {r.text[:500]}", 502)
        data = r.json()
        items: List[Dict[str, Any]] = []
        if isinstance(data, list):
            for it in data:
                if not isinstance(it, dict):
                    continue
                items.append(
                    {
                        "name": it.get("name"),
                        "path": it.get("path"),
                        "type": it.get("type"),
                        "size": it.get("size"),
                    }
                )
        elif isinstance(data, dict) and data.get("type") == "file":
            items.append(
                {
                    "name": data.get("name"),
                    "path": data.get("path"),
                    "type": "file",
                    "size": data.get("size"),
                }
            )
        return {
            "code": 200,
            "message": "success",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "repo": repo,
                "branch": branch,
                "path": path,
                "items": items,
            },
        }
