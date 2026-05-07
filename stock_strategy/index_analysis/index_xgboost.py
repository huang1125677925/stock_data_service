import sys
import os
from pathlib import Path
import datetime

# 设置Django环境（用于数据库模型的导入与保存）
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_data_service.settings')
try:
    import django
    django.setup()
except Exception:
    # 允许在未配置 Django 环境时作为纯脚本运行
    pass

from stock_strategy.index_analysis.component import (
    IndexDataSource,
    SWIndexFeatureExtractor,
    SWIndexModelTrainer,
    SWIndexModelPredictor,
    PredictionResultSaver,
)

# 该管道仅使用组件数据源，不直接调用外部接口


class IndexXGBPipeline:
    """
    组件：指数 XGBoost 训练与预测（基于 index_basic 与 index_daily）

    功能：
    - 使用 `index_basic` 获取指数列表（市场可选，如 SW/CSI/SSE/SZSE 等）；
    - 使用 `index_daily` 拉取指定指数的日线行情数据；
    - 支持切换到 `etf_basic` 路径，汇总 ETF 追踪指数后统一拉取；
    - 组合特征提取、模型训练、预测与（可选）结果入库组件；
    - 提供训练与推理两个高层方法，简化调用。

    参数：
    - lookback_days(int): 回看天数，默认 60；
    - forecast_days(int): 未来预测天数，默认 5；
    - growth_threshold(float): 上涨阈值，默认 0.05；
    - target_mode(str): 任务类型 'up' 或 'down'；
    - interface_name(str): 数据接口名称，默认 'index_daily'。

    返回值：
    - 无（通过成员方法返回训练评估与预测结果）。

    事件：
    - 训练：获取指数列表 → 拉取日线数据 → 特征工程 → 训练 → 保存模型与 scaler；
    - 推理：获取指数列表 → 拉取日线数据 → 特征工程 → 载入模型 → 逐代码预测 → （可选）入库。
    """

    def __init__(
        self,
        lookback_days: int = 60,
        forecast_days: int = 5,
        growth_threshold: float = 0.05,
        target_mode: str = 'up',
        interface_name: str = 'index_daily',
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
        - 在本模块下的 `models/` 目录生成包含任务类型的文件名；

        参数：
        - 无

        返回值：
        - (model_path, scaler_path): 两个字符串路径。

        事件：无
        """
        model_dir = Path(__file__).resolve().parent / "models"
        model_dir.mkdir(parents=True, exist_ok=True)
        tag = f"{self.target_mode}"
        model_path = model_dir / f"index_xgb_{tag}.joblib"
        scaler_path = model_dir / f"index_xgb_{tag}_scaler.joblib"
        return str(model_path), str(scaler_path)

    # 数据获取委托给组件数据源，不在管道内直接调用 TuShare

    def train(
        self,
        start_date: str,
        end_date: str,
        market: str | None = 'SW',
        category: str | None = None,
        source: str = 'index_basic',
    ) -> dict:
        """
        训练模型并保存

        功能：
        - 根据 `source` 选择数据源：
          - `index_basic`：获取指数列表并拉取指数日线；
          - `etf_basic`：汇总 ETF 追踪的指数集合并拉取指数日线；
        - 执行特征工程并训练 XGBClassifier，保存模型与 scaler。

        参数：
        - start_date(str): 开始日期 YYYYMMDD；
        - end_date(str): 结束日期 YYYYMMDD；
        - market(str|None): 指数市场过滤（仅当 `source='index_basic'` 时生效），默认 'SW'；
        - category(str|None): 指数类别过滤（仅当 `source='index_basic'` 时生效）；
        - source(str): 数据源选择，`'index_basic'` 或 `'etf_basic'`，默认 `'index_basic'`。

        返回值：
        - dict: 训练与评估摘要（train_accuracy、test_accuracy、feature_importance 等）。

        事件：
        - 指数列表 → 日线数据 → 特征工程 → 训练与保存。
        """
        ds = IndexDataSource(interface_name=self.interface_name)
        if str(source).lower() == 'etf_basic':
            df, _code_info_map = ds.fetch_index_daily_dataset_from_etf(start_date=start_date, end_date=end_date)
        else:
            df, _code_info_map = ds.fetch_index_daily_dataset(start_date=start_date, end_date=end_date, market=market, category=category)
        if df is None or df.empty:
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
        market: str | None = 'SW',
        category: str | None = None,
        source: str = 'index_basic',
        code_info_map: dict | None = None,
        prediction_type: str | None = None,
        prob_threshold: float = 0.5,
    ) -> list[dict]:
        """
        预测并保存到 StockSelectionRecord

        功能：
        - 根据 `source` 选择数据源：
          - `index_basic`：获取指数列表并拉取指数日线；
          - `etf_basic`：汇总 ETF 追踪的指数集合并拉取指数日线；
        - 载入模型，逐 `ts_code` 进行最近样本预测并入库（示例代码保留）。

        参数：
        - start_date(str): 开始日期 YYYYMMDD；
        - end_date(str): 结束日期 YYYYMMDD；
        - market(str|None): 指数市场过滤（仅当 `source='index_basic'` 时生效），默认 'SW'；
        - category(str|None): 指数类别过滤（仅当 `source='index_basic'` 时生效）；
        - source(str): 数据源选择，`'index_basic'` 或 `'etf_basic'`，默认 `'index_basic'`；
        - code_info_map(dict|None): 代码信息映射 {ts_code: {name, market}}；
        - prediction_type(str|None): 预测类型标识，如 `Index_MACD_XGBoost_for_5`；
        - prob_threshold(float): 选择入库的正类概率阈值，默认 0.5。

        返回值：
        - list[dict]: 每个代码的预测与保存状态摘要。

        事件：
        - 指数列表 → 日线数据 → 特征工程 → 载入模型 → 逐代码预测 → （可选）入库。
        """
        ds = IndexDataSource(interface_name=self.interface_name)
        if str(source).lower() == 'etf_basic':
            df, code_info_map = ds.fetch_index_daily_dataset_from_etf(start_date=start_date, end_date=end_date)
        else:
            df, code_info_map = ds.fetch_index_daily_dataset(start_date=start_date, end_date=end_date, market=market, category=category)
        if df is None or df.empty:
            return []

        df_features, feature_cols = self.feature_extractor.transform(df, for_inference=True)
        model_path, scaler_path = self._default_model_paths()
        predictor = SWIndexModelPredictor(model_path=model_path, scaler_path=scaler_path)
        predictor.bind_features(feature_cols)
        saver = PredictionResultSaver()

        out: list[dict] = []
        for code, g in df_features.groupby('ts_code'):
            g = g.dropna()
            if g.empty:
                continue
            row = predictor.predict_latest(g)
            trade_date = row['trade_date']
            prob_up = float(row.get('probability_1', 0.0))
            if prob_up < prob_threshold:
                continue
            name = (code_info_map.get(code, {}) or {}).get('name', code)

            # 如需入库，请取消下面注释并根据业务模型调整字段
            market_tag = (code_info_map or {}).get(code, {}).get('market', 'CN')
            prediction_tag = prediction_type or f"Index_From_ETF_MACD_XGBoost_for_{self.forecast_days}"
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
                f"上涨概率：{prob_up * 100.0:.2f}%  置信度：{row['confidence'] * 100.0:.2f}% save={bool(saved)}"
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

    def train_test(self, start_date: str, end_date: str, market: str | None = 'SW', category: str | None = None) -> dict:
        """
        训练样例抽查

        功能：
        - 拉取数据与特征工程，打印首个正类样本的特征行，便于快速验证目标生成；
        - 本方法使用 `index_basic` 路径；如需 ETF 路径请通过 `train/predict_and_save` 设置 `source='etf_basic'`。

        参数：
        - start_date(str): 开始日期 YYYYMMDD；
        - end_date(str): 结束日期 YYYYMMDD；
        - market(str|None): 指数市场过滤，默认 'SW'；
        - category(str|None): 指数类别过滤（可选）。

        返回值：
        - dict: 包含首个正类样本的行内容（若存在）。

        事件：
        - 指数列表 → 日线数据 → 特征工程 → 正类样本检索。
        """
        ds = IndexDataSource(interface_name=self.interface_name)
        df, _code_info_map = ds.fetch_index_daily_dataset_from_etf(start_date=start_date, end_date=end_date, market=market, category=category)
        if df is None or df.empty:
            return {}
        df_features, _feature_cols = self.feature_extractor.transform(df, for_inference=False)
        for _, row in df_features.iterrows():
            if row.get('target', 0) >= 0.5:
                print(row)
                return dict(row)
        return {}


def PredictIndexFromEtfXGB():
    """
    预测指数并保存选择记录
    """
    pipeline = IndexXGBPipeline(
        lookback_days=60,
        forecast_days=5,
        growth_threshold=0.05,
        target_mode='up',
        interface_name='index_daily',
    )
    end_date = datetime.datetime.now().strftime("%Y%m%d")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=365*2)).strftime("%Y%m%d")
    pipeline.predict_and_save(start_date=start_date, end_date=end_date, source='etf_basic')


if __name__ == "__main__":
    print("IndexXGBPipeline 已就绪：请在业务流程中调用 train/predict_and_save。")
    # 示例（谨慎执行，可能触发外部数据拉取）
    pipeline = IndexXGBPipeline(
        lookback_days=60,
        forecast_days=5,
        growth_threshold=0.05,
        target_mode='up',
        interface_name='index_daily',
    )
    end_date = datetime.datetime.now().strftime("%Y%m%d")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=365*2)).strftime("%Y%m%d")
    # pipeline.train(start_date='20240101', end_date='20251202', market='SW', source='index_basic')
    # 使用 ETF 路径示例：
    # pipeline.train(start_date=start_date, end_date=end_date, source='etf_basic')
    # pipeline.predict_and_save(start_date='20250901', end_date='20251202', market='SW', source='index_basic')
    pipeline.predict_and_save(start_date='20250901', end_date=end_date, source='etf_basic')