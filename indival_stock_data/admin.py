from django.contrib import admin
from .models import IndividualStock, IndividualStockDaily, IndividualStockRealtime


@admin.register(IndividualStock)
class IndividualStockAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'industry', 'total_shares', 'circulating_shares', 'list_date', 'pe_ratio', 'pb_ratio', 'total_market_cap')
    search_fields = ('code', 'name', 'industry')
    list_filter = ('industry',)
    ordering = ('code',)


@admin.register(IndividualStockDaily)
class IndividualStockDailyAdmin(admin.ModelAdmin):
    list_display = ('stock', 'date', 'open_price', 'close_price', 'high_price', 'low_price', 'change_percent', 'volume', 'amount')
    search_fields = ('stock__code', 'stock__name')
    list_filter = ('date',)
    date_hierarchy = 'date'
    ordering = ('-date', 'stock')


@admin.register(IndividualStockRealtime)
class IndividualStockRealtimeAdmin(admin.ModelAdmin):
    list_display = ('stock', 'latest_price', 'change_percent', 'change_amount', 'volume', 'amount', 'timestamp')
    search_fields = ('stock__code', 'stock__name')
    list_filter = ('timestamp',)
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp', 'stock')
