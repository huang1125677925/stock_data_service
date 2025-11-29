import sys
import os
from pathlib import Path
from tracemalloc import start
import django
# 设置Django环境
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_data_service.settings')
django.setup()

import pandas as pd
import numpy as np
import time
import xgboost as xgb
import joblib
import inspect
import random
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
import warnings
from datetime import datetime, timedelta
from common.tushare_proxy import call_tushare
from common.email_utils import send_qq_email
from user_management.models import User
from stock_strategy.models import StockSelectionRecord
import re


warnings.filterwarnings('ignore')

def save_selection_records_from_text(text: str, prediction_type: str = 'MACD_XGBoost_for_5') -> int:
    """
    组件：从“命中”文本解析并保存选股记录（save_selection_records_from_text）

    功能：
    - 解析终端/日志中的“命中”文本行，抽取市场、代码、名称、交易日、预测概率与置信度，并保存到 `StockSelectionRecord` 表。
    - 基于 `(code, trade_date)` 去重，避免重复写入同一天同代码的记录。

    参数：
    - text(str): 包含若干“命中:”行的原始文本，支持多行。
    - prediction_type(str): 预测类型标识，如 `MACD_XGBoost_for_5`，用于区分来源模型。

    返回值：
    - int: 成功写入的记录条数。

    事件：
    - 文本解析 → 字段抽取 → 数据库写入（遇到重复自动跳过）。
    """

    if not text or not str(text).strip():
        return 0

    pattern = re.compile(
        r"命中:\s*市场\s*(?P<market>\S+)\s*指数\s*(?P<code>[^-]+)-(?P<name>[^\s]+)\s*在\s*(?P<trade_date>\d{8})\s*存在未来(?P<days>\d+)天上涨≥(?P<threshold>\d+)%\s*的可能，预测概率为\s*(?P<prob>[\d\.]+)%[，,]\s*置信度\s*(?P<conf>[\d\.]+)%"
    )

    saved = 0
    for m in pattern.finditer(text):
        market = m.group('market').strip()
        code = m.group('code').strip()
        name = m.group('name').strip()
        raw_date = m.group('trade_date').strip()
        prob = float(m.group('prob'))  # 已是百分比数值，如 77.18
        conf = float(m.group('conf'))  # 已是百分比数值

        try:
            trade_date = datetime.strptime(raw_date, '%Y%m%d').date()
        except ValueError:
            # 兼容 YYYY-MM-DD
            trade_date = datetime.strptime(raw_date, '%Y-%m-%d').date()

        # 去重
        if StockSelectionRecord.objects.filter(code=code, trade_date=trade_date).exists():
            continue

        try:
            StockSelectionRecord.objects.create(
                market=market,
                code=code,
                name=name,
                trade_date=trade_date,
                predict_rise_prob=prob,
                confidence=conf,
                prediction_type=prediction_type,
            )
            saved += 1
        except Exception as e:
            print(f"保存选股记录失败（{code} {raw_date}）：{e}")

    return saved

