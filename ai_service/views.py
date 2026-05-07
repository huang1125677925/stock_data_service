import json
from asgiref.sync import sync_to_async
from django.http import StreamingHttpResponse, JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from common.response import success_response, error_response
from user_management.services import TokenService

from .services import ai_agent_service
from .serializers import (
    PromptConfigSerializer,
    PromptConfigListSerializer,
    AiAnalyzeRequestSerializer,
    AiAnalyzeResponseSerializer,
)

@method_decorator(csrf_exempt, name='dispatch')
class AiAgentChatView(View):
    """
    提供给 Android App 的大模型对话接口 (支持 SSE)
    可选 body.conversation_id：从 chat_service 数据库加载该会话历史，
    再与本次 messages 拼接后送入模型（客户端可不传历史）。
    传入 conversation_id 时须在 Header 携带 Bearer 令牌，且会话须属于当前用户。
    """
    async def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body)
            messages = body.get("messages", [])
            if not messages:
                return error_response("messages 不能为空", 400)

            conversation_id = body.get("conversation_id")
            if conversation_id is not None:
                try:
                    conversation_id = int(conversation_id)
                except (TypeError, ValueError):
                    return error_response("conversation_id 无效", 400)
                auth_header = request.headers.get("Authorization", "")
                if not auth_header.startswith("Bearer "):
                    return error_response("使用 conversation_id 时必须提供 Bearer 认证", 401)
                token_str = auth_header.split(" ", 1)[1].strip()

                def _merge_with_db():
                    from chat_service.services import chat_conversation_service

                    token_service = TokenService()
                    ok, _msg, user = token_service.validate_token(token_str)
                    if not ok or not user:
                        return None, error_response("未认证或令牌无效", 401)
                    conversation = chat_conversation_service.get_conversation_for_user(
                        user=user,
                        conversation_id=conversation_id,
                    )
                    if not conversation:
                        return None, error_response("会话不存在", 404)
                    merged = chat_conversation_service.merge_incoming_with_db_history(
                        conversation,
                        messages,
                    )
                    return merged, None

                messages, err = await sync_to_async(_merge_with_db)()
                if err is not None:
                    return err
            
            # 使用流式返回
            response = StreamingHttpResponse(
                ai_agent_service.chat_stream_generator(messages),
                content_type='text/event-stream; charset=utf-8',
            )
            response['Cache-Control'] = 'no-cache, no-transform'
            response['X-Accel-Buffering'] = 'no'
            return response
        except Exception as e:
            return error_response(str(e), 500)


class PromptConfigListView(APIView):
    @extend_schema(
        summary="获取 Prompt 配置列表",
        description="返回所有已配置的 Prompt 列表，按更新时间倒序排列。",
        tags=["AI 服务"],
        responses={200: PromptConfigListSerializer(many=True)},
    )
    def get(self, request):
        configs = ai_agent_service.get_all_prompts_list()
        # Sort by updated_at desc
        configs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return success_response(configs)

    @extend_schema(
        summary="创建或更新 Prompt 配置",
        description="根据 interface_name 创建或更新 Prompt 模板。",
        tags=["AI 服务"],
        request=PromptConfigSerializer,
        responses={200: PromptConfigSerializer},
    )
    def post(self, request):
        interface_name = request.data.get("interface_name")
        prompt_template = request.data.get("prompt_template")
        is_active = request.data.get("is_active", True)

        if not interface_name:
            return error_response("interface_name 不能为空", 400)
        if not prompt_template:
            return error_response("prompt_template 不能为空", 400)

        config = ai_agent_service.save_prompt_config(
            interface_name, prompt_template, bool(is_active)
        )
        return success_response(config, "配置已保存")


class PromptConfigDetailView(APIView):
    @extend_schema(
        summary="获取 Prompt 配置详情",
        description="根据 interface_name 获取单个 Prompt 配置。",
        tags=["AI 服务"],
        parameters=[
            OpenApiParameter(
                name="interface_name",
                description="接口名称",
                required=True,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={200: PromptConfigSerializer, 404: None},
    )
    def get(self, request, interface_name: str):
        config = ai_agent_service.get_prompt_config(interface_name)
        if not config:
            return error_response("未找到配置", 404)
        return success_response(config)

    @extend_schema(
        summary="删除 Prompt 配置",
        description="根据 interface_name 删除对应的 Prompt 配置。",
        tags=["AI 服务"],
        parameters=[
            OpenApiParameter(
                name="interface_name",
                description="接口名称",
                required=True,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={200: None, 404: None},
    )
    def delete(self, request, interface_name: str):
        deleted = ai_agent_service.delete_prompt_config(interface_name)
        if not deleted:
            return error_response("未找到配置", 404)
        return success_response({"interface_name": interface_name}, "配置已删除")


class AiAnalyzeView(APIView):
    @extend_schema(
        summary="AI 数据分析接口",
        description="提交数据，利用 AI 进行分析。如果未指定 interface_name，默认使用 'default' 配置。",
        tags=["AI 服务"],
        request=AiAnalyzeRequestSerializer,
        responses={200: AiAnalyzeResponseSerializer},
    )
    def post(self, request):
        interface_name = request.data.get("interface_name") or "default"
        input_data = request.data.get("data")

        if input_data is None:
            return error_response("data 不能为空", 400)

        try:
            result, prompt, source = ai_agent_service.analyze(interface_name, input_data)
            return success_response(
                {
                    "interface_name": interface_name,
                    # "prompt_source": source,
                    # "prompt": prompt,
                    "result": result,
                }
            )
        except Exception as e:
            return error_response(f"AI 分析失败: {str(e)}", 500)
