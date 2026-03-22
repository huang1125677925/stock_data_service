import json
import logging
import os
import asyncio
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from django.conf import settings
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
import traceback

from mcp_service.server import create_server
from mcp_service.tavily_mcp_service import register_tavily_mcp_client

logger = logging.getLogger(__name__)

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
                "1) 对于A股股票行情、财务数据、交易数据、上市公司信息等问题，优先使用 tushare 相关工具。\n"
                "2) 以下情况必须使用 Tavily 联网搜索工具：\n"
                "   - 用户问题涉及最新新闻、实时动态、政策变化\n"
                "   - 用户问题涉及非A股市场（美股、港股、外盘等）\n"
                "   - 用户问题涉及宏观经济、央行政策、利率汇率等\n"
                "   - 用户问题涉及加密货币、数字货币\n"
                "   - 用户问题需要解释概念、分析原因、提供建议\n"
                "   - tushare 工具返回结果为空或错误时\n"
                "   - 你判断 tushare 工具无法满足用户需求时\n"
                "3) 回答时优先基于工具返回的结果，不要凭空编造数据。\n"
                "4) 如果不确定使用哪个工具，可以先尝试 tushare 工具，如果结果不满意再使用联网搜索。"
            ),
        )
        self.tavily_mcp_url = "https://mcp.tavily.com/mcp/?tavilyApiKey=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"
        self.tavily_mcp_enabled = True
        self.default_prompt = getattr(
            settings,
            "AI_DEFAULT_PROMPT",
            "请根据以下数据进行分析，输出简洁的中文结果：\n{data}",
        )
        
        self.prompts_file = os.path.join(os.path.dirname(__file__), "prompts.json")
        self.prompts_map = self._load_active_prompts()
        self.tavily_mcp_client = register_tavily_mcp_client(
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
            # 为 Tavily 工具增强描述，让 LLM 更清楚这是联网搜索工具
            enhanced_description = description
            if source == "tavily":
                enhanced_description = (
                    f"[联网搜索工具] {description} "
                    "此工具可以搜索互联网获取实时信息、最新新闻、政策动态、"
                    "非A股市场信息、宏观经济数据等 tushare 无法提供的内容。"
                    "当本地数据工具无法回答问题时，请使用此工具。"
                )
            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": safe_name,
                        "description": enhanced_description,
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

    def _get_latest_user_query(self, messages_data: List[Dict]) -> str:
        """
        获取最近一条用户消息文本。
        参数:
            messages_data: 对话消息列表。
        返回值:
            最近一条 role=user 的 content；若不存在则返回空字符串。
        异常:
            无。
        """
        for item in reversed(messages_data):
            if item.get("role") == "user":
                return str(item.get("content", "")).strip()
        return ""

    def _should_force_tavily_for_query(self, query: str) -> bool:
        """
        判断是否需要对当前问题优先触发一次联网查询。
        参数:
            query: 用户问题文本。
        返回值:
            True 表示应优先联网；False 表示按常规工具决策。
        异常:
            无。
        """
        if not query:
            return False
        # 明确需要实时联网的关键词模式
        realtime_patterns = [
            r"天气",
            r"温度",
            r"降雨|下雨|雨",
            r"空气质量|AQI",
            r"台风|预警",
        ]
        if any(re.search(pattern, query, re.IGNORECASE) for pattern in realtime_patterns):
            return True
        return False

    def _is_non_tushare_query(self, query: str) -> bool:
        """
        判断问题是否明显不属于 tushare 能处理的范围。
        参数:
            query: 用户问题文本。
        返回值:
            True 表示问题不在 tushare 能力范围内，应尝试联网搜索。
        异常:
            无。
        """
        if not query:
            return False
        # tushare 能处理的关键词（股票、财务、交易相关）
        tushare_keywords = [
            r"股票|股价|股市|A股|个股|涨跌|涨停|跌停",
            r"行情|K线|日线|分钟线|走势",
            r"市值|市盈率|PE|PB|ROE|换手率",
            r"财报|财务|利润|营收|净利润|毛利|资产负债",
            r"龙虎榜|大宗交易|融资融券|北向资金|南向资金",
            r"分红|送股|配股|增发|减持",
            r"上市公司|IPO|新股|退市",
            r"基金|ETF|LOF|指数|大盘|沪深300|上证|深证|创业板|科创板",
            r"交易日|开盘|收盘|成交量|成交额",
            r"概念股|板块|行业板块|地域板块",
            r"[0-9]{6}\.(SZ|SH|BJ)|[0-9]{6}",  # 股票代码
        ]
        # 明确需要联网搜索的关键词
        web_search_keywords = [
            r"搜索|查一下|帮我查|网上|百度|谷歌",
            r"怎么.*做|如何.*做|方法|教程|步骤",
            r"是什么|什么是|定义|解释|介绍",
            r"为什么|原因|背景",
            r"比较|对比|区别|差异",
            r"推荐|建议|最好的",
            r"最新.*消息|最新.*新闻|最新.*动态|最新.*进展",
            r"实时|现在|当前|今日(?!行情|涨跌)",
            r"政策|法规|规定|监管",
            r"宏观|经济形势|GDP|CPI|PPI|PMI",
            r"美股|港股|外盘|海外市场|纳斯达克|道琼斯|标普",
            r"加密货币|比特币|以太坊|数字货币",
            r"汇率|外汇|人民币.*美元",
            r"利率|降息|加息|央行|美联储",
        ]
        # 如果包含明确的联网搜索关键词，返回 True
        for pattern in web_search_keywords:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        # 如果不包含任何 tushare 关键词，也返回 True
        has_tushare_keyword = any(
            re.search(pattern, query, re.IGNORECASE) for pattern in tushare_keywords
        )
        if not has_tushare_keyword:
            return True
        return False

    def _build_forced_tavily_call(
        self, query: str, tavily_tools: List[Dict[str, Any]]
    ) -> tuple[Optional[str], Dict[str, Any]]:
        """
        基于 Tavily 工具定义构建一次兜底联网调用。
        参数:
            query: 用户问题文本。
            tavily_tools: Tavily MCP 工具元数据列表。
        返回值:
            (tool_name, args)；当无法构建时 tool_name 为 None。
        异常:
            无。
        """
        if not tavily_tools:
            return None, {}

        preferred_names = ["tavily_search", "tavily_research"]
        tool_map = {str(t.get("name", "")): t for t in tavily_tools if t.get("name")}
        selected_tool = None
        for name in preferred_names:
            if name in tool_map:
                selected_tool = tool_map[name]
                break
        if selected_tool is None:
            for t in tavily_tools:
                tool_name = str(t.get("name", ""))
                if "search" in tool_name or "research" in tool_name:
                    selected_tool = t
                    break
        if selected_tool is None:
            return None, {}

        tool_name = str(selected_tool.get("name", ""))
        schema = selected_tool.get("inputSchema") or {}
        properties = schema.get("properties") if isinstance(schema, dict) else {}
        required = schema.get("required") if isinstance(schema, dict) else []
        if not isinstance(properties, dict):
            properties = {}
        if not isinstance(required, list):
            required = []

        if "query" in properties:
            return tool_name, {"query": query}
        if "input" in properties:
            return tool_name, {"input": query}
        if len(required) == 1 and isinstance(required[0], str):
            return tool_name, {required[0]: query}
        return None, {}

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
            logger.info(f"Loaded {len(local_tools)} local MCP tools")
            tavily_tools: List[Dict[str, Any]] = []
            if self.tavily_mcp_enabled:
                try:
                    tavily_tools = await self.tavily_mcp_client.list_tools()
                    logger.info(f"Loaded {len(tavily_tools)} Tavily MCP tools: {[t.get('name') for t in tavily_tools]}")
                except Exception as tavily_error:
                    logger.warning(f"Failed to list Tavily MCP tools: {tavily_error}")
            else:
                logger.info("Tavily MCP is disabled")

            openai_tools, tool_route_map = self._build_tools_payload(local_tools, tavily_tools)
            forced_tavily_result_text = ""
            latest_user_query = self._get_latest_user_query(messages_data)
            # 判断是否需要强制联网：实时信息查询 或 非 tushare 能力范围的问题
            is_realtime_query = self._should_force_tavily_for_query(latest_user_query)
            is_non_tushare = self._is_non_tushare_query(latest_user_query)
            should_force_tavily = is_realtime_query or is_non_tushare
            logger.info(
                f"Query analysis - realtime: {is_realtime_query}, non_tushare: {is_non_tushare}, "
                f"should_force_tavily: {should_force_tavily}, tavily_enabled: {self.tavily_mcp_enabled}, "
                f"tavily_tools_count: {len(tavily_tools)}"
            )
            if self.tavily_mcp_enabled and should_force_tavily and tavily_tools:
                forced_tool_name, forced_tool_args = self._build_forced_tavily_call(latest_user_query, tavily_tools)
                if forced_tool_name:
                    try:
                        yield f"data: {json.dumps({'type': 'status', 'content': f'正在调用联网工具 {forced_tool_name}...'}, ensure_ascii=False)}\n\n"
                        forced_result = await self.tavily_mcp_client.call_tool(forced_tool_name, forced_tool_args)
                        forced_tavily_result_text = self._extract_tool_result_text(forced_result)
                        if len(forced_tavily_result_text) > 8000:
                            forced_tavily_result_text = forced_tavily_result_text[:8000] + "\n...(由于长度限制已截断)"
                        yield f"data: {json.dumps({'type': 'tool_card', 'tool_name': forced_tool_name, 'result': forced_tavily_result_text}, ensure_ascii=False)}\n\n"
                    except Exception as forced_error:
                        logger.warning(f"Forced Tavily call failed: {forced_error}")

            messages = []
            messages.append(SystemMessage(content=self._build_chat_system_prompt()))
            for m in messages_data:
                if m["role"] == "user":
                    messages.append(HumanMessage(content=m["content"]))
                elif m["role"] == "assistant":
                    messages.append(AIMessage(content=m["content"]))
                elif m["role"] == "tool":
                    messages.append(ToolMessage(content=m["content"], tool_call_id=m.get("tool_call_id", "")))
            if forced_tavily_result_text:
                messages.append(
                    SystemMessage(
                        content=f"以下为已获取的联网信息，请优先基于该信息回答，并可按需继续调用工具：\n{forced_tavily_result_text}"
                    )
                )

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
