import sys
import os
from pathlib import Path
import django

# 设置Django环境（用于数据库模型的导入与保存）
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_data_service.settings')
try:
    django.setup()
except Exception:
    # 允许在未配置 Django 环境时作为纯脚本运行
    pass

import time
import datetime
import pandas as pd
from typing import Iterable

try:
    # TuShare 代理（统一响应结构：success_response / error_response）
    from common.tushare_proxy import call_tushare
except Exception:
    call_tushare = None

from stock_strategy.index_analysis.component import (
    DCIndexDataSource,
    SWIndexFeatureExtractor,
    SWIndexModelTrainer,
    SWIndexModelPredictor,
    PredictionResultSaver,
)
from stock_strategy.index_analysis.component.result_notifier import (
    send_macd_xgboost_results_email,
)

class DCIndexXGBPipeline:
    """
    管道封装：东财行业/概念指数 XGBoost 训练与预测（dc_daily）

    功能：
    - 组合数据源、特征提取、模型训练、预测与结果入库组件；
    - 使用本地指数清单与 TuShare `dc_daily` 接口进行数据拉取；
    - 提供训练与推理两个高层方法，简化调用。

    参数：
    - lookback_days(int): 回看天数，默认 60；
    - forecast_days(int): 未来预测天数，默认 5；
    - growth_threshold(float): 上涨阈值，默认 0.05；
    - target_mode(str): 任务类型 'up' 或 'down'；
    - interface_name(str): 数据接口名称，默认 'dc_daily'；
    - list_file_path(str|Path|None): 指数清单文件路径（默认当前目录）。

    返回值：
    - 无（通过成员方法返回训练评估与预测结果）。

    事件：
    - 训练：读取清单 → 拉取日线数据 → 特征工程 → 训练 → 保存模型与 scaler；
    - 推理：读取清单 → 拉取日线数据 → 特征工程 → 载入模型 → 逐代码预测 → （可选）入库。
    """

    def __init__(
        self,
        lookback_days: int = 60,
        forecast_days: int = 5,
        growth_threshold: float = 0.05,
        target_mode: str = 'up',
        interface_name: str = 'dc_daily',
        list_file_path: str | Path | None = None,
    ) -> None:
        self.lookback_days = lookback_days
        self.forecast_days = forecast_days
        self.growth_threshold = growth_threshold
        self.target_mode = target_mode
        self.interface_name = interface_name

        self.feature_extractor = SWIndexFeatureExtractor(
            lookback_days=lookback_days,
            forecast_days=forecast_days,
            growth_threshold=growth_threshold,
            target_mode=target_mode,
        )
        self.trainer = SWIndexModelTrainer()

        self.data_source = DCIndexDataSource(
            list_file_path=list_file_path,
            interface_name=interface_name,
        )

    def _default_model_paths(self) -> tuple[str, str]:
        """
        组件：模型与标准化器默认保存路径（_default_model_paths）

        功能：
        - 在本模块下的 `models/` 目录生成包含任务类型标识的文件名；

        参数：无

        返回值：
        - (model_path, scaler_path): 两个字符串路径。

        事件：无
        """
        model_dir = Path(__file__).resolve().parent / 'models'
        model_dir.mkdir(parents=True, exist_ok=True)
        tag = f'{self.target_mode}'
        model_path = model_dir / f'dc_index_xgb_{tag}.joblib'
        scaler_path = model_dir / f'dc_index_xgb_{tag}_scaler.joblib'
        return str(model_path), str(scaler_path)

    def train(self, start_date: str, end_date: str, limit: int | None = 500) -> dict:
        """
        训练模型并保存

        功能：
        - 读取东财指数清单，拉取 `dc_daily` 日线数据并进行特征工程；
        - 训练 XGBClassifier，保存模型与 scaler。

        参数：
        - start_date(str): 开始日期 YYYYMMDD；
        - end_date(str): 结束日期 YYYYMMDD；
        - limit(int|None): 指数代码数量上限，默认 500。

        返回值：
        - dict: 训练与评估摘要（train_accuracy、test_accuracy、feature_importance 等）。

        事件：
        - 清单 → 日线数据 → 特征工程 → 训练与保存。
        """
        df, _code_map = self.data_source.fetch_dc_daily_dataset(start_date, end_date, limit=limit)
        if df is None or df.empty:
            return {}
        df_features, feature_cols = self.feature_extractor.transform(df, for_inference=False)
        # 仅按特征列与目标清理缺失，避免无关列导致样本被过度丢弃
        df_train = df_features.dropna(subset=feature_cols + ['target'])
        result = self.trainer.train(df_train, feature_cols)
        model_path, scaler_path = self._default_model_paths()
        self.trainer.save(model_path, scaler_path)
        return result

    def predict_and_save(
        self,
        start_date: str,
        end_date: str,
        limit: int | None = None,
        prediction_type: str | None = None,
        prob_threshold: float = 0.3,
    ) -> list[dict]:
        """
        预测并保存到 StockSelectionRecord（示例）

        功能：
        - 读取东财指数清单与 `dc_daily` 数据，进行特征工程，载入模型；
        - 逐 `ts_code` 对最近样本进行预测，打印预测摘要并（可选）入库。

        参数：
        - start_date(str): 开始日期 YYYYMMDD；
        - end_date(str): 结束日期 YYYYMMDD；
        - limit(int|None): 指数代码数量上限；
        - prediction_type(str|None): 预测类型标识，如 `DCIndex_MACD_XGBoost_for_5`；
        - prob_threshold(float): 选择入库的正类概率阈值，默认 0.5。

        返回值：
        - list[dict]: 每个代码的预测与保存状态摘要。

        事件：
        - 清单 → 日线数据 → 特征工程 → 载入模型 → 逐代码预测 → （可选）入库。
        """
        df, code_map = self.data_source.fetch_dc_daily_dataset(start_date, end_date, limit=limit)
        if df is None or df.empty:
            return []

        df_features, feature_cols = self.feature_extractor.transform(df, for_inference=True)
        model_path, scaler_path = self._default_model_paths()
        predictor = SWIndexModelPredictor(model_path=model_path, scaler_path=scaler_path)
        predictor.bind_features(feature_cols)
        saver = PredictionResultSaver()

        out: list[dict] = []
        for code, g in df_features.groupby('ts_code'):
            # 预测阶段的数据在 transform(for_inference=True) 已按特征列清理缺失，
            # 此处不再全量 dropna，避免误删含非关键列缺失的有效样本。
            if g.empty:
                continue
            row = predictor.predict_latest(g)
            trade_date = row['trade_date']
            prob_up = float(row.get('probability_1', 0.0))
            if prob_up < prob_threshold or int(row.get('prediction', 0)) < 1:
                continue
            name = code_map.get(code, {}).get('name') if isinstance(code_map.get(code), dict) else code_map.get(code, code)

            # 如需入库，请取消下面注释并根据业务模型调整字段
            market_tag = 'DC'
            prediction_tag = prediction_type or f"DCIndex_MACD_XGBoost_for_{self.forecast_days}"
            saved = saver.save_selection(
                ts_code=code,
                trade_date=str(trade_date),
                market=market_tag,
                name=name,
                predict_rise_prob_percent=float(prob_up * 100.0),
                confidence_percent=float(row['confidence'] * 100.0),
                prediction_type=prediction_tag,
            )
            print(
                f"预测 {code} {name} {trade_date}  预测值：{int(row['prediction'])} "
                f"上涨概率：{prob_up * 100.0:.2f}%  置信度：{row['confidence'] * 100.0:.2f}% "
            )
            out.append({
                'ts_code': code,
                'trade_date': str(trade_date),
                'prediction': int(row['prediction']),
                'prob_up_percent': float(prob_up * 100.0),
                'confidence_percent': float(row['confidence'] * 100.0),
                'saved': bool(saved),
            })
        return out

    def send_email(
        self,
        start_date: str,
        end_date: str,
        limit: int | None = None,
        prediction_type: str | None = None,
        prob_threshold: float = 0.5,
        usernames: list[str] | None = None,
        sender_email: str = "1125677925@qq.com",
        auth_code: str = "wsxmvqhgoeszigdh",
    ) -> dict:
        """
        组件：管道便捷方法——预测并发送结果邮件（send_email）

        功能：
        - 调用 `predict_and_save` 获取预测命中结果；
        - 整理预测参数并生成 HTML；
        - 调用组件 `send_dc_index_prediction_email` 发送邮件。

        参数：
        - start_date(str): 开始日期 YYYYMMDD；
        - end_date(str): 结束日期 YYYYMMDD；
        - limit(int|None): 指数代码数量上限；
        - prediction_type(str|None): 预测类型标识，如 `DCIndex_MACD_XGBoost_for_5`；
        - prob_threshold(float): 入库的正类概率阈值，默认 0.5；
        - usernames(list[str] | None): 收件用户名列表；为空则使用组件默认集合；
        - sender_email(str): 发件人邮箱地址；
        - auth_code(str): QQ 邮箱 SMTP 授权码。

        返回值：
        - dict: 邮件发送返回结果摘要（emails/scanned_count/hit_count/send_result）。

        事件：
        - 预测 → 组装参数 → 生成 HTML → 发送邮件。
        """

        results = self.predict_and_save(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            prediction_type=prediction_type,
            prob_threshold=prob_threshold,
        )

        params = {
            'start_date': start_date,
            'end_date': end_date,
            'limit': limit,
            'interface_name': self.interface_name,
            'prob_threshold': prob_threshold,
            'prediction_type': prediction_type,
            'forecast_days': self.forecast_days,
            'growth_threshold': self.growth_threshold,
            'target_mode': self.target_mode,
        }

        return send_dc_index_prediction_email(
            results=results,
            params=params,
            usernames=usernames,
            sender_email=sender_email,
            auth_code=auth_code,
        )

    def train_test(self, start_date: str, end_date: str) -> dict:
        """
        训练样例抽查

        功能：
        - 拉取数据与特征工程，打印首个正类样本的特征行，便于快速验证目标生成；

        参数：
        - start_date(str): 开始日期 YYYYMMDD；
        - end_date(str): 结束日期 YYYYMMDD。

        返回值：
        - dict: 包含首个正类样本的行内容（若存在）。

        事件：
        - 清单 → 日线数据 → 特征工程 → 正类样本检索。
        """
        df, _code_map = self.data_source.fetch_dc_daily_dataset(start_date, end_date, limit=500)
        if df is None or df.empty:
            return {}
        df_features, _feature_cols = self.feature_extractor.transform(df, for_inference=False)
        for _, row in df_features.iterrows():
            if row.get('target', 0) >= 0.5:
                print(row)
                return dict(row)
        return {}


