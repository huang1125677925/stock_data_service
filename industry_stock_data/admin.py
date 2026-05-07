from django.contrib import admin
from .models import StockInfo, StockRealtime, MarketSummary

@admin.register(StockInfo)
class StockInfoAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'industry', 'total_shares', 'circulating_shares', 'list_date', 'updated_at']
    list_filter = ['industry', 'list_date']
    search_fields = ['code', 'name', 'industry']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['code']

@admin.register(StockRealtime)
class StockRealtimeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'latest_price', 'change_percent', 'volume', 'amount', 'timestamp']
    list_filter = ['timestamp']
    search_fields = ['code', 'name']
    readonly_fields = ['timestamp']
    ordering = ['-timestamp', 'code']
    date_hierarchy = 'timestamp'

@admin.register(MarketSummary)
class MarketSummaryAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_stocks', 'rising_stocks', 'falling_stocks', 'total_volume', 'total_amount']
    list_filter = ['date']
    readonly_fields = ['created_at']
    ordering = ['-date']
    date_hierarchy = 'date'