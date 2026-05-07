from django.apps import AppConfig


class StockMarketConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "stock_market"
    verbose_name = '股票大盘数据'
