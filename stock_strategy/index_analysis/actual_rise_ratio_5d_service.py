import sys
import os
from pathlib import Path
import django

# 设置Django环境，确保在脚本/任务中可直接导入模型与配置
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_data_service.settings')
django.setup()
"""
组件：5日实际上涨比例计算与更新服务（actual_rise_ratio_5d_service）

功能：
- 遍历 `StockSelectionRecord` 中 `actual_rise_ratio_5d` 为空的记录，
  拉取交易日到交易日+5天的指数日线数据（index_daily），
  计算这几天日线数据中最高价减去最低价对应交易日收盘价的比例值，
  并将结果保存到 `actual_rise_ratio_5d` 字段。

参数：
- compute_actual_rise_ratio_5d(ts_code: str, trade_date: date, token: Optional[str] = None) -> Optional[Decimal]
  - ts_code: Tushare基金代码（ETF），如 `510330.SH`
  - trade_date: 交易日期（Date）
  - token: 可选 Tushare Token

- update_actual_rise_ratio_5d(stock_code: Optional[str] = None,
                              prediction_type: Optional[str] = None,
                              token: Optional[str] = None,
                              dry_run: bool = False,
                              limit: Optional[int] = None) -> dict
  - stock_code: 可选，指定只处理某个代码的记录（需为 Tushare ts_code 形态，如 `510330.SH`）
  - prediction_type: 可选，按预测类型筛选（如 `MACD_XGBoost`）
  - token: 可选 Tushare Token，用于数据拉取
  - dry_run: 是否仅计算不入库（默认 False）
  - limit: 限制处理记录数（默认 None 不限制）

返回值：
- compute_actual_rise_ratio_5d: 返回 Decimal 百分比（保留两位小数），若无法计算则返回 None。
- update_actual_rise_ratio_5d: 返回字典统计结果，包含 processed/updated/skipped/errors。

事件：
- 调用本模块 `fetch_index_daily` 代理 Tushare `index_daily` 接口获取指数日线数据。
- 根据计算结果更新 `StockSelectionRecord.actual_rise_ratio_5d` 字段。

说明：
- 本服务假设 `StockSelectionRecord.code` 为 Tushare `ts_code`（带市场后缀，如 `.SH`/`.SZ`）。
- 若代码不含市场后缀，无法确定所属市场，将跳过该记录并记录错误信息。
"""

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any, List

from django.db import transaction

from stock_strategy.models import StockSelectionRecord
from common.tushare_proxy import call_tushare


