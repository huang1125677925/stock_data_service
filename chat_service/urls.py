from django.urls import path
from .views import (
    ConversationCollectionView,
    ConversationMessagesView,
    ConversationDetailView,
    ConversationStreamView,
)

app_name = 'chat_service'

urlpatterns = [
    path('conversations/', ConversationCollectionView.as_view(), name='conversation-collection'),
    path('conversations/<int:conversation_id>/messages/', ConversationMessagesView.as_view(), name='conversation-messages'),
    path('conversations/<int:conversation_id>/', ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<int:conversation_id>/stream/', ConversationStreamView.as_view(), name='conversation-stream'),
]
