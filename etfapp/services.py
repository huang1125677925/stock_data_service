from typing import Dict, List, Optional
from datetime import datetime
from django.db.models import Q, OuterRef, Subquery
from .models import EtfBasic, EtfDaily


class EtfService:
    """
    ETF 数据服务
    功能：提供ETF基础信息和日线行情的查询服务，封装 ORM 过滤逻辑。
    参数：无（实例初始化不需要参数）
    返回值：列表或对象的字典表示，由序列化器在视图层处理。
    事件：无
    """

    def query_basic(self, filters: Dict) -> List[EtfBasic]:
        """
        查询ETF基础信息列表
        功能：支持根据ts_code、index_code、exchange、list_status、mgr_name、etf_type、名称模糊等筛选。
        参数：
        - filters: dict，包含可选筛选条件
        返回值：EtfBasic QuerySet 列表
        事件：无
        """
        qs = EtfBasic.objects.all()

        ts_code = filters.get('ts_code')
        index_code = filters.get('index_code')
        exchange = filters.get('exchange')
        list_status = filters.get('list_status')
        mgr_name = filters.get('mgr_name')
        etf_type = filters.get('etf_type')
        name = filters.get('name')

        if ts_code:
            qs = qs.filter(ts_code=ts_code)
        if index_code:
            qs = qs.filter(index_code=index_code)
        if exchange:
            qs = qs.filter(exchange=exchange)
        if list_status:
            qs = qs.filter(list_status=list_status)
        if mgr_name:
            qs = qs.filter(mgr_name__icontains=mgr_name)
        if etf_type:
            qs = qs.filter(etf_type=etf_type)
        if name:
            qs = qs.filter(Q(extname__icontains=name) | Q(ts_code__icontains=name))

        return list(qs)

    def query_daily(self, ts_code: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[EtfDaily]:
        """
        查询ETF日线行情
        功能：根据ts_code与日期范围筛选日线数据。
        参数：
        - ts_code: 目标ETF的TS代码（必填）
        - start_date: 开始日期(YYYY-MM-DD)
        - end_date: 结束日期(YYYY-MM-DD)
        返回值：EtfDaily QuerySet 列表
        事件：无
        """
        if not ts_code:
            return []

        qs = EtfDaily.objects.filter(ts_code=ts_code)

        def parse_date(s: Optional[str]) -> Optional[datetime.date]:
            if not s:
                return None
            return datetime.strptime(s, '%Y-%m-%d').date()

        sd = parse_date(start_date)
        ed = parse_date(end_date)
        if sd:
            qs = qs.filter(trade_date__gte=sd)
        if ed:
            qs = qs.filter(trade_date__lte=ed)

        return list(qs.order_by('trade_date'))

    def query_daily_latest_all(self) -> List[EtfDaily]:
        """
        查询最近一个交易日的所有ETF日线数据
        功能：获取数据库中最新的 trade_date，并返回该日期下的全部 EtfDaily 记录；同时注解中文简称（csname）。
        参数：无
        返回值：EtfDaily 列表（若库无数据则返回空列表），每条记录包含注解字段 csname（可能为空）。
        事件：无
        """
        latest = (
            EtfDaily.objects.order_by('-trade_date').values_list('trade_date', flat=True).first()
        )
        if not latest:
            return []
        # 通过 ts_code 注解中文简称 csname
        csname_subq = EtfBasic.objects.filter(ts_code=OuterRef('ts_code')).values('csname')[:1]
        qs = (
            EtfDaily.objects.filter(trade_date=latest)
            .order_by('ts_code')
            .annotate(csname=Subquery(csname_subq))
        )
        
        return list(qs)


etf_service = EtfService()