class MACDPredictor:
    def __init__(
        self,
        lookback_days=60,
        forecast_days=5,
        growth_threshold=0.05,
        target_mode: str = 'up',
        drop_threshold: float = 0.05,
        drop_forecast_days: int | None = None,
    ):
        """
        MACD趋势预测模型（支持上涨/下跌两类任务）

        Parameters:
        - lookback_days: 回看天数（默认2个月约60天）
        - forecast_days: 预测未来天数（上涨任务默认5天）
        - growth_threshold: 上涨阈值（默认5%）
        - target_mode: 目标任务类型，'up' 表示预测上涨超过阈值；'down' 表示预测下跌超过阈值
        - drop_threshold: 下跌阈值（默认5%）
        - drop_forecast_days: 下跌预测的未来天数（默认与 forecast_days 相同）
        """
        self.lookback_days = lookback_days
        self.forecast_days = forecast_days
        self.growth_threshold = growth_threshold
        self.target_mode = target_mode  # 'up' 或 'down'
        self.drop_threshold = drop_threshold
        self.drop_forecast_days = drop_forecast_days if drop_forecast_days is not None else forecast_days
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = []
    
    def calculate_technical_indicators(self, df):
        """
        计算技术指标特征

        功能：
        - 基于 MACD 指标补充变化率、滚动统计、趋势、相对位置与波动特征。
        - 增加与信号相关的交叉与运行长度特征，刻画动量延续与拐点信息。

        参数：
        - df: pandas.DataFrame，需至少包含列 `macd_bfq, macd_dif_bfq, macd_dea_bfq`

        返回值：
        - pandas.DataFrame：新增 MACD 系列相关特征后的数据集（含 NaN，待外部清理）

        事件：
        - 无
        """
        # 基础MACD指标
        df['macd_prev'] = df['macd_bfq'].shift(1)
        df['dif_prev'] = df['macd_dif_bfq'].shift(1)
        df['dea_prev'] = df['macd_dea_bfq'].shift(1)
        
        # MACD变化率
        df['macd_pct_change'] = df['macd_bfq'].pct_change()
        df['dif_pct_change'] = df['macd_dif_bfq'].pct_change()
        df['dea_pct_change'] = df['macd_dea_bfq'].pct_change()
        
        # 滚动统计特征 - 过去5,10,20天的统计
        for window in [5, 10, 20]:
            df[f'macd_rolling_mean_{window}'] = df['macd_bfq'].rolling(window=window).mean()
            df[f'macd_rolling_std_{window}'] = df['macd_bfq'].rolling(window=window).std()
            df[f'macd_rolling_min_{window}'] = df['macd_bfq'].rolling(window=window).min()
            df[f'macd_rolling_max_{window}'] = df['macd_bfq'].rolling(window=window).max()
            
            df[f'dif_rolling_mean_{window}'] = df['macd_dif_bfq'].rolling(window=window).mean()
            df[f'dea_rolling_mean_{window}'] = df['macd_dea_bfq'].rolling(window=window).mean()
        
        # 趋势特征
        df['macd_trend'] = df['macd_bfq'].rolling(window=5).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0], raw=True
        )
        
        # 相对位置特征
        rolling_min = df['macd_bfq'].rolling(20).min()
        rolling_max = df['macd_bfq'].rolling(20).max()
        denom = (rolling_max - rolling_min).replace(0, np.nan)
        df['macd_position'] = (df['macd_bfq'] - rolling_min) / denom
        
        # 波动特征
        df['macd_volatility'] = df['macd_bfq'].rolling(window=10).std()

        # MACD 直方图与信号交叉特征
        df['macd_hist'] = df['macd_dif_bfq'] - df['macd_dea_bfq']
        df['macd_hist_slope_5'] = df['macd_hist'].rolling(window=5).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0], raw=True
        )
        df['macd_above_zero'] = (df['macd_bfq'] > 0).astype(int)
        df['dif_above_dea'] = (df['macd_dif_bfq'] > df['macd_dea_bfq']).astype(int)
        df['dif_cross_up'] = (
            ((df['macd_dif_bfq'] >= df['macd_dea_bfq']) & (df['dif_prev'] < df['dea_prev']))
        ).astype(int)
        df['dif_cross_down'] = (
            ((df['macd_dif_bfq'] <= df['macd_dea_bfq']) & (df['dif_prev'] > df['dea_prev']))
        ).astype(int)

        # 运行长度特征（动量延续强度）
        run = df['dif_above_dea']
        run_groups = (run != run.shift()).cumsum()
        df['dif_above_dea_run'] = run.groupby(run_groups).cumcount() + 1
        df.loc[run == 0, 'dif_above_dea_run'] = 0

        run2 = df['macd_above_zero']
        run_groups2 = (run2 != run2.shift()).cumsum()
        df['macd_above_zero_run'] = run2.groupby(run_groups2).cumcount() + 1
        df.loc[run2 == 0, 'macd_above_zero_run'] = 0

        return df

    def calculate_price_features(self, df):
        """
        计算价格、波动与振荡类特征（仅使用历史数据，不泄露未来信息）

        功能：
        - 添加收益率、波动率、真实波动范围（ATR）、布林带、移动均线、RSI、随机指标、K线形态等特征。
        - 强化对突破、延续与压缩后的扩张等行情的刻画，以提升事件召回。

        参数：
        - df: pandas.DataFrame，需至少包含列 `open, high, low, close, trade_date`

        返回值：
        - pandas.DataFrame：新增价格动量与波动特征后的数据集（含 NaN，待外部清理）

        事件：
        - 无
        """
        # 收益率与波动率
        df['ret_1d'] = df['close'].pct_change()
        df['ret_3d'] = df['close'].pct_change(3)
        df['ret_5d'] = df['close'].pct_change(5)
        df['ret_5_mean'] = df['ret_1d'].rolling(5).mean()
        df['ret_5_std'] = df['ret_1d'].rolling(5).std()
        df['ret_10_std'] = df['ret_1d'].rolling(10).std()

        # 真实波动范围 ATR（归一化）
        prev_close = df['close'].shift(1)
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - prev_close).abs()
        tr3 = (df['low'] - prev_close).abs()
        df['true_range'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr_14'] = df['true_range'].rolling(14).mean()
        df['atr_14_norm'] = df['atr_14'] / df['close'].replace(0, np.nan).abs()

        # 布林带
        ma20 = df['close'].rolling(20).mean()
        std20 = df['close'].rolling(20).std()
        upper = ma20 + 2 * std20
        lower = ma20 - 2 * std20
        df['bb_width'] = (upper - lower) / ma20.replace(0, np.nan).abs()
        df['bb_percent_b'] = (df['close'] - lower) / (upper - lower).replace(0, np.nan)

        # 移动均线与斜率
        df['sma_5'] = df['close'].rolling(5).mean()
        df['sma_10'] = df['close'].rolling(10).mean()
        df['sma_20'] = ma20
        df['close_above_sma5'] = (df['close'] > df['sma_5']).astype(int)
        df['close_above_sma20'] = (df['close'] > df['sma_20']).astype(int)
        df['sma_5_slope'] = df['sma_5'].rolling(5).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0], raw=True
        )
        df['sma_20_slope'] = df['sma_20'].rolling(5).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0], raw=True
        )

        # RSI（14）
        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df['rsi_14'] = 100 - 100 / (1 + rs)

        # 随机指标（Stochastic %K/%D）
        lowest_14 = df['low'].rolling(14).min()
        highest_14 = df['high'].rolling(14).max()
        df['stoch_k'] = 100 * (df['close'] - lowest_14) / (highest_14 - lowest_14).replace(0, np.nan)
        df['stoch_d'] = df['stoch_k'].rolling(3).mean()

        # K线形态特征（归一化）
        rng = (df['high'] - df['low']).replace(0, np.nan)
        body = df['close'] - df['open']
        upper_shadow = df['high'] - np.maximum(df['open'], df['close'])
        lower_shadow = np.minimum(df['open'], df['close']) - df['low']
        df['body_pct_range'] = body / rng
        df['upper_shadow_ratio'] = upper_shadow / rng
        df['lower_shadow_ratio'] = lower_shadow / rng

        return df
    
    def create_target_variable(self, df):
        """
        创建目标变量：根据任务类型生成上涨/下跌标签

        功能：
        - 上涨任务（target_mode='up'）：未来 forecast_days 天累计涨幅 > growth_threshold 则标签为 1。
        - 下跌任务（target_mode='down'）：未来 drop_forecast_days 天累计跌幅 < -drop_threshold 则标签为 1。

        参数：
        - df: 原始数据，需包含 `close`

        返回值：
        - pandas.DataFrame：包含 `future_close`、`future_growth_rate` 与 `target`

        事件：
        - 无
        """
        # 计算未来收盘价（根据任务类型使用不同的天数）
        horizon = self.forecast_days if self.target_mode == 'up' else self.drop_forecast_days
        df['future_close'] = df['close'].shift(-horizon)

        # 计算未来增长率（负值表示下跌）
        df['future_growth_rate'] = (df['future_close'] - df['close']) / df['close'].abs()

        # 创建二分类目标变量：正类始终为“满足阈值的事件”
        if self.target_mode == 'up':
            df['target'] = (df['future_growth_rate'] > self.growth_threshold).astype(int)
        else:  # 'down'
            df['target'] = (df['future_growth_rate'] < -self.drop_threshold).astype(int)

        return df
    
    def create_lag_features(self, df, n_lags=10):
        """
        创建滞后特征

        功能：
        - 为 MACD、DIF、DEA 生成 1..n 的滞后特征，刻画短期记忆与延迟效应。

        参数：
        - df: pandas.DataFrame，需包含 `macd_bfq, macd_dif_bfq, macd_dea_bfq`
        - n_lags: int，滞后阶数，默认 10

        返回值：
        - pandas.DataFrame：新增滞后特征后的数据集（含 NaN，待外部清理）

        事件：
        - 无
        """
        for lag in range(1, n_lags + 1):
            df[f'macd_lag_{lag}'] = df['macd_bfq'].shift(lag)
            df[f'dif_lag_{lag}'] = df['macd_dif_bfq'].shift(lag)
            df[f'dea_lag_{lag}'] = df['macd_dea_bfq'].shift(lag)
        
        return df
    
    def prepare_features(self, df, for_inference: bool = False):
        """
        准备特征数据（按指数代码分组进行特征计算，避免跨指数数据泄露）

        功能：
        - 对输入的原始数据按 `ts_code` 分组，分别计算技术指标、价格/波动特征与滞后特征。
        - 在训练模式下（for_inference=False）额外创建目标变量，并对全量列进行缺失清理。
        - 在推理模式下（for_inference=True）不创建目标变量，仅对特征列进行缺失清理，以保留最近交易日样本。

        参数：
        - df: 原始数据 DataFrame，至少包含列 `ts_code, trade_date, close, macd_bfq, macd_dif_bfq, macd_dea_bfq`
        - for_inference(bool, 可选): 是否为推理模式（默认 False，训练模式）。

        返回值：
        - pandas.DataFrame：已计算好特征（训练模式下包含目标变量）的整合数据集

        事件：
        - 无
        """
        # 确保时间顺序与分组
        df = df.sort_values(['ts_code', 'trade_date']).reset_index(drop=True)

        grouped_results = []
        for code, group in df.groupby('ts_code'):
            g = group.copy()
            # 技术指标
            g = self.calculate_technical_indicators(g)
            # 价格动量与波动特征
            g = self.calculate_price_features(g)
            # 滞后特征
            g = self.create_lag_features(g, n_lags=10)
            # 目标变量（训练模式）
            if not for_inference:
                g = self.create_target_variable(g)
            grouped_results.append(g)

        df_all = pd.concat(grouped_results, ignore_index=True)
        # 将无穷大替换为NaN以便清理
        df_all.replace([np.inf, -np.inf], np.nan, inplace=True)
        
        # 选择特征列（排除目标列和标识列）
        candidate_feature_columns = [
            col for col in df_all.columns
            if col not in ['ts_code', 'trade_date', 'target', 'future_macd', 'future_growth_rate', 'future_close']
        ]

        # 清理缺失：
        # - 训练模式：对全量列清理，并设置特征列为 candidate_feature_columns
        # - 推理模式：仅对已训练模型的特征列（self.feature_columns 若存在，否则使用 candidate）清理；不覆盖 self.feature_columns
        if for_inference:
            effective_features = self.feature_columns if getattr(self, 'feature_columns', None) else candidate_feature_columns
            df_clean = df_all.dropna(subset=effective_features).copy()
        else:
            df_clean = df_all.dropna().copy()
            self.feature_columns = candidate_feature_columns

        return df_clean
    
    def train_test_split_temporal(self, df, test_size=0.2):
        """时间序列数据分割（避免未来信息泄露）"""
        split_idx = int(len(df) * (1 - test_size))
        
        train_df = df.iloc[:split_idx].copy()
        test_df = df.iloc[split_idx:].copy()
        
        X_train = train_df[self.feature_columns]
        y_train = train_df['target']
        X_test = test_df[self.feature_columns]
        y_test = test_df['target']
        
        return X_train, X_test, y_train, y_test, train_df, test_df
    
    def train(self, df):
        """训练模型"""
        # 准备数据
        df_processed = self.prepare_features(df)
        
        if len(df_processed) < self.lookback_days:
            print("数据量不足，需要至少{}个交易日数据".format(self.lookback_days))
            return None
        
        # 分割数据
        X_train, X_test, y_train, y_test, train_df, test_df = self.train_test_split_temporal(df_processed)
        
        # 特征标准化
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # 定义XGBoost模型
        self.model = xgb.XGBClassifier(
            n_estimators=1000,
            max_depth=6,
            learning_rate=0.01,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='logloss'
        )
        
        # 训练模型
        # 兼容不同 xgboost 版本的早停与评估参数：基于 fit 签名动态设置
        fit_params = inspect.signature(self.model.fit).parameters
        fit_kwargs = {}
        if 'eval_set' in fit_params:
            fit_kwargs['eval_set'] = [(X_test_scaled, y_test)]
        if 'eval_metric' in fit_params:
            fit_kwargs['eval_metric'] = 'logloss'
        # 优先使用 callbacks，其次 early_stopping_rounds，若都不支持则跳过早停
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

        self.model.fit(
            X_train_scaled,
            y_train,
            **fit_kwargs,
        )
        
        # 评估模型
        train_accuracy, test_accuracy = self.evaluate_model(X_train_scaled, y_train, X_test_scaled, y_test)
        
        return {
            'train_accuracy': train_accuracy,
            'test_accuracy': test_accuracy,
            'feature_importance': self.get_feature_importance(),
            'train_df': train_df,
            'test_df': test_df
        }
    
    def evaluate_model(self, X_train, y_train, X_test, y_test):
        """评估模型性能"""
        y_train_pred = self.model.predict(X_train)
        y_test_pred = self.model.predict(X_test)
        
        train_accuracy = accuracy_score(y_train, y_train_pred)
        test_accuracy = accuracy_score(y_test, y_test_pred)
        
        print("=" * 50)
        print("模型评估结果")
        print("=" * 50)
        print(f"训练集准确率: {train_accuracy:.4f}")
        print(f"测试集准确率: {test_accuracy:.4f}")
        print("\n测试集详细分类报告:")
        print(classification_report(y_test, y_test_pred))
        
        return train_accuracy, test_accuracy
    
    def get_feature_importance(self, top_n=15):
        """获取特征重要性"""
        if self.model is None:
            return None
            
        importance_scores = self.model.feature_importances_
        feature_importance = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': importance_scores
        }).sort_values('importance', ascending=False).head(top_n)
        
        print("\nTop {} 重要特征:".format(top_n))
        print(feature_importance.to_string(index=False))
        
        return feature_importance
    
    def predict(self, df_recent):
        """使用最近数据进行预测（根据任务类型输出上涨/下跌概率）"""
        if self.model is None:
            print("请先训练模型")
            return None
        
        # 准备特征
        df_processed = self.prepare_features(df_recent, for_inference=True)
        
        if len(df_processed) == 0:
            print("数据不足无法预测")
            return None
        
        # 使用最近的数据点
        latest_data = df_processed.iloc[[-1]][self.feature_columns]
        latest_data_scaled = self.scaler.transform(latest_data)
        
        # 预测
        prediction = self.model.predict(latest_data_scaled)[0]
        prediction_proba = self.model.predict_proba(latest_data_scaled)[0]
        
        # 根据任务类型定义输出文案
        if self.target_mode == 'up':
            result = {
                'prediction': prediction,
                'probability_0': prediction_proba[0],  # 不增长的概率
                'probability_1': prediction_proba[1],  # 增长的概率
                'confidence': max(prediction_proba)
            }
            print(
                f"预测结果: 未来{self.forecast_days}天收盘价增长超过{self.growth_threshold*100:.0f}%的概率为 {prediction_proba[1]:.2%}"
            )
            print(f"预测类别: {'增长' if prediction == 1 else '不增长'}")
        else:
            result = {
                'prediction': prediction,
                'probability_0': prediction_proba[0],  # 不下跌的概率
                'probability_1': prediction_proba[1],  # 下跌的概率（超过阈值）
                'confidence': max(prediction_proba)
            }
            print(
                f"预测结果: 未来{self.drop_forecast_days}天收盘价下跌超过{self.drop_threshold*100:.0f}%的概率为 {prediction_proba[1]:.2%}"
            )
            print(f"预测类别: {'下跌' if prediction == 1 else '不下跌'}")

        print(f"置信度: {max(prediction_proba):.2%}")
        
        return result

    def predict_all_growth_dates(self, df_one: pd.DataFrame, for_inference: bool = False) -> list:
        """
        基于指定指数的全部样本进行批量预测，输出预测为增长的交易日期

        功能：
        - 对单个指数的全部历史数据进行特征处理并批量预测类别。
        - 返回预测结果为“增长”（类别 1）的 `trade_date` 列表。

        参数：
        - df_one: 单指数的原始数据 DataFrame，至少包含 `ts_code, trade_date, close, macd_bfq, macd_dif_bfq, macd_dea_bfq`

        返回值：
        - list[str]: 预测为增长的交易日期列表（按时间顺序）

        事件：
        - 无
        """
        if self.model is None:
            print("请先训练模型")
            return []

        processed = self.prepare_features(df_one, for_inference)
        if processed.empty:
            return []

        X = processed[self.feature_columns]
        X_scaled = self.scaler.transform(X)
        y_pred = self.model.predict(X_scaled)

        growth_dates = processed.loc[y_pred == 1, 'trade_date'].astype(str).tolist()
        return growth_dates

    def predict_all_drop_dates(self, df_one: pd.DataFrame) -> list:
        """
        基于指定指数的全部样本进行批量预测，输出预测为下跌的交易日期

        功能：
        - 需在 `target_mode='down'` 下训练得到的模型上调用，返回预测类别为 1（下跌超过阈值）的日期列表。

        参数：
        - df_one: 单指数的原始数据 DataFrame

        返回值：
        - list[str]: 预测为下跌的交易日期列表（按时间顺序）

        事件：
        - 无
        """
        if self.model is None:
            print("请先训练模型")
            return []

        processed = self.prepare_features(df_one)
        if processed.empty:
            return []

        X = processed[self.feature_columns]
        X_scaled = self.scaler.transform(X)
        y_pred = self.model.predict(X_scaled)

        drop_dates = processed.loc[y_pred == 1, 'trade_date'].astype(str).tolist()
        return drop_dates

    def compute_actual_event_dates(self, df_one: pd.DataFrame) -> list:
        """
        从原始数据直接计算“实际满足条件”的事件日期列表（与当前任务模式/阈值一致）

        功能：
        - 依据当前 `target_mode`、阈值与窗口天数，在原始数据上生成 `target` 标签，并返回 target==1 的 `trade_date` 列表。

        参数：
        - df_one: 单指数原始数据 DataFrame，需包含 `close` 与 `trade_date`

        返回值：
        - list[str]: 实际满足事件条件的交易日期列表（按时间顺序）

        事件：
        - 无
        """
        if df_one is None or df_one.empty:
            return []

        df_gt = df_one.sort_values('trade_date').copy()
        df_gt = self.create_target_variable(df_gt)
        # 去除无法计算的行（未来窗口导致的NaN）
        df_gt = df_gt.dropna(subset=['future_close', 'future_growth_rate'])
        actual_dates = df_gt.loc[df_gt['target'] == 1, 'trade_date'].astype(str).tolist()
        return actual_dates

