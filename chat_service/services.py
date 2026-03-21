from django.conf import settings
from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone
from .models import Conversation, Message


class ChatConversationService:
    @staticmethod
    def create_conversation(user, title=None, model_name=None):
        final_title = title or '新会话'
        final_model = model_name or getattr(settings, 'DEEPSEEK_MODEL_NAME', 'deepseek-chat')
        return Conversation.objects.create(
            user=user,
            title=final_title,
            model=final_model,
        )

    @staticmethod
    def get_conversation_for_user(user, conversation_id):
        return Conversation.objects.filter(
            id=conversation_id,
            user=user,
            deleted_at__isnull=True,
        ).first()

    @staticmethod
    def list_conversations(user, page=1, page_size=20):
        queryset = Conversation.objects.filter(
            user=user,
            deleted_at__isnull=True,
        ).order_by('-is_pinned', '-updated_at')
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        return {
            'items': page_obj.object_list,
            'total': paginator.count,
            'page': page_obj.number,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
        }

    @staticmethod
    def list_messages(conversation, cursor=0, page_size=50):
        queryset = Message.objects.filter(
            conversation=conversation,
            seq__gt=cursor,
        ).order_by('seq')
        rows = list(queryset[:page_size + 1])
        has_more = len(rows) > page_size
        items = rows[:page_size]
        next_cursor = items[-1].seq if items else cursor
        return {
            'items': items,
            'has_more': has_more,
            'next_cursor': next_cursor,
        }

    @staticmethod
    @transaction.atomic
    def create_message(conversation, role, content, tool_data=None):
        locked_conversation = Conversation.objects.select_for_update().get(id=conversation.id)
        last_message = Message.objects.filter(conversation=locked_conversation).order_by('-seq').first()
        next_seq = (last_message.seq + 1) if last_message else 1
        message = Message.objects.create(
            conversation=locked_conversation,
            role=role,
            content=content,
            tool_data=tool_data,
            seq=next_seq,
        )
        return message

    @staticmethod
    def build_chat_messages(conversation):
        messages = []
        queryset = Message.objects.filter(conversation=conversation).order_by('seq')
        for row in queryset:
            if row.role == Message.ROLE_TOOL:
                payload = {
                    'role': row.role,
                    'content': row.content,
                }
                if isinstance(row.tool_data, dict):
                    tool_call_id = row.tool_data.get('tool_call_id')
                    if tool_call_id:
                        payload['tool_call_id'] = tool_call_id
                messages.append(payload)
                continue
            messages.append(
                {
                    'role': row.role,
                    'content': row.content,
                }
            )
        return messages

    @staticmethod
    def update_conversation(conversation, title=None, is_pinned=None):
        update_fields = []
        if title is not None:
            conversation.title = title
            update_fields.append('title')
        if is_pinned is not None:
            conversation.is_pinned = bool(is_pinned)
            update_fields.append('is_pinned')
        if update_fields:
            update_fields.append('updated_at')
            conversation.save(update_fields=update_fields)
        return conversation

    @staticmethod
    def soft_delete_conversation(conversation):
        now = timezone.now()
        conversation.deleted_at = now
        conversation.save(update_fields=['deleted_at', 'updated_at'])
        return conversation


chat_conversation_service = ChatConversationService()
