from __future__ import annotations

import base64
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests


class GitHubMarkdownService:
    """
    GitHub Markdown 文档只读服务。

    用于给前端展示指定仓库中的 Markdown 文件目录和文件内容。
    """

    def __init__(
        self,
        repo: Optional[str] = None,
        branch: Optional[str] = None,
        token: Optional[str] = None,
        request_get=None,
    ):
        self.repo = self.normalize_repo(repo or self._setting("AI_GITHUB_SYNC_REPO", "huang1125677925/mybook"))
        self.branch = branch or self._setting("AI_GITHUB_SYNC_BRANCH", "main")
        self.token = token or self._setting("AI_GITHUB_TOKEN", "") or self._setting("GITHUB_TOKEN", "")
        self.request_get = request_get or requests.get

    def list_directory(self, path: str = "") -> Dict[str, Any]:
        safe_path = self.validate_path(path, allow_empty=True)
        payload = self._github_get_json(self._contents_url(safe_path), params={"ref": self.branch})

        items: List[Dict[str, Any]] = []
        raw_items = payload if isinstance(payload, list) else [payload]
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            item_path = item.get("path") or ""
            items.append({
                "name": item.get("name"),
                "path": item_path,
                "type": item_type,
                "size": item.get("size"),
                "sha": item.get("sha"),
                "download_url": item.get("download_url"),
                "html_url": item.get("html_url"),
                "is_markdown": self._is_markdown_path(item_path) if item_type == "file" else False,
            })

        items.sort(key=lambda item: (item.get("type") != "dir", item.get("name") or ""))
        return {
            "repo": self.repo,
            "branch": self.branch,
            "path": safe_path,
            "count": len(items),
            "items": items,
            "query_time": datetime.now().isoformat(),
        }

    def list_markdown_files(self, prefix: str = "", recursive: bool = True) -> Dict[str, Any]:
        safe_prefix = self.validate_path(prefix, allow_empty=True).strip("/")
        if recursive:
            payload = self._github_get_json(self._tree_url(), params={"recursive": "1"})
            tree = payload.get("tree", []) if isinstance(payload, dict) else []
            files = []
            for item in tree:
                if not isinstance(item, dict) or item.get("type") != "blob":
                    continue
                path = item.get("path") or ""
                if safe_prefix and not path.startswith(f"{safe_prefix}/") and path != safe_prefix:
                    continue
                if not self._is_markdown_path(path):
                    continue
                files.append({
                    "name": path.rsplit("/", 1)[-1],
                    "path": path,
                    "size": item.get("size"),
                    "sha": item.get("sha"),
                    "html_url": f"https://github.com/{self.repo}/blob/{quote(self.branch, safe='')}/{quote(path, safe='/')}",
                })
        else:
            data = self.list_directory(safe_prefix)
            files = [
                {
                    "name": item.get("name"),
                    "path": item.get("path"),
                    "size": item.get("size"),
                    "sha": item.get("sha"),
                    "html_url": item.get("html_url"),
                }
                for item in data.get("items", [])
                if item.get("type") == "file" and item.get("is_markdown")
            ]

        files.sort(key=lambda item: item.get("path") or "")
        return {
            "repo": self.repo,
            "branch": self.branch,
            "prefix": safe_prefix,
            "recursive": recursive,
            "count": len(files),
            "files": files,
            "query_time": datetime.now().isoformat(),
        }

    def get_markdown_content(self, path: str, max_chars: int = 200000) -> Dict[str, Any]:
        safe_path = self.validate_path(path, allow_empty=False)
        if not self._is_markdown_path(safe_path):
            raise ValueError("path 必须指向 .md 或 .markdown 文件")

        payload = self._github_get_json(self._contents_url(safe_path), params={"ref": self.branch})
        if not isinstance(payload, dict) or payload.get("type") != "file":
            raise ValueError("path 不是文件")

        content = self._decode_content(payload)
        safe_limit = max(1000, min(int(max_chars or 200000), 500000))
        truncated = False
        if len(content) > safe_limit:
            content = content[:safe_limit]
            truncated = True

        return {
            "repo": self.repo,
            "branch": self.branch,
            "path": safe_path,
            "name": payload.get("name"),
            "sha": payload.get("sha"),
            "size": payload.get("size"),
            "encoding": "utf-8",
            "content": content,
            "truncated": truncated,
            "html_url": payload.get("html_url"),
            "download_url": payload.get("download_url"),
            "query_time": datetime.now().isoformat(),
        }

    def _github_get_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        if not self.token:
            raise RuntimeError("未配置 AI_GITHUB_TOKEN 或 GITHUB_TOKEN")

        response = self.request_get(url, headers=self._headers(), params=params or {}, timeout=20)
        if response.status_code == 404:
            raise RuntimeError("GitHub 路径不存在或仓库不可访问")
        if response.status_code >= 400:
            raise RuntimeError(f"GitHub API 调用失败: HTTP {response.status_code}")
        return response.json()

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _contents_url(self, path: str) -> str:
        base = f"https://api.github.com/repos/{self.repo}/contents"
        safe_path = path.strip("/")
        if not safe_path:
            return base
        encoded_path = "/".join(quote(part, safe="") for part in safe_path.split("/"))
        return f"{base}/{encoded_path}"

    def _tree_url(self) -> str:
        branch = quote(self.branch, safe="")
        return f"https://api.github.com/repos/{self.repo}/git/trees/{branch}"

    @staticmethod
    def normalize_repo(repo: str) -> str:
        value = (repo or "").strip().strip("/")
        if value.startswith("https://github.com/"):
            value = value.replace("https://github.com/", "", 1).strip("/")
        if value.endswith(".git"):
            value = value[:-4]
        if "/" not in value:
            raise ValueError("GitHub 仓库配置格式错误，应为 owner/repo 或 https://github.com/owner/repo")
        return value

    @staticmethod
    def validate_path(path: str, allow_empty: bool = False) -> str:
        value = (path or "").strip().replace("\\", "/").strip("/")
        if not value and allow_empty:
            return ""
        if not value:
            raise ValueError("path 不能为空")
        if "\x00" in value or ".." in value.split("/"):
            raise ValueError("path 不合法")
        return value

    @staticmethod
    def _is_markdown_path(path: str) -> bool:
        lower = (path or "").lower()
        return lower.endswith(".md") or lower.endswith(".markdown")

    @staticmethod
    def _decode_content(payload: Dict[str, Any]) -> str:
        encoded = payload.get("content") or ""
        if not isinstance(encoded, str):
            return ""
        raw = base64.b64decode(encoded.encode("utf-8"))
        return raw.decode("utf-8", errors="replace")

    @staticmethod
    def _setting(name: str, default: str = "") -> str:
        try:
            from django.conf import settings

            value = getattr(settings, name, None)
            if value:
                return str(value).strip()
        except Exception:
            pass
        return os.environ.get(name, default).strip()


github_markdown_service = GitHubMarkdownService()