# 使用示例
def _f1_from_pr(precision: float, recall: float) -> float:
    """
    计算 F1（此处按用户要求命名为 R1）

    功能：
    - 基于精确率与召回率计算 F1 分数。

    参数：
    - precision: 精确率（0~1）
    - recall: 召回率（0~1）

    返回值：
    - float: F1 分数（当 P 或 R 为 0 时返回 0.0）

    事件：
    - 无
    """
    if precision > 0 and recall > 0:
        return 2 * (precision * recall) / (precision + recall)
    return 0.0


def evaluate_params_on_dataset(
    df: pd.DataFrame,
    lookback_days: int,
    forecast_days: int,
    growth_threshold: float,
    target_mode: str = 'up',
    train_limit: int = 300,
):
    """
    在给定聚合数据集上按指定参数进行训练与评估，返回指标。

    功能：
    - 基于参数构建 MACDPredictor，按训练/预测指数拆分进行训练与全样本预测。
    - 汇总跨指数的微平均与宏平均召回率、精确率与 R1(F1)。

    参数：
    - df: 跨指数聚合原始数据集（包含 `ts_code, trade_date, open, high, low, close, macd_*`）
    - lookback_days: 回看天数
    - forecast_days: 预测未来天数
    - growth_threshold: 上涨阈值（或在下跌模式下忽略）
    - target_mode: 任务模式，'up' 或 'down'
    - train_limit: 训练集指数数量 n（将使用前 n 只指数训练，后 5 只指数仅用于评估）

    返回值：
    - dict: 指标字典，例如：
      {
        'micro': {'recall': float, 'precision': float, 'R1': float},
        'macro': {'recall': float, 'precision': float, 'R1': float},
        'train_codes_count': int,
        'predict_codes_count': int,
      }

    事件：
    - 无
    """
    predictor = MACDPredictor(
        lookback_days=lookback_days,
        forecast_days=forecast_days,
        target_mode=target_mode,
        growth_threshold=growth_threshold,
    )

    # 拆分指数集合：前 n 只用于训练，后 5 只仅用于预测
    codes = df['ts_code'].dropna().unique().tolist()
    if len(codes) <= 5:
        # 指数不足，退化为使用全部指数进行训练与随机一只指数评估
        results = predictor.train(df)
        if not results:
            return {
                'micro': {'recall': 0.0, 'precision': 0.0, 'R1': 0.0},
                'macro': {'recall': 0.0, 'precision': 0.0, 'R1': 0.0},
                'train_codes_count': len(codes),
                'predict_codes_count': 0,
            }

        any_code = random.choice(codes) if codes else None
        if any_code is None:
            return {
                'micro': {'recall': 0.0, 'precision': 0.0, 'R1': 0.0},
                'macro': {'recall': 0.0, 'precision': 0.0, 'R1': 0.0},
                'train_codes_count': len(codes),
                'predict_codes_count': 0,
            }

        df_one = df[df['ts_code'] == any_code].sort_values('trade_date')
        # 预测事件日期
        if predictor.target_mode == 'down':
            pred_dates = predictor.predict_all_drop_dates(df_one)
        else:
            pred_dates = predictor.predict_all_growth_dates(df_one)
        # 实际事件日期
        actual_dates = predictor.compute_actual_event_dates(df_one)

        pred_set = set(pred_dates)
        actual_set = set(actual_dates)
        tp = len(pred_set & actual_set)
        recall = tp / len(actual_set) if len(actual_set) > 0 else 0.0
        precision = tp / len(pred_set) if len(pred_set) > 0 else 0.0
        return {
            'micro': {'recall': recall, 'precision': precision, 'R1': _f1_from_pr(precision, recall)},
            'macro': {'recall': recall, 'precision': precision, 'R1': _f1_from_pr(precision, recall)},
            'train_codes_count': len(codes),
            'predict_codes_count': 1,
        }

    # 正常路径：预留 5 只指数用于评估
    # 注意：此处不直接截断 df，以指数代码为划分依据
    predict_tail = 5
    if len(codes) < train_limit + predict_tail:
        # 若实际代码数量不足以满足训练 + 评估，则按现有数量进行拆分
        train_codes = codes[:-predict_tail] if len(codes) > predict_tail else codes
        predict_codes = codes[-predict_tail:] if len(codes) > predict_tail else []
    else:
        train_codes = codes[:train_limit]
        predict_codes = codes[train_limit:train_limit + predict_tail]

    df_train = df[df['ts_code'].isin(train_codes)].copy()
    results = predictor.train(df_train)
    if not results:
        return {
            'micro': {'recall': 0.0, 'precision': 0.0, 'R1': 0.0},
            'macro': {'recall': 0.0, 'precision': 0.0, 'R1': 0.0},
            'train_codes_count': len(train_codes),
            'predict_codes_count': len(predict_codes),
        }

    # 汇总总体指标（微/宏平均）
    overall_tp = 0
    overall_pred = 0
    overall_actual = 0
    recalls = []
    precisions = []

    for any_code in predict_codes:
        df_one = df[df['ts_code'] == any_code].sort_values('trade_date')
        if predictor.target_mode == 'down':
            pred_dates = predictor.predict_all_drop_dates(df_one)
        else:
            pred_dates = predictor.predict_all_growth_dates(df_one)

        actual_dates = predictor.compute_actual_event_dates(df_one)

        pred_set = set(pred_dates)
        actual_set = set(actual_dates)
        tp = len(pred_set & actual_set)
        recall = tp / len(actual_set) if len(actual_set) > 0 else 0.0
        precision = tp / len(pred_set) if len(pred_set) > 0 else 0.0

        overall_tp += tp
        overall_pred += len(pred_set)
        overall_actual += len(actual_set)
        recalls.append(recall)
        precisions.append(precision)

    micro_recall = overall_tp / overall_actual if overall_actual > 0 else 0.0
    micro_precision = overall_tp / overall_pred if overall_pred > 0 else 0.0
    micro_f1 = _f1_from_pr(micro_precision, micro_recall)

    macro_recall = float(np.mean(recalls)) if len(recalls) > 0 else 0.0
    macro_precision = float(np.mean(precisions)) if len(precisions) > 0 else 0.0
    macro_f1 = _f1_from_pr(macro_precision, macro_recall)

    return {
        'micro': {'recall': micro_recall, 'precision': micro_precision, 'R1': micro_f1},
        'macro': {'recall': macro_recall, 'precision': macro_precision, 'R1': macro_f1},
        'train_codes_count': len(train_codes),
        'predict_codes_count': len(predict_codes),
    }


