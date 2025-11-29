import sys
import os
from pathlib import Path
import django

# 设置Django环境，确保在脚本/任务中可直接导入模型与配置
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_data_service.settings')
django.setup()

import pandas as pd
import numpy as np
import warnings
import inspect
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
try:
    import talib  # TA-Lib 指标库
except Exception:
    talib = None

from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    precision_recall_curve,
    roc_auc_score,
    confusion_matrix,
)
import xgboost as xgb

from common.tushare_proxy import call_tushare
from common.response import success_response, error_response
from stock_strategy.models import StockSelectionRecord

warnings.filterwarnings('ignore')


def _infer_market(ts_code: str) -> str:
    """
    组件：市场推断工具（_infer_market）

    功能：
    - 根据 Tushare `ts_code` 后缀推断市场（`SH` or `SZ`），默认返回 `SSE` 或 `SZSE` 的简写。

    参数：
    - ts_code(str): 带后缀的代码，如 `510330.SH`、`159919.SZ`

    返回值：
    - str: 市场标识，`SH` 或 `SZ`，未知返回 `UNK`

    事件：无
    """
    if not ts_code or not isinstance(ts_code, str):
        return 'UNK'
    if ts_code.endswith('.SH'):
        return 'SH'
    if ts_code.endswith('.SZ'):
        return 'SZ'
    return 'UNK'


def fetch_etf_basic(
    ts_code: Optional[str] = None,
    index_code: Optional[str] = None,
    list_date: Optional[str] = None,
    list_status: Optional[str] = 'L',
    exchange: Optional[str] = None,
    mgr: Optional[str] = None,
    fields: Optional[str] = 'ts_code,extname,index_code,index_name,exchange,mgr_name,csname,cname,setup_date,list_date,list_status,etf_type,custod_name,mgt_fee',
    token: Optional[str] = None,
) -> Dict:
    """
    组件：ETF基础信息拉取（fetch_etf_basic）

    功能：
    - 代理调用 Tushare `etf_basic` 接口，获取国内ETF基础信息（含QDII）。
    - 支持按代码、指数、日期、状态、交易所、管理人过滤。

    参数：
    - ts_code(str, 可选): ETF代码（带后缀），如 `510330.SH`
    - index_code(str, 可选): 跟踪指数代码，如 `000300.SH`
    - list_date(str, 可选): 上市日期 `YYYYMMDD`
    - list_status(str, 可选): 上市状态（L上市 D退市 P待上市），默认 `L`
    - exchange(str, 可选): 交易所（SH、SZ）
    - mgr(str, 可选): 管理人简称，如 `嘉实基金`
    - fields(str, 可选): 返回字段列表，逗号分隔
    - token(str, 可选): Tushare Token

    返回值：
    - dict: { code, message, data: { interface, count, records } }

    事件：
    - 调用 common.tushare_proxy.call_tushare
    """
    params: Dict[str, str] = {}
    if ts_code:
        params['ts_code'] = ts_code
    if index_code:
        params['index_code'] = index_code
    if list_date:
        params['list_date'] = list_date
    if list_status:
        params['list_status'] = list_status
    if exchange:
        params['exchange'] = exchange
    if mgr:
        params['mgr'] = mgr

    resp = call_tushare(
        interface='etf_basic',
        params=params,
        fields=fields,
        token=token,
        use_query=False,
    )
    return resp


def fetch_etf_daily(
    ts_code: Optional[str] = None,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    fields: Optional[str] = 'ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount',
    token: Optional[str] = None,
) -> Dict:
    """
    组件：ETF日线行情拉取（fetch_etf_daily）

    功能：
    - 代理调用 Tushare `fund_daily` 接口，获取ETF的日频行情数据。
    - 支持按代码与日期区间过滤，历史超过10年。

    参数：
    - ts_code(str, 可选): 基金代码（ETF），如 `510330.SH`
    - trade_date(str, 可选): 交易日期 `YYYYMMDD`
    - start_date(str, 可选): 开始日期 `YYYYMMDD`
    - end_date(str, 可选): 结束日期 `YYYYMMDD`
    - fields(str, 可选): 返回字段列表，逗号分隔
    - token(str, 可选): Tushare Token

    返回值：
    - dict: { code, message, data: { interface, count, records } }

    事件：
    - 调用 common.tushare_proxy.call_tushare
    """
    params: Dict[str, str] = {}
    if ts_code:
        params['ts_code'] = ts_code
    if trade_date:
        params['trade_date'] = trade_date
    if start_date:
        params['start_date'] = start_date
    if end_date:
        params['end_date'] = end_date

    resp = call_tushare(
        interface='fund_daily',
        params=params,
        fields=fields,
        token=token,
        use_query=False,
    )
    return resp


