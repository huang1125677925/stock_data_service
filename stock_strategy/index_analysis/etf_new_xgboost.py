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

from stock_strategy.index_analysis.component import (
    ETFDataSource,
    SWIndexFeatureExtractor,
    SWIndexModelTrainer,
    SWIndexModelPredictor,
    PredictionResultSaver,
)

from typing import Iterable
import datetime

try:
    # TuShare 代理（统一响应结构：success_response / error_response）
    from common.tushare_proxy import call_tushare
except Exception:
    call_tushare = None


class ETFXGBPipeline:
    """
    管道封装：ETF XGBoost 训练与预测（参考 sw_index_xgboost）

    功能：
    - 组合数据源、特征提取、模型训练、预测与结果入库组件；
    - 提供训练与推理两个高层方法，简化原脚本的调用；
    - 以 `fund_daily` 为数据接口，自动获取 ETF 列表并拉取日线。

    参数：
    - lookback_days(int): 回看天数，默认 60；
    - forecast_days(int): 未来预测天数，默认 5；
    - growth_threshold(float): 上涨阈值，默认 0.03；
    - target_mode(str): 任务类型 'up' 或 'down'；
    - interface_name(str): 数据接口名称，默认 'fund_daily'。

    返回值：
    - 无（通过成员方法返回训练评估与预测结果）。

    事件：
    - 训练：拉取数据 → 特征工程 → 训练 → 保存模型与 scaler；
    - 推理：拉取数据 → 特征工程 → 载入模型 → 逐代码预测 → 结果入库。
    """

    def __init__(
        self,
        lookback_days: int = 60,
        forecast_days: int = 5,
        growth_threshold: float = 0.03,
        target_mode: str = 'up',
        interface_name: str = 'fund_daily',
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

    def _default_model_paths(self) -> tuple[str, str]:
        """
        组件：模型与标准化器默认保存路径（_default_model_paths）

        功能：
        - 在本模块下的 `models/` 目录生成包含日期与任务类型的文件名；

        参数：
        - 无

        返回值：
        - (model_path, scaler_path): 两个字符串路径。

        事件：无
        """
        model_dir = Path(__file__).resolve().parent / "models"
        model_dir.mkdir(parents=True, exist_ok=True)
        tag = f"{self.target_mode}"
        model_path = model_dir / f"etf_new_xgb_{tag}.joblib"
        scaler_path = model_dir / f"etf_new_xgb_{tag}_scaler.joblib"
        return str(model_path), str(scaler_path)

    def _get_etf_list(self, list_status: str = 'L') -> tuple[list[str], dict[str, str]]:
        """
        组件：获取ETF列表（_get_etf_list）

        功能：
        - 调用 TuShare `etf_basic` 接口，返回当前上市 ETF 的代码与名称映射；
        - 统一响应结构，若调用失败返回空列表与空映射。

        参数：
        - list_status(str): 上市状态过滤，默认 'L'。

        返回值：
        - (ts_codes, code_map): 代码列表与 {ts_code: name} 映射。

        事件：
        - 外部调用 `common.tushare_proxy.call_tushare`；若不可用则返回空。
        """
        if call_tushare is None:
            return [], {}

        resp = call_tushare(
            interface='etf_basic',
            params={'list_status': list_status},
            fields='ts_code,extname',
            use_query=False,
        )
        if not isinstance(resp, dict) or resp.get('code') != 200:
            return [], {}
        records = resp.get('data', {}).get('records', [])
        ts_codes: list[str] = []
        code_map: dict[str, str] = {}
        for r in records:
            code = r.get('ts_code')
            name = r.get('extname') or r.get('ts_code')
            if code:
                ts_codes.append(code)
                code_map[code] = name
        return ts_codes, code_map

    def train(self, start_date: str, end_date: str, ts_codes: Iterable[str] | None = None) -> dict:
        """
        训练模型并保存

        功能：
        - 拉取ETF日线数据并进行特征工程，训练 XGBClassifier，保存模型与 scaler。

        参数：
        - start_date(str): 开始日期 YYYYMMDD；
        - end_date(str): 结束日期 YYYYMMDD；
        - ts_codes(Iterable[str]|None): 指定训练的 ETF 代码集合；None 则自动加载上市 ETF 列表。

        返回值：
        - dict: 训练与评估摘要（train_accuracy、test_accuracy、feature_importance 等）。

        事件：
        - 数据拉取 → 特征工程 → 训练与保存。
        """
        ds = ETFDataSource(interface_name=self.interface_name)
        df, code_map = ds.fetch_etf_daily_dataset(start_date, end_date, limit=500)
        if df.empty:
            return {}
        df_features, feature_cols = self.feature_extractor.transform(df, for_inference=False)
        result = self.trainer.train(df_features.dropna(), feature_cols)
        model_path, scaler_path = self._default_model_paths()
        self.trainer.save(model_path, scaler_path)
        return result

    def predict_and_save(
        self,
        start_date: str,
        end_date: str,
        ts_codes: Iterable[str] | None = None,
        code_info_map: dict | None = None,
        prediction_type: str | None = None,
        prob_threshold: float = 0.5,
    ) -> list[dict]:
        """
        预测并保存到 StockSelectionRecord

        功能：
        - 拉取数据与特征工程，载入模型，逐 `ts_code` 进行最近样本预测并入库。

        参数：
        - start_date(str): 开始日期 YYYYMMDD；
        - end_date(str): 结束日期 YYYYMMDD；
        - ts_codes(Iterable[str]|None): 指定要预测的 ETF 列表；None 则自动加载上市 ETF；
        - code_info_map(dict|None): 代码信息映射 {ts_code: {name, market}}；
        - prediction_type(str|None): 预测类型标识，如 `ETF_MACD_XGBoost_for_5`；
        - prob_threshold(float): 选择入库的正类概率阈值，默认 0.5。

        返回值：
        - list[dict]: 每个代码的预测与保存状态摘要。

        事件：
        - 数据拉取 → 特征工程 → 载入模型 → 逐代码预测 → 入库。
        """
        ds = ETFDataSource(interface_name=self.interface_name)

        df, code_map = ds.fetch_etf_daily_dataset(start_date, end_date)
        if df.empty:
            return []
        df_features, feature_cols = self.feature_extractor.transform(df, for_inference=True)
        model_path, scaler_path = self._default_model_paths()
        predictor = SWIndexModelPredictor(model_path=model_path, scaler_path=scaler_path)
        predictor.bind_features(feature_cols)
        saver = PredictionResultSaver()

        out: list[dict] = []
        for code, g in df_features.groupby('ts_code'):
            if g.empty:
                continue
            g = g.dropna()
            if g.empty:
                continue
            row = predictor.predict_latest(g)
            trade_date = row['trade_date']
            prob_up = float(row.get('probability_1', 0.0))
            if row['prediction'] < 1:
                continue
            name = code_map.get(code, code)
            # market = (code_info_map or {}).get(code, {}).get('market', 'CN')
            # prediction_tag = prediction_type or f"ETF_MACD_XGBoost_for_{self.forecast_days}"
            # saved = saver.save_selection(
            #     ts_code=code,
            #     trade_date=str(trade_date),
            #     market=market,
            #     name=name,
            #     predict_rise_prob_percent=float(prob_up * 100.0),
            #     confidence_percent=float(row['confidence'] * 100.0),
            #     prediction_type=prediction_tag,
            # )
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
                # 'saved': bool(saved),
            })
        return out

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
        - 数据拉取 → 特征工程 → 正类样本检索。
        """
        ds = ETFDataSource(interface_name=self.interface_name)
        df, code_map = ds.fetch_etf_daily_dataset(start_date, end_date, limit=500)
        df_features, _feature_cols = self.feature_extractor.transform(df, for_inference=False)
        for _, row in df_features.iterrows():
            if row.get('target', 0) >= 0.5:
                print(row)
                return dict(row)
        return {}


if __name__ == "__main__":
    print("ETFXGBPipeline 已就绪：请在业务流程中调用 train/predict_and_save。")
    # 示例（谨慎执行，可能触发外部数据拉取）：
    pipeline = ETFXGBPipeline(
        lookback_days=60,
        forecast_days=3,
        growth_threshold=0.05,
        target_mode='up',
        interface_name='fund_daily',
    )
    pipeline.train(start_date='20240101', end_date='20251202')
    pipeline.predict_and_save(start_date='20250901', end_date='20251202')
    # pipeline.train(start_date='20240101', end_date='20251001')