# 模拟数据获取（已替换为真实数据获取逻辑）
def get_mock_data(ts_code: str, days: int = 365) -> pd.DataFrame:
    """
    获取真实指数技术面因子数据（替代模拟数据）

    功能：
    - 通过 Tushare `idx_factor_pro` 接口获取指定指数最近一段时间（默认一年）的技术面因子与行情数据。
    - 返回包含 MACD 三项与基础行情的 DataFrame，以满足训练和特征工程需求。

    参数：
    - ts_code: 指数代码（如 `000001.SH` 为上证指数，SSE 市场）
    - days: 获取的自然日跨度，默认 365（最近一年）

    返回值：
    - pandas.DataFrame：包含列 `ts_code, trade_date, open, high, low, close, macd_bfq, macd_dif_bfq, macd_dea_bfq`

    事件：
    - 无
    """

    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

    fields = (
        'ts_code,trade_date,open,high,low,close,'
        'macd_bfq,macd_dif_bfq,macd_dea_bfq'
    )

    resp = call_tushare(
        interface='idx_factor_pro',
        params={
            'ts_code': ts_code,
            'start_date': start_date,
            'end_date': end_date,
        },
        fields=fields,
        use_query=False,
    )

    if not isinstance(resp, dict) or resp.get('code') != 200:
        message = resp.get('message') if isinstance(resp, dict) else str(resp)
        raise RuntimeError(f"获取 Tushare 数据失败: {message}")

    data = resp.get('data', {})
    records = data.get('records', []) if isinstance(data, dict) else []
    df = pd.DataFrame(records)

    if df.empty:
        raise RuntimeError("idx_factor_pro 返回空数据，请确认 ts_code 与时间范围是否有效")

    # 保证时间顺序由早到晚
    df = df.sort_values('trade_date').reset_index(drop=True)
    return df

