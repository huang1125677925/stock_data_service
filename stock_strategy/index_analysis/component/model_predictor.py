"""
模型预测组件

功能：
- 封装基于训练模型的推理流程；
- 支持加载已保存的模型与标准化器，进行单点或批量预测。

参数：
- 无（通过成员方法传入数据与路径）。

返回值：
- dict: 单点预测结果或批量预测汇总。

事件：
- 无
"""

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from typing import Any


class SWIndexModelPredictor:
    """
    申万指数模型预测器

    功能：
    - 载入模型与 scaler；
    - 对输入数据进行特征对齐与标准化后进行预测；
    - 输出类别与概率信息。

    参数：
    - 无

    返回值：
    - 无（通过成员方法返回推理结果）。

    事件：
    - 无
    """

    def __init__(self, model_path: str | None = None, scaler_path: str | None = None):
        self.model = None
        self.scaler = None
        self.feature_columns: list[str] = []
        if model_path and scaler_path:
            self.load(model_path, scaler_path)

    def bind_features(self, feature_columns: list[str]) -> None:
        """
        绑定特征列

        功能：
        - 设置推理阶段所需的特征列表，以便数据对齐。

        参数：
        - feature_columns(list[str]): 训练时使用的特征列名。

        返回值：
        - None

        事件：
        - 无
        """
        self.feature_columns = feature_columns

    def load(self, model_path: str, scaler_path: str) -> None:
        """
        加载模型与标准化器

        功能：
        - 从磁盘载入已保存的模型与 scaler。

        参数：
        - model_path(str): 模型文件路径；
        - scaler_path(str): 标准化器文件路径。

        返回值：
        - None

        事件：
        - 无
        """
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)

    def predict_latest(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        使用最新样本进行预测

        功能：
        - 对输入数据按特征列抽取最新一行并进行标准化；
        - 输出类别与两类概率及置信度。

        参数：
        - df(pd.DataFrame): 已完成特征工程的数据；

        返回值：
        - dict: {prediction, probability_0, probability_1, confidence}

        事件：
        - 无
        """
        if self.model is None or self.scaler is None:
            raise RuntimeError("模型或标准化器未加载。")
        if not self.feature_columns:
            raise RuntimeError("推理所需特征列未绑定。")

        latest = df.iloc[[-1]][self.feature_columns]
        latest_scaled = self.scaler.transform(latest)
        pred = self.model.predict(latest_scaled)[0]
        proba = self.model.predict_proba(latest_scaled)[0]

        return {
            'trade_date': df.iloc[[-1]]['trade_date'].values[0],
            'prediction': int(pred),
            'probability_0': float(proba[0]),
            'probability_1': float(proba[1]),
            'confidence': float(np.max(proba)),
        }

    def predict_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        批量预测所有样本

        功能：
        - 对输入数据按绑定的特征列对齐并标准化；
        - 对每一行进行预测，输出类别、两类概率与置信度；
        - 自动跳过含缺失值的样本行。

        参数：
        - df(pd.DataFrame): 已完成特征工程的全量数据；

        返回值：
        - pd.DataFrame: 仅包含可预测行，附加列 {prediction, probability_0, probability_1, confidence}；

        事件：
        - 无
        """
        if self.model is None or self.scaler is None:
            raise RuntimeError("模型或标准化器未加载。")
        if not self.feature_columns:
            raise RuntimeError("推理所需特征列未绑定。")

        X = df[self.feature_columns]
        X_valid = X.dropna()

        if X_valid.empty:
            # 返回空结果表，保持调用方逻辑简洁
            return pd.DataFrame(columns=['prediction', 'probability_0', 'probability_1', 'confidence'])

        X_scaled = self.scaler.transform(X_valid)
        preds = self.model.predict(X_scaled)
        probas = self.model.predict_proba(X_scaled)

        result = df.loc[X_valid.index].copy()
        result['prediction'] = preds.astype(int)
        result['probability_0'] = probas[:, 0].astype(float)
        result['probability_1'] = probas[:, 1].astype(float)
        result['confidence'] = np.max(probas, axis=1).astype(float)

        return result