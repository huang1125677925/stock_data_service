from django.urls import path

from .views import PromptConfigListView, PromptConfigDetailView, AiAnalyzeView, AiAgentChatView

app_name = "ai_service"

urlpatterns = [
    path("prompts/", PromptConfigListView.as_view(), name="prompt-config-list"),
    path("prompts/<str:interface_name>/", PromptConfigDetailView.as_view(), name="prompt-config-detail"),
    path("analyze/", AiAnalyzeView.as_view(), name="ai-analyze"),
    path("chat/", AiAgentChatView.as_view(), name="ai-chat"),
]