def get_sse_index_codes(limit: int | None = None) -> list[str]:
    """
    获取上交所（SSE）指数代码列表

    功能：
    - 通过 Tushare `index_basic` 接口查询 `market='SSE'` 的指数基本信息，提取指数代码列表。

    参数：
    - limit: 限制返回的指数数量，默认 None（返回全部），建议在批量训练时设置以控制请求量。

    返回值：
    - list[str]: 指数 TS 代码列表，例如 `['000001.SH', '000300.SH', ...]`

    事件：
    - 无
    """
    resp = call_tushare(
        interface='index_basic',
        params={'market': 'SSE'},
        fields='ts_code,name,market',
        use_query=False,
    )

    if not isinstance(resp, dict) or resp.get('code') != 200:
        msg = resp.get('message') if isinstance(resp, dict) else str(resp)
        raise RuntimeError(f"获取 SSE 指数列表失败: {msg}")

    records = resp.get('data', {}).get('records', [])
    codes = [r['ts_code'] for r in records if isinstance(r, dict) and r.get('ts_code')]
    if limit is not None:
        codes = codes[:limit]
    return codes

def get_index_codes(limit: int | None = None, market: str = 'SSE') -> list[str]:
    """
    获取指定市场（market）的指数代码列表

    功能：
    - 通过 Tushare `index_basic` 接口查询指定市场（默认 SSE）的指数基本信息，提取指数代码列表。

    参数：
    - limit: 限制返回的指数数量，默认 None（返回全部），建议在批量训练时设置以控制请求量。

    返回值：
    - list[str]: 指数 TS 代码列表，例如 `['000001.SH', '000300.SH', ...]`

    事件：
    - 无
    """
    resp = call_tushare(
        interface='index_basic',
        params={'market': market},
        fields='ts_code,name,market',
        use_query=False,
    )

    if not isinstance(resp, dict) or resp.get('code') != 200:
        msg = resp.get('message') if isinstance(resp, dict) else str(resp)
        raise RuntimeError(f"获取 {market} 指数列表失败: {msg}")

    records = resp.get('data', {}).get('records', [])
    codes = [r for r in records if isinstance(r, dict) and r.get('ts_code')]
    return codes

def load_sse_indices_dataset(days: int = 365, limit: int = 30) -> pd.DataFrame:
    """
    批量获取多个 SSE 指数的技术面因子数据并聚合为训练样本

    功能：
    - 先查询 SSE 指数列表，再对每个指数调用 `idx_factor_pro` 获取最近一年数据。
    - 聚合为一个 DataFrame，包含各指数的 `ts_code` 和逐日记录，按 `ts_code, trade_date` 排序。

    参数：
    - days: 自然日跨度，默认 365（最近一年）
    - limit: 指数数量上限，默认 30，避免请求过多导致速率限制或耗时过长。

    返回值：
    - pandas.DataFrame：跨多个指数的训练样本原始数据

    事件：
    - 无
    """
    codes = get_sse_index_codes(limit=limit)
    all_records: list[pd.DataFrame] = []

    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
    fields = (
        'ts_code,trade_date,open,high,low,close,'
        'macd_bfq,macd_dif_bfq,macd_dea_bfq'
    )

    for ts_code in codes:
        resp = call_tushare(
            interface='idx_factor_pro',
            params={'ts_code': ts_code, 'start_date': start_date, 'end_date': end_date},
            fields=fields,
            use_query=False,
        )
        if isinstance(resp, dict) and resp.get('code') == 200:
            recs = resp.get('data', {}).get('records', [])
            if recs:
                df_one = pd.DataFrame(recs)
                all_records.append(df_one)
        # 若失败或无数据，跳过该指数

    if not all_records:
        raise RuntimeError('未获取到任何 SSE 指数的技术面数据')

    df_all = pd.concat(all_records, ignore_index=True)
    df_all = df_all.sort_values(['ts_code', 'trade_date']).reset_index(drop=True)
    return df_all

def select_recent_index_data(df: pd.DataFrame, ts_code: str | None = None, days: int = 70) -> pd.DataFrame:
    """
    从聚合数据集中选择某一指数的最近若干天数据用于预测

    功能：
    - 若未指定 `ts_code`，则从数据集中取第一个可用指数代码。
    - 按该指数的 `trade_date` 升序排列后截取最近 `days` 条记录。

    参数：
    - df: 聚合数据集，包含多个指数的记录
    - ts_code: 指定的指数代码，可为 None（自动选择）
    - days: 最近样本条数，默认 70

    返回值：
    - pandas.DataFrame：该指数最近 `days` 条记录

    事件：
    - 无
    """
    if ts_code is None:
        codes = df['ts_code'].dropna().unique().tolist()
        if not codes:
            raise RuntimeError('数据集中未发现有效的指数代码')
        ts_code = codes[0]

    df_one = df[df['ts_code'] == ts_code].sort_values('trade_date')
    return df_one.tail(days)