def send_dc_index_prediction_email(
    results: list[dict],
    params: dict,
    usernames: list[str] | None = None,
    sender_email: str = "1125677925@qq.com",
    auth_code: str = "wsxmvqhgoeszigdh",
) -> dict:
    """
    组件：东财指数预测结果邮件发送（send_dc_index_prediction_email）

    功能：
    - 将预测结果整合为 HTML 表格；
    - 在邮件正文中注明预测参数（如开始/结束日期、接口、阈值、类型等）；
    - 使用组件 `result_notifier.send_macd_xgboost_results_email` 统一发送邮件。

    参数：
    - results(list[dict]): 预测与保存状态摘要列表（来自 `predict_and_save` 输出）；
      每项示例：{
        'ts_code': str,
        'trade_date': str,
        'prediction': int,
        'prob_up_percent': float,
        'confidence_percent': float,
        'saved': bool,
      }
    - params(dict): 邮件中注明的预测参数，建议包含：
      {
        'start_date': str,
        'end_date': str,
        'limit': int | None,
        'interface_name': str,
        'prob_threshold': float,
        'prediction_type': str | None,
        'forecast_days': int | None,
        'growth_threshold': float | None,
        'target_mode': str | None,
      }
    - usernames(list[str] | None): 收件用户名列表；为空则使用组件默认集合。
    - sender_email(str): 发件人邮箱地址；默认使用当前配置值。
    - auth_code(str): QQ 邮箱 SMTP 授权码；默认使用当前配置值。

    返回值：
    - dict: {
        'emails': list[str],          # 实际发送的收件人邮箱列表
        'scanned_count': int,         # 默认 0（不在此处统计）
        'hit_count': int,             # 默认 0（不在此处统计）
        'send_result': dict,          # 邮件发送返回结果（含 code/message 等）
      }

    事件：
    - 判断是否有预测结果 → 构建参数摘要 → 生成表格 HTML → 发送邮件。
    """

    # 参数安全读取
    start_date = params.get('start_date', '')
    end_date = params.get('end_date', '')
    limit = params.get('limit', None)
    interface_name = params.get('interface_name', 'dc_daily')
    prob_threshold = params.get('prob_threshold', 0.5)
    prediction_type = params.get('prediction_type', None)
    forecast_days = params.get('forecast_days', None)
    growth_threshold = params.get('growth_threshold', None)
    target_mode = params.get('target_mode', None)

    # 构建参数说明块
    param_lines = [
        f"开始日期：{start_date}",
        f"结束日期：{end_date}",
        f"接口：{interface_name}",
        f"数量上限：{limit if limit is not None else '未限制'}",
        f"入库概率阈值：{prob_threshold}",
        f"预测类型：{prediction_type or '未指定'}",
        f"预测天数（forecast_days）：{forecast_days if forecast_days is not None else '未指定'}",
        f"上涨阈值（growth_threshold）：{growth_threshold if growth_threshold is not None else '未指定'}",
        f"任务类型（target_mode）：{target_mode if target_mode is not None else '未指定'}",
    ]
    params_html = "".join([f"<li>{line}</li>" for line in param_lines])

    # 空结果邮件
    if not results:
        html = f"""
        <div style='font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", "Apple Color Emoji", "Segoe UI Emoji";'>
          <h2>东财指数 XGBoost 预测结果</h2>
          <p>本次预测未产生任何命中记录。</p>
          <h3>预测参数</h3>
          <ul>{params_html}</ul>
        </div>
        """
        return send_macd_xgboost_results_email(
            usernames=usernames,
            sender_email=sender_email,
            auth_code=auth_code,
            email_html_content=html,
        )

    # 表格样式与内容
    rows_html = "".join([
        (
            f"<tr>"
            f"<td>{r.get('ts_code','')}</td>"
            f"<td>{r.get('trade_date','')}</td>"
            f"<td>{int(r.get('prediction', 0))}</td>"
            f"<td>{float(r.get('prob_up_percent', 0.0)):.2f}%</td>"
            f"<td>{float(r.get('confidence_percent', 0.0)):.2f}%</td>"
            f"<td>{'是' if bool(r.get('saved', False)) else '否'}</td>"
            f"</tr>"
        ) for r in results
    ])

    html = f"""
    <div style='font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", "Apple Color Emoji", "Segoe UI Emoji";'>
      <h2>东财指数 XGBoost 预测结果</h2>
      <h3>预测参数</h3>
      <ul>{params_html}</ul>
      <h3>命中明细（{len(results)} 条）</h3>
      <table style='border-collapse: collapse; width: 100%;'>
        <thead>
          <tr style='background: #f6f8fa;'>
            <th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>代码</th>
            <th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>交易日</th>
            <th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>预测值</th>
            <th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>上涨概率</th>
            <th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>置信度</th>
            <th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>已入库</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>
    """

    return send_macd_xgboost_results_email(
        usernames=usernames,
        sender_email=sender_email,
        auth_code=auth_code,
        email_html_content=html,
    )

