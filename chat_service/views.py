import json
from asgiref.sync import sync_to_async
from django.http import StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework.authentication import BaseAuthentication
from rest_framework.views import APIView
from common.response import success_response, error_response
from ai_service.services import ai_agent_service
from .models import Message
from .serializers import ConversationSerializer, MessageSerializer
from .services import chat_conversation_service


def _parse_positive_int(raw_value, default_value, min_value=1, max_value=200):
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return default_value
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value


def _extract_sse_data(chunk):
    if not isinstance(chunk, str):
        return None
    if not chunk.startswith('data:'):
        return None
    payload = chunk[5:].strip()
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def _parse_bool(raw_value):
    if isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, str):
        lowered = raw_value.strip().lower()
        if lowered in ('true', '1', 'yes', 'y', 'on'):
            return True
        if lowered in ('false', '0', 'no', 'n', 'off'):
            return False
    if isinstance(raw_value, (int, float)):
        return bool(raw_value)
    return None


class MiddlewareUserAuthentication(BaseAuthentication):
    def authenticate(self, request):
        raw_request = getattr(request, '_request', None)
        raw_user = getattr(raw_request, 'user', None)
        if getattr(raw_user, 'id', None):
            return raw_user, None
        return None


def _get_authenticated_user(request):
    user = getattr(request, 'user', None)
    if getattr(user, 'id', None):
        return user
    raw_request = getattr(request, '_request', None)
    raw_user = getattr(raw_request, 'user', None)
    if getattr(raw_user, 'id', None):
        return raw_user
    return None


@method_decorator(csrf_exempt, name='dispatch')
class ConversationCollectionView(APIView):
    authentication_classes = [MiddlewareUserAuthentication]

    def post(self, request):
        user = _get_authenticated_user(request)
        if not user:
            return error_response('未认证', code=401)
        title = request.data.get('title')
        model_name = request.data.get('model')
        conversation = chat_conversation_service.create_conversation(
            user=user,
            title=title,
            model_name=model_name,
        )
        data = ConversationSerializer(conversation).data
        return success_response(data, '创建成功')

    def get(self, request):
        user = _get_authenticated_user(request)
        if not user:
            return error_response('未认证', code=401)
        page = _parse_positive_int(
            request.GET.get('page'),
            1,
            min_value=1,
            max_value=1000000,
        )
        page_size = _parse_positive_int(
            request.GET.get('page_size'),
            20,
            min_value=1,
            max_value=200,
        )
        result = chat_conversation_service.list_conversations(
            user=user,
            page=page,
            page_size=page_size,
        )
        items = ConversationSerializer(result['items'], many=True).data
        return success_response(
            {
                'items': items,
                'total': result['total'],
                'page': result['page'],
                'page_size': result['page_size'],
                'total_pages': result['total_pages'],
            }
        )


@method_decorator(csrf_exempt, name='dispatch')
class ConversationMessagesView(APIView):
    authentication_classes = [MiddlewareUserAuthentication]

    def get(self, request, conversation_id):
        user = _get_authenticated_user(request)
        if not user:
            return error_response('未认证', code=401)
        conversation = chat_conversation_service.get_conversation_for_user(
            user=user,
            conversation_id=conversation_id,
        )
        if not conversation:
            return error_response('会话不存在', code=404)
        cursor = _parse_positive_int(
            request.GET.get('cursor'),
            0,
            min_value=0,
            max_value=1000000000,
        )
        page_size = _parse_positive_int(
            request.GET.get('page_size'),
            50,
            min_value=1,
            max_value=200,
        )
        result = chat_conversation_service.list_messages(
            conversation=conversation,
            cursor=cursor,
            page_size=page_size,
        )
        items = MessageSerializer(result['items'], many=True).data
        return success_response(
            {
                'items': items,
                'next_cursor': result['next_cursor'],
                'has_more': result['has_more'],
            }
        )

    def post(self, request, conversation_id):
        user = _get_authenticated_user(request)
        if not user:
            return error_response('未认证', code=401)
        conversation = chat_conversation_service.get_conversation_for_user(
            user=user,
            conversation_id=conversation_id,
        )
        if not conversation:
            return error_response('会话不存在', code=404)
        content = request.data.get('content')
        if not content:
            return error_response('content 不能为空', code=400)
        tool_data = request.data.get('tool_data')
        message = chat_conversation_service.create_message(
            conversation=conversation,
            role=Message.ROLE_USER,
            content=content,
            tool_data=tool_data,
        )
        return success_response(MessageSerializer(message).data, '写入成功')


