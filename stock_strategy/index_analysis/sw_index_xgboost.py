import sys
import os
from pathlib import Path
import django

# 设置Django环境（用于数据库模型的导入与保存）
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_data_service.settings')
django.setup()

from stock_strategy.index_analysis.component import (
    SWIndexDataSource,
    SWIndexFeatureExtractor,
    SWIndexModelTrainer,
    SWIndexModelPredictor,
    PredictionResultSaver,
)

import datetime



class SWIndexXGBPipeline:
    """
    管道封装：申万指数 XGBoost 训练与预测

    功能：
    - 组合数据源、特征提取、模型训练、预测与结果入库组件；
    - 提供训练与推理两个高层方法，简化原脚本的调用。

    参数：
    - lookback_days(int): 回看天数，默认 60；
    - forecast_days(int): 未来预测天数，默认 5；
    - growth_threshold(float): 上涨阈值，默认 0.05；
    - target_mode(str): 任务类型 'up' 或 'down'；
    - interface_name(str): 数据接口名称，'index_daily' 或 'sw_daily'。

    返回值：
    - 无（通过成员方法返回训练评估与预测结果）。

    事件：
    - 训练：拉取数据 → 特征工程 → 训练 → 保存模型与 scaler；
    - 推理：拉取数据 → 特征工程 → 载入模型 → 逐代码预测 → 结果入库。
    """

    def __init__(self, lookback_days=60, forecast_days=5, growth_threshold=0.05, target_mode='up', interface_name='index_daily'):
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

    def _default_model_paths(self):
        model_dir = Path(__file__).resolve().parent / "models"
        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / f"sw_index_xgb_{datetime.datetime.now().strftime('%Y%m%d')}_{self.target_mode}.joblib"
        scaler_path = model_dir / f"sw_index_xgb_{datetime.datetime.now().strftime('%Y%m%d')}_{self.target_mode}_scaler.joblib"
        return str(model_path), str(scaler_path)

    def train(self, start_date: str, end_date: str):
        """
        训练模型并保存

        功能：
        - 拉取申万指数日线数据并进行特征工程，训练 XGBClassifier，保存模型与 scaler。

        参数：
        - start_date(str): 开始日期 YYYYMMDD；
        - end_date(str): 结束日期 YYYYMMDD。

        返回值：
        - dict: 训练与评估摘要（train_accuracy、test_accuracy、feature_importance 等）。

        事件：
        - 数据拉取 → 特征工程 → 训练与保存。
        """
        ds = SWIndexDataSource(interface_name=self.interface_name)
        df, code_map = ds.fetch_sw_index_daily(start_date, end_date)
        df_features, feature_cols = self.feature_extractor.transform(df, for_inference=False)
        result = self.trainer.train(df_features.dropna(), feature_cols)
        model_path, scaler_path = self._default_model_paths()
        self.trainer.save(model_path, scaler_path)
        return result

    def predict_and_save(self, start_date: str, end_date: str, code_info_map: dict = None, prediction_type: str = None):
        """
        预测并保存到 StockSelectionRecord

        功能：
        - 拉取数据与特征工程，载入模型，逐 `ts_code` 进行最近样本预测并入库。

        参数：
        - ts_codes(list[str]): 指数代码列表；
        - start_date(str): 开始日期 YYYYMMDD；
        - end_date(str): 结束日期 YYYYMMDD；
        - code_info_map(dict): 代码信息映射 {ts_code: {name, market}}；
        - prediction_type(str): 预测类型标识，如 `MACD_XGBoost_for_5`。

        返回值：
        - list[dict]: 每个代码的预测与保存状态摘要。

        事件：
        - 数据拉取 → 特征工程 → 载入模型 → 逐代码预测 → 入库。
        """
        ds = SWIndexDataSource(interface_name=self.interface_name)
        df, code_map = ds.fetch_sw_index_daily(start_date, end_date)
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
            if row['prediction'] < 0.5:
                continue
            print(f"预测 {code} {code_map.get(code, code)} {trade_date}  预测值：{int(row['prediction'])} 置信度：{float(row['confidence'] * 100.0)}%")
            # info = code_info_map.get(code, {})
            # name = info.get('name', code)
            # market = info.get('market', 'CN')
            # saved = saver.save_selection(
            #     ts_code=code,
            #     trade_date=str(trade_date),
            #     market=market,
            #     name=name,
            #     predict_rise_prob_percent=float(pred['probability_1'] * 100.0),
            #     confidence_percent=float(pred['confidence'] * 100.0),
            #     prediction_type=prediction_type,
            # )
            # for index, row in pred.iterrows():
            #     if row['prediction'] < 0.5:
            #         continue
            #     print(f"预测 {code} {code_map.get(code, code)} {row['trade_date']}  预测值：{int(row['prediction'])} 置信度：{float(row['confidence'] * 100.0)}%")
            #     out.append({
            #         'ts_code': code,
            #         'trade_date': str(row['trade_date']),
            #         'prediction': int(row['prediction']),
            #         'prob_up_percent': float(row['probability_1'] * 100.0),
            #         'confidence_percent': float(row['confidence'] * 100.0),
            #         # 'saved': bool(saved),
            #     })
        return out

    def train_test(self, start_date: str, end_date: str):
        """
        训练模型并保存

        功能：
        - 拉取申万指数日线数据并进行特征工程，训练 XGBClassifier，保存模型与 scaler。

        参数：
        - start_date(str): 开始日期 YYYYMMDD；
        - end_date(str): 结束日期 YYYYMMDD。

        返回值：
        - dict: 训练与评估摘要（train_accuracy、test_accuracy、feature_importance 等）。

        事件：
        - 数据拉取 → 特征工程 → 训练与保存。
        """
        ds = SWIndexDataSource(interface_name=self.interface_name)
        df, code_map = ds.fetch_sw_index_daily(start_date, end_date)
        df_features, feature_cols = self.feature_extractor.transform(df, for_inference=False)
        for index, row in df_features.iterrows():
            if row['target'] < 0.5:
                continue
            print(row)
            break



if __name__ == "__main__":
    # 该脚本仅保留管道类与必要导入；具体训练/预测请在任务或调度中调用。
    print("SWIndexXGBPipeline 已就绪：请在业务流程中调用 train/predict_and_save。")
    pipeline = SWIndexXGBPipeline(
        lookback_days=60,
        forecast_days=5,
        growth_threshold=0.05,
        target_mode='binary',
        interface_name='sw_daily',
    )
    pipeline.train(
        start_date='20240101',
        end_date='20251201',
    )
    pipeline.predict_and_save(
        start_date='20250901',
        end_date='20251201',
    )