def fetch_index_daily(
    ts_code: Optional[str] = None,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    fields: Optional[str] = 'ts_code,trade_date,high,low,close',
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    组件：指数日线行情拉取（fetch_index_daily）

    功能：
    - 代理调用 Tushare `index_daily` 接口，获取指数日频行情数据。
    - 支持按代码与日期区间过滤。

    参数：
    - ts_code(str, 可选): 指数代码，如 `399300.SZ`
    - trade_date(str, 可选): 交易日期 `YYYYMMDD`
    - start_date(str, 可选): 开始日期 `YYYYMMDD`
    - end_date(str, 可选): 结束日期 `YYYYMMDD`
    - fields(str, 可选): 返回字段列表，逗号分隔（默认 `ts_code,trade_date,high,low,close`）
    - token(str, 可选): Tushare Token

    返回值：
    - dict: { code, message, data: { interface, count, records } }

    事件：
    - 调用 common.tushare_proxy.call_tushare
    """
    params: Dict[str, str] = {}
    if ts_code:
        params['ts_code'] = ts_code
    if trade_date:
        params['trade_date'] = trade_date
    if start_date:
        params['start_date'] = start_date
    if end_date:
        params['end_date'] = end_date

    resp = call_tushare(
        interface='idx_factor_pro',
        params=params,
        fields=fields,
        token=token,
        use_query=False,
    )
    return resp


def compute_actual_rise_ratio_5d(ts_code: str, trade_date: date, token: Optional[str] = None) -> Optional[Decimal]:
    """
    组件：计算5日实际上涨比例（compute_actual_rise_ratio_5d）

    功能：
    - 拉取交易日到交易日+5天的指数日线数据，计算区间最高价与最低价的差值，
      再除以交易日当日的收盘价，得到百分比（保留两位小数）。

    参数：
    - ts_code(str): Tushare基金代码（ETF），如 `510330.SH`
    - trade_date(date): 交易日期
    - token(str | None): 可选 Tushare Token

    返回值：
    - Decimal | None: 百分比，若数据不足或计算失败返回 None

    事件：
    - 调用 `fetch_index_daily` 获取指数日线数据
    """
    # 构造日期区间（包含交易日当日）
    start_str = trade_date.strftime('%Y%m%d')
    end_str = (trade_date + timedelta(days=5)).strftime('%Y%m%d')

    # 拉取所需字段，尽量精简
    resp = fetch_index_daily(
        ts_code=ts_code,
        start_date=start_str,
        end_date=end_str,
        fields='ts_code,trade_date,high,low,close',
        token=token,
    )

    if not isinstance(resp, dict) or resp.get('code') != 200:
        return None

    data = resp.get('data') or {}
    records: List[Dict[str, Any]] = data.get('records') or []
    if not records:
        return None

    # 找到交易日当日的收盘价作为分母
    trade_day_row = next((r for r in records if str(r.get('trade_date')) == start_str), None)
    if not trade_day_row:
        return None

    try:
        close_on_trade = float(trade_day_row.get('low'))
    except (TypeError, ValueError):
        return None
    if close_on_trade <= 0:
        return None

    # 计算区间最高价与最低价
    highs: List[float] = []
    lows: List[float] = []
    for r in records:
        try:
            h = float(r.get('high'))
            l = float(r.get('low'))
            highs.append(h)
            lows.append(l)
        except (TypeError, ValueError):
            # 跳过无效数据行
            continue

    if not highs or not lows:
        return None

    max_high = max(highs)
    min_low = min(lows)
    # 按要求计算比例（百分比值）
    ratio = (max_high - close_on_trade) / close_on_trade * 100.0

    # 保留两位小数
    return Decimal(ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def update_actual_rise_ratio_5d(
    stock_code: Optional[str] = None,
    prediction_type: Optional[str] = None,
    token: Optional[str] = None,
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    组件：批量更新5日实际上涨比例（update_actual_rise_ratio_5d）

    功能：
    - 查询 `StockSelectionRecord` 中 `actual_rise_ratio_5d` 为空的记录，
      按需过滤代码与预测类型，逐条计算并更新入库。

    参数：
    - stock_code(str | None): 仅处理指定代码（需为 Tushare ts_code，含市场后缀）
    - prediction_type(str | None): 仅处理指定预测类型
    - token(str | None): Tushare Token，用于数据拉取
    - dry_run(bool): 仅计算不写库，用于预览（默认 False）
    - limit(int | None): 限制处理数量（默认 None 为不限制）

    返回值：
    - dict: { code, message, data }
      data 包含：processed, updated, skipped, errors(list)

    事件：
    - 读取数据库记录 → 拉取指数日线 → 计算比例 → 更新 `actual_rise_ratio_5d`
    """
    qs = StockSelectionRecord.objects.filter(trade_date__isnull=False)
    if stock_code:
        qs = qs.filter(code=stock_code)
    if prediction_type:
        qs = qs.filter(prediction_type=prediction_type)

    if limit is not None and limit > 0:
        qs = qs[:limit]

    processed = 0
    updated = 0
    skipped = 0
    errors: List[str] = []

    # 使用事务批量更新，确保一致性
    with transaction.atomic():
        for rec in qs.iterator():
            processed += 1
            ts_code = rec.code or ''

            # 要求 ts_code 形态（包含市场后缀），否则跳过
            if '.' not in ts_code:
                skipped += 1
                errors.append(f"记录ID={rec.id} 代码缺少市场后缀: {ts_code}")
                continue

            ratio = compute_actual_rise_ratio_5d(ts_code=ts_code, trade_date=rec.trade_date, token=token)
            if ratio is None:
                skipped += 1
                errors.append(f"记录ID={rec.id} 无法计算比例或数据不足: code={ts_code}, date={rec.trade_date}")
                continue

            if not dry_run:
                rec.actual_rise_ratio_5d = ratio
                rec.save(update_fields=['actual_rise_ratio_5d'])
            updated += 1

    return {
        'code': 200,
        'message': 'update completed' if not dry_run else 'dry-run completed',
        'data': {
            'processed': processed,
            'updated': updated,
            'skipped': skipped,
            'errors': errors,
        }
    }

if __name__ == '__main__':
    resp = update_actual_rise_ratio_5d()
    print(resp)