def _compute_macd_for_group(g: pd.DataFrame, close_col: str = 'close', fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    组件：MACD计算（_compute_macd_for_group）

    功能：
    - 对单个 ETF 的时间序列（按 trade_date 排序）计算 DIF/DEA/MACD。

    参数：
    - g(DataFrame): 单个ETF的行情数据，至少包含 `close`
    - close_col(str): 收盘价列名，默认 `close`
    - fast(int): 快速EMA周期，默认12
    - slow(int): 慢速EMA周期，默认26
    - signal(int): 信号DEA周期，默认9

    返回值：
    - DataFrame: 增加 `macd_dif`, `macd_dea`, `macd` 三列后的数据框

    事件：无
    """
    c = g[close_col].astype(float)
    ema_fast = c.ewm(span=fast, adjust=False).mean()
    ema_slow = c.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    macd = dif - dea
    g['macd_dif'] = dif
    g['macd_dea'] = dea
    g['macd'] = macd
    return g


class ETFXGBoostPredictor:
    """
    组件：ETF基于XGBoost的趋势预测器（ETFXGBoostPredictor）

    功能：
    - 使用ETF日频行情数据（`fund_daily`）生成MACD与价格动量等特征。
    - 引入TA-Lib生成常用技术指标（SMA/EMA/RSI/MACD/ATR/BBANDS/SAR等），丰富特征维度。
    - 训练二分类模型，预测未来若干天累计涨幅是否超过阈值（上涨/下跌任务）。
    - 支持推理模式，对最新交易日进行预测并选出高概率指数，保存到 `StockSelectionRecord`。

    参数：
    - lookback_days(int): 回看历史天数（用于最小数据量判断），默认60
    - forecast_days(int): 预测未来天数，默认5
    - growth_threshold(float): 上涨事件阈值（相对涨幅），默认0.03（3%）
    - target_mode(str): 目标类型 'up' 或 'down'，默认 'up'
    - drop_threshold(float): 下跌事件阈值（用于 'down' 任务），默认0.05（5%）
    - drop_forecast_days(Optional[int]): 下跌预测天数，默认与 forecast_days 相同

    返回值：
    - 类实例，内部包含 `model`, `scaler`, `feature_columns` 等状态

    事件：
    - 训练过程中打印评估信息；保存选指数记录时进行数据库写入与去重。
    """

    def __init__(
        self,
        lookback_days: int = 60,
        forecast_days: int = 5,
        growth_threshold: float = 0.03,
        target_mode: str = 'up',
        drop_threshold: float = 0.05,
        drop_forecast_days: Optional[int] = None,
        use_scale_pos_weight: bool = True,
        pred_threshold: Optional[float] = None,
        threshold_mode: str = 'f1',
        target_precision: float = 0.85,
        min_pos_rate: float = 0.005,
    ) -> None:
        self.lookback_days = lookback_days
        self.forecast_days = forecast_days
        self.growth_threshold = growth_threshold
        self.target_mode = target_mode
        self.drop_threshold = drop_threshold
        self.drop_forecast_days = drop_forecast_days if drop_forecast_days is not None else forecast_days
        self.model: Optional[xgb.XGBClassifier] = None
        self.scaler = StandardScaler()
        self.feature_columns: List[str] = []
        # 类别不平衡处理：是否启用 scale_pos_weight（针对正类稀少场景）
        self.use_scale_pos_weight = use_scale_pos_weight
        # 预测标签阈值：None 表示训练阶段自动选择最优阈值；否则使用固定业务阈值
        self.pred_threshold: Optional[float] = pred_threshold
        # 阈值选择模式：'f1'（默认）或 'precision'（优先高准确率）
        self.threshold_mode = threshold_mode
        # 当模式为 'precision' 时的目标准确率（正类精确率），无法达成则选择可达的最高精确率
        self.target_precision = float(np.clip(target_precision, 0.5, 0.99))
        # 阈值选择的最小正类占比约束，避免几乎不预测正类导致“伪高准确率”
        self.min_pos_rate = float(np.clip(min_pos_rate, 0.0, 0.1))

    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        组件：技术指标特征构造（calculate_technical_indicators）

        功能：
        - 基于MACD与信号交叉、斜率、运行长度等构造动量特征。

        参数：
        - df(DataFrame): 至少包含 `macd`, `macd_dif`, `macd_dea`

        返回值：
        - DataFrame: 增加MACD相关特征后的数据框

        事件：无
        """
        df['macd_prev'] = df['macd'].shift(1)
        df['dif_prev'] = df['macd_dif'].shift(1)
        df['dea_prev'] = df['macd_dea'].shift(1)

        # 变化率
        df['macd_pct_change'] = df['macd'].pct_change()
        df['dif_pct_change'] = df['macd_dif'].pct_change()
        df['dea_pct_change'] = df['macd_dea'].pct_change()

        # 滚动统计
        for window in [5, 10, 20]:
            df[f'macd_rolling_mean_{window}'] = df['macd'].rolling(window).mean()
            df[f'macd_rolling_std_{window}'] = df['macd'].rolling(window).std()
            df[f'macd_rolling_min_{window}'] = df['macd'].rolling(window).min()
            df[f'macd_rolling_max_{window}'] = df['macd'].rolling(window).max()
            df[f'dif_rolling_mean_{window}'] = df['macd_dif'].rolling(window).mean()
            df[f'dea_rolling_mean_{window}'] = df['macd_dea'].rolling(window).mean()

        # 趋势斜率
        df['macd_trend'] = df['macd'].rolling(window=5).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0], raw=True
        )

        # 相对位置
        rolling_min = df['macd'].rolling(20).min()
        rolling_max = df['macd'].rolling(20).max()
        denom = (rolling_max - rolling_min).replace(0, np.nan)
        df['macd_position'] = (df['macd'] - rolling_min) / denom

        # 波动
        df['macd_volatility'] = df['macd'].rolling(window=10).std()

        # 直方图与交叉
        df['macd_hist'] = df['macd_dif'] - df['macd_dea']
        df['macd_hist_slope_5'] = df['macd_hist'].rolling(window=5).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0], raw=True
        )
        df['macd_above_zero'] = (df['macd'] > 0).astype(int)
        df['dif_above_dea'] = (df['macd_dif'] > df['macd_dea']).astype(int)
        df['dif_cross_up'] = (
            ((df['macd_dif'] >= df['macd_dea']) & (df['dif_prev'] < df['dea_prev']))
        ).astype(int)
        df['dif_cross_down'] = (
            ((df['macd_dif'] <= df['macd_dea']) & (df['dif_prev'] > df['dea_prev']))
        ).astype(int)

        # 运行长度
        run = df['dif_above_dea']
        run_groups = (run != run.shift()).cumsum()
        df['dif_above_dea_run'] = run.groupby(run_groups).cumcount() + 1
        df.loc[run == 0, 'dif_above_dea_run'] = 0

        run2 = df['macd_above_zero']
        run_groups2 = (run2 != run2.shift()).cumsum()
        df['macd_above_zero_run'] = run2.groupby(run_groups2).cumcount() + 1
        df.loc[run2 == 0, 'macd_above_zero_run'] = 0

        return df

    def calculate_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        组件：价格动量与波动特征构造（calculate_price_features）

        功能：
        - 基于OHLCV构造收益率、波动率、ATR、布林带、均线斜率、RSI、随机指标与K线形态特征。

        参数：
        - df(DataFrame): 至少包含 `open, high, low, close`

        返回值：
        - DataFrame: 新增价格相关特征后的数据框

        事件：无
        """
        # 收益率与波动率
        df['ret_1d'] = df['close'].pct_change()
        df['ret_3d'] = df['close'].pct_change(3)
        df['ret_5d'] = df['close'].pct_change(5)
        df['ret_5_mean'] = df['ret_1d'].rolling(5).mean()
        df['ret_5_std'] = df['ret_1d'].rolling(5).std()
        df['ret_10_std'] = df['ret_1d'].rolling(10).std()

        # ATR（归一化）
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

        # 均线与斜率
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

        # 随机指标
        lowest_14 = df['low'].rolling(14).min()
        highest_14 = df['high'].rolling(14).max()
        df['stoch_k'] = 100 * (df['close'] - lowest_14) / (highest_14 - lowest_14).replace(0, np.nan)
        df['stoch_d'] = df['stoch_k'].rolling(3).mean()

        # K线形态比率
        rng = (df['high'] - df['low']).replace(0, np.nan)
        body = df['close'] - df['open']
        upper_shadow = df['high'] - np.maximum(df['open'], df['close'])
        lower_shadow = np.minimum(df['open'], df['close']) - df['low']
        df['body_pct_range'] = body / rng
        df['upper_shadow_ratio'] = upper_shadow / rng
        df['lower_shadow_ratio'] = lower_shadow / rng

        return df

    def create_target_variable(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        组件：目标变量生成（create_target_variable）

        功能：
        - 'up'：未来 `forecast_days` 天累计涨幅 > `growth_threshold` → 标签 1
        - 'down'：未来 `drop_forecast_days` 天累计跌幅 < -`drop_threshold` → 标签 1

        参数：
        - df(DataFrame): 至少包含 `close`

        返回值：
        - DataFrame: 增加 `future_close`, `future_growth_rate`, `target`

        事件：无
        """
        horizon = self.forecast_days if self.target_mode == 'up' else self.drop_forecast_days
        df['future_close'] = df['close'].shift(-horizon)
        df['future_growth_rate'] = (df['future_close'] - df['close']) / df['close'].abs()
        if self.target_mode == 'up':
            df['target'] = (df['future_growth_rate'] >= self.growth_threshold).astype(int)
        else:
            df['target'] = (df['future_growth_rate'] < -self.drop_threshold).astype(int)
        return df

    def create_lag_features(self, df: pd.DataFrame, n_lags: int = 10) -> pd.DataFrame:
        """
        组件：滞后特征构造（create_lag_features）

        功能：
        - 为 `macd`, `macd_dif`, `macd_dea` 生成 1..n 阶滞后特征。

        参数：
        - df(DataFrame): 至少包含 `macd`, `macd_dif`, `macd_dea`
        - n_lags(int): 滞后天数，默认10

        返回值：
        - DataFrame: 增加滞后特征后的数据框

        事件：无
        """
        for lag in range(1, n_lags + 1):
            df[f'macd_lag_{lag}'] = df['macd'].shift(lag)
            df[f'dif_lag_{lag}'] = df['macd_dif'].shift(lag)
            df[f'dea_lag_{lag}'] = df['macd_dea'].shift(lag)
        return df

    def prepare_features(self, df: pd.DataFrame, for_inference: bool = False) -> pd.DataFrame:
        """
        组件：特征准备（prepare_features）

        功能：
        - 按 `ts_code` 分组，计算MACD→技术指标→价格特征→滞后特征；
        - 训练模式下创建目标变量并记录特征列；推理模式下仅清理特征列对应缺失，保留最新样本。

        参数：
        - df(DataFrame): 至少包含 `ts_code, trade_date, open, high, low, close`
        - for_inference(bool): 推理模式标识，默认 False

        返回值：
        - DataFrame: 整合后的特征数据集

        事件：无
        """
        df = df.sort_values(['ts_code', 'trade_date']).reset_index(drop=True)

        groups: List[pd.DataFrame] = []
        for code, g in df.groupby('ts_code'):
            g = g.copy()
            # 计算MACD
            g = _compute_macd_for_group(g)
            # 技术指标
            g = self.calculate_technical_indicators(g)
            # 价格特征
            g = self.calculate_price_features(g)
            # 滞后特征
            g = self.create_lag_features(g, n_lags=10)
            # 目标变量（训练模式）
            if not for_inference:
                g = self.create_target_variable(g)
            groups.append(g)

        df_all = pd.concat(groups, ignore_index=True)
        df_all.replace([np.inf, -np.inf], np.nan, inplace=True)

        # 候选特征列（剔除标识与目标列）
        candidate_feature_columns = [
            col for col in df_all.columns
            if col not in ['ts_code', 'trade_date', 'target', 'future_growth_rate', 'future_close']
        ]

        if for_inference:
            effective = self.feature_columns if self.feature_columns else candidate_feature_columns
            df_clean = df_all.dropna(subset=effective).copy()
        else:
            df_clean = df_all.dropna().copy()
            self.feature_columns = candidate_feature_columns

        return df_clean

    def train_test_split_temporal(self, df: pd.DataFrame, test_size: float = 0.2) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.DataFrame, pd.DataFrame]:
        """
        组件：时间序列划分（train_test_split_temporal）

        功能：
        - 避免未来信息泄露，按照时间顺序进行训练/测试划分。

        参数：
        - df(DataFrame): 训练数据（包含 `target` 与特征列）
        - test_size(float): 测试集比例，默认0.2

        返回值：
        - (X_train, X_test, y_train, y_test, train_df, test_df)

        事件：无
        """
        split_idx = int(len(df) * (1 - test_size))
        train_df = df.iloc[:split_idx].copy()
        test_df = df.iloc[split_idx:].copy()
        X_train = train_df[self.feature_columns]
        y_train = train_df['target']
        X_test = test_df[self.feature_columns]
        y_test = test_df['target']
        return X_train, X_test, y_train, y_test, train_df, test_df

    def train(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        组件：训练模型（train）

        功能：
        - 准备特征数据→时间序列划分→特征标准化→训练XGBoost→评估。
        - 加入类别不平衡处理（scale_pos_weight），并在验证集上选择动态概率阈值（支持 F1/Precision）。

        参数：
        - df(DataFrame): 原始ETF日线数据

        返回值：
        - dict|None: 包含训练/测试准确率、AP（AUC-PR）、最优阈值、特征重要性与数据片段；不足数据时返回None

        事件：
        - 打印：总特征数、数据集规模、模型参数、类别不平衡信息
        - 打印：动态阈值、阈值处精确率/召回率、AP(AUC-PR)、ROC AUC
        - 打印：基于最佳阈值的分类报告与混淆矩阵、预测正类占比
        - 打印：Top特征重要性、早停信息（如最佳迭代轮次/评分）
        """
        df_processed = self.prepare_features(df)
        if len(df_processed) < self.lookback_days:
            print(f"数据量不足，需要至少{self.lookback_days}个交易日数据")
            return None

        X_train, X_test, y_train, y_test, train_df, test_df = self.train_test_split_temporal(df_processed)

        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # 类别不平衡处理：根据训练集动态计算 scale_pos_weight
        pos = int(y_train.sum())
        neg = int(len(y_train) - pos)
        spw = None
        if self.use_scale_pos_weight:
            spw = float(neg) / float(pos if pos > 0 else 1)
            # 边界与稳定性保护，避免过大或过小值
            if not np.isfinite(spw):
                spw = 1.0
            spw = float(np.clip(spw, 1.0, 100.0))

        # 初始化模型（eval_metric 在 fit 时使用 AUC-PR）
        self.model = xgb.XGBClassifier(
            n_estimators=800,
            max_depth=6,
            learning_rate=0.02,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            scale_pos_weight=spw if spw is not None else 1.0,
            eval_metric='logloss'
        )

        fit_params = inspect.signature(self.model.fit).parameters
        fit_kwargs: Dict = {}
        if 'eval_set' in fit_params:
            fit_kwargs['eval_set'] = [(X_test_scaled, y_test)]
        if 'eval_metric' in fit_params:
            # 在验证集上采用 AUC-PR 更适合稀疏正类场景
            fit_kwargs['eval_metric'] = 'aucpr'
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

        # 数据与特征维度信息
        n_features = len(self.feature_columns)
        train_size = int(X_train_scaled.shape[0])
        test_size = int(X_test_scaled.shape[0])
        pos_train = int(y_train.sum())
        neg_train = int(train_size - pos_train)
        pos_test = int(y_test.sum())
        neg_test = int(test_size - pos_test)

        y_train_pred = self.model.predict(X_train_scaled)
        y_test_pred = self.model.predict(X_test_scaled)
        train_accuracy = accuracy_score(y_train, y_train_pred)
        test_accuracy = accuracy_score(y_test, y_test_pred)

        # 验证集概率与AP（AUC-PR）
        try:
            y_test_proba = self.model.predict_proba(X_test_scaled)[:, 1]
        except Exception:
            # 二分类失败容错
            proba_all = self.model.predict_proba(X_test_scaled)
            y_test_proba = proba_all[:, -1] if proba_all.ndim == 2 else proba_all
        average_precision = 0.0
        try:
            average_precision = float(average_precision_score(y_test, y_test_proba))
        except Exception:
            pass

        # 动态选择最佳概率阈值：若未提供业务阈值，则基于F1在验证集优化
        best_threshold = self.pred_threshold
        precision_at_best: Optional[float] = None
        recall_at_best: Optional[float] = None
        if best_threshold is None:
            if self.threshold_mode == 'precision':
                # 基于 PR 曲线选择达到目标精确率（或尽可能高）的阈值，并保证预测的正类数量不低于最小占比
                prec, rec, ths = precision_recall_curve(y_test, y_test_proba)
                # precision_recall_curve 的 thresholds 与 prec/rec 对齐方式：ths 长度比 prec/rec 少 1
                candidates = []
                for i in range(len(ths)):
                    th = float(ths[i])
                    p = float(prec[i+1])  # 与 th 对应的下一个点
                    r = float(rec[i+1])
                    # 约束：预测正类占比
                    pos_count = int(np.sum(y_test_proba >= th))
                    min_pos = int(max(1, self.min_pos_rate * len(y_test)))
                    if pos_count >= min_pos:
                        candidates.append((th, p, r, pos_count))
                if candidates:
                    # 优先选满足 target_precision 的阈值（最高阈值），否则选 precision 最大的阈值
                    meet_target = [c for c in candidates if c[1] >= self.target_precision]
                    if meet_target:
                        # 选阈值高的（更保守）以提升泛化的准确率
                        th, p, r, _ = sorted(meet_target, key=lambda x: x[0], reverse=True)[0]
                    else:
                        th, p, r, _ = sorted(candidates, key=lambda x: (x[1], x[0]), reverse=True)[0]
                    best_threshold = float(th)
                    precision_at_best = float(p)
                    recall_at_best = float(r)
                else:
                    # 回退：扫描网格选择最高精确率（带最小正类约束）
                    best_prec = -1.0
                    best_rec = 0.0
                    for th in np.linspace(0.1, 0.95, 43):
                        y_pred_th = (y_test_proba >= th).astype(int)
                        pos_count = int(y_pred_th.sum())
                        min_pos = int(max(1, self.min_pos_rate * len(y_test)))
                        if pos_count < min_pos:
                            continue
                        p = float(precision_score(y_test, y_pred_th, zero_division=0))
                        r = float(recall_score(y_test, y_pred_th, zero_division=0))
                        if p > best_prec or (np.isclose(p, best_prec) and th > (best_threshold or 0.0)):
                            best_prec = p
                            best_rec = r
                            best_threshold = float(th)
                    if best_threshold is not None:
                        precision_at_best = best_prec
                        recall_at_best = best_rec
                        
            else:
                # 默认 F1 最优阈值（在不平衡场景下平衡查准查全）
                candidate_thresholds = np.linspace(0.1, 0.9, 41)
                best_f1 = -1.0
                for th in candidate_thresholds:
                    y_pred_th = (y_test_proba >= th).astype(int)
                    f1 = float(f1_score(y_test, y_pred_th, zero_division=0))
                    if f1 > best_f1:
                        best_f1 = f1
                        best_threshold = float(th)
                        precision_at_best = float(precision_score(y_test, y_pred_th, zero_division=0))
                        recall_at_best = float(recall_score(y_test, y_pred_th, zero_division=0))
            self.pred_threshold = best_threshold

        pos_rate = float(pos) / float(len(y_train)) if len(y_train) > 0 else 0.0
        neg_rate = 1.0 - pos_rate

        print("=" * 50)
        print("ETF XGBoost 模型评估")
        print("=" * 50)
        print(f"特征总数: {n_features}（模型识别特征数: {getattr(self.model, 'n_features_in_', n_features)}）")
        print(f"训练/测试样本数: {train_size}/{test_size}")
        print(f"训练集标签分布: 正类 {pos_train}（{pos_rate:.2%}），负类 {neg_train}（{neg_rate:.2%}）")
        print(f"测试集标签分布: 正类 {pos_test}（{(pos_test/max(1,test_size)):.2%}），负类 {neg_test}（{(neg_test/max(1,test_size)):.2%}）")
        print(f"训练集准确率: {train_accuracy:.4f}")
        print(f"测试集准确率: {test_accuracy:.4f}")
        print("\n模型参数摘要:")
        try:
            params = self.model.get_params()
            # 精选关键参数展示
            key_params = {k: params[k] for k in [
                'n_estimators','max_depth','learning_rate','subsample','colsample_bytree','random_state','scale_pos_weight','eval_metric'
            ] if k in params}
            print(key_params)
        except Exception:
            pass

        # 阈值与评估（基于最佳阈值）
        if best_threshold is not None:
            print(f"\n动态选择的概率阈值: {best_threshold:.2f}（模式: {self.threshold_mode}）")
            if precision_at_best is not None:
                print(f"阈值处精确率(precision): {precision_at_best:.4f}，召回率(recall): {recall_at_best:.4f}")
            y_test_pred_best = (y_test_proba >= best_threshold).astype(int)
            print("\n测试集分类报告（基于最佳阈值）:")
            print(classification_report(y_test, y_test_pred_best))
            cm = confusion_matrix(y_test, y_test_pred_best)
            tn, fp, fn, tp = int(cm[0,0]), int(cm[0,1]), int(cm[1,0]), int(cm[1,1])
            pos_pred = int(y_test_pred_best.sum())
            print(f"混淆矩阵 tn={tn}, fp={fp}, fn={fn}, tp={tp}")
            print(f"预测正类数量: {pos_pred}/{test_size}（{(pos_pred/max(1,test_size)):.2%}）")
        else:
            print("\n测试集分类报告（默认阈值0.50）:")
            print(classification_report(y_test, y_test_pred))

        # 曲线度量
        try:
            roc_auc = float(roc_auc_score(y_test, y_test_proba))
            print(f"ROC AUC: {roc_auc:.4f}")
        except Exception:
            pass
        print(f"验证集平均精度 AP(AUC-PR): {average_precision:.4f}")

        # 早停/最佳迭代信息
        try:
            best_iter = getattr(self.model, 'best_iteration', None)
            best_score = getattr(self.model, 'best_score', None)
            if best_iter is not None:
                print(f"早停最佳迭代轮次: {best_iter}")
            if best_score is not None:
                print(f"早停最佳评分: {best_score}")
        except Exception:
            pass

        # 特征重要性（Top 15）
        importance_scores = self.model.feature_importances_
        feature_importance = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': importance_scores,
        }).sort_values('importance', ascending=False).head(15)
        print("\nTop 15 特征重要性:")
        print(feature_importance.to_string(index=False))

        return {
            'train_accuracy': train_accuracy,
            'test_accuracy': test_accuracy,
            'average_precision': average_precision,
            'best_threshold': best_threshold,
            'precision_at_best': precision_at_best,
            'recall_at_best': recall_at_best,
            'pos_rate': pos_rate,
            'neg_rate': neg_rate,
            'scale_pos_weight': spw if spw is not None else 1.0,
            'feature_importance': feature_importance,
            'train_df': train_df,
            'test_df': test_df,
        }

    def predict_latest_probabilities(self, df: pd.DataFrame) -> List[Dict]:
        """
        组件：最新交易日概率预测（predict_latest_probabilities）

        功能：
        - 在已训练模型与已知特征列基础上，对各 `ts_code` 最新可用样本进行概率预测。

        参数：
        - df(DataFrame): 原始ETF日线数据（不含目标列）

        返回值：
        - list[dict]: 每个ETF的最新预测结果，如：
          { ts_code, trade_date, probability_1, confidence, predicted_label }

        事件：无
        """
        if self.model is None or not self.feature_columns:
            raise RuntimeError('模型未训练或特征列未设置，请先调用 train()')

        df_features = self.prepare_features(df, for_inference=True)
        if df_features.empty:
            return []

        results: List[Dict] = []
        for code, g in df_features.groupby('ts_code'):
            g_last = g.iloc[-1]
            X_row = g_last[self.feature_columns].values.reshape(1, -1)
            X_row_scaled = self.scaler.transform(X_row)
            proba = self.model.predict_proba(X_row_scaled)[0]
            prob_1 = float(proba[1]) if len(proba) > 1 else float(proba[0])
            # 使用动态/业务阈值进行标签判断（默认回退到0.5）
            thr = self.pred_threshold if self.pred_threshold is not None else 0.5
            pred_label = int(1 if prob_1 >= thr else 0)
            results.append({
                'ts_code': code,
                'trade_date': str(g_last['trade_date']),
                'probability_1': prob_1,
                'confidence': prob_1,
                'predicted_label': pred_label,
            })
        return results

    def select_top(self, df: pd.DataFrame, top_n: int = 10) -> List[Dict]:
        """
        组件：选指数（select_top）

        功能：
        - 基于最新预测概率，选出概率最高的前 `top_n` 个ETF指数。

        参数：
        - df(DataFrame): 原始ETF日线数据
        - top_n(int): 选取数量，默认10

        返回值：
        - list[dict]: 选出的ETF摘要记录，按 `probability_1` 降序

        事件：无
        """
        preds = self.predict_latest_probabilities(df)
        return sorted(preds, key=lambda x: x['probability_1'], reverse=True)[:top_n]

    def save_selection_records(self, selections: List[Dict], code_info_map: Optional[Dict[str, Dict]] = None, prediction_type: Optional[str] = None) -> int:
        """
        组件：保存选指数记录（save_selection_records）

        功能：
        - 将选出的ETF指数（含预测概率与置信度）保存到 `StockSelectionRecord`。
        - 基于 (code, trade_date) 去重，避免重复写入。

        参数：
        - selections(list[dict]): 来自 `select_top` 的结果列表
        - code_info_map(dict, 可选): ts_code → { name/extname/csname } 的映射，用于补充名称与市场
        - prediction_type(str, 可选): 预测类型标签，如 `ETF_XGBoost_up_5`

        返回值：
        - int: 成功写入条数

        事件：数据库写入、异常打印
        """
        saved = 0
        for item in selections:
            ts_code = item.get('ts_code')
            trade_date_str = str(item.get('trade_date'))
            prob = float(item.get('probability_1', 0.0)) * 100.0
            conf = float(item.get('confidence', 0.0)) * 100.0
            try:
                trade_date = datetime.strptime(trade_date_str, '%Y%m%d').date()
            except Exception:
                try:
                    trade_date = datetime.strptime(trade_date_str, '%Y-%m-%d').date()
                except Exception:
                    continue

            # 名称与市场信息
            name = ts_code
            market = _infer_market(ts_code)
            if isinstance(code_info_map, dict):
                info = code_info_map.get(ts_code) or {}
                name = info.get('extname') or info.get('csname') or info.get('cname') or ts_code

            # 去重
            if StockSelectionRecord.objects.filter(code=ts_code, trade_date=trade_date).exists():
                continue

            try:
                StockSelectionRecord.objects.create(
                    market=market,
                    code=ts_code,
                    name=name,
                    trade_date=trade_date,
                    predict_rise_prob=prob,
                    confidence=conf,
                    prediction_type=prediction_type or f'ETF_XGBoost_{self.target_mode}_{self.forecast_days}',
                )
                saved += 1
            except Exception as e:
                print(f"保存选指数记录失败（{ts_code} {trade_date_str}）：{e}")
        return saved


def build_training_dataset_from_universe(
    list_status: str = 'L',
    mgr: Optional[str] = None,
    exchange: Optional[str] = None,
    index_code: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = 50,
    token: Optional[str] = None,
) -> Tuple[pd.DataFrame, Dict[str, Dict]]:
    """
    组件：从ETF基础信息构建训练数据集（build_training_dataset_from_universe）

    功能：
    - 拉取符合条件的ETF列表，然后为每个ETF拉取日线行情并合并为统一训练集。

    参数：
    - list_status(str): 上市状态，默认 `L`
    - mgr(str, 可选): 管理人简称过滤
    - exchange(str, 可选): 交易所过滤（SH/SZ）
    - index_code(str, 可选): 跟踪指数过滤，如 `000300.SH`
    - start_date(str, 可选): 行情开始日期 `YYYYMMDD`
    - end_date(str, 可选): 行情结束日期 `YYYYMMDD`
    - limit(int, 可选): 限定ETF数量以减少调用负载，默认50
    - token(str, 可选): Tushare Token

    返回值：
    - (DataFrame, dict): 合并的日线行情数据集，以及 ts_code→基础信息 映射

    事件：
    - 多次调用 Tushare 接口，可能受频率与积分限制；建议合理设置 `limit` 与时间范围。
    """
    basic_resp = fetch_etf_basic(index_code=index_code, list_status=list_status, exchange=exchange, mgr=mgr, token=token)
    if basic_resp.get('code') != 200:
        raise RuntimeError(f"获取ETF基础信息失败: {basic_resp.get('message')}")

    basic_records = basic_resp.get('data', {}).get('records', [])
    original_count = len(basic_records)
    print(
        f"获取ETF基础信息成功：原始记录数={original_count}, list_status={list_status}, "
        f"exchange={exchange}, index_code={index_code}, mgr={mgr}"
    )
    if not basic_records:
        raise RuntimeError('未获取到ETF基础信息记录')

    # 限定ETF列表
    if isinstance(limit, int) and limit > 0:
        basic_records = basic_records[:limit]
    limited_count = len(basic_records)
    if limited_count != original_count:
        print(f"应用限制 limit={limit}，实际处理记录数={limited_count}")
    else:
        print(f"处理记录数={limited_count}")
    print(f"准备拉取ETF日线数据：start_date={start_date}, end_date={end_date}")

    code_info_map: Dict[str, Dict] = {r['ts_code']: r for r in basic_records if 'ts_code' in r}
    all_rows: List[pd.DataFrame] = []
    etf_total = limited_count
    etf_success = 0
    etf_failed = 0
    etf_empty = 0
    rows_total = 0

    for r in basic_records:
        ts_code = r.get('ts_code')
        if not ts_code:
            continue
        daily_resp = fetch_etf_daily(ts_code=ts_code, start_date=start_date, end_date=end_date, token=token)
        if daily_resp.get('code') != 200:
            print(f"拉取{ts_code}日线失败: {daily_resp.get('message')}")
            etf_failed += 1
            continue
        df = pd.DataFrame(daily_resp.get('data', {}).get('records', []))
        if df.empty:
            etf_empty += 1
            continue
        # 统一数据类型与排序
        df = df.sort_values('trade_date').reset_index(drop=True)
        # 若记录数不足100，则不纳入训练集汇总
        if len(df) < 100:
            print(f"拉取{ts_code}日线成功但记录不足(<100)，跳过：记录数={len(df)}")
            continue
        all_rows.append(df)
        etf_success += 1
        rows_total += len(df)
        print(f"拉取{ts_code}日线成功：记录数={len(df)}")

    if not all_rows:
        print(
            f"ETF日线汇总：总ETF={etf_total}, 成功拉取={etf_success}, 失败={etf_failed}, 空数据={etf_empty}, 累计行数={rows_total}"
        )
        raise RuntimeError('未获取到任何ETF日线数据')

    df_all = pd.concat(all_rows, ignore_index=True)
    print(
        f"ETF日线汇总完成：总ETF={etf_total}, 成功拉取={etf_success}, 空数据={etf_empty}, "
        f"累计行数={rows_total}, 合并后形状={df_all.shape}"
    )
    return df_all, code_info_map


def train_and_select_etf_indices(
    list_status: str = 'L',
    mgr: Optional[str] = None,
    exchange: Optional[str] = None,
    index_code: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = 50,
    forecast_days: int = 5,
    growth_threshold: float = 0.03,
    target_mode: str = 'up',
    top_n: int = 10,
    token: Optional[str] = None,
    use_scale_pos_weight: bool = True,
    pred_threshold: Optional[float] = None,
    threshold_mode: str = 'f1',
    target_precision: float = 0.85,
    min_pos_rate: float = 0.005,
) -> Dict:
    """
    组件：训练并选指数（train_and_select_etf_indices）

    功能：
    - 综合流程：获取ETF列表→组装训练集→训练模型→选出Top指数→保存选指数记录。

    参数：
    - list_status(str): 上市状态过滤，默认 `L`
    - mgr(str, 可选): 管理人过滤（如 `嘉实基金`）
    - exchange(str, 可选): 交易所过滤（SH/SZ）
    - index_code(str, 可选): 跟踪指数过滤
    - start_date(str, 可选): 行情开始日期 `YYYYMMDD`
    - end_date(str, 可选): 行情结束日期 `YYYYMMDD`
    - limit(int, 可选): 限定ETF数量，默认50
    - forecast_days(int): 预测未来天数，默认5
    - growth_threshold(float): 上涨事件阈值，默认3%
    - target_mode(str): 'up' 或 'down'，默认 'up'
    - top_n(int): 选取数量，默认10
    - token(str, 可选): Tushare Token
    - use_scale_pos_weight(bool, 可选): 是否启用类别不平衡处理（scale_pos_weight），默认 True
    - pred_threshold(float, 可选): 固定业务阈值（0-1），None 表示训练阶段自动选择
    - threshold_mode(str, 可选): 阈值选择模式：'f1'（默认）或 'precision'（优先高准确率）
    - target_precision(float, 可选): 当模式为 'precision' 时的目标准确率（正类精确率），默认 0.85
    - min_pos_rate(float, 可选): 阈值选择的最小正类占比约束（避免几乎不预测正类导致“伪高准确率”），默认 0.005

    返回值：
    - dict: { success, data: { selections, train_accuracy, test_accuracy, average_precision, best_threshold, pos_rate, neg_rate, scale_pos_weight }, message }

    事件：
    - 多接口调用与数据库写入；遵循唯一约束避免重复。
    """
    try:
        df_all, code_info_map = build_training_dataset_from_universe(
            list_status=list_status,
            mgr=mgr,
            exchange=exchange,
            index_code=index_code,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            token=token,
        )

        predictor = ETFXGBoostPredictor(
            forecast_days=forecast_days,
            growth_threshold=growth_threshold,
            target_mode=target_mode,
            use_scale_pos_weight=use_scale_pos_weight,
            pred_threshold=pred_threshold,
            threshold_mode=threshold_mode,
            target_precision=target_precision,
            min_pos_rate=min_pos_rate,
        )

        train_info = predictor.train(df_all)
        if train_info is None:
            return {
                'success': False,
                'data': None,
                'message': '训练数据不足或特征准备失败',
            }

        # 仅筛选出模型识别为 1 的记录，再按概率降序取 Top N
        preds_all = predictor.predict_latest_probabilities(df_all)
        preds_pos = [p for p in preds_all if int(p.get('predicted_label', 0)) == 1]
        selections = sorted(preds_pos, key=lambda x: x['probability_1'], reverse=True)
        # saved = predictor.save_selection_records(selections, code_info_map=code_info_map)

        return {
            'success': True,
            'data': {
                'selections': selections,
                # 'saved': saved,
                'train_accuracy': train_info['train_accuracy'],
                'test_accuracy': train_info['test_accuracy'],
                'average_precision': train_info.get('average_precision'),
                'best_threshold': train_info.get('best_threshold'),
                'precision_at_best': train_info.get('precision_at_best'),
                'recall_at_best': train_info.get('recall_at_best'),
                'pos_rate': train_info.get('pos_rate'),
                'neg_rate': train_info.get('neg_rate'),
                'scale_pos_weight': train_info.get('scale_pos_weight'),
            },
            'message': f'训练完成并选出Top{top_n}指数',
        }

    except Exception as e:
        return {
            'success': False,
            'data': None,
            'message': f'训练与选指数流程失败: {str(e)}',
        }


def train_and_select_etf_indices_api(**kwargs):
    """
    组件：面向API的统一响应封装（train_and_select_etf_indices_api）

    功能：
    - 调用 `train_and_select_etf_indices` 并按照工作区接口规范返回 `success_response` 或 `error_response`。

    参数：
    - 与 `train_and_select_etf_indices` 一致，支持关键字参数传入。

    返回值：
    - JsonResponse: 统一结构的响应

    事件：无
    """
    result = train_and_select_etf_indices(**kwargs)
    if result.get('success'):
        return success_response(result.get('data'), result.get('message'))
    return error_response(result.get('message'), 500)


# 使用示例（仅供参考，不会在导入时执行）：
if __name__ == '__main__':
    # 示例：训练并选择沪深300相关ETF的Top 5指数
    resp = train_and_select_etf_indices(
        start_date=(datetime.now() - timedelta(days=365*5)).strftime('%Y%m%d'),
        end_date=datetime.now().strftime('%Y%m%d'),
        limit=1500,
        forecast_days=5,
        growth_threshold=0.05,
        target_mode='up',
        threshold_mode='precision',
        target_precision=0.95,
        top_n=50,
    )
    print(resp)