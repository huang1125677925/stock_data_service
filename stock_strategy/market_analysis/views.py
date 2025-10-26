import logging
from datetime import datetime, timedelta
from typing import List, Dict

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q

from common.response import success_response, error_response
from indival_stock_data.models import IndividualStockDaily

logger = logging.getLogger(__name__)


def _get_latest_trading_date() -> datetime.date:
    latest = (
        IndividualStockDaily.objects
        .filter(stock__index_type__isnull=True)
        .order_by('-date')
        .values_list('date', flat=True)
        .first()
    )
    return latest


def _fetch_daily_breadth(start_date: str = None, end_date: str = None, limit_days: int = 30) -> List[Dict]:
    """
    获取指定日期范围内（最多limit_days）的每日涨跌家数统计。
    仅统计 `IndividualStock.index_type is NULL` 的股票。
    返回按日期升序的列表。
    """
    qs = IndividualStockDaily.objects.filter(stock__index_type__isnull=True)

    if start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)

    # 聚合按日期的涨跌平家数
    grouped = (
        qs.values('date')
          .annotate(
              adv_count=Count('id', filter=Q(change_percent__gt=0)),
              decl_count=Count('id', filter=Q(change_percent__lt=0)),
              flat_count=Count('id', filter=Q(change_percent=0)),
          )
          .order_by('date')
    )

    data = list(grouped)
    if not data:
        return []

    # 限制最多limit_days天（从末尾倒数）
    if len(data) > limit_days:
        data = data[-limit_days:]
    return data


@csrf_exempt
@require_http_methods(["GET"])
def get_market_adr(request):
    """
    涨跌家数比（ADR）接口

    - 统计最近N日（默认10日，最大不超过30日）内，上涨家数之和 / 下跌家数之和。
    - 同时返回按日的涨跌平家数与当日ADR，便于观察波动。 

    Query Params:
    - days: 统计天数，默认10，范围1-30
    - start_date/end_date: 自定义日期范围（YYYY-MM-DD），跨度不超过30天；优先级高于days
    """
    try:
        days_param = request.GET.get('days')
        days = int(days_param) if days_param else 10
        if days < 1:
            return error_response('参数 days 必须大于等于1', 400)
        if days > 30:
            days = 30  # 强制上限

        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        # 如果未提供日期范围，则以数据库最新交易日为终点，取days个交易日
        if not start_date or not end_date:
            latest = _get_latest_trading_date()
            if not latest:
                return error_response('无可用个股日频数据', 404)
            end_date = end_date or latest.isoformat()
            # 先取宽一点的范围，再在函数里裁剪到最多30天
            start_dt = datetime.fromisoformat(end_date).date() - timedelta(days=days * 2)
            start_date = start_dt.isoformat()

        # 校验跨度不超过30天
        start_dt = datetime.fromisoformat(start_date).date()
        end_dt = datetime.fromisoformat(end_date).date()
        if (end_dt - start_dt).days > 60:  # 允许宽取，再由fetch裁剪到30天
            logger.info('日期跨度较大，结果将按最近30个交易日裁剪')

        daily = _fetch_daily_breadth(start_date, end_date, limit_days=30)
        if not daily:
            return error_response('指定范围内无数据', 404)

        # 若用户传了days，小于取到的天数，则只取最后days天
        if days and len(daily) > days:
            daily = daily[-days:]

        adv_sum = sum(d['adv_count'] for d in daily)
        decl_sum = sum(d['decl_count'] for d in daily)
        adr_value = float(adv_sum) / float(decl_sum) if decl_sum > 0 else None

        # 构建每日ADR
        daily_output = []
        for d in daily:
            daily_adr = float(d['adv_count']) / float(d['decl_count']) if d['decl_count'] > 0 else None
            daily_output.append({
                'date': d['date'].isoformat(),
                'adv_count': d['adv_count'],
                'decl_count': d['decl_count'],
                'flat_count': d['flat_count'],
                'daily_adr': daily_adr
            })

        result = {
            'query': {
                'days': days,
                'start_date': daily_output[0]['date'],
                'end_date': daily_output[-1]['date']
            },
            'aggregated': {
                'adv_sum': adv_sum,
                'decl_sum': decl_sum,
                'adr': adr_value,
                'typical_range': [0.5, 1.5]
            },
            'daily': daily_output,
            'total_days': len(daily),
            'timestamp': datetime.now().isoformat()
        }
        return success_response(result)
    except ValueError as e:
        return error_response(f'参数错误: {str(e)}', 400)
    except Exception as e:
        logger.exception('计算ADR失败')
        return error_response(f'计算ADR失败: {str(e)}', 500)


@csrf_exempt
@require_http_methods(["GET"])
def get_market_adl(request):
    """
    腾落指标（ADL）接口

    - 统计每日（上涨家数 - 下跌家数），并从基期开始累计求和。
    - 基期取所选范围的第一天（最多30个交易日）。

    Query Params:
    - days: 最大天数，默认10，范围1-30；若提供start_date/end_date，则忽略days并按范围裁剪至30天
    - start_date/end_date: 自定义日期范围（YYYY-MM-DD），跨度不超过30个交易日（自动裁剪）
    """
    try:
        days_param = request.GET.get('days')
        days = int(days_param) if days_param else 10
        if days < 1:
            return error_response('参数 days 必须大于等于1', 400)
        if days > 30:
            days = 30

        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        if not start_date or not end_date:
            latest = _get_latest_trading_date()
            if not latest:
                return error_response('无可用个股日频数据', 404)
            end_date = end_date or latest.isoformat()
            start_dt = datetime.fromisoformat(end_date).date() - timedelta(days=days * 2)
            start_date = start_dt.isoformat()

        daily = _fetch_daily_breadth(start_date, end_date, limit_days=30)
        if not daily:
            return error_response('指定范围内无数据', 404)
        if days and len(daily) > days:
            daily = daily[-days:]

        # 计算ADL累计值
        adl_series = []
        cumulative = 0
        for d in daily:
            diff = int(d['adv_count']) - int(d['decl_count'])
            cumulative += diff
            adl_series.append({
                'date': d['date'].isoformat(),
                'advance_count': int(d['adv_count']),
                'decline_count': int(d['decl_count']),
                'flat_count': int(d['flat_count']),
                'daily_diff': diff,
                'adl_cumulative': cumulative
            })

        result = {
            'query': {
                'days': days,
                'start_date': adl_series[0]['date'],
                'end_date': adl_series[-1]['date']
            },
            'adl': adl_series,
            'final_adl': cumulative,
            'timestamp': datetime.now().isoformat()
        }
        return success_response(result)
    except ValueError as e:
        return error_response(f'参数错误: {str(e)}', 400)
    except Exception as e:
        logger.exception('计算ADL失败')
        return error_response(f'计算ADL失败: {str(e)}', 500)