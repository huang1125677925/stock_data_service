"""
组件包：申万指数XGBoost流程模块化

功能：
- 提供数据源、特征提取、模型训练保存、模型预测、结果保存五类组件。

参数：
- 无

返回值：
- 无

事件：
- 无
"""

from .data_source import SWIndexDataSource, ETFDataSource, IndexDataSource
from .feature_extractor import SWIndexFeatureExtractor
from .model_training import SWIndexModelTrainer
from .model_predictor import SWIndexModelPredictor
from .result_saver import PredictionResultSaver

__all__ = [
    'SWIndexDataSource',
    'IndexDataSource',
    'ETFDataSource',
    'SWIndexFeatureExtractor',
    'SWIndexModelTrainer',
    'SWIndexModelPredictor',
    'PredictionResultSaver',
]