import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from django.conf import settings
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class AiAgentService:
    def __init__(self):
        self.api_key = getattr(settings, "DEEPSEEK_API_KEY", None) or "sk-901c17c669a241f098b25144957667ec"
        self.base_url = getattr(settings, "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        self.model_name = getattr(settings, "DEEPSEEK_MODEL_NAME", "deepseek-chat")
        self.system_prompt = getattr(
            settings,
            "AI_SYSTEM_PROMPT",
            "你是一个专业的金融分析师，擅长对结构化数据进行分析并给出简洁结论。",
        )
        self.default_prompt = getattr(
            settings,
            "AI_DEFAULT_PROMPT",
            "请根据以下数据进行分析，输出简洁的中文结果：\n{data}",
        )
        
        self.prompts_file = os.path.join(os.path.dirname(__file__), "prompts.json")
        self.prompts_map = self._load_active_prompts()
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
            system_prompt=self.system_prompt
        )

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
