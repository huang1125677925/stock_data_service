from django.apps import AppConfig


class EtfappConfig(AppConfig):
    """
    ETF 应用配置
    功能：注册 etfapp 应用的配置元数据。
    参数：无
    返回值：无
    事件：Django 启动时调用，用于应用初始化。
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'etfapp'
    verbose_name = 'ETF 数据'