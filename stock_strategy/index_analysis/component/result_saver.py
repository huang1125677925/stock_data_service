"""
预测结果保存组件

功能：
- 将预测出的指数或个股选择结果保存到数据库；
- 在已有记录存在时避免重复写入。

参数：
- 无（通过成员方法传入要保存的字段）。

返回值：
- bool: 是否成功保存（或已存在）。

事件：
- 无
"""

from __future__ import annotations

from typing import Optional

try:
    from stock_strategy.models import StockSelectionRecord
except Exception:
    StockSelectionRecord = None  # 允许在未配置 Django 环境时导入占位


class PredictionResultSaver:
    """
    预测结果保存器

    功能：
    - 负责将预测结果以 `StockSelectionRecord` 形式写入数据库；
    - 支持幂等写入（存在则跳过）。

    参数：
    - 无

    返回值：
    - 无（通过成员方法返回是否保存成功）。

    事件：
    - 无
    """

    def save_selection(
        self,
        ts_code: str,
        trade_date,
        market: str,
        name: str,
        predict_rise_prob_percent: float,
        confidence_percent: float,
        prediction_type: str,
    ) -> bool:
        """
        保存预测选择记录

        功能：
        - 将指定代码与交易日期的概率与置信度等信息保存到 `StockSelectionRecord`；
        - 若记录已存在则不重复创建。

        参数：
        - ts_code(str): 代码；
        - trade_date(date|str): 交易日期，可为 `date` 或 `YYYYMMDD`/`YYYY-MM-DD` 字符串；
        - market(str): 市场，如 `SSE`/`SZSE`/`CN`；
        - name(str): 名称；
        - predict_rise_prob_percent(float): 预测上涨概率的百分比数值，如 77.18；
        - confidence_percent(float): 置信度百分比数值；
        - prediction_type(str): 预测类型标识，如 `MACD_XGBoost_for_5`。

        返回值：
        - bool: True 表示新建成功或已存在；False 表示保存失败。

        事件：
        - 无
        """
        if StockSelectionRecord is None:
            # 在无 Django 环境时直接视为保存成功（便于离线流程）
            return True

        # trade_date 统一转换为 date
        from datetime import datetime, date as _date
        if isinstance(trade_date, str):
            try:
                trade_date_dt = datetime.strptime(trade_date, '%Y%m%d').date()
            except ValueError:
                trade_date_dt = datetime.strptime(trade_date, '%Y-%m-%d').date()
        elif isinstance(trade_date, _date):
            trade_date_dt = trade_date
        else:
            raise ValueError('trade_date 必须为字符串或 date 类型')

        exists = StockSelectionRecord.objects.filter(code=ts_code, trade_date=trade_date_dt).exists()
        if exists:
            return True

        try:
            StockSelectionRecord.objects.create(
                market=market,
                code=ts_code,
                name=name,
                trade_date=trade_date_dt,
                predict_rise_prob=predict_rise_prob_percent,
                confidence=confidence_percent,
                prediction_type=prediction_type,
            )
            return True
        except Exception as e:
            print(f"保存预测选择记录失败：{e}")
            return False