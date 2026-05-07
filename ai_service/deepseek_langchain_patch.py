"""
DeepSeek + LangChain 兼容补丁

为 OpenAI 兼容接口的 thinking 模式补齐 reasoning_content 的解析与回传：
- 从响应中提取 assistant.message.reasoning_content 写入 additional_kwargs
- 构造下一轮请求 messages 时，把 reasoning_content 随 assistant 消息一并带回
"""

from typing import Any, Mapping


def apply_deepseek_reasoning_patch() -> None:
    """
    应用 DeepSeek thinking 模式兼容补丁。

    参数:
        无。
    返回值:
        无。
    异常:
        无。
    """
    try:
        import langchain_openai.chat_models.base as lc_openai_base
        from langchain_core.messages import AIMessage
        from langchain_core.messages.ai import AIMessageChunk
    except Exception:
        return

    if getattr(lc_openai_base, "__deepseek_reasoning_patch_applied__", False):
        return

    original_convert_dict_to_message = lc_openai_base._convert_dict_to_message
    original_convert_delta_to_message_chunk = lc_openai_base._convert_delta_to_message_chunk
    original_convert_message_to_dict = lc_openai_base._convert_message_to_dict

    def _patched_convert_dict_to_message(_dict: Mapping[str, Any]):
        msg = original_convert_dict_to_message(_dict)
        if isinstance(msg, AIMessage):
            reasoning_content = _dict.get("reasoning_content")
            if isinstance(reasoning_content, str) and reasoning_content:
                msg.additional_kwargs = dict(msg.additional_kwargs or {})
                msg.additional_kwargs["reasoning_content"] = reasoning_content
        return msg

    def _patched_convert_delta_to_message_chunk(_dict: Mapping[str, Any], default_class):
        msg = original_convert_delta_to_message_chunk(_dict, default_class)
        if isinstance(msg, AIMessageChunk):
            reasoning_content = _dict.get("reasoning_content")
            if isinstance(reasoning_content, str) and reasoning_content:
                msg.additional_kwargs = dict(msg.additional_kwargs or {})
                msg.additional_kwargs["reasoning_content"] = reasoning_content
        return msg

    def _patched_convert_message_to_dict(message, api="chat/completions"):
        message_dict = original_convert_message_to_dict(message, api=api)
        if isinstance(message, AIMessage):
            reasoning_content = (message.additional_kwargs or {}).get("reasoning_content")
            if isinstance(reasoning_content, str) and reasoning_content:
                message_dict["reasoning_content"] = reasoning_content
        return message_dict

    lc_openai_base._convert_dict_to_message = _patched_convert_dict_to_message
    lc_openai_base._convert_delta_to_message_chunk = _patched_convert_delta_to_message_chunk
    lc_openai_base._convert_message_to_dict = _patched_convert_message_to_dict
    lc_openai_base.__deepseek_reasoning_patch_applied__ = True

