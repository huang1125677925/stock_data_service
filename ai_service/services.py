import json
import logging
import os
import asyncio
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict
import aiohttp

from django.conf import settings
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
import traceback

from mcp_service.server import create_server

logger = logging.getLogger(__name__)

# Initialize MCP Server globally
mcp_server = create_server()

class ToolRoute(TypedDict):
    source: str
    name: str


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
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(self.url, json=payload) as response:
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
        获取 Tavily MCP 可用工具列表。
        参数:
            无。
        返回值:
            工具元数据列表，每项包含 name、description、inputSchema。
        异常:
            RuntimeError: 当远程请求失败时抛出。
        """
        if not self.enabled:
            return []
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
        return [t for t in normalized if t["name"]]

    async def call_tool(self, name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        调用 Tavily MCP 指定工具。
        参数:
            name: 工具名称。
            args: 工具参数对象。
        返回值:
            MCP tools/call 的 result 对象。
        异常:
            RuntimeError: 当远程请求失败时抛出。
        """
        return await self._request("tools/call", {"name": name, "arguments": args or {}})


class AiAgentService:
    def __init__(self):
        """
        初始化 AI Agent 服务与本地/远程 MCP 配置。
        参数:
            无。
        返回值:
            无。
        异常:
            无，初始化异常会在后续调用阶段暴露。
        """
        self.api_key = getattr(settings, "DEEPSEEK_API_KEY", None) or "sk-901c17c669a241f098b25144957667ec"
        self.base_url = getattr(settings, "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        self.model_name = getattr(settings, "DEEPSEEK_MODEL_NAME", "deepseek-chat")
        self.system_prompt = getattr(
            settings,
            "AI_SYSTEM_PROMPT",
            "你是一个专业的金融分析师，擅长对结构化数据进行分析并给出简洁结论。",
        )
        self.tool_policy_prompt = getattr(
            settings,
            "AI_TOOL_POLICY_PROMPT",
            (
                "工具使用策略：\n"
                "1) 遇到用户问题时，先判断是否可由 tushare 相关工具回答，能回答就必须优先调用 tushare 工具。\n"
                "2) 仅当 tushare 工具不存在对应能力或返回信息不足时，才调用 Tavily 联网工具补充。\n"
                "3) 回答时优先基于工具结果，不要凭空编造数据。"
            ),
        )
        self.tavily_mcp_url = getattr(
            settings,
            "TAVILY_MCP_URL",
            "https://mcp.tavily.com/mcp/?tavilyApiKey=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",
        )
        self.tavily_mcp_enabled = getattr(settings, "TAVILY_MCP_ENABLED", True)
        self.default_prompt = getattr(
            settings,
            "AI_DEFAULT_PROMPT",
            "请根据以下数据进行分析，输出简洁的中文结果：\n{data}",
        )
        
        self.prompts_file = os.path.join(os.path.dirname(__file__), "prompts.json")
        self.prompts_map = self._load_active_prompts()
        self.tavily_mcp_client = TavilyMCPClient(
            url=self.tavily_mcp_url,
            enabled=self.tavily_mcp_enabled,
            timeout_seconds=getattr(settings, "TAVILY_MCP_TIMEOUT_SECONDS", 30),
        )
        self.agent = self._build_agent()

    def _load_active_prompts(self) -> Dict[str, Any]:
        """Load active prompts into a map for quick access during analysis."""
        try:
            if not os.path.exists(self.prompts_file):
                return {}
            with open(self.prompts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    item["interface_name"]: item 
                    for item in data.get("prompts", []) 
                    if item.get("is_active")
                }
        except Exception as e:
            logger.error(f"Failed to load prompts: {e}")
            return {}

    def _build_agent(self):
        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY not configured, agent will not work.")
            return None

        llm = ChatOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model_name,
            temperature=0.3,
        )

        # Create agent using the new create_agent function
        return create_agent(
            model=llm,
            tools=[],
            system_prompt=self._build_chat_system_prompt()
        )

    def _build_chat_system_prompt(self) -> str:
        """
        构建聊天场景使用的系统提示词。
        参数:
            无。
        返回值:
            合并后的系统提示词字符串。
        异常:
            无。
        """
        return f"{self.system_prompt}\n\n{self.tool_policy_prompt}"

    def _to_safe_tool_name(self, name: str) -> str:
        """
        将任意工具名转换为 OpenAI function name 兼容格式。
        参数:
            name: 原始工具名。
        返回值:
            仅包含字母数字下划线的安全工具名。
        异常:
            无。
        """
        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        safe_name = re.sub(r"_+", "_", safe_name).strip("_")
        if not safe_name:
            safe_name = "tool"
        if safe_name[0].isdigit():
            safe_name = f"tool_{safe_name}"
        return safe_name

    def _build_tools_payload(
        self, local_tools: List[Any], tavily_tools: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], Dict[str, ToolRoute]]:
        """
        组装模型可调用的工具清单，并建立工具路由映射。
        参数:
            local_tools: 本地 MCP 工具列表。
            tavily_tools: Tavily MCP 工具列表。
        返回值:
            (openai_tools, tool_route_map) 二元组。
        异常:
            无，异常由调用方控制。
        """
        openai_tools: List[Dict[str, Any]] = []
        tool_route_map: Dict[str, ToolRoute] = {}
        used_safe_names = set()

        combined_tools: List[tuple[str, str, str, Dict[str, Any]]] = []
        for t in local_tools:
            combined_tools.append(
                (
                    "local",
                    getattr(t, "name", ""),
                    getattr(t, "description", "") or "",
                    getattr(t, "inputSchema", None) or {"type": "object", "properties": {}},
                )
            )
        for t in tavily_tools:
            combined_tools.append(
                (
                    "tavily",
                    t.get("name", ""),
                    t.get("description", "") or "",
                    t.get("inputSchema") or {"type": "object", "properties": {}},
                )
            )

        for source, tool_name, description, input_schema in combined_tools:
            if not tool_name:
                continue
            safe_name_base = self._to_safe_tool_name(tool_name)
            safe_name = safe_name_base
            index = 1
            while safe_name in used_safe_names:
                index += 1
                safe_name = f"{safe_name_base}_{index}"
            used_safe_names.add(safe_name)
            tool_route_map[safe_name] = {"source": source, "name": tool_name}
            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": safe_name,
                        "description": description,
                        "parameters": input_schema,
                    },
                }
            )
        return openai_tools, tool_route_map

    async def _call_tool_by_route(self, route: ToolRoute, args: Dict[str, Any]) -> Any:
        """
        按路由信息调用本地或 Tavily 工具。
        参数:
            route: 工具路由，包含 source 与 name。
            args: 工具参数对象。
        返回值:
            工具原始返回结果。
        异常:
            Exception: 当工具执行失败时抛出具体异常。
        """
        if route["source"] == "tavily":
            return await self.tavily_mcp_client.call_tool(route["name"], args)
        return await mcp_server.call_tool(route["name"], args)

    def _extract_tool_result_text(self, tool_result: Any) -> str:
        """
        统一提取工具返回内容为文本，兼容本地 MCP 与 Tavily MCP。
        参数:
            tool_result: 工具返回对象。
        返回值:
            适合注入上下文与前端展示的文本结果。
        异常:
            无，异常由上游调用流程处理。
        """
        if isinstance(tool_result, dict):
            content = tool_result.get("content")
            if isinstance(content, list):
                text_parts: List[str] = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text" and item.get("text"):
                            text_parts.append(str(item["text"]))
                        elif "text" in item:
                            text_parts.append(str(item["text"]))
                if text_parts:
                    return "\n".join(text_parts)
            if "result" in tool_result:
                return json.dumps(tool_result["result"], ensure_ascii=False)
            return json.dumps(tool_result, ensure_ascii=False)

        if (
            isinstance(tool_result, tuple)
            and tool_result
            and isinstance(tool_result[0], list)
            and len(tool_result[0]) > 0
            and hasattr(tool_result[0][0], "text")
        ):
            return str(tool_result[0][0].text)
        return str(tool_result)

    def _format_input_data(self, input_data: Any) -> str:
        if isinstance(input_data, str):
            return input_data
        return json.dumps(input_data, ensure_ascii=False)

    def resolve_prompt(self, interface_name: str, input_data: Any):
        # Refresh prompts map in case file changed
        self.prompts_map = self._load_active_prompts()
        
        config = self.prompts_map.get(interface_name)
        template = config["prompt_template"] if config else self.default_prompt
        data_text = self._format_input_data(input_data)
        
        if "{data}" in template:
            prompt = template.format(data=data_text)
        else:
            prompt = f"{template}\n{data_text}"
            
        return prompt, "configured" if config else "default"

    def analyze(self, interface_name: str, input_data: Any):
        if not self.agent:
             raise ValueError("Agent not initialized (check API key)")

        prompt_text, source = self.resolve_prompt(interface_name, input_data)
        
        try:
            inputs = {"messages": [{"role": "user", "content": prompt_text}]}
            result = self.agent.invoke(inputs)
            
            # result is the final state, containing 'messages'
            messages = result.get("messages", [])
            if not messages:
                return "", prompt_text, source
                
            last_message = messages[-1]
            # Handle different message types if needed, but usually it's AIMessage or ToolMessage
            content = getattr(last_message, "content", str(last_message))
            
            return content, prompt_text, source
        except Exception as e:
            logger.error(f"Agent analysis failed: {e}")
            raise e

    async def chat_stream_generator(self, messages_data: List[Dict]):
        """
        根据设计图中的交互逻辑，与本地 MCP 和 Tavily MCP 结合并返回 SSE 数据流。
        参数:
            messages_data: 对话消息列表，格式为 [{"role": "...", "content": "..."}]。
        返回值:
            异步生成器，按 SSE 格式产出 text、status、tool_card、done、error 事件。
        异常:
            异常不会向外抛出，统一转换为 error 事件返回给调用方。
        """
        try:
            local_tools = await mcp_server.list_tools()
            tavily_tools: List[Dict[str, Any]] = []
            if self.tavily_mcp_enabled:
                try:
                    tavily_tools = await self.tavily_mcp_client.list_tools()
                except Exception as tavily_error:
                    logger.warning(f"Failed to list Tavily MCP tools: {tavily_error}")

            openai_tools, tool_route_map = self._build_tools_payload(local_tools, tavily_tools)

            messages = []
            messages.append(SystemMessage(content=self._build_chat_system_prompt()))
            for m in messages_data:
                if m["role"] == "user":
                    messages.append(HumanMessage(content=m["content"]))
                elif m["role"] == "assistant":
                    messages.append(AIMessage(content=m["content"]))
                elif m["role"] == "tool":
                    messages.append(ToolMessage(content=m["content"], tool_call_id=m.get("tool_call_id", "")))

            llm = ChatOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model_name,
                temperature=0.3,
            )
            
            if openai_tools:
                llm = llm.bind_tools(openai_tools)
            
            rounds = 0
            while rounds < 20:
                rounds += 1
                
                is_tool_call = False
                accumulated_message = None
                
                async for chunk in llm.astream(messages):
                    if accumulated_message is None:
                        accumulated_message = chunk
                    else:
                        accumulated_message += chunk
                        
                    if chunk.tool_call_chunks:
                        is_tool_call = True
                        
                    if not is_tool_call and chunk.content:
                        yield f"data: {json.dumps({'type': 'text', 'content': chunk.content}, ensure_ascii=False)}\n\n"

                if is_tool_call and accumulated_message.tool_calls:
                    for tc in accumulated_message.tool_calls:
                        safe_tool_name = tc["name"]
                        route = tool_route_map.get(safe_tool_name, {"source": "local", "name": safe_tool_name})
                        real_tool_name = route["name"]
                        source_label = "联网" if route["source"] == "tavily" else "本地"
                        yield f"data: {json.dumps({'type': 'status', 'content': f'正在调用{source_label}工具 {real_tool_name}...'}, ensure_ascii=False)}\n\n"
                    
                    messages.append(accumulated_message)
                    
                    resolved_tool_calls: List[tuple[Dict[str, Any], ToolRoute]] = []
                    for tc in accumulated_message.tool_calls:
                        safe_tool_name = tc["name"]
                        route = tool_route_map.get(safe_tool_name, {"source": "local", "name": safe_tool_name})
                        resolved_tool_calls.append((tc, route))

                    tool_tasks = [
                        self._call_tool_by_route(route, tc.get("args", {}))
                        for tc, route in resolved_tool_calls
                    ]
                    tool_results = await asyncio.gather(*tool_tasks, return_exceptions=True)

                    for (tc, route), result in zip(resolved_tool_calls, tool_results):
                        real_tool_name = route["name"]
                        tool_call_id = tc["id"]
                        if isinstance(result, Exception):
                            logger.error(f"Tool {real_tool_name} execution failed: {result}")
                            messages.append(ToolMessage(content=f"Error executing tool {real_tool_name}: {str(result)}", tool_call_id=tool_call_id))
                            continue

                        tool_result_text = self._extract_tool_result_text(result)

                        if len(tool_result_text) > 8000:
                            tool_result_text = tool_result_text[:8000] + "\n...(由于长度限制已截断)"

                        messages.append(ToolMessage(content=tool_result_text, tool_call_id=tool_call_id))
                        yield f"data: {json.dumps({'type': 'tool_card', 'tool_name': real_tool_name, 'result': tool_result_text}, ensure_ascii=False)}\n\n"
                    
                    continue
                else:
                    break
                    
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"Chat stream failed: {e}\n{traceback.format_exc()}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    # CRUD methods for Views
    def get_all_prompts_list(self) -> List[Dict]:
        try:
            if not os.path.exists(self.prompts_file):
                return []
            with open(self.prompts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("prompts", [])
        except Exception as e:
            logger.error(f"Failed to read prompts file: {e}")
            return []

    def save_prompt_config(self, interface_name: str, prompt_template: str, is_active: bool):
        prompts = self.get_all_prompts_list()
        now_str = datetime.now().isoformat()
        
        found = False
        target_config = None
        
        for p in prompts:
            if p["interface_name"] == interface_name:
                p["prompt_template"] = prompt_template
                p["is_active"] = is_active
                p["updated_at"] = now_str
                target_config = p
                found = True
                break
        
        if not found:
            target_config = {
                "interface_name": interface_name,
                "prompt_template": prompt_template,
                "is_active": is_active,
                "created_at": now_str,
                "updated_at": now_str
            }
            prompts.append(target_config)
            
        self._write_prompts_file(prompts)
        self.prompts_map = self._load_active_prompts() # Refresh cache
        return target_config

    def delete_prompt_config(self, interface_name: str) -> bool:
        prompts = self.get_all_prompts_list()
        initial_len = len(prompts)
        prompts = [p for p in prompts if p["interface_name"] != interface_name]
        
        if len(prompts) < initial_len:
            self._write_prompts_file(prompts)
            self.prompts_map = self._load_active_prompts()
            return True
        return False

    def get_prompt_config(self, interface_name: str):
        prompts = self.get_all_prompts_list()
        for p in prompts:
            if p["interface_name"] == interface_name:
                return p
        return None

    def _write_prompts_file(self, prompts_list: List[Dict]):
        try:
            with open(self.prompts_file, "w", encoding="utf-8") as f:
                json.dump({"prompts": prompts_list}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to write prompts file: {e}")
            raise e


ai_agent_service = AiAgentService()
