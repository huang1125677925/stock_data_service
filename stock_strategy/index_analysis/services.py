from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
import joblib
import pandas as pd

from django.db.models import QuerySet

from common.tushare_proxy import call_tushare
from stock_market.models import IndexBasicData
from .macd_xgboost import MACDPredictor


def _fmt_date(dt: datetime) -> str:
    """
    日期格式化工具

    功能：将 datetime 转换为 Tushare 需要的 `YYYYMMDD` 字符串。
    参数：
    - dt: datetime 对象
    返回值：
    - 格式化后的日期字符串
    事件：无
    """
    return dt.strftime("%Y%m%d")


def filter_macd_golden_cross_indices(
    ts_codes: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    筛选 MACD 金叉的指数

    功能：
    - 基于 Tushare 指数技术面因子接口（idx_factor_pro），对给定或数据库中的指数集合进行 MACD 金叉筛选。
      金叉判定规则：前一交易日 DIF <= DEA 且当前交易日 DIF > DEA。

    参数：
    - ts_codes(List[str], 可选)：指数 ts_code 列表，如 ['000001.SH', '399001.SZ']；为空时读取数据库中的所有指数基础数据。
    - start_date(str, 可选)：开始日期，格式 'YYYYMMDD'；为空时默认取最近 20 个自然日作为起始（由 Tushare过滤至交易日）。
    - end_date(str, 可选)：结束日期，格式 'YYYYMMDD'；为空时默认使用当前日期。
    - token(str, 可选)：Tushare Token，优先使用传入值，其次读取环境变量。

    返回值：
    - dict：结构如下
        {
          'success': True/False,
          'data': {
              'total': <int>,
              'list': [
                  {
                      'ts_code': str,
                      'name': str,
                      'trade_date': str,
                      'dif': float,
                      'dea': float,
                      'macd': float
                  }, ...
              ],
              'query': { 'start_date': str, 'end_date': str, 'count_checked': int }
          },
          'message': str
        }

    事件：
    - 读取指数基础数据（当 ts_codes 未提供时）
    - 调用 Tushare idx_factor_pro 接口获取技术面因子
    - 依据最近两个交易日的 DIF/DEA 判断是否形成金叉
    - 汇总结果并返回供视图层统一封装响应
    """

    try:
        # 准备指数代码集合
        if ts_codes is None:
            qs: QuerySet[IndexBasicData] = IndexBasicData.objects.all().only("code", "name")
            codes = [(item.code, item.name) for item in qs]
        else:
            # 当提供 ts_codes 时，尝试补充名称（若存在于数据库）
            name_map = {
                obj.code: obj.name for obj in IndexBasicData.objects.filter(code__in=ts_codes).only("code", "name")
            }
            codes = [(code, name_map.get(code, code)) for code in ts_codes]

        # 默认日期范围：最近 20 个自然日到今天（由 Tushare 返回有效交易日）
        if end_date is None:
            end_date = _fmt_date(datetime.now())
        if start_date is None:
            start_date = _fmt_date(datetime.now() - timedelta(days=20))

        results: List[Dict[str, Any]] = []
        checked_count = 0

        for ts_code, name in codes:
            checked_count += 1

            # 仅请求必要字段以提高效率
            fields = "ts_code,trade_date,macd_dif_bfq,macd_dea_bfq,macd_bfq"
            resp = call_tushare(
                interface="idx_factor_pro",
                params={
                    "ts_code": ts_code,
                    "start_date": start_date,
                    "end_date": end_date,
                },
                token=token,
                fields=fields,
                use_query=False,
            )

            if resp.get("code") != 200:
                # 跳过当前指数并继续
                continue

            records = (resp.get("data", {}) or {}).get("records", [])
            if not records or len(records) < 2:
                # 至少需要最近两个交易日数据判断金叉
                continue

            # 按交易日升序排序，确保 last_two 为最新两天
            sorted_records = sorted(records, key=lambda r: r.get("trade_date", ""))
            last_two = sorted_records[-2:]

            prev = last_two[0]
            curr = last_two[1]

            try:
                prev_dif = float(prev.get("macd_dif_bfq"))
                prev_dea = float(prev.get("macd_dea_bfq"))
                curr_dif = float(curr.get("macd_dif_bfq"))
                curr_dea = float(curr.get("macd_dea_bfq"))
                curr_macd = float(curr.get("macd_bfq"))
            except (TypeError, ValueError):
                # 数据缺失或类型异常，跳过
                continue

            is_golden_cross = (prev_dif <= prev_dea) and (curr_dif > curr_dea)

            if is_golden_cross:
                results.append({
                    "ts_code": ts_code,
                    "name": name,
                    "trade_date": curr.get("trade_date"),
                    "dif": curr_dif,
                    "dea": curr_dea,
                    "macd": curr_macd,
                })

        message = f"共检查 {checked_count} 个指数，筛选到 {len(results)} 个出现MACD金叉的指数"

        return {
            "success": True,
            "data": {
                "total": len(results),
                "list": results,
                "query": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "count_checked": checked_count,
                },
            },
            "message": message,
        }

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"筛选MACD金叉指数失败: {str(e)}",
        }


def get_macd_xgb_recent_growth_dates(
    ts_code: str,
    days: int = 30,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    使用已保存的MACD XGBoost模型，返回指定指数最近30天预测为上涨的交易日期列表

    功能：
    - 加载本地保存的 `macd_xgb_up.joblib` 模型文件。
    - 获取指定指数的最近一段时间数据（包含模型所需的技术面字段）。
    - 通过模型批量预测，筛选最近 `days` 天内预测类别为“增长”的交易日期。

    参数：
    - ts_code(str): 指数TS代码，如 '000001.SH'
    - days(int, 可选): 返回最近多少个交易日的预测结果，默认30
    - token(str, 可选): 覆盖Tushare环境变量的Token

    返回值：
    - dict：
        {
          'success': True/False,
          'data': {
              'ts_code': str,
              'list': [str, ...],
              'count': int,
              'params': {
                  'lookback_days': int,
                  'forecast_days': int,
                  'growth_threshold': float
              }
          },
          'message': str
        }

    事件：
    - 加载本地模型文件
    - 调用Tushare idx_factor_pro获取原始数据
    - 进行批量预测并筛选最近days天内的预测日期
    """
    try:
        # 加载模型文件
        model_path = Path(__file__).resolve().parent / "models" / "macd_xgb_up.joblib"
        if not model_path.exists():
            return {
                'success': False,
                'data': None,
                'message': f"模型文件不存在: {model_path}。请先运行 main_predict() 生成模型。",
            }

        artifacts = joblib.load(model_path)
        params = artifacts.get('params', {})
        lookback_days = int(params.get('lookback_days', 60))
        forecast_days = int(params.get('forecast_days', 5))
        growth_threshold = float(params.get('growth_threshold', 0.06))

        # 构建预测器并加载已训练好的组件
        predictor = MACDPredictor(
            lookback_days=lookback_days,
            forecast_days=forecast_days,
            growth_threshold=growth_threshold,
            target_mode='up',
        )
        predictor.model = artifacts.get('model')
        predictor.scaler = artifacts.get('scaler')
        predictor.feature_columns = artifacts.get('feature_columns', [])

        # 获取最近一段时间的原始数据（包含回看期 + 最近days）
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=lookback_days + days + 20)).strftime('%Y%m%d')
        fields = (
            'ts_code,trade_date,open,high,low,close,'
            'macd_bfq,macd_dif_bfq,macd_dea_bfq'
        )
        resp = call_tushare(
            interface='idx_factor_pro',
            params={'ts_code': ts_code, 'start_date': start_date, 'end_date': end_date},
            fields=fields,
            token=token,
            use_query=False,
        )
        if not isinstance(resp, dict) or resp.get('code') != 200:
            message = resp.get('message') if isinstance(resp, dict) else str(resp)
            return {
                'success': False,
                'data': None,
                'message': f"获取Tushare数据失败: {message}",
            }

        records = resp.get('data', {}).get('records', [])
        df = pd.DataFrame(records)
        if df.empty:
            return {
                'success': False,
                'data': None,
                'message': '未获取到有效数据，请检查ts_code与时间范围',
            }
        df = df.sort_values('trade_date').reset_index(drop=True)

        # 进行批量预测，获取增长日期（推理模式在类方法内部处理）
        all_growth_dates = predictor.predict_all_growth_dates(df)

        # 仅返回最近days个交易日内的日期
        recent_trade_dates = df['trade_date'].astype(str).tolist()
        recent_trade_dates = recent_trade_dates[-days:] if len(recent_trade_dates) >= days else recent_trade_dates
        recent_growth_dates = [d for d in all_growth_dates if d in set(recent_trade_dates)]

        return {
            'success': True,
            'data': {
                'ts_code': ts_code,
                'list': sorted(recent_growth_dates),
                'count': len(recent_growth_dates),
                'params': {
                    'lookback_days': lookback_days,
                    'forecast_days': forecast_days,
                    'growth_threshold': growth_threshold,
                }
            },
            'message': f"成功获取最近{days}天内预测为上涨的交易日期",
        }

    except Exception as e:
        return {
            'success': False,
            'data': None,
            'message': f"预测失败: {str(e)}",
        }