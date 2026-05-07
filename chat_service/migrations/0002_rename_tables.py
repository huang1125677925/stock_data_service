from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('chat_service', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelTable(name='conversation', table='chat_conversation'),
        migrations.AlterModelTable(name='message', table='chat_message'),
    ]
