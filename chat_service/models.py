from django.db import models
from user_management.models import User


class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_conversations', verbose_name='用户')
    title = models.CharField(max_length=200, verbose_name='会话标题')
    model = models.CharField(max_length=100, verbose_name='模型')
    is_pinned = models.BooleanField(default=False, verbose_name='是否置顶')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='删除时间')

    class Meta:
        db_table = 'chat_conversation'
        verbose_name = '会话'
        verbose_name_plural = '会话'
        ordering = ['-is_pinned', '-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at'], name='idx_conv_user_updated'),
            models.Index(fields=['user', 'deleted_at'], name='idx_conv_user_deleted'),
        ]

    def __str__(self):
        return f'{self.user_id}:{self.title}'


class Message(models.Model):
    ROLE_USER = 'user'
    ROLE_ASSISTANT = 'assistant'
    ROLE_TOOL = 'tool'
    ROLE_SYSTEM = 'system'
    ROLE_CHOICES = (
        (ROLE_USER, '用户'),
        (ROLE_ASSISTANT, '助手'),
        (ROLE_TOOL, '工具'),
        (ROLE_SYSTEM, '系统'),
    )

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages', verbose_name='会话')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name='角色')
    content = models.TextField(verbose_name='内容')
    tool_data = models.JSONField(null=True, blank=True, verbose_name='工具数据')
    seq = models.PositiveIntegerField(verbose_name='消息序号')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'chat_message'
        verbose_name = '消息'
        verbose_name_plural = '消息'
        ordering = ['seq']
        unique_together = ('conversation', 'seq')
        indexes = [
            models.Index(fields=['conversation', 'seq'], name='idx_msg_conv_seq'),
        ]

    def __str__(self):
        return f'{self.conversation_id}:{self.role}:{self.seq}'
