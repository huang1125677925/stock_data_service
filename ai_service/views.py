import json
from django.http import StreamingHttpResponse, JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from common.response import success_response, error_response

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
    """
    async def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body)
            messages = body.get("messages", [])
            if not messages:
                return error_response("messages 不能为空", 400)
            
            # 使用流式返回
            response = StreamingHttpResponse(
                ai_agent_service.chat_stream_generator(messages),
                content_type='text/event-stream'
            )
            response['Cache-Control'] = 'no-cache'
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
