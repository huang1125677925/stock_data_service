import json
import logging
import os
import asyncio
import re
import uuid
import base64
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from django.conf import settings
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
import traceback
import requests

from mcp_service.server import create_server

from ai_service.model_config import get_active_model_config
from ai_service.deepseek_langchain_patch import apply_deepseek_reasoning_patch

logger = logging.getLogger(__name__)

apply_deepseek_reasoning_patch()

# Initialize MCP Server globally
mcp_server = create_server()

class ToolRoute(TypedDict):
    source: str
    name: str


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
        model_config = get_active_model_config()
        self._api_key_optional = bool(model_config.get("api_key_optional"))
        raw_key = model_config.get("api_key")
        if self._api_key_optional:
            # langchain-openai 要求传入非 None 的 api_key；公开 Qwen2API 用空字符串即可
            self.api_key = raw_key if raw_key else ""
        else:
            self.api_key = raw_key or None
        self.base_url = model_config["base_url"]
        self.model_name = model_config["model_name"]
        self.model_kwargs = model_config.get("model_kwargs") or {}
        self.extra_body = model_config.get("extra_body")
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
                "1) 使用 tushare 相关工具回答A股股票行情、财务数据、交易数据、上市公司信息等问题。\n"
                "2) 回答时优先基于工具返回的结果，不要凭空编造数据。\n"
                "3) 如工具无法满足用户需求，请如实说明能力范围，仅支持股票相关数据查询。\n"
                "4) 每次调用工具时，必须严格依照该工具的说明（description）与参数模式（parameters / JSON Schema）"
                "传参：使用文档中给出的参数名与取值含义，必填参数一律提供；可选参数按问题需要选用；"
                "日期、股票代码、交易所等格式与工具说明保持一致，禁止臆造未在 Schema 中出现的参数名。\n"
                "5) 若单次工具返回表明仍有更多数据（例如结果中出现 has_more 为 true、next_offset、remaining、"
                "total_count 与当前返回条数不一致等分页信息），必须在其余查询条件不变的前提下，"
                "使用 next_offset 或递增 offset 等方式再次调用同一工具，重复直至已取全或 has_more 为 false，"
                "再基于完整数据作答；不得在未翻页取全的情况下声称已覆盖全部数据。"
            ),
        )
        self.default_prompt = getattr(
            settings,
            "AI_DEFAULT_PROMPT",
            "请根据以下数据进行分析，输出简洁的中文结果：\n{data}",
        )
        
        self.prompts_file = os.path.join(os.path.dirname(__file__), "prompts.json")
        self.prompts_map = self._load_active_prompts()
        self.chat_tool_mode = getattr(
            settings,
            "AI_CHAT_TOOL_MODE",
            "native",
        )
        if isinstance(self.chat_tool_mode, str):
            self.chat_tool_mode = self.chat_tool_mode.strip().lower()
        else:
            self.chat_tool_mode = "native"
        self.model_provider = getattr(settings, "AI_MODEL_PROVIDER", "deepseek")
        if isinstance(self.model_provider, str):
            self.model_provider = self.model_provider.strip().lower()
        else:
            self.model_provider = "deepseek"
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
        if not self._api_key_optional and not self.api_key:
            logger.warning("AI model API key not configured, agent will not work.")
            return None

        llm = ChatOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model_name,
            temperature=0.3,
            model_kwargs=self.model_kwargs,
            extra_body=self.extra_body,
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
        prompt = f"{self.system_prompt}\n\n{self.tool_policy_prompt}"
        
        # Load skill prompts dynamically per request
        from ai_service.skill_manager import skill_manager
        skill_prompts = skill_manager.get_all_skills_prompts()
        if skill_prompts:
            prompt += f"\n\n{skill_prompts}"
            
        return prompt

    def _build_stream_system_prompt(
        self,
        openai_tools: List[Dict[str, Any]],
        json_protocol: bool,
    ) -> str:
        base = f"{self.system_prompt}\n\n{self.tool_policy_prompt}"
        
        from ai_service.skill_manager import skill_manager
        skill_prompts = skill_manager.get_all_skills_prompts()
        if skill_prompts:
            base += f"\n\n{skill_prompts}"
            
        if not json_protocol or not openai_tools:
            return base
        catalog_lines: List[str] = [
            "## 可用工具（JSON 中的 name 必须与下列工具名完全一致）",
        ]
        for spec in openai_tools:
            fn = spec["function"]
            catalog_lines.append(
                f"### {fn['name']}\n{fn.get('description') or ''}\n参数 JSON Schema:\n"
                f"{json.dumps(fn.get('parameters') or {}, ensure_ascii=False)}"
            )
        catalog = "\n".join(catalog_lines)
        instruction = (
            "\n\n## JSON 工具调用协议（当前模型网关不支持原生 function calling，必须使用本协议）\n"
            "需要查询数据时，请**仅**输出一个 Markdown 代码块（语言标记为 json），内容为单个 JSON 对象；"
            "代码块外不要输出其它文字。示例：\n"
            "```json\n"
            '{"tool_calls":[{"name":"工具名","arguments":{}}]}\n'
            "```\n"
            "可同时发起多个调用：`tool_calls` 为数组；`arguments` 须符合对应工具的 JSON Schema。\n"
            "不需要工具、信息已足够时，**不要**输出上述代码块，直接用自然语言回答用户。\n"
        )
        return base + instruction + "\n" + catalog

    def _extract_json_tool_payload(self, content: str) -> Optional[Any]:
        if not content or not str(content).strip():
            return None
        text = str(content).strip()
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if fence:
            text = fence.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        start = text.find("{")
        if start < 0:
            return None
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        return None
        return None

    def _resolve_tool_route(
        self, name: str, tool_route_map: Dict[str, ToolRoute]
    ) -> tuple[str, ToolRoute]:
        if name in tool_route_map:
            return name, tool_route_map[name]
        for safe_name, route in tool_route_map.items():
            if route["name"] == name:
                return safe_name, route
        return name, {"source": "local", "name": name}

    def _parse_json_protocol_tool_calls(
        self, payload: Any, tool_route_map: Dict[str, ToolRoute]
    ) -> Optional[List[Dict[str, Any]]]:
        if not isinstance(payload, dict):
            return None
        raw_items: List[Any] = []
        if "tool_calls" in payload:
            tc = payload["tool_calls"]
            if isinstance(tc, list):
                raw_items = tc
            else:
                return None
        elif "tool_call" in payload:
            raw_items = [payload["tool_call"]]
        elif "tool" in payload or "name" in payload:
            raw_items = [payload]
        else:
            return None
        out: List[Dict[str, Any]] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            raw_name = item.get("name") or item.get("tool")
            if not raw_name or not isinstance(raw_name, str):
                continue
            args = item.get("arguments")
            if args is None:
                args = item.get("args")
            if not isinstance(args, dict):
                args = {}
            safe_name, _route = self._resolve_tool_route(raw_name.strip(), tool_route_map)
            out.append(
                {
                    "name": safe_name,
                    "args": args,
                    "id": f"json_{uuid.uuid4().hex[:12]}",
                }
            )
        return out or None

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

    def _build_tools_payload(self, local_tools: List[Any]) -> tuple[List[Dict[str, Any]], Dict[str, ToolRoute]]:
        """
        组装模型可调用的工具清单，并建立工具路由映射（仅本地 tushare 工具）。
        参数:
            local_tools: 本地 MCP 工具列表。
        返回值:
            (openai_tools, tool_route_map) 二元组。
        异常:
            无，异常由调用方控制。
        """
        openai_tools: List[Dict[str, Any]] = []
        tool_route_map: Dict[str, ToolRoute] = {}
        used_safe_names = set()

        for t in local_tools:
            tool_name = getattr(t, "name", "")
            if not tool_name:
                continue
            description = getattr(t, "description", "") or ""
            input_schema = getattr(t, "inputSchema", None) or {"type": "object", "properties": {}}
            safe_name_base = self._to_safe_tool_name(tool_name)
            safe_name = safe_name_base
            index = 1
            while safe_name in used_safe_names:
                index += 1
                safe_name = f"{safe_name_base}_{index}"
            used_safe_names.add(safe_name)
            tool_route_map[safe_name] = {"source": "local", "name": tool_name}
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
        按路由信息调用本地工具。
        参数:
            route: 工具路由，包含 source 与 name。
            args: 工具参数对象。
        返回值:
            工具原始返回结果。
        异常:
            Exception: 当工具执行失败时抛出具体异常。
        """
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
        """
        使用配置的 Agent 对输入数据进行一次性分析并返回完整文本结果。
        参数:
            interface_name: 业务接口名，用于选择 prompt 模板。
            input_data: 输入数据（字符串或任意可 JSON 序列化对象）。
        返回值:
            (content, prompt_text, source) 三元组：
            - content: 最终回答文本；
            - prompt_text: 实际发送给模型的 prompt；
            - source: prompt 来源（configured/default）。
        异常:
            ValueError: 当 Agent 未初始化（例如缺少 API Key）时抛出。
            Exception: 当模型调用或解析失败时抛出原始异常。
        """
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
            try:
                question_text = prompt_text
                answer_text = str(content or "").strip()
                if answer_text:
                    self._schedule_github_sync(question_text=question_text, answer_text=answer_text)
            except Exception as e:
                logger.warning(f"GitHub sync scheduling skipped: {e}")

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
            # 首包尽快写出，避免反向代理/客户端长时间无数据而缓冲或超时
            yield ": stream-open\n\n"
            yield (
                f"data: {json.dumps({'type': 'status', 'content': '正在准备回复...'}, ensure_ascii=False)}\n\n"
            )
            local_tools = await mcp_server.list_tools()
            logger.info(f"Loaded {len(local_tools)} local MCP tools")
            openai_tools, tool_route_map = self._build_tools_payload(local_tools)

            # JSON 工具协议仅用于千问（qwen2api）；DeepSeek / 豆包始终走原生 bind_tools
            use_json_protocol = (
                self.chat_tool_mode == "json_protocol"
                and self.model_provider == "qwen2api"
            )
            messages = []
            messages.append(
                SystemMessage(
                    content=self._build_stream_system_prompt(
                        openai_tools, use_json_protocol
                    )
                )
            )
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
                model_kwargs=self.model_kwargs,
                extra_body=self.extra_body,
            )
            
            if openai_tools and not use_json_protocol:
                llm = llm.bind_tools(openai_tools)
            
            rounds = 0
            final_answer_text = ""
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

                json_parsed_calls: Optional[List[Dict[str, Any]]] = None
                if (
                    use_json_protocol
                    and openai_tools
                    and accumulated_message is not None
                    and not is_tool_call
                ):
                    raw_content = accumulated_message.content or ""
                    payload = self._extract_json_tool_payload(raw_content)
                    if payload is not None:
                        json_parsed_calls = self._parse_json_protocol_tool_calls(
                            payload, tool_route_map
                        )
                        if json_parsed_calls:
                            is_tool_call = True
                            tool_calls_lc = [
                                {
                                    "name": x["name"],
                                    "args": x["args"],
                                    "id": x["id"],
                                    "type": "tool_call",
                                }
                                for x in json_parsed_calls
                            ]
                            accumulated_message = AIMessage(
                                content="",
                                tool_calls=tool_calls_lc,
                            )

                if is_tool_call and accumulated_message.tool_calls:
                    for tc in accumulated_message.tool_calls:
                        safe_tool_name = tc["name"]
                        route = tool_route_map.get(safe_tool_name, {"source": "local", "name": safe_tool_name})
                        real_tool_name = route["name"]
                        yield f"data: {json.dumps({'type': 'status', 'content': f'正在调用本地工具 {real_tool_name}...'}, ensure_ascii=False)}\n\n"
                    
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

                        messages.append(ToolMessage(content=tool_result_text, tool_call_id=tool_call_id))
                        tool_args = tc.get("args") if isinstance(tc.get("args"), dict) else {}
                        yield f"data: {json.dumps({'type': 'tool_card', 'tool_name': real_tool_name, 'args': tool_args, 'result': tool_result_text}, ensure_ascii=False)}\n\n"
                    
                    continue
                else:
                    if accumulated_message is not None and not is_tool_call:
                        final_answer_text = str(accumulated_message.content or "").strip()
                    break

            try:
                question_text = self._extract_last_user_question(messages_data)
                if question_text and final_answer_text:
                    self._schedule_github_sync(question_text=question_text, answer_text=final_answer_text)
            except Exception as e:
                logger.warning(f"GitHub sync scheduling skipped: {e}")

            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"Chat stream failed: {e}\n{traceback.format_exc()}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    def _extract_last_user_question(self, messages_data: List[Dict[str, Any]]) -> str:
        """
        从对话消息列表中提取最后一条用户问题文本。
        参数:
            messages_data: 对话消息列表，元素包含 role 与 content 字段。
        返回值:
            最后一条 role=user 的 content（去除首尾空白）；若不存在则返回空字符串。
        异常:
            无。
        """
        for m in reversed(messages_data or []):
            if isinstance(m, dict) and m.get("role") == "user":
                return str(m.get("content") or "").strip()
        return ""

    def _schedule_github_sync(self, question_text: str, answer_text: str) -> None:
        """
        以异步任务方式触发 GitHub 仓库内容更新，避免阻塞主流程（尤其是 SSE 流式返回）。
        参数:
            question_text: 用户问题文本。
            answer_text: AI 最终回答文本。
        返回值:
            无。
        异常:
            无（内部捕获并记录日志）。
        """
        if not self._is_github_sync_enabled():
            logger.info("GitHub sync skipped: feature disabled or missing required config")
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                self._sync_answer_to_github(
                    question_text=question_text,
                    answer_text=answer_text,
                )
            )
        except RuntimeError:
            t = threading.Thread(
                target=self._sync_answer_to_github_blocking,
                kwargs={"question_text": question_text, "answer_text": answer_text},
                daemon=True,
            )
            t.start()

    def _is_github_sync_enabled(self) -> bool:
        """
        判断是否启用 GitHub 同步功能。
        参数:
            无。
        返回值:
            启用返回 True，否则返回 False。
        异常:
            无。
        """
        token = self._get_github_token()
        repo = self._get_github_repo()
        enabled = getattr(settings, "AI_GITHUB_SYNC_ENABLED", None)
        if enabled is None:
            enabled_env = os.getenv("AI_GITHUB_SYNC_ENABLED", "").strip().lower()
            if enabled_env:
                enabled = enabled_env in ("1", "true", "yes", "on")
            else:
                # 未显式配置开关时，只要存在 token 和 repo 就自动启用。
                enabled = bool(token and repo)
        return bool(enabled) and bool(token) and bool(repo)

    def _get_github_token(self) -> str:
        """
        获取用于 GitHub API 的访问令牌（不允许硬编码在代码中）。
        参数:
            无。
        返回值:
            token 字符串；若未配置则返回空字符串。
        异常:
            无。
        """
        token = getattr(settings, "AI_GITHUB_TOKEN", "") or ""
        if token:
            return str(token).strip()
        return os.getenv("GITHUB_TOKEN", "").strip()

    def _get_github_repo(self) -> str:
        """
        获取目标 GitHub 仓库标识（owner/repo）。
        参数:
            无。
        返回值:
            仓库标识字符串（例如 huang1125677925/mybook）；若未配置则返回空字符串。
        异常:
            无。
        """
        repo = getattr(settings, "AI_GITHUB_SYNC_REPO", "") or ""
        if repo:
            return str(repo).strip()
        repo = os.getenv("AI_GITHUB_SYNC_REPO", "").strip()
        if repo:
            return repo
        return "huang1125677925/mybook"

    def _get_github_branch(self) -> str:
        """
        获取写入目标分支名。
        参数:
            无。
        返回值:
            分支名，默认 main。
        异常:
            无。
        """
        branch = getattr(settings, "AI_GITHUB_SYNC_BRANCH", "") or ""
        branch = str(branch).strip() if branch else ""
        return branch or os.getenv("AI_GITHUB_SYNC_BRANCH", "").strip() or "main"

    def _get_github_path(self) -> str:
        """
        获取写入文件路径（仓库内相对路径）。
        参数:
            无。
        返回值:
            以日期渲染后的文件路径，默认 ai_answers/YYYY-MM-DD.md。
        异常:
            无。
        """
        template = getattr(settings, "AI_GITHUB_SYNC_PATH_TEMPLATE", "") or ""
        template = str(template).strip() if template else ""
        template = template or os.getenv("AI_GITHUB_SYNC_PATH_TEMPLATE", "").strip() or "ai_answers/{date}.md"
        date_str = datetime.now().strftime("%Y-%m-%d")
        try:
            return template.format(date=date_str)
        except Exception:
            return f"ai_answers/{date_str}.md"

    def _format_answer_markdown(self, question_text: str, answer_text: str) -> str:
        """
        将一次问答格式化为 Markdown 段落，便于在仓库中按天累计保存。
        参数:
            question_text: 用户问题文本。
            answer_text: AI 最终回答文本。
        返回值:
            Markdown 字符串（包含时间、唯一标识、问题与回答）。
        异常:
            无。
        """
        now = datetime.now()
        ts = now.strftime("%H:%M:%S")
        entry_id = uuid.uuid4().hex[:8]
        q = (question_text or "").strip()
        a = (answer_text or "").strip()
        return (
            f"\n\n## {ts} {entry_id}\n\n"
            f"**Q:** {q}\n\n"
            f"**A:**\n\n{a}\n"
        )

    async def _sync_answer_to_github(self, question_text: str, answer_text: str) -> None:
        """
        异步将问答内容写入 GitHub 仓库（通过 Contents API 创建/更新文件）。
        参数:
            question_text: 用户问题文本。
            answer_text: AI 最终回答文本。
        返回值:
            无。
        异常:
            无（内部捕获并记录日志）。
        """
        repo = self._get_github_repo()
        token = self._get_github_token()
        branch = self._get_github_branch()
        path = self._get_github_path()
        block = self._format_answer_markdown(question_text=question_text, answer_text=answer_text)

        if not repo or not token or not path:
            return

        try:
            await asyncio.to_thread(
                self._github_upsert_markdown_file,
                repo,
                path,
                block,
                branch,
                token,
            )
        except Exception as e:
            logger.error(f"GitHub sync failed: {e}")

    def _sync_answer_to_github_blocking(self, question_text: str, answer_text: str) -> None:
        """
        在无事件循环的同步上下文中，将问答内容写入 GitHub 仓库（阻塞式，建议由后台线程调用）。
        参数:
            question_text: 用户问题文本。
            answer_text: AI 最终回答文本。
        返回值:
            无。
        异常:
            无（内部捕获并记录日志）。
        """
        repo = self._get_github_repo()
        token = self._get_github_token()
        branch = self._get_github_branch()
        path = self._get_github_path()
        block = self._format_answer_markdown(question_text=question_text, answer_text=answer_text)
        if not repo or not token or not path:
            return
        try:
            self._github_upsert_markdown_file(repo, path, block, branch, token)
        except Exception as e:
            logger.error(f"GitHub sync failed: {e}")

    def _github_upsert_markdown_file(
        self,
        repo: str,
        path: str,
        append_block: str,
        branch: str,
        token: str,
    ) -> None:
        """
        使用 GitHub Contents API 将 Markdown 片段追加写入文件（不存在则创建）。
        参数:
            repo: 仓库标识 owner/repo。
            path: 仓库内文件相对路径。
            append_block: 需要追加的 Markdown 片段。
            branch: 目标分支名。
            token: GitHub 访问令牌（仅用于请求头，不做日志输出）。
        返回值:
            无。
        异常:
            requests.RequestException: 网络或 API 请求失败时抛出。
            ValueError: 当 GitHub API 返回非预期数据时抛出。
        """
        owner_repo = repo.strip().strip("/")
        if owner_repo.startswith("https://github.com/"):
            owner_repo = owner_repo.replace("https://github.com/", "").strip("/")
        url = f"https://api.github.com/repos/{owner_repo}/contents/{path.lstrip('/')}"

        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        }

        existing_text = ""
        existing_sha = None
        get_params = {"ref": branch}
        r = requests.get(url, headers=headers, params=get_params, timeout=15)
        if r.status_code == 200:
            payload = r.json()
            existing_sha = payload.get("sha")
            encoded = payload.get("content") or ""
            if isinstance(encoded, str) and encoded.strip():
                try:
                    existing_text = base64.b64decode(encoded.encode("utf-8")).decode("utf-8", errors="replace")
                except Exception:
                    existing_text = ""
        elif r.status_code == 404:
            existing_text = ""
            existing_sha = None
        else:
            raise ValueError(f"GitHub GET content failed: {r.status_code} {r.text}")

        if not (existing_text or "").strip():
            date_str = datetime.now().strftime("%Y-%m-%d")
            existing_text = f"# {date_str}\n"

        new_text = (existing_text or "") + (append_block or "")
        encoded_new = base64.b64encode(new_text.encode("utf-8")).decode("utf-8")
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        body: Dict[str, Any] = {
            "message": f"ai: sync answer {now_ts}",
            "content": encoded_new,
            "branch": branch,
        }
        if existing_sha:
            body["sha"] = existing_sha

        r2 = requests.put(url, headers=headers, json=body, timeout=20)
        if r2.status_code not in (200, 201):
            raise ValueError(f"GitHub PUT content failed: {r2.status_code} {r2.text}")

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