def PredictIndexFromEtfXGB():
    """
    预测指数并保存选择记录
    """
    pipeline = DCIndexXGBPipeline(
        lookback_days=30,
        forecast_days=5,
        growth_threshold=0.05,
        target_mode='up',
        interface_name='dc_daily',
    )
    end_date = datetime.datetime.now().strftime("%Y%m%d")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=120)).strftime("%Y%m%d")
    # pipeline.train(start_date='20230101', end_date='20251214', limit=500)
    # pipeline.predict_and_save(start_date='20250901', end_date='20251214', limit=500)
    pipeline.send_email(start_date=start_date, end_date=end_date, limit=500)

if __name__ == '__main__':
    print('DCIndexXGBPipeline 已就绪：请在业务流程中调用 train/predict_and_save。')
    # 示例（谨慎执行，可能触发外部数据拉取）：
    pipeline = DCIndexXGBPipeline(
        lookback_days=30,
        forecast_days=5,
        growth_threshold=0.05,
        target_mode='up',
        interface_name='dc_daily',
    )
    # pipeline.train(start_date='20230101', end_date='20251214', limit=500)
    # pipeline.predict_and_save(start_date='20250901', end_date='20251214', limit=500)
    end_date = datetime.datetime.now().strftime("%Y%m%d")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=3650)).strftime("%Y%m%d")
    pipeline.train(start_date=start_date, end_date=end_date, limit=500)
    # pipeline.train(start_date='20230101', end_date='20251214', limit=500)
    pipeline.predict_and_save(start_date='20250801', end_date='20251215', limit=500)
    # pipeline.send_email(start_date=start_date, end_date=end_date, limit=500)
    # pipeline.train_test(start_date='20250101', end_date='20250901')