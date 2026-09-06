from django.contrib import admin
from .models import User, InvitationCode, UserToken, SiteVisitCounter


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'phone', 'is_active', 'is_admin', 'last_login', 'created_at')
    list_filter = ('is_active', 'is_admin', 'created_at')
    search_fields = ('username', 'email', 'phone')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('基本信息', {'fields': ('username', 'email', 'phone')}),
        ('权限信息', {'fields': ('is_active', 'is_admin')}),
        ('时间信息', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )


@admin.register(InvitationCode)
class InvitationCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'created_by', 'used_by', 'is_used', 'expires_at', 'created_at')
    list_filter = ('is_used', 'created_at')
    search_fields = ('code', 'created_by__username', 'used_by__username')
    readonly_fields = ('created_at',)


@admin.register(UserToken)
class UserTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'token', 'expires_at', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'token')
    readonly_fields = ('created_at',)


@admin.register(SiteVisitCounter)
class SiteVisitCounterAdmin(admin.ModelAdmin):
    list_display = ('id', 'key', 'total_count', 'created_at', 'updated_at')
    search_fields = ('key',)
    readonly_fields = ('created_at', 'updated_at')