@method_decorator(csrf_exempt, name='dispatch')
class ConversationMessageDetailView(APIView):
    authentication_classes = [MiddlewareUserAuthentication]

    def patch(self, request, conversation_id, message_id):
        user = _get_authenticated_user(request)
        if not user:
            return error_response('未认证', code=401)
        conversation = chat_conversation_service.get_conversation_for_user(
            user=user,
            conversation_id=conversation_id,
        )
        if not conversation:
            return error_response('会话不存在', code=404)
        if 'tool_data' not in request.data:
            return error_response('tool_data 字段缺失', code=400)
        updated = chat_conversation_service.update_message_tool_data(
            conversation=conversation,
            message_id=message_id,
            tool_data=request.data.get('tool_data'),
        )
        if not updated:
            return error_response('消息不存在', code=404)
        return success_response(MessageSerializer(updated).data, '更新成功')


@method_decorator(csrf_exempt, name='dispatch')
class ConversationDetailView(APIView):
    authentication_classes = [MiddlewareUserAuthentication]

    def patch(self, request, conversation_id):
        user = _get_authenticated_user(request)
        if not user:
            return error_response('未认证', code=401)
        conversation = chat_conversation_service.get_conversation_for_user(
            user=user,
            conversation_id=conversation_id,
        )
        if not conversation:
            return error_response('会话不存在', code=404)
        title = request.data.get('title') if 'title' in request.data else None
        is_pinned = (
            _parse_bool(request.data.get('is_pinned'))
            if 'is_pinned' in request.data
            else None
        )
        if 'is_pinned' in request.data and is_pinned is None:
            return error_response('is_pinned 参数无效', code=400)
        if title is None and is_pinned is None:
            return error_response('至少提供一个可更新字段', code=400)
        updated = chat_conversation_service.update_conversation(
            conversation=conversation,
            title=title,
            is_pinned=is_pinned,
        )
        return success_response(ConversationSerializer(updated).data, '更新成功')

    def delete(self, request, conversation_id):
        user = _get_authenticated_user(request)
        if not user:
            return error_response('未认证', code=401)
        conversation = chat_conversation_service.get_conversation_for_user(
            user=user,
            conversation_id=conversation_id,
        )
        if not conversation:
            return error_response('会话不存在', code=404)
        chat_conversation_service.soft_delete_conversation(conversation)
        return success_response(message='删除成功')


@method_decorator(csrf_exempt, name='dispatch')
class ConversationStreamView(View):
    async def post(self, request, conversation_id):
        user = _get_authenticated_user(request)
        if not user:
            return error_response('未认证', code=401)
        get_conversation = sync_to_async(
            chat_conversation_service.get_conversation_for_user,
        )
        conversation = await get_conversation(user, conversation_id)
        if not conversation:
            return error_response('会话不存在', code=404)
        try:
            body = json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return error_response('请求体必须是合法 JSON', code=400)
        content = body.get('content')
        if content:
            await sync_to_async(chat_conversation_service.create_message)(
                conversation=conversation,
                role=Message.ROLE_USER,
                content=content,
                tool_data=body.get('tool_data'),
            )
        build_messages = sync_to_async(
            chat_conversation_service.build_chat_messages,
        )
        messages_data = await build_messages(conversation)
        if not messages_data:
            return error_response('请先写入用户消息', code=400)

        async def stream_generator():
            assistant_parts = []
            generator = ai_agent_service.chat_stream_generator(messages_data)
            async for chunk in generator:
                payload = _extract_sse_data(chunk)
                if payload and payload.get('type') == 'text':
                    assistant_parts.append(payload.get('content') or '')
                yield chunk
            assistant_content = ''.join(assistant_parts).strip()
            if assistant_content:
                await sync_to_async(chat_conversation_service.create_message)(
                    conversation=conversation,
                    role=Message.ROLE_ASSISTANT,
                    content=assistant_content,
                    tool_data=None,
                )

        response = StreamingHttpResponse(
            stream_generator(),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