def scan_all_indices_recent_growth(
    limit: int = 500,
    forecast_days: int = 5,
    growth_threshold: float = 0.05,
    days_buffer: int = 90,
    token: str | None = None,
) -> dict:
    """
    使用已训练的 MACD XGBoost 上涨模型，批量扫描所有指数的“最近一天”是否存在未来5天内上涨≥5%的可能

    功能：
    - 加载本地保存的 `macd_xgb_up.joblib` 模型组件（模型/标准化器/特征列/参数）。
    - 遍历上交所（SSE）全部或指定数量的指数代码，拉取最近一段时间的技术面数据。
    - 针对每个指数的“最近一个交易日”样本进行预测，若预测类别为上涨事件（类别=1），打印并收集结果。

    参数：
    - limit(int | None): 限制扫描的指数数量，默认 None（扫描全部SSE指数）。
    - forecast_days(int): 预测未来天数（仅用于文案与参数说明，模型本身已训练），默认 5。
    - growth_threshold(float): 上涨阈值（仅用于文案与参数说明），默认 0.05（5%）。
    - days_buffer(int): 在模型回看期之外额外补充的抓取天数，用于稳定滚动/滞后特征，默认 90。
    - token(str | None): 可选的 Tushare Token（覆盖环境变量）。

    返回值：
    - dict: {
        'email_content': str,         # HTML 格式的邮件内容（包含扫描总数与命中表格）
        'hits': list[dict],           # 命中明细列表
        'scanned_count': int,         # 实际扫描的指数数量
        'hit_count': int,             # 命中数量
      }

    事件：
    - 加载模型文件
    - 获取SSE指数代码列表
    - 逐指数抓取 idx_factor_pro 数据并生成最近样本预测
    - 构建 HTML 邮件头与命中表格，打印并返回命中结果集合
    """
    # 加载模型文件
    model_path = Path(__file__).resolve().parent / "models" / "macd_xgb_up.joblib"
    if not model_path.exists():
        raise RuntimeError(f"模型文件不存在: {model_path}。请先运行 main_predict() 生成模型。")

    artifacts = joblib.load(model_path)
    params = artifacts.get('params', {})
    lookback_days = int(params.get('lookback_days', 60))

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
    # 'CICC', 'SW', 'SZSE', 'SSE', 
    makret_list = ['CICC', 'SW', 'SZSE', 'SSE', ]
    # 获取指数列表
    code_list = []
    for market in makret_list:
        codes = get_index_codes(limit=limit, market=market)
        if not codes:
            raise RuntimeError(f'未获取到任何{market}指数代码')
        code_list.extend(codes)

    # 时间范围与字段
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=lookback_days + days_buffer)).strftime('%Y%m%d')
    fields = (
        'ts_code,trade_date,open,high,low,close,'
        'macd_bfq,macd_dif_bfq,macd_dea_bfq'
    )

    hits: list[dict] = []

    for code in code_list:
        resp = call_tushare(
            interface='idx_factor_pro',
            params={'ts_code': code['ts_code'], 'start_date': start_date, 'end_date': end_date},
            token=token,
            fields=fields,
            use_query=False,
        )
        time.sleep(0.1)

        # 仅处理成功返回的数据
        if not isinstance(resp, dict) or resp.get('code') != 200:
            continue

        records = resp.get('data', {}).get('records', [])
        if not records:
            continue

        df = pd.DataFrame(records).sort_values('trade_date').reset_index(drop=True)
        processed = predictor.prepare_features(df, for_inference=True)
        if processed.empty:
            continue

        # 取最近一条样本进行预测
        latest_row = processed.iloc[[-1]]
        latest_features = latest_row[predictor.feature_columns]
        latest_scaled = predictor.scaler.transform(latest_features)

        y_pred = predictor.model.predict(latest_scaled)[0]
        y_proba = predictor.model.predict_proba(latest_scaled)[0]

        if int(y_pred) == 1:
            last_date = str(latest_row['trade_date'].iloc[0])
            result = {
                'ts_code': code['ts_code'],
                'trade_date': last_date,
                'probability_1': float(y_proba[1]),
                'confidence': float(max(y_proba)),
                'params': {
                    'forecast_days': forecast_days,
                    'growth_threshold': growth_threshold,
                }
            }
            # 打印命中结果
            print(
                f"命中: 市场 {code['market']} 指数 {code['ts_code']}-{code['name']} 在 {last_date} 存在未来{forecast_days}天上涨≥{growth_threshold*100:.0f}% 的可能，"
                f"预测概率为 {y_proba[1]:.2%}，置信度 {max(y_proba):.2%}"
            )
            hits.append(result)
    # 组装整体邮件内容（包含扫描总数与命中明细）
    scanned_count = len(code_list)
    hit_count = len(hits)
    # 以 HTML 形式构建更友好的邮件内容：包含基本信息与命中明细表格
    header_html = (
        f"<div style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;font-size:14px;color:#333;\">"
        f"<h2 style=\"margin:0 0 8px;\">MACD XGBoost 指数扫描结果【此数据仅作参考，不构成任何交易建议】</h2>"
        f"<p style=\"margin:0;\">扫描时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>"
        f"<p style=\"margin:0;\">预测参数：未来{forecast_days}天，上涨阈值≥{growth_threshold*100:.0f}%</p>"
        f"<p style=\"margin:0 0 12px;\">共扫描 {scanned_count} 只指数，命中 {hit_count} 只</p>"
        f"</div>"
    )

    # 命中明细表格（若无命中则输出提示）
    if hits:
        # 将命中结果保存到选股记录表（按交易日+代码去重）
        try:
            for h in hits:
                code_info = next((c for c in code_list if c.get('ts_code') == h['ts_code']), None)
                market = code_info.get('market') if code_info else 'SSE'
                name = code_info.get('name') if code_info else h['ts_code']
                # 将 Tushare 的日期字符串转换为 date
                trade_date = datetime.strptime(str(h['trade_date']), '%Y%m%d').date()

                # 先查重：若同(交易日, 代码)已存在则跳过
                exists = StockSelectionRecord.objects.filter(code=h['ts_code'], trade_date=trade_date).exists()
                if exists:
                    continue

                # 保存记录（概率/置信度转为百分比数值）
                StockSelectionRecord.objects.create(
                    market=market,
                    code=h['ts_code'],
                    name=name,
                    trade_date=trade_date,
                    predict_rise_prob=float(h.get('probability_1', 0.0)) * 100.0,
                    confidence=float(h.get('confidence', 0.0)) * 100.0,
                    prediction_type='MACD_XGBoost_for_5',
                )
        except Exception as e:
            print(f"保存选股记录失败: {e}")

        table_header = (
            "<table style=\"width:100%;border-collapse:collapse;border:1px solid #e5e7eb;\">"
            "<thead>"
            "<tr style=\"background:#f9fafb;\">"
            "<th style=\"padding:8px;border:1px solid #e5e7eb;text-align:left;\">市场</th>"
            "<th style=\"padding:8px;border:1px solid #e5e7eb;text-align:left;\">代码</th>"
            "<th style=\"padding:8px;border:1px solid #e5e7eb;text-align:left;\">名称</th>"
            "<th style=\"padding:8px;border:1px solid #e5e7eb;text-align:left;\">交易日</th>"
            "<th style=\"padding:8px;border:1px solid #e5e7eb;text-align:left;\">预测上涨概率</th>"
            "<th style=\"padding:8px;border:1px solid #e5e7eb;text-align:left;\">置信度</th>"
            "</tr>"
            "</thead><tbody>"
        )

        rows_html = []
        for idx, h in enumerate(hits):
            code_info = next((c for c in code_list if c.get('ts_code') == h['ts_code']), None)
            market = code_info.get('market') if code_info else 'SSE'
            name = code_info.get('name') if code_info else h['ts_code']
            row_bg = '#ffffff' if idx % 2 == 0 else '#fcfcfc'
            prob = f"{h['probability_1']*100:.2f}%"
            conf = f"{h['confidence']*100:.2f}%"
            rows_html.append(
                (
                    f"<tr style=\"background:{row_bg};\">"
                    f"<td style=\"padding:8px;border:1px solid #e5e7eb;\">{market}</td>"
                    f"<td style=\"padding:8px;border:1px solid #e5e7eb;\">{h['ts_code']}</td>"
                    f"<td style=\"padding:8px;border:1px solid #e5e7eb;\">{name}</td>"
                    f"<td style=\"padding:8px;border:1px solid #e5e7eb;\">{h['trade_date']}</td>"
                    f"<td style=\"padding:8px;border:1px solid #e5e7eb;\">{prob}</td>"
                    f"<td style=\"padding:8px;border:1px solid #e5e7eb;\">{conf}</td>"
                    f"</tr>"
                )
            )

        table_footer = "</tbody></table>"
        table_section = (
            f"<div style=\"margin-top:8px;\"><strong>命中明细</strong></div>" +
            table_header + "".join(rows_html) + table_footer
        )
    else:
        table_section = "<p style=\"margin-top:8px;color:#666;\">暂无命中</p>"

    email_content = header_html + table_section

    return {
        'email_content': email_content,
        'hits': hits,
        'scanned_count': scanned_count,
        'hit_count': hit_count,
    }

