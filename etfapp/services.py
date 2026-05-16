from collections import defaultdict
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from django.db.models import Q
from common.tushare_proxy import call_tushare
from index_data.utils import replace_nan
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

    def _fetch_index_basic_map(self) -> Dict[str, Dict[str, Any]]:
        """
        查询指数基础信息映射
        功能：从 Tushare 拉取 index_basic，构建 index_code -> 元信息映射。
        参数：无
        返回值：dict，键为指数代码，值为指数元信息。
        事件：无
        """
        resp = call_tushare(
            interface='index_basic',
            params={},
            fields='ts_code,name,fullname,publisher,category',
            use_query=False,
        )
        if resp.get('code') != 200:
            raise RuntimeError(
                resp.get('error') or resp.get('message') or '获取指数基础信息失败'
            )

        records = self._only_dict_records((resp.get('data') or {}).get('records') or [])
        return {
            str(item.get('ts_code')): replace_nan(item)
            for item in records
            if item.get('ts_code')
        }

    def _matches_keyword(self, value: Optional[str], keyword: str) -> bool:
        return keyword.lower() in (value or '').lower()

    def _only_dict_records(self, records: Any) -> List[Dict[str, Any]]:
        """
        过滤仅保留字典型记录
        功能：兼容外部接口 records 中混入 None/非 dict 的情况。
        参数：
        - records: 任意类型记录集合
        返回值：dict 列表
        事件：无
        """
        if not isinstance(records, list):
            return []
        return [item for item in records if isinstance(item, dict)]

    def _build_group_analysis(self, items: List[Dict[str, Any]], group_by: str) -> List[Dict[str, Any]]:
        """
        构建分组分析结果
        功能：按指定字段聚合 ETF 数量、成交额与涨跌幅概览。
        参数：
        - items: ETF 行情列表
        - group_by: 分组字段，仅支持 index_publisher/index_category
        返回值：分组分析结果列表
        事件：无
        """
        grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for item in items:
            key = item.get(group_by) or '未分类'
            grouped[str(key)].append(item)

        analysis: List[Dict[str, Any]] = []
        for group_value, group_items in grouped.items():
            pct_values = [
                float(item['pct_chg'])
                for item in group_items
                if item.get('pct_chg') is not None
            ]
            amount_values = [
                float(item['amount'])
                for item in group_items
                if item.get('amount') is not None
            ]
            analysis.append(
                {
                    'group_by': group_by,
                    'group_value': group_value,
                    'etf_count': len(group_items),
                    'index_count': len({item.get('index_code') for item in group_items if item.get('index_code')}),
                    'avg_pct_chg': round(sum(pct_values) / len(pct_values), 4) if pct_values else None,
                    'up_count': sum(1 for val in pct_values if val > 0),
                    'down_count': sum(1 for val in pct_values if val < 0),
                    'flat_count': sum(1 for val in pct_values if val == 0),
                    'total_amount': round(sum(amount_values), 2) if amount_values else None,
                    'sample_index_names': sorted(
                        {
                            item.get('index_name')
                            for item in group_items
                            if item.get('index_name')
                        }
                    )[:10],
                }
            )

        analysis.sort(key=lambda item: (-item['etf_count'], item['group_value']))
        return analysis

    def query_daily_latest_all(
        self,
        index_publisher: Optional[str] = None,
        index_category: Optional[str] = None,
        group_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        查询最近一个有数据交易日的所有ETF日线数据
        功能：从 Tushare 交易日历倒序定位最近交易日，拉取该日期下全部 ETF 日线行情，
        并支持按所跟踪指数的发布机构/类别筛选与分组分析。
        参数：
        - index_publisher: 指数发布机构筛选（模糊匹配）
        - index_category: 指数类别/主题筛选（匹配 category、name、fullname）
        - group_by: 分组字段，可选 index_publisher/index_category
        返回值：dict，包含 trade_date/items/analysis/filters。
        事件：无
        """
        end_dt = datetime.now().date()
        start_dt = end_dt - timedelta(days=14)

        trade_cal_resp = call_tushare(
            interface='trade_cal',
            params={
                'exchange': '',
                'start_date': start_dt.strftime('%Y%m%d'),
                'end_date': end_dt.strftime('%Y%m%d'),
                'is_open': '1',
            },
            fields='cal_date,is_open',
            use_query=False,
        )
        if trade_cal_resp.get('code') != 200:
            raise RuntimeError(
                trade_cal_resp.get('error') or trade_cal_resp.get('message') or '获取交易日历失败'
            )

        open_dates = sorted(
            [
                str(item.get('cal_date'))
                for item in self._only_dict_records((trade_cal_resp.get('data') or {}).get('records', []))
                if item.get('cal_date')
            ],
            reverse=True,
        )
        if not open_dates:
            return {'trade_date': None, 'items': [], 'analysis': [], 'filters': {}}

        fields = 'ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount'
        index_basic_map = self._fetch_index_basic_map()
        for trade_date in open_dates:
            daily_resp = call_tushare(
                interface='fund_daily',
                params={'trade_date': trade_date},
                fields=fields,
                use_query=False,
            )
            if daily_resp.get('code') != 200:
                raise RuntimeError(
                    daily_resp.get('error') or daily_resp.get('message') or '获取 ETF 日线失败'
                )

            records = self._only_dict_records((daily_resp.get('data') or {}).get('records') or [])
            if not records:
                continue

            ts_codes = [item.get('ts_code') for item in records if item.get('ts_code')]
            etf_basic_map = {
                item['ts_code']: item
                for item in EtfBasic.objects.filter(ts_code__in=ts_codes).values(
                    'ts_code',
                    'csname',
                    'index_code',
                    'index_name',
                    'mgr_name',
                )
            }

            items: List[Dict[str, Any]] = []
            for item in records:
                normalized = dict(item)
                etf_basic = etf_basic_map.get(normalized.get('ts_code')) or {}
                index_code = etf_basic.get('index_code')
                index_basic = index_basic_map.get(str(index_code)) if index_code else {}
                if not isinstance(index_basic, dict):
                    index_basic = {}
                raw_trade_date = str(normalized.get('trade_date') or '')
                if len(raw_trade_date) == 8:
                    normalized['trade_date'] = (
                        f'{raw_trade_date[:4]}-{raw_trade_date[4:6]}-{raw_trade_date[6:]}'
                    )
                normalized['csname'] = etf_basic.get('csname')
                normalized['mgr_name'] = etf_basic.get('mgr_name')
                normalized['index_code'] = index_code
                normalized['index_name'] = etf_basic.get('index_name') or index_basic.get('name')
                normalized['index_publisher'] = index_basic.get('publisher')
                normalized['index_category'] = index_basic.get('category')
                normalized['index_fullname'] = index_basic.get('fullname')
                items.append(replace_nan(normalized))

            if index_publisher:
                items = [
                    item for item in items
                    if self._matches_keyword(item.get('index_publisher'), index_publisher)
                ]
            if index_category:
                items = [
                    item for item in items
                    if (
                        self._matches_keyword(item.get('index_category'), index_category)
                        or self._matches_keyword(item.get('index_name'), index_category)
                        or self._matches_keyword(item.get('index_fullname'), index_category)
                    )
                ]

            items.sort(key=lambda item: item.get('ts_code') or '')
            analysis = []
            if group_by in {'index_publisher', 'index_category'}:
                analysis = self._build_group_analysis(items, group_by)
            return {
                'trade_date': items[0].get('trade_date') if items else f'{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}',
                'items': items,
                'analysis': analysis,
                'filters': {
                    'index_publisher': index_publisher,
                    'index_category': index_category,
                    'group_by': group_by,
                },
            }

        return {
            'trade_date': None,
            'items': [],
            'analysis': [],
            'filters': {
                'index_publisher': index_publisher,
                'index_category': index_category,
                'group_by': group_by,
            },
        }


etf_service = EtfService()
