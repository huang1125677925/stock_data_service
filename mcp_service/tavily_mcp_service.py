import json
import logging
import uuid
from urllib.parse import parse_qs, urlparse

from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

# MCP 无法获取工具时的默认 tavily_search 工具定义（用于 REST API fallback）
TAVILY_SEARCH_FALLBACK_TOOL = {
    "name": "tavily_search",
    "description": "Search the web for real-time information, news, and general knowledge.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
            "max_results": {"type": "integer", "description": "Max results to return", "default": 5},
        },
        "required": ["query"],
    },
}


class TavilyMCPClient:
    def __init__(self, url: str, enabled: bool = True, timeout_seconds: int = 30):
        """
        初始化 Tavily MCP 远程客户端。
        参数:
            url: Tavily MCP 的 HTTP 端点地址。
            enabled: 是否启用远程联网 MCP。
            timeout_seconds: 单次请求超时时间（秒）。
        返回值:
            无。
        异常:
            无，初始化阶段不发起网络请求。
        """
        self.url = url
        self.enabled = enabled and bool(url)
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._api_key: Optional[str] = self._extract_api_key_from_url(url)
        self._use_rest_fallback = False  # MCP tools/list 返回空时设为 True

    @staticmethod
    def _extract_api_key_from_url(url: str) -> Optional[str]:
        """从 MCP URL 的 tavilyApiKey 参数提取 API key"""
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            key = params.get("tavilyApiKey", [None])[0]
            return key if key else None
        except Exception:
            return None

    async def _request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        通过 JSON-RPC 调用 Tavily MCP 方法。
        参数:
            method: MCP 方法名，例如 tools/list、tools/call。
            params: JSON-RPC 参数对象。
        返回值:
            MCP 响应中的 result 字段。
        异常:
            RuntimeError: 当 HTTP 请求失败或 MCP 返回 error 时抛出。
        """
        if not self.enabled:
            raise RuntimeError("Tavily MCP is disabled")

        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params or {},
        }
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(self.url, json=payload, headers=headers) as response:
                text = await response.text()
                if response.status >= 400:
                    raise RuntimeError(f"Tavily MCP HTTP {response.status}: {text}")
                try:
                    data = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(f"Tavily MCP invalid JSON response: {text}") from exc

        if isinstance(data, dict) and data.get("error"):
            raise RuntimeError(f"Tavily MCP error: {data['error']}")
        if not isinstance(data, dict) or "result" not in data:
            raise RuntimeError(f"Tavily MCP unexpected response: {data}")
        return data["result"]

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        获取 Tavily MCP 可用工具列表。若 MCP 返回空则使用 REST API fallback 的默认工具。
        参数:
            无。
        返回值:
            工具元数据列表，每项包含 name、description、inputSchema。
        异常:
            无，MCP 失败时返回 fallback 工具。
        """
        if not self.enabled:
            return []
        try:
            result = await self._request("tools/list")
            tools = result.get("tools", [])
            normalized: List[Dict[str, Any]] = []
            for tool in tools:
                normalized.append(
                    {
                        "name": tool.get("name", ""),
                        "description": tool.get("description", ""),
                        "inputSchema": tool.get("inputSchema") or {"type": "object", "properties": {}},
                    }
                )
            out = [t for t in normalized if t["name"]]
            if not out:
                self._use_rest_fallback = True
                logger.warning("Tavily MCP tools/list returned empty, using REST API fallback")
                return [TAVILY_SEARCH_FALLBACK_TOOL.copy()]
            self._use_rest_fallback = False
            return out
        except Exception as e:
            logger.warning(f"Tavily MCP list_tools failed: {e}, using REST API fallback")
            self._use_rest_fallback = True
            return [TAVILY_SEARCH_FALLBACK_TOOL.copy()]

    async def _call_tavily_rest_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        通过 Tavily REST API 直接调用搜索（当 MCP 不可用时使用）。
        """
        if not self._api_key:
            raise RuntimeError("Tavily API key not found in URL, cannot use REST fallback")
        api_url = "https://api.tavily.com/search"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }
        payload = {
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
            "include_answer": True,
        }
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(api_url, json=payload, headers=headers) as resp:
                text = await resp.text()
                if resp.status >= 400:
                    raise RuntimeError(f"Tavily REST API HTTP {resp.status}: {text}")
                data = json.loads(text)
        # 转换为与 MCP tools/call 兼容的格式
        results = data.get("results", [])
        answer = data.get("answer", "")
        content_parts = [f"Answer: {answer}"] if answer else []
        for r in results:
            title = r.get("title", "")
            url_link = r.get("url", "")
            content = r.get("content", "")[:500]
            content_parts.append(f"\n\n### {title}\n{content}\nSource: {url_link}")
        text_content = "\n".join(content_parts) if content_parts else json.dumps(data, ensure_ascii=False)
        return {
            "content": [{"type": "text", "text": text_content}],
        }

    async def call_tool(self, name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        调用 Tavily 工具。优先使用 MCP；若启用了 REST fallback 或 MCP 失败，则使用 REST API。
        参数:
            name: 工具名称。
            args: 工具参数对象。
        返回值:
            与 MCP tools/call 兼容的 result 对象。
        异常:
            RuntimeError: 当调用失败时抛出。
        """
        args = args or {}
        query = args.get("query") or args.get("input") or str(args)
        if isinstance(query, dict):
            query = json.dumps(query, ensure_ascii=False)

        if self._use_rest_fallback or name in ("tavily_search", "tavily-search"):
            try:
                return await self._call_tavily_rest_search(
                    query=query,
                    max_results=int(args.get("max_results", 5)),
                )
            except Exception as e:
                raise RuntimeError(f"Tavily REST fallback failed: {e}") from e

        try:
            return await self._request("tools/call", {"name": name, "arguments": args})
        except Exception as mcp_err:
            if name in ("tavily_search", "tavily-search") and self._api_key:
                logger.warning(f"Tavily MCP call failed: {mcp_err}, trying REST fallback")
                return await self._call_tavily_rest_search(query=query, max_results=int(args.get("max_results", 5)))
            raise


_tavily_mcp_client: Optional[TavilyMCPClient] = None


def register_tavily_mcp_client(url: str, enabled: bool = True, timeout_seconds: int = 30) -> TavilyMCPClient:
    """
    注册并返回 Tavily MCP 客户端实例。
    参数:
        url: Tavily MCP 的 HTTP 端点地址。
        enabled: 是否启用远程联网 MCP。
        timeout_seconds: 单次请求超时时间（秒）。
    返回值:
        已注册的 TavilyMCPClient 实例。
    异常:
        无，初始化阶段不发起网络请求。
    """
    global _tavily_mcp_client
    _tavily_mcp_client = TavilyMCPClient(url=url, enabled=enabled, timeout_seconds=timeout_seconds)
    return _tavily_mcp_client


def get_tavily_mcp_client() -> Optional[TavilyMCPClient]:
    """
    获取当前已注册的 Tavily MCP 客户端实例。
    参数:
        无。
    返回值:
        TavilyMCPClient 实例；若尚未注册则返回 None。
    异常:
        无。
    """
    return _tavily_mcp_client
