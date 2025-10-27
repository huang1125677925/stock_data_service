import logging
from datetime import datetime, timedelta
from typing import List, Dict

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q

from common.response import success_response, error_response
from indival_stock_data.models import IndividualStockDaily
import pandas as pd
import akshare as ak

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


@csrf_exempt
@require_http_methods(["GET"])
def get_market_nh_nl(request):
    """
    A股市场创新高/新低家数(NH-NL)接口

    Query Params:
    - days: 窗口期，默认250
    - end_date: 截止日期，格式YYYYMMDD，可选
    - start_date: 起始日期，格式YYYYMMDD，可选
    - limit: 处理的股票数量上限，默认300
    """
    try:
        days = int(request.GET.get('days', 250))
        if days < 20:
            days = 20
        limit = int(request.GET.get('limit', 300))
        end_date = request.GET.get('end_date')
        start_date = request.GET.get('start_date')

        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        if not start_date:
            end_dt = datetime.strptime(end_date, '%Y%m%d').date()
            start_dt = end_dt - timedelta(days=days * 2)
            start_date = start_dt.strftime('%Y%m%d')

        # 获取股票代码
        try:
            stock_info = ak.stock_info_a_code_name()
            stock_codes = stock_info['code'].astype(str).tolist()
        except Exception as e:
            return error_response(f'获取股票列表失败: {str(e)}', 500)

        if limit and limit > 0:
            stock_codes = stock_codes[:limit]

        all_nh_counts = pd.Series(dtype=float)
        all_nl_counts = pd.Series(dtype=float)

        for code in stock_codes:
            try:
                df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date)
                if df is None or df.empty:
                    continue
                if not {'日期', '最高', '最低'}.issubset(df.columns):
                    continue
                df['日期'] = pd.to_datetime(df['日期'])
                df.set_index('日期', inplace=True)
                df.sort_index(inplace=True)

                df['N_day_high'] = df['最高'].rolling(window=days, min_periods=days).max()
                df['N_day_low'] = df['最低'].rolling(window=days, min_periods=days).min()

                df['is_new_high'] = ((df['最高'] >= df['N_day_high']) & df['N_day_high'].notna()).astype(int)
                df['is_new_low'] = ((df['最低'] <= df['N_day_low']) & df['N_day_low'].notna()).astype(int)

                nh_series = df['is_new_high']
                nl_series = df['is_new_low']

                all_nh_counts = all_nh_counts.add(nh_series, fill_value=0)
                all_nl_counts = all_nl_counts.add(nl_series, fill_value=0)
            except Exception as e:
                logger.warning(f'处理股票 {code} 时出错: {e}')
                continue

        if all_nh_counts.empty and all_nl_counts.empty:
            return error_response('无法计算NH-NL：无有效数据', 404)

        all_nh_counts = all_nh_counts.sort_index()
        all_nl_counts = all_nl_counts.reindex(all_nh_counts.index, fill_value=0)
        nh_nl_series = all_nh_counts - all_nl_counts

        output = []
        for date, nhnl in nh_nl_series.items():
            output.append({
                'date': date.date().isoformat(),
                'new_high_count': int(all_nh_counts.get(date, 0)),
                'new_low_count': int(all_nl_counts.get(date, 0)),
                'nh_nl': int(nhnl)
            })

        if output:
            start_out = output[0]['date']
            end_out = output[-1]['date']
        else:
            start_out = datetime.strptime(start_date, '%Y%m%d').date().isoformat()
            end_out = datetime.strptime(end_date, '%Y%m%d').date().isoformat()

        result = {
            'query': {
                'days': days,
                'start_date': start_out,
                'end_date': end_out,
                'limit': limit,
            },
            'daily': output,
            'timestamp': datetime.now().isoformat()
        }
        return success_response(result)
    except ValueError as e:
        return error_response(f'参数错误: {str(e)}', 400)
    except Exception as e:
        logger.exception('计算NH-NL失败')
        return error_response(f'计算NH-NL失败: {str(e)}', 500)