def main_predict(
    lookback_days: int = 60,
    forecast_days: int = 5,
    growth_threshold: float = 0.05,
    target_mode: str = 'up',
    train_limit: int = 300,
    days: int = 365,
):
    """
    主预测入口（参数化）

    功能：
    - 参数化构造预测器与训练/评估流程，返回跨指数汇总的指标（召回率、精确率、R1）。

    参数：
    - lookback_days: 回看天数（示例：30/60/90）
    - forecast_days: 预测未来天数（示例：2/3/4/5）
    - growth_threshold: 上涨阈值（示例：0.03/0.04/0.05/0.06）
    - target_mode: 任务模式，'up' 或 'down'，默认 'up'
    - train_limit: 训练集指数数量（示例：30/50/100/200/300）
    - days: 数据时间跨度（自然日），默认 365

    返回值：
    - dict: 指标字典，包含微/宏平均的召回率、精确率与 R1(F1)。

    事件：
    - 无
    """
    
    # 获取数据
    print("获取历史数据（SSE多指数聚合）...")
    # 如需仅训练上证指数，可替换为：df = get_mock_data('000001.SH', days=365)
    # 训练/预测数据拆分策略：若训练limit为n，则实际获取n+5只指数数据，其中后5只仅用于预测
    # 功能：控制训练与预测指数集合，避免数据泄露并提供独立评估
    # 参数：n（训练集指数数量），此处通过 train_limit 变量设定
    # 返回值：无（在主流程中使用拆分后的数据进行训练与预测）
    # 事件：无

    total_limit = train_limit + 5  # 实际抓取 n+5 个指数数据
    df = load_sse_indices_dataset(days=days, limit=total_limit)

    # 实例化预测器
    predictor = MACDPredictor(
        lookback_days=lookback_days,
        forecast_days=forecast_days,
        growth_threshold=growth_threshold,
        target_mode=target_mode,
    )
    
    # 训练模型
    # 拆分指数集合：前 n 只用于训练，后 5 只仅用于预测
    codes = df['ts_code'].dropna().unique().tolist()
    if len(codes) <= 5:
        print("指数数量不足（<=5），无法预留5只用于预测；将使用全部指数进行训练与随机预测。")
        print("训练XGBoost模型...")
        results = predictor.train(df)
        
        if results:
            print("\n进行预测（随机指数全样本）...")
            any_code = random.choice(codes) if codes else None
            if any_code is None:
                print("未找到可用指数代码，跳过预测。")
            else:
                df_one = df[df['ts_code'] == any_code].sort_values('trade_date')
                # 预测事件日期
                if predictor.target_mode == 'down':
                    pred_dates = predictor.predict_all_drop_dates(df_one)
                else:
                    pred_dates = predictor.predict_all_growth_dates(df_one)
                # 实际事件日期
                actual_dates = predictor.compute_actual_event_dates(df_one)

                # 指标：召回率与准确率(精确率)
                pred_set = set(pred_dates)
                actual_set = set(actual_dates)
                tp = len(pred_set & actual_set)
                recall = tp / len(actual_set) if len(actual_set) > 0 else 0.0
                precision = tp / len(pred_set) if len(pred_set) > 0 else 0.0

                label_cn = "下跌" if predictor.target_mode == 'down' else "增长"
                print(f"预测指数: {any_code}")
                print(f"实际{label_cn}日期数: {len(actual_dates)}，预测{label_cn}日期数: {len(pred_dates)}，命中数: {tp}")
                print(f"召回率: {recall:.2%}，准确率(精确率): {precision:.2%}")
                print(f"预测{label_cn}日期列表:", sorted(pred_dates))
                print(f"实际{label_cn}日期列表:", sorted(actual_dates))

        # 保存模型文件（小样本分支也保存）
        try:
            model_dir = Path(__file__).resolve().parent / "models"
            model_dir.mkdir(parents=True, exist_ok=True)
            model_path = model_dir / f"macd_xgb_{predictor.target_mode}.joblib"
            joblib.dump({
                'model': predictor.model,
                'scaler': predictor.scaler,
                'feature_columns': predictor.feature_columns,
                'params': {
                    'lookback_days': predictor.lookback_days,
                    'forecast_days': predictor.forecast_days,
                    'growth_threshold': predictor.growth_threshold,
                    'target_mode': predictor.target_mode,
                }
            }, model_path)
            print(f"模型已保存: {model_path}")
        except Exception as e:
            print(f"保存模型失败: {e}")
    else:
        train_codes = codes[:-5]
        predict_codes = codes[-5:]

        df_train = df[df['ts_code'].isin(train_codes)].copy()
        print(f"训练XGBoost模型（使用 {len(train_codes)} 只指数）...")
        results = predictor.train(df_train)

        if results:
            print("\n进行预测（剩余5只指数全样本）...")
            # 汇总总体指标（微/宏平均）
            overall_tp = 0
            overall_pred = 0
            overall_actual = 0
            recalls = []
            precisions = []
            for any_code in predict_codes:
                df_one = df[df['ts_code'] == any_code].sort_values('trade_date')
                # 模型预测的事件日期
                if predictor.target_mode == 'down':
                    pred_dates = predictor.predict_all_drop_dates(df_one)
                else:
                    pred_dates = predictor.predict_all_growth_dates(df_one)

                # 原始数据计算的实际事件日期
                actual_dates = predictor.compute_actual_event_dates(df_one)

                # 指标对比：召回率与准确率（此处准确率按预测日期的精确率定义）
                pred_set = set(pred_dates)
                actual_set = set(actual_dates)
                tp = len(pred_set & actual_set)
                recall = tp / len(actual_set) if len(actual_set) > 0 else 0.0
                precision = tp / len(pred_set) if len(pred_set) > 0 else 0.0

                label_cn = "下跌" if predictor.target_mode == 'down' else "增长"
                print(f"预测指数: {any_code}")
                print(f"实际{label_cn}日期数: {len(actual_dates)}，预测{label_cn}日期数: {len(pred_dates)}，命中数: {tp}")
                print(f"召回率: {recall:.2%}，准确率(精确率): {precision:.2%}")
                print(f"预测{label_cn}日期列表:", sorted(pred_dates))
                print(f"实际{label_cn}日期列表:", sorted(actual_dates))

                # 累计总体统计
                overall_tp += tp
                overall_pred += len(pred_set)
                overall_actual += len(actual_set)
                recalls.append(recall)
                precisions.append(precision)

            # 打印总体指标
            micro_recall = overall_tp / overall_actual if overall_actual > 0 else 0.0
            micro_precision = overall_tp / overall_pred if overall_pred > 0 else 0.0
            macro_recall = float(np.mean(recalls)) if len(recalls) > 0 else 0.0
            macro_precision = float(np.mean(precisions)) if len(precisions) > 0 else 0.0

            label_cn = "下跌" if predictor.target_mode == 'down' else "增长"
            print("\n总体评估（跨指数汇总）")
            print("=" * 50)
            print(f"样本汇总：实际{label_cn}日期总数: {overall_actual}，预测{label_cn}日期总数: {overall_pred}，命中总数: {overall_tp}")
            print(f"微平均：召回率 {micro_recall:.2%}，准确率(精确率) {micro_precision:.2%}")
            print(f"宏平均：召回率 {macro_recall:.2%}，准确率(精确率) {macro_precision:.2%}")

        # 保存模型文件（常规分支保存）
        try:
            model_dir = Path(__file__).resolve().parent / "models"
            model_dir.mkdir(parents=True, exist_ok=True)
            model_path = model_dir / f"macd_xgb_{predictor.target_mode}.joblib"
            joblib.dump({
                'model': predictor.model,
                'scaler': predictor.scaler,
                'feature_columns': predictor.feature_columns,
                'params': {
                    'lookback_days': predictor.lookback_days,
                    'forecast_days': predictor.forecast_days,
                    'growth_threshold': predictor.growth_threshold,
                    'target_mode': predictor.target_mode,
                }
            }, model_path)
            print(f"模型已保存: {model_path}")
        except Exception as e:
            print(f"保存模型失败: {e}")

    # 返回指标（不再返回 predictor/results，聚焦评估结果）
    metrics = evaluate_params_on_dataset(
        df=df,
        lookback_days=lookback_days,
        forecast_days=forecast_days,
        growth_threshold=growth_threshold,
        target_mode=target_mode,
        train_limit=train_limit,
    )
    return metrics


