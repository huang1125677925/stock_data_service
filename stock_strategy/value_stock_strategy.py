import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from django.conf import settings
from django.core.cache import cache

from common.tushare_proxy import call_tushare
from index_data.utils import replace_nan
from indival_stock_data.models import IndividualStock


class ValueStockStrategyService:
    """
    价值股筛选服务
    功能：基于 Tushare 最新财报数据，筛选营收正增长且净利润靠前的股票。
    """

    income_fields = (
        'ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,'
        'total_revenue,revenue,n_income,n_income_attr_p'
    )
    indicator_fields = (
        'ts_code,end_date,or_yoy,q_sales_yoy,netprofit_yoy,q_profit_yoy,'
        'roe,grossprofit_margin'
    )

    def __init__(self):
        self.cache_timeout = getattr(settings, 'STOCK_CACHE_TIMEOUT', 3600)

    def _safe_float(self, value: Any) -> Optional[float]:
        if value is None or value == '':
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    def _safe_round(self, value: Any, digits: int = 2) -> Optional[float]:
        number = self._safe_float(value)
        return round(number, digits) if number is not None else None

    def _recent_report_periods(self, count: int = 8) -> List[str]:
        today = datetime.now().date()
        periods: List[str] = []
        year = today.year
        quarter_ends = ['1231', '0930', '0630', '0331']

        while len(periods) < count:
            for suffix in quarter_ends:
                period = f'{year}{suffix}'
                period_date = datetime.strptime(period, '%Y%m%d').date()
                if period_date <= today:
                    periods.append(period)
                    if len(periods) >= count:
                        break
            year -= 1

        return periods

    def _only_dict_records(self, records: Any) -> List[Dict[str, Any]]:
        if not isinstance(records, list):
            return []
        return [item for item in records if isinstance(item, dict)]

    def _fetch_tushare_records(
        self,
        interface: str,
        params: Dict[str, Any],
        fields: str,
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        resp = call_tushare(interface=interface, params=params, fields=fields, use_query=False)
        if resp.get('code') != 200:
            return [], resp.get('error') or resp.get('message') or f'{interface} 调用失败'
        records = self._only_dict_records((resp.get('data') or {}).get('records') or [])
        return records, None

    def _dedupe_latest_report(self, records: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        sorted_records = sorted(
            records,
            key=lambda item: (
                str(item.get('f_ann_date') or item.get('ann_date') or ''),
                str(item.get('report_type') or ''),
            ),
            reverse=True,
        )
        result: Dict[str, Dict[str, Any]] = {}
        for item in sorted_records:
            ts_code = item.get('ts_code')
            if ts_code and ts_code not in result:
                result[str(ts_code)] = item
        return result

    def _stock_name_map(self, ts_codes: Sequence[str]) -> Dict[str, str]:
        code_map = {code.split('.')[0]: code for code in ts_codes if code}
        stocks = IndividualStock.objects.filter(code__in=code_map.keys()).values('code', 'name', 'industry')
        result = {}
        for stock in stocks:
            ts_code = code_map.get(stock['code'])
            if ts_code:
                result[ts_code] = stock.get('name') or ''
        return result

    def screen_value_stocks(
        self,
        *,
        report_period: Optional[str] = None,
        min_revenue_growth: float = 0.0,
        min_net_profit: float = 0.0,
        limit: int = 50,
        lookback_periods: int = 8,
    ) -> Dict[str, Any]:
        """
        筛选价值股
        功能：使用最新可用财报期的收入与财务指标，筛选营收同比正增长且净利润达到阈值的股票。
        """
        limit = max(1, min(int(limit), 2000))
        lookback_periods = max(1, min(int(lookback_periods), 16))
        periods = [report_period] if report_period else self._recent_report_periods(lookback_periods)
        errors: List[Dict[str, str]] = []

        for period in periods:
            cache_key = f'value_stock_screen:{period}:{min_revenue_growth}:{min_net_profit}:{limit}'
            cached = cache.get(cache_key)
            if cached:
                return replace_nan(cached)

            income_records, income_error = self._fetch_tushare_records(
                'income_vip',
                {'period': period},
                self.income_fields,
            )
            if income_error:
                errors.append({'period': period, 'interface': 'income_vip', 'error': income_error})
                continue
            if not income_records:
                errors.append({'period': period, 'interface': 'income_vip', 'error': '无利润表数据'})
                continue

            indicator_records, indicator_error = self._fetch_tushare_records(
                'fina_indicator_vip',
                {'period': period},
                self.indicator_fields,
            )
            if indicator_error:
                errors.append({'period': period, 'interface': 'fina_indicator_vip', 'error': indicator_error})
                indicator_records = []

            income_map = self._dedupe_latest_report(income_records)
            indicator_map = self._dedupe_latest_report(indicator_records)
            name_map = self._stock_name_map(list(income_map.keys()))

            candidates: List[Dict[str, Any]] = []
            for ts_code, income in income_map.items():
                indicator = indicator_map.get(ts_code, {})
                revenue_growth = self._safe_float(indicator.get('or_yoy'))
                if revenue_growth is None:
                    revenue_growth = self._safe_float(indicator.get('q_sales_yoy'))

                net_profit = self._safe_float(income.get('n_income_attr_p'))
                if net_profit is None:
                    net_profit = self._safe_float(income.get('n_income'))

                if revenue_growth is None or net_profit is None:
                    continue
                if revenue_growth <= min_revenue_growth or net_profit < min_net_profit:
                    continue

                total_revenue = self._safe_float(income.get('total_revenue'))
                if total_revenue is None:
                    total_revenue = self._safe_float(income.get('revenue'))

                candidates.append({
                    'ts_code': ts_code,
                    'stock_code': ts_code.split('.')[0],
                    'stock_name': name_map.get(ts_code),
                    'report_period': period,
                    'ann_date': income.get('ann_date'),
                    'f_ann_date': income.get('f_ann_date'),
                    'total_revenue': self._safe_round(total_revenue, 2),
                    'net_profit': self._safe_round(net_profit, 2),
                    'revenue_growth_rate': self._safe_round(revenue_growth, 2),
                    'net_profit_growth_rate': self._safe_round(
                        indicator.get('netprofit_yoy') if indicator.get('netprofit_yoy') is not None else indicator.get('q_profit_yoy'),
                        2,
                    ),
                    'roe': self._safe_round(indicator.get('roe'), 4),
                    'gross_profit_margin': self._safe_round(indicator.get('grossprofit_margin'), 4),
                })

            candidates.sort(
                key=lambda item: (
                    item['net_profit'] if item['net_profit'] is not None else float('-inf'),
                    item['revenue_growth_rate'] if item['revenue_growth_rate'] is not None else float('-inf'),
                ),
                reverse=True,
            )

            payload = replace_nan({
                'report_period': period,
                'total': len(candidates[:limit]),
                'matched_total': len(candidates),
                'filters': {
                    'min_revenue_growth': min_revenue_growth,
                    'min_net_profit': min_net_profit,
                    'limit': limit,
                    'lookback_periods': lookback_periods,
                },
                'data': candidates[:limit],
                'errors': errors,
                'query_time': datetime.now().isoformat(),
            })
            cache.set(cache_key, payload, self.cache_timeout)
            return payload

        return replace_nan({
            'report_period': report_period,
            'total': 0,
            'matched_total': 0,
            'filters': {
                'min_revenue_growth': min_revenue_growth,
                'min_net_profit': min_net_profit,
                'limit': limit,
                'lookback_periods': lookback_periods,
            },
            'data': [],
            'errors': errors,
            'query_time': datetime.now().isoformat(),
        })

    def get_revenue_history(
        self,
        *,
        ts_codes: Sequence[str],
        periods: int = 8,
    ) -> Dict[str, Any]:
        """
        查询营收历史
        功能：按多个股票 ts_code 获取过去若干财报期的营业收入与净利润数据。
        """
        clean_codes = [code.strip().upper() for code in ts_codes if code and code.strip()]
        clean_codes = list(dict.fromkeys(clean_codes))
        periods = max(1, min(int(periods), 16))
        report_periods = self._recent_report_periods(periods)
        wanted = set(clean_codes)
        errors: List[Dict[str, str]] = []
        rows_by_code: Dict[str, List[Dict[str, Any]]] = {code: [] for code in clean_codes}

        for period in report_periods:
            records, error = self._fetch_tushare_records(
                'income_vip',
                {'period': period},
                self.income_fields,
            )
            if error:
                errors.append({'period': period, 'interface': 'income_vip', 'error': error})
                continue

            latest_map = self._dedupe_latest_report(records)
            for ts_code in wanted:
                row = latest_map.get(ts_code)
                if not row:
                    continue
                total_revenue = self._safe_float(row.get('total_revenue'))
                if total_revenue is None:
                    total_revenue = self._safe_float(row.get('revenue'))
                net_profit = self._safe_float(row.get('n_income_attr_p'))
                if net_profit is None:
                    net_profit = self._safe_float(row.get('n_income'))
                rows_by_code[ts_code].append({
                    'report_period': period,
                    'ann_date': row.get('ann_date'),
                    'f_ann_date': row.get('f_ann_date'),
                    'total_revenue': self._safe_round(total_revenue, 2),
                    'net_profit': self._safe_round(net_profit, 2),
                })

        name_map = self._stock_name_map(clean_codes)
        data = [
            {
                'ts_code': ts_code,
                'stock_code': ts_code.split('.')[0],
                'stock_name': name_map.get(ts_code),
                'history': rows,
            }
            for ts_code, rows in rows_by_code.items()
        ]

        return replace_nan({
            'total': len(data),
            'periods': report_periods,
            'data': data,
            'errors': errors,
            'query_time': datetime.now().isoformat(),
        })


value_stock_strategy_service = ValueStockStrategyService()
