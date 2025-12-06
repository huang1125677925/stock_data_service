"""
模型训练与保存组件

功能：
- 封装 XGBoost 模型的训练、评估、特征重要性导出与持久化保存；
- 标准化特征缩放，避免数据泄露（时间序列划分）。

参数：
- 无（通过成员方法传入训练数据与路径）。

返回值：
- dict: 训练与评估结果，包括准确率、重要特征、划分后的数据切片。

事件：
- 无
"""

from __future__ import annotations

import inspect
import joblib
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import StandardScaler


class SWIndexModelTrainer:
    """
    申万指数模型训练器

    功能：
    - 训练 XGBClassifier；
    - 输出评估指标与特征重要性；
    - 保存模型与标准化器到指定路径。

    参数：
    - 无

    返回值：
    - 无（通过成员方法返回训练结果与执行保存）。

    事件：
    - 无
    """

    def __init__(self) -> None:
        self.scaler = StandardScaler()
        self.model: xgb.XGBClassifier | None = None
        self.feature_columns: list[str] = []

    def temporal_split(self, df: pd.DataFrame, test_size: float = 0.2):
        split_idx = int(len(df) * (1 - test_size))
        train_df = df.iloc[:split_idx].copy()
        test_df = df.iloc[split_idx:].copy()
        X_train = train_df[self.feature_columns]
        y_train = train_df['target']
        X_test = test_df[self.feature_columns]
        y_test = test_df['target']
        return X_train, X_test, y_train, y_test, train_df, test_df

    def train(self, df: pd.DataFrame, feature_columns: list[str]):
        """
        训练模型

        功能：
        - 依据提供的特征列训练 XGBClassifier；
        - 输出训练/测试准确率与分类报告。

        参数：
        - df(pd.DataFrame): 已准备好的训练数据，包含 'target' 与特征列；
        - feature_columns(list[str]): 用于训练的特征列名。

        返回值：
        - dict: {train_accuracy, test_accuracy, feature_importance, train_df, test_df}

        事件：
        - 无
        """
        self.feature_columns = feature_columns
        X_train, X_test, y_train, y_test, train_df, test_df = self.temporal_split(df)

        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        self.model = xgb.XGBClassifier(
            n_estimators=1000,
            max_depth=6,
            learning_rate=0.01,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='logloss',
        )

        fit_params = inspect.signature(self.model.fit).parameters
        fit_kwargs = {}
        if 'eval_set' in fit_params:
            fit_kwargs['eval_set'] = [(X_test_scaled, y_test)]
        if 'eval_metric' in fit_params:
            fit_kwargs['eval_metric'] = 'logloss'
        if 'callbacks' in fit_params:
            try:
                from xgboost import callback as xgb_callback
                fit_kwargs['callbacks'] = [xgb_callback.EarlyStopping(rounds=50)]
            except Exception:
                pass
        elif 'early_stopping_rounds' in fit_params:
            fit_kwargs['early_stopping_rounds'] = 50
        if 'verbose' in fit_params:
            fit_kwargs['verbose'] = False

        self.model.fit(X_train_scaled, y_train, **fit_kwargs)

        y_train_pred = self.model.predict(X_train_scaled)
        y_test_pred = self.model.predict(X_test_scaled)
        train_acc = accuracy_score(y_train, y_train_pred)
        test_acc = accuracy_score(y_test, y_test_pred)

        try:
            _ = classification_report(y_test, y_test_pred)
        except Exception:
            pass

        feature_importance = self.get_feature_importance(top_n=15)
        return {
            'train_accuracy': train_acc,
            'test_accuracy': test_acc,
            'feature_importance': feature_importance,
            'train_df': train_df,
            'test_df': test_df,
        }

    def get_feature_importance(self, top_n: int = 15) -> pd.DataFrame | None:
        if self.model is None:
            return None
        importance_scores = self.model.feature_importances_
        feature_importance = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': importance_scores,
        }).sort_values('importance', ascending=False).head(top_n)
        return feature_importance

    def save(self, model_path: str, scaler_path: str) -> None:
        """
        保存模型与标准化器

        功能：
        - 将训练好的模型与 scaler 分别持久化到磁盘。

        参数：
        - model_path(str): 模型保存路径；
        - scaler_path(str): 标准化器保存路径。

        返回值：
        - None

        事件：
        - 无
        """
        if self.model is None:
            raise RuntimeError('模型未训练，无法保存。')
        joblib.dump(self.model, model_path)
        joblib.dump(self.scaler, scaler_path)