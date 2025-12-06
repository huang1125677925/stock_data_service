"""
特征提取组件：价格与指标特征工程

功能：
- 将原脚本中的 MACD、价格动量、波动、滞后特征等提取逻辑模块化；
- 统一对输入 DataFrame 的分组处理并产出可训练的特征列集合。

参数：
- 无（通过成员方法传入 DataFrame 与控制参数）。

返回值：
- pandas.DataFrame: 增加特征后的数据；
- list[str]: 使用的特征列名。

事件：
- 无
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class SWIndexFeatureExtractor:
    """
    申万指数特征提取器

    功能：
    - 负责计算技术指标、价格与波动特征、滞后特征；
    - 根据任务类型在训练阶段生成目标变量。

    参数：
    - lookback_days(int): 回看天数；
    - forecast_days(int): 上涨任务预测的未来天数；
    - growth_threshold(float): 上涨阈值；
    - target_mode(str): 'up' 或 'down'；
    - drop_threshold(float): 下跌阈值；
    - drop_forecast_days(int|None): 下跌任务预测的未来天数，默认与 forecast_days 相同。

    返回值：
    - 无（通过成员方法返回 DataFrame 与特征列表）。

    事件：
    - 无
    """

    def __init__(
        self,
        lookback_days: int = 60,
        forecast_days: int = 5,
        growth_threshold: float = 0.05,
        target_mode: str = "up",
        drop_threshold: float = 0.05,
        drop_forecast_days: int | None = None,
    ) -> None:
        self.lookback_days = lookback_days
        self.forecast_days = forecast_days
        self.growth_threshold = growth_threshold
        self.target_mode = target_mode
        self.drop_threshold = drop_threshold
        self.drop_forecast_days = drop_forecast_days if drop_forecast_days is not None else forecast_days
        self.feature_columns: list[str] = []

    # --- 指标与特征构建 ---
    def _calc_technical(self, df: pd.DataFrame) -> pd.DataFrame:
        # 若 MACD 相关列不存在，则尝试基于收盘价计算
        df = self._ensure_macd(df)
        df['macd_prev'] = df['macd_bfq'].shift(1)
        df['dif_prev'] = df['macd_dif_bfq'].shift(1)
        df['dea_prev'] = df['macd_dea_bfq'].shift(1)

        df['macd_pct_change'] = df['macd_bfq'].pct_change()
        df['dif_pct_change'] = df['macd_dif_bfq'].pct_change()
        df['dea_pct_change'] = df['macd_dea_bfq'].pct_change()

        for window in [5, 10, 20]:
            df[f'macd_rolling_mean_{window}'] = df['macd_bfq'].rolling(window=window).mean()
            df[f'macd_rolling_std_{window}'] = df['macd_bfq'].rolling(window=window).std()
            df[f'macd_rolling_min_{window}'] = df['macd_bfq'].rolling(window=window).min()
            df[f'macd_rolling_max_{window}'] = df['macd_bfq'].rolling(window=window).max()
            df[f'dif_rolling_mean_{window}'] = df['macd_dif_bfq'].rolling(window=window).mean()
            df[f'dea_rolling_mean_{window}'] = df['macd_dea_bfq'].rolling(window=window).mean()

        df['macd_trend'] = df['macd_bfq'].rolling(window=5).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0], raw=True
        )

        rolling_min = df['macd_bfq'].rolling(20).min()
        rolling_max = df['macd_bfq'].rolling(20).max()
        denom = (rolling_max - rolling_min).replace(0, np.nan)
        df['macd_position'] = (df['macd_bfq'] - rolling_min) / denom
        df['macd_volatility'] = df['macd_bfq'].rolling(window=10).std()

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

        run = df['dif_above_dea']
        run_groups = (run != run.shift()).cumsum()
        df['dif_above_dea_run'] = run.groupby(run_groups).cumcount() + 1
        df.loc[run == 0, 'dif_above_dea_run'] = 0

        run2 = df['macd_above_zero']
        run_groups2 = (run2 != run2.shift()).cumsum()
        df['macd_above_zero_run'] = run2.groupby(run_groups2).cumcount() + 1
        df.loc[run2 == 0, 'macd_above_zero_run'] = 0
        return df

    def _calc_price(self, df: pd.DataFrame) -> pd.DataFrame:
        df['ret_1d'] = df['close'].pct_change()
        df['ret_3d'] = df['close'].pct_change(3)
        df['ret_5d'] = df['close'].pct_change(5)
        df['ret_5_mean'] = df['ret_1d'].rolling(5).mean()
        df['ret_5_std'] = df['ret_1d'].rolling(5).std()
        df['ret_10_std'] = df['ret_1d'].rolling(10).std()

        prev_close = df['close'].shift(1)
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - prev_close).abs()
        tr3 = (df['low'] - prev_close).abs()
        df['true_range'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr_14'] = df['true_range'].rolling(14).mean()
        df['atr_14_norm'] = df['atr_14'] / df['close'].replace(0, np.nan).abs()

        ma20 = df['close'].rolling(20).mean()
        std20 = df['close'].rolling(20).std()
        upper = ma20 + 2 * std20
        lower = ma20 - 2 * std20
        df['bb_width'] = (upper - lower) / ma20.replace(0, np.nan).abs()
        df['bb_percent_b'] = (df['close'] - lower) / (upper - lower).replace(0, np.nan)

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

        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df['rsi_14'] = 100 - 100 / (1 + rs)

        lowest_14 = df['low'].rolling(14).min()
        highest_14 = df['high'].rolling(14).max()
        df['stoch_k'] = 100 * (df['close'] - lowest_14) / (highest_14 - lowest_14).replace(0, np.nan)
        df['stoch_d'] = df['stoch_k'].rolling(3).mean()

        rng = (df['high'] - df['low']).replace(0, np.nan)
        body = df['close'] - df['open']
        upper_shadow = df['high'] - np.maximum(df['open'], df['close'])
        lower_shadow = np.minimum(df['open'], df['close']) - df['low']
        df['body_pct_range'] = body / rng
        df['upper_shadow_ratio'] = upper_shadow / rng
        df['lower_shadow_ratio'] = lower_shadow / rng
        return df

    def _create_lags(self, df: pd.DataFrame, n_lags: int = 10) -> pd.DataFrame:
        for lag in range(1, n_lags + 1):
            df[f'macd_lag_{lag}'] = df['macd_bfq'].shift(lag)
            df[f'dif_lag_{lag}'] = df['macd_dif_bfq'].shift(lag)
            df[f'dea_lag_{lag}'] = df['macd_dea_bfq'].shift(lag)
        return df

    def _create_target(self, df: pd.DataFrame) -> pd.DataFrame:
        horizon = self.forecast_days if self.target_mode == 'up' else self.drop_forecast_days
        df['start_predict_close'] = df['close'].shift(horizon)
        df['future_growth_rate'] = (df['close'] - df['start_predict_close']) / df['start_predict_close'].abs()
        if self.target_mode == 'up':
            df['target'] = (df['future_growth_rate'] > self.growth_threshold).astype(int)
        else:
            df['target'] = (df['future_growth_rate'] < -self.drop_threshold).astype(int)
        return df

    def transform(self, df: pd.DataFrame, for_inference: bool = False) -> tuple[pd.DataFrame, list[str]]:
        """
        主流程：生成特征并清理缺失

        功能：
        - 按 `ts_code` 分组计算指标、价格与滞后特征；
        - 训练模式下生成目标变量；
        - 输出清理后的数据与特征列名。

        参数：
        - df(pd.DataFrame): 输入原始数据，至少包含 `ts_code, trade_date, open, high, low, close` 以及 MACD 三列；
        - for_inference(bool): 是否为推理模式（不生成目标）。

        返回值：
        - (pd.DataFrame, list[str]): 清理后的数据与特征列名。

        事件：
        - 无
        """
        df = df.sort_values(['ts_code', 'trade_date']).reset_index(drop=True)
        grouped = []
        for _, g in df.groupby('ts_code'):
            g = self._calc_technical(g)
            g = self._calc_price(g)
            g = self._create_lags(g, n_lags=10)
            if not for_inference:
                g = self._create_target(g)
            grouped.append(g)

        out = pd.concat(grouped, ignore_index=True)
        out.replace([np.inf, -np.inf], np.nan, inplace=True)

        exclude = {'ts_code', 'trade_date', 'target', 'future_macd', 'future_growth_rate', 'start_predict_close'}
        candidate_features = [c for c in out.columns if c not in exclude]

        if for_inference:
            features = self.feature_columns or candidate_features
            out_clean = out.dropna(subset=features).copy()
        else:
            out_clean = out.dropna().copy()
            self.feature_columns = candidate_features
            features = self.feature_columns

        return out_clean, features

    # --- 辅助：MACD 计算 ---
    def _ensure_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        若缺失 MACD 列则基于收盘价计算补齐

        功能：
        - 计算常规 DIF/DEA 与直方图（dif-dea），并以 `macd_*_bfq` 命名与原脚本兼容。

        参数：
        - df(pd.DataFrame): 输入数据，需包含 `close` 列。

        返回值：
        - pd.DataFrame: 补齐后的数据。

        事件：
        - 无
        """
        need_cols = {'macd_bfq', 'macd_dif_bfq', 'macd_dea_bfq'}
        if need_cols.issubset(df.columns):
            return df

        close = df['close']
        # EMA 计算（简易实现，避免依赖 ta 库）
        def ema(series: pd.Series, span: int) -> pd.Series:
            return series.ewm(span=span, adjust=False).mean()

        ema12 = ema(close, 12)
        ema26 = ema(close, 26)
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        hist = dif - dea  # 与原脚本命名 `macd_bfq`

        df['macd_dif_bfq'] = dif
        df['macd_dea_bfq'] = dea
        df['macd_bfq'] = hist
        return df