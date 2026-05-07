from django.contrib import admin
from .models import EtfBasic, EtfDaily


@admin.register(EtfBasic)
class EtfBasicAdmin(admin.ModelAdmin):
    """
    ETF 基础信息后台管理
    功能：在 Django Admin 中管理 EtfBasic 记录。
    参数：无
    返回值：无
    事件：后台列表显示与搜索。
    """
    list_display = (
        'ts_code', 'csname', 'extname', 'cname',
        'index_code', 'index_name', 'exchange', 'mgr_name',
        'list_status', 'setup_date', 'list_date', 'custod_name', 'mgt_fee', 'etf_type'
    )
    search_fields = ('ts_code', 'csname', 'extname', 'cname', 'index_code', 'index_name', 'mgr_name')
    list_filter = ('exchange', 'list_status', 'etf_type')


@admin.register(EtfDaily)
class EtfDailyAdmin(admin.ModelAdmin):
    """
    ETF 日线行情后台管理
    功能：在 Django Admin 中管理 EtfDaily 记录。
    参数：无
    返回值：无
    事件：后台列表显示与筛选。
    """
    list_display = ('ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'pre_close', 'change', 'pct_chg', 'vol', 'amount')
    search_fields = ('ts_code',)
    list_filter = ('ts_code',)