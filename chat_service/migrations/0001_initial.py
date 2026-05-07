from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('user_management', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Conversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='会话标题')),
                ('model', models.CharField(max_length=100, verbose_name='模型')),
                ('is_pinned', models.BooleanField(default=False, verbose_name='是否置顶')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='删除时间')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chat_conversations', to='user_management.user', verbose_name='用户')),
            ],
            options={
                'db_table': 'chat_conversation',
                'verbose_name': '会话',
                'verbose_name_plural': '会话',
                'ordering': ['-is_pinned', '-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('user', '用户'), ('assistant', '助手'), ('tool', '工具'), ('system', '系统')], max_length=20, verbose_name='角色')),
                ('content', models.TextField(verbose_name='内容')),
                ('tool_data', models.JSONField(blank=True, null=True, verbose_name='工具数据')),
                ('seq', models.PositiveIntegerField(verbose_name='消息序号')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='chat_service.conversation', verbose_name='会话')),
            ],
            options={
                'db_table': 'chat_message',
                'verbose_name': '消息',
                'verbose_name_plural': '消息',
                'ordering': ['seq'],
                'unique_together': {('conversation', 'seq')},
            },
        ),
        migrations.AddIndex(
            model_name='conversation',
            index=models.Index(fields=['user', '-updated_at'], name='idx_conv_user_updated'),
        ),
        migrations.AddIndex(
            model_name='conversation',
            index=models.Index(fields=['user', 'deleted_at'], name='idx_conv_user_deleted'),
        ),
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['conversation', 'seq'], name='idx_msg_conv_seq'),
        ),
    ]
