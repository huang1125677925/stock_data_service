from rest_framework import serializers
from .models import Conversation, Message


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ['id', 'user_id', 'title', 'model', 'is_pinned', 'created_at', 'updated_at', 'deleted_at']


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'conversation_id', 'role', 'content', 'tool_data', 'seq', 'created_at']
