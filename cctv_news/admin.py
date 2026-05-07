from django.contrib import admin
from .models import CCTVNews

@admin.register(CCTVNews)
class CCTVNewsAdmin(admin.ModelAdmin):
    list_display = ['title', 'publish_date', 'create_time', 'summary']
    list_filter = ['publish_date', 'create_time']
    search_fields = ['title', 'content', 'ai_content']
    readonly_fields = ['create_time']
    ordering = ['-publish_date', '-create_time']
    date_hierarchy = 'publish_date'
    
    def summary(self, obj):
        """显示内容摘要"""
        return obj.summary
    summary.short_description = '内容摘要'