def batch_test_macd_xgboost():
    """
    批量测试：遍历参数组合并输出召回率、准确率（精确率）与 R1(F1)

    功能：
    - 一次性拉取最大所需指数数量的数据集，遍历参数网格进行训练与评估。
    - 返回每个参数组合下的微/宏平均指标，便于比较与选型。

    参数：
    - 无（内部固定参数网格：lookback_days=[30,60,90]，forecast_days=[2,3,4,5]，growth_threshold=[0.03,0.04,0.05,0.06]，train_limit=[30,50,100,200,300]）

    返回值：
    - pandas.DataFrame：列包含参数与指标（micro_recall, micro_precision, micro_R1, macro_recall, macro_precision, macro_R1）

    事件：
    - 无
    """
    lookbacks = [30, 60, 90]
    forecasts = [2, 3, 4, 5]
    thresholds = [0.03, 0.04, 0.05, 0.06]
    train_limits = [30, 50, 100, 200, 300]

    # 仅拉取一次数据——以最大训练集数量为上限
    max_train = max(train_limits)
    total_limit = max_train + 5
    print(f"批量测试：拉取 {total_limit} 只指数的数据用于参数网格评估...")
    df = load_sse_indices_dataset(days=365, limit=total_limit)

    rows = []
    for lb in lookbacks:
        for fc in forecasts:
            for th in thresholds:
                for tl in train_limits:
                    metrics = evaluate_params_on_dataset(
                        df=df,
                        lookback_days=lb,
                        forecast_days=fc,
                        growth_threshold=th,
                        target_mode='up',
                        train_limit=tl,
                    )
                    rows.append({
                        'lookback_days': lb,
                        'forecast_days': fc,
                        'growth_threshold': th,
                        'train_limit': tl,
                        'micro_recall': metrics['micro']['recall'],
                        'micro_precision': metrics['micro']['precision'],
                        'micro_R1': metrics['micro']['R1'],
                        'macro_recall': metrics['macro']['recall'],
                        'macro_precision': metrics['macro']['precision'],
                        'macro_R1': metrics['macro']['R1'],
                        'train_codes_count': metrics.get('train_codes_count', 0),
                        'predict_codes_count': metrics.get('predict_codes_count', 0),
                    })

    return pd.DataFrame(rows)

def send_macd_xgboost_results_email(
    usernames: list[str] | None = None,
    sender_email: str = "1125677925@qq.com",
    auth_code: str = "wsxmvqhgoeszigdh",
) -> dict:
    """
    发送 MACD XGBoost 指数增长预测结果到指定用户邮箱

    功能：
    - 根据提供的用户名列表查询用户邮箱，生成命中结果的 HTML 邮件内容，并统一发送邮件。

    参数：
    - usernames(list[str] | None): 用户名列表；若为 None 则使用系统预设用户名集合。
    - sender_email(str): 发件人邮箱地址；默认使用当前配置值。
    - auth_code(str): QQ 邮箱 SMTP 授权码；默认使用当前配置值。

    返回值：
    - dict: {
        'emails': list[str],          # 实际发送的收件人邮箱列表
        'scanned_count': int,         # 扫描指数数量
        'hit_count': int,             # 命中数量
        'send_result': dict,          # 邮件发送返回结果（含 code/message 等）
    }

    事件：
    - 查询用户邮箱 → 执行指数扫描 → 生成 HTML 邮件内容 → 发送邮件。
    """

    default_user_list = [
        "admin","Neil","Eleven","huang36077","windeve","sony","jnukylin","大森不胖",
        "桐桐巴巴","LucHu","snoopy","金牛腾飞","wuxingchen","knight","tuwu","shine",
        "zxxx241","Jerome","feng","鹏鹏涨了","xiafine","heatonc","SAM","Cyt4222525","catashd"
    ]

    names = (usernames or default_user_list)
    user_email_list: list[str] = ['1605895800@qq.com', 'mymailbox_2003@163.com']
    for uname in names:
        if not uname or not str(uname).strip():
            continue
        user_object = User.objects.filter(username=str(uname).strip()).first()
        if user_object is None:
            print(f"用户 {uname} 不存在")
            continue
        print(f"用户 {uname} 的邮箱是 xxx{user_object.email[3:]}" )
        user_email_list.append(user_object.email)

    scan_hits = scan_all_indices_recent_growth()

    send_result = send_qq_email(
        subject=f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} XGBoost 指数增长预测结果",
        body=scan_hits["email_content"],
        to_emails=user_email_list,
        sender_email=sender_email,
        auth_code=auth_code,
        use_html=True,
    )

    return {
        "emails": user_email_list,
        "scanned_count": scan_hits.get("scanned_count", 0),
        "hit_count": scan_hits.get("hit_count", 0),
        "send_result": send_result,
    }

if __name__ == "__main__":
    # 运行批量测试并打印结果
    # df_results = batch_test_macd_xgboost()
    # # 打印结果表（避免过长换行，用户可自行保存/分析）
    # print(df_results.to_string(index=False))
    # main_predict()
    # 使用封装好的函数发送结果邮件
    # send_macd_xgboost_results_email()
    # StockSelectionRecord.objects.create(
    #     market = 'SSE',
    #     code = '000692.SH',
    #     name = '科创新能',
    #     trade_date = datetime(2025, 11, 25),
    #     predict_rise_prob = 0.749,
    #     confidence = 0.749,
    #     prediction_type = 'MACD_XGBoost_for_5',
    # )
    # exists = StockSelectionRecord.objects.filter(code='000692.SH', trade_date=datetime(2025, 11, 25)).exists()
    # if exists:
    #     print("记录已存在")

    text = """
    命中: 市场 SSE 指数 000692.SH-科创新能 在 20251124 存在未来5天上涨≥5% 的可能，预测概率为 77.18%，置信度 77.18%
    命中: 市场 SSE 指数 000813.SH-细分化工(SH) 在 20251124 存在未来5天上涨≥5% 的可能，预测概率为 51.65%，置信度 51.65%
    命中: 市场 SSE 指数 000827.SH-中证环保 在 20251124 存在未来5天上涨≥5% 的可能，预测概率为 64.63%，置信度 64.63%
    命中: 市场 SSE 指数 000941.SH-新能源(SH) 在 20251124 存在未来5天上涨≥5% 的可能，预测概率为 53.24%，置信度 53.24%
    命中: 市场 SZSE 指数 399249.SZ-综企指数 在 20251124 存在未来5天上涨≥5% 的可能，预测概率为 92.71%，置信度 92.71%
    命中: 市场 SZSE 指数 399259.SZ-创业低碳 在 20251124 存在未来5天上涨≥5% 的可能，预测概率为 54.21%，置信度 54.21%
    命中: 市场 SZSE 指数 399614.SZ-深证材料 在 20251124 存在未来5天上涨≥5% 的可能，预测概率为 50.89%，置信度 50.89%
    命中: 市场 SZSE 指数 399639.SZ-深证大宗 在 20251124 存在未来5天上涨≥5% 的可能，预测概率为 51.66%，置信度 51.66%
    命中: 市场 SZSE 指数 399695.SZ-深证节能 在 20251124 存在未来5天上涨≥5% 的可能，预测概率为 79.94%，置信度 79.94%
    命中: 市场 SZSE 指数 399808.SZ-中证新能 在 20251124 存在未来5天上涨≥5% 的可能，预测概率为 85.20%，置信度 85.20%
    """

    saved = save_selection_records_from_text(text, prediction_type="MACD_XGBoost_for_5")
    print(f"成功写入 {saved} 条记录")
