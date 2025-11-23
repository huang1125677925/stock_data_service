# MACD XGBoost 指数趋势预测技术文档

本文件详细说明 `/stock_strategy/index_analysis/macd_xgboost.py` 的数据准备、特征工程、训练与预测流程，并对涉及的特征、计算方式与作用进行解释说明。文档同时给出主要函数的用途、参数、返回值与事件约定，便于后续维护与扩展。

## 概览

- 目标：基于指数技术面因子（MACD）与价格数据，训练二分类模型，预测未来 `forecast_days` 天是否增长超过 `growth_threshold`。
- 模型：`XGBoost.XGBClassifier`，配合 `StandardScaler` 做特征标准化。
- 数据源：Tushare 指数专题接口（`index_basic` 获取指数列表，`idx_factor_pro` 获取技术面因子与价格数据）。
- 训练范围：默认聚合上交所（SSE）指数最近一年的数据，并按指数分组进行特征计算与样本生成。

## 数据获取与准备

### 数据源与字段

- 指数列表：`index_basic(market='SSE')`
  - 字段：`ts_code, name, market`
- 技术面因子与行情：`idx_factor_pro`
  - 字段：`ts_code, trade_date, open, high, low, close, macd_bfq, macd_dif_bfq, macd_dea_bfq`
  - 时间范围：最近一年（`days=365`），`start_date ~ end_date`。

### 获取流程（主函数 `main`）

- 查询 SSE 指数代码列表（可通过 `limit` 控制数量）。
- 循环各指数代码，调用 `idx_factor_pro` 拉取最近一年的数据（若失败或无数据则跳过）。
- 合并为一个多指数数据集 `df_all`，按 `ts_code, trade_date` 升序排序。

### 清洗与分组

- 在特征工程阶段对数据进行分组处理：每个指数单独计算特征与标签，防止跨指数信息泄露。
- 为避免数值错误：先替换无穷大值为 `NaN`，再统一 `dropna()` 清理。
  - 产生 `NaN` 的常见原因：滚动窗口统计、`pct_change`、滞后（`shift`）与除零保护。

## 特征工程

特征工程主要在类 `MACDPredictor` 的方法中完成：

### 1) 计算技术指标（`calculate_technical_indicators`）

- 基础前值特征：
  - `macd_prev`: `macd_bfq` 的前一日值（`shift(1)`）。
  - `dif_prev`: `macd_dif_bfq` 的前一日值。
  - `dea_prev`: `macd_dea_bfq` 的前一日值。
  - 作用：提供短期动量与信号线的延迟信息，帮助模型学习变化惯性。

- 变化率特征（使用 `pct_change()`）：
  - `macd_pct_change`、`dif_pct_change`、`dea_pct_change`。
  - 作用：量化指标的相对变化速度，提升对快速趋势变动的敏感性。

- 滚动统计特征（窗口 5、10、20）：
  - MACD 的滚动均值与标准差：`macd_rolling_mean_{w}`、`macd_rolling_std_{w}`。
  - MACD 的滚动最小值与最大值：`macd_rolling_min_{w}`、`macd_rolling_max_{w}`。
  - DIF 与 DEA 的滚动均值：`dif_rolling_mean_{w}`、`dea_rolling_mean_{w}`。
  - 作用：平滑噪声、刻画中短期的中心与波动范围，帮助模型理解区间位置与波动强度。

- 趋势斜率特征：
  - `macd_trend`: 用 `np.polyfit(range(len(x)), x, 1)[0]` 在滚动窗口 5 上拟合斜率。
  - 作用：近端趋势方向与强度的线性近似，形似“动量”信号的强化版。

- 相对位置特征：
  - `macd_position`: 在滚动窗口 20 内，将当前 `macd_bfq` 映射到 `[min, max]` 范围的相对位置。
  - 计算：`(macd_bfq - rolling_min) / (rolling_max - rolling_min)`，分母为 0 时记为 `NaN` 以避免除零。
  - 作用：量化当前指标在近期区间内所处的相对高度，帮助识别“高位/低位”环境。

- 波动特征：
  - `macd_volatility`: `macd_bfq` 在窗口 10 上的滚动标准差。
  - 作用：短期波动强度刻画，高波动通常意味着不确定性或转折概率提升。

### 2) 滞后特征（`create_lag_features`）

- 对 `macd_bfq`、`macd_dif_bfq`、`macd_dea_bfq` 分别生成 1~10 日的滞后特征：
  - `macd_lag_1 ... macd_lag_10`
  - `dif_lag_1 ... dif_lag_10`
  - `dea_lag_1 ... dea_lag_10`
  - 作用：提供时间依赖结构，帮助模型理解指标的演化轨迹与惯性。

### 3) 原始价格特征

- `open, high, low, close` 作为原始价格维度直接参与训练（未被排除）。
  - 作用：提供价格层面的绝对与相对关系，配合 MACD 等指标提升语义完整性。

### 4) 特征选择与清理（`prepare_features`）

- 按 `ts_code` 分组，依次执行：技术指标计算 → 滞后特征 → 标签生成。
- 合并后做数据清理：替换无穷值为 `NaN` → `dropna()`。
- 特征列选择规则：排除 `['ts_code', 'trade_date', 'target', 'future_macd', 'future_growth_rate']`，其余列均作为特征。
  - 注：`future_macd` 并未在当前逻辑中生成，属于预留排除项，不影响现状。

## 标签与任务定义（`create_target_variable`）

- 未来收盘价：`future_close = close.shift(-forecast_days)`。
- 增长率：`future_growth_rate = (future_close - close) / close.abs()`。
- 二分类标签：`target = (future_growth_rate > growth_threshold).astype(int)`。
- 语义：预测未来 `forecast_days` 天是否累计上涨超过 `growth_threshold`（例如 5%）。

## 训练与评估流程

### 时间序列切分（`train_test_split_temporal`）

- 按时间划分训练/测试：`test_size=0.2` → 80% 训练、20% 测试。
- 保证时间顺序且避免未来信息泄露。

### 标准化（`StandardScaler`）

- 对训练特征 `X_train` 拟合缩放器，应用于 `X_train` 与 `X_test`（同分布假设）。
- 作用：消除量纲影响，提升树模型在早停与概率输出阶段的稳定性。

### 模型配置（`XGBClassifier`）

- 超参数：
  - `n_estimators=1000, max_depth=6, learning_rate=0.01, subsample=0.8, colsample_bytree=0.8, random_state=42`
  - 评估度量默认 `logloss`。
- 早停与版本兼容：
  - 动态检测 `fit()` 形参：优先使用 `callbacks=[EarlyStopping(rounds=50)]`，否则回退到 `early_stopping_rounds=50`，再否则跳过早停。
  - 始终在支持时传入 `eval_set=[(X_test_scaled, y_test)]` 与 `eval_metric='logloss'`。

### 训练调用（`train`）

- 流程：特征准备 → 时间切分 → 标准化 → 构造模型 → 动态早停训练。
- 评估：输出训练集与测试集准确率、打印 `classification_report`，并返回：
  - `train_accuracy`、`test_accuracy`、`feature_importance`（模型内置重要性）、`train_df`、`test_df`。

## 预测

### 最近样本单点预测（`predict`）

- 对最近样本（`df_recent` 的最后一行）进行预测，返回：
  - `prediction`（0=不增长、1=增长）、`probability_0`、`probability_1`、`confidence`（最大概率）。
- 同时打印增长概率与类别、置信度。

### 单指数全样本批量预测（`predict_all_growth_dates`）

- 对单指数完整数据集 `df_one` 执行特征工程并批量预测，返回所有预测为增长（1）的 `trade_date` 列表。
- 用途：在主流程中随机选择一个指数，输出其历史所有“增长预测日期”。

### 辅助选择函数（`select_recent_index_data`）

- 从多指数聚合数据集中选择指定指数最近 `days` 条记录，便于近端窗口预测或可视化。

## 主流程（`main`）

- 初始化预测器：`MACDPredictor(lookback_days=60, forecast_days=5, growth_threshold=0.03)`。
- 加载数据：`load_sse_indices_dataset(days=365, limit=30)` 聚合 SSE 多指数数据。
- 训练模型：`predictor.train(df)`。
- 预测展示：随机选择一个指数，打印其“增长预测日期列表”。

## 主要函数说明

下面列出关键函数的用途、参数、返回值与事件（符合注释规范）：

- `MACDPredictor.__init__(lookback_days=60, forecast_days=5, growth_threshold=0.05)`
  - 用途：初始化模型与超参数。
  - 参数：回看天数、预测天数、增长阈值。
  - 返回：无。
  - 事件：无。

- `calculate_technical_indicators(df)`
  - 用途：生成 MACD 相关的技术指标特征。
  - 参数：包含至少 MACD 三项与收盘价的 DataFrame。
  - 返回：加入新特征后的 DataFrame。
  - 事件：无。

- `create_target_variable(df)`
  - 用途：生成二分类标签 `target`。
  - 参数：含 `close` 的 DataFrame。
  - 返回：加入 `target` 与 `future_growth_rate` 的 DataFrame。
  - 事件：无。

- `create_lag_features(df, n_lags=10)`
  - 用途：生成 MACD、DIF、DEA 的滞后特征。
  - 参数：原始 DataFrame、滞后阶数。
  - 返回：加入滞后列的 DataFrame。
  - 事件：无。

- `prepare_features(df)`
  - 用途：按指数分组完成特征工程与标签生成，并清理无效值。
  - 参数：原始聚合数据。
  - 返回：可训练/预测的干净特征集，`self.feature_columns` 同步更新。
  - 事件：无。

- `train_test_split_temporal(df, test_size=0.2)`
  - 用途：时间顺序切分训练/测试集。
  - 参数：特征集、测试比例。
  - 返回：`X_train, X_test, y_train, y_test, train_df, test_df`。
  - 事件：无。

- `train(df)`
  - 用途：完整训练流程与评估。
  - 参数：原始数据（需包含所需字段）。
  - 返回：包含准确率、特征重要性与切分数据的字典。
  - 事件：无。

- `evaluate_model(X_train, y_train, X_test, y_test)`
  - 用途：评估模型、打印报告。
  - 参数：标准化后特征与标签。
  - 返回：训练集/测试集准确率。
  - 事件：无。

- `get_feature_importance(top_n=15)`
  - 用途：输出特征重要性 Top N。
  - 参数：Top N 数量。
  - 返回：特征重要性 DataFrame。
  - 事件：无。

- `predict(df_recent)`
  - 用途：对最近单点样本预测类别与概率。
  - 参数：最近窗口数据。
  - 返回：字典，包含类别与概率。
  - 事件：无。

- `predict_all_growth_dates(df_one)`
  - 用途：对单指数全部样本批量预测并返回增长日期列表。
  - 参数：单指数数据集。
  - 返回：增长日期字符串列表。
  - 事件：无。

- `get_sse_index_codes(limit=None)`
  - 用途：拉取 SSE 指数列表。
  - 参数：可选数量上限。
  - 返回：指数代码列表。
  - 事件：无。

- `load_sse_indices_dataset(days=365, limit=30)`
  - 用途：批量拉取并聚合多个指数最近一年的数据。
  - 参数：时间跨度与指数数量上限。
  - 返回：聚合数据集。
  - 事件：无。

- `select_recent_index_data(df, ts_code=None, days=70)`
  - 用途：获取指定指数最近 N 天样本。
  - 参数：聚合数据集、指数代码、天数。
  - 返回：过滤后的 DataFrame。
  - 事件：无。

## 依赖与环境

- 运行依赖：`pandas`、`numpy`、`scikit-learn`、`xgboost`、`django`（用于初始化设置）、Tushare 代理模块。
- 环境变量：需要配置 Tushare 访问令牌（参考项目文档），并确保 Django 设置可加载。
- 速率限制：批量拉取指数数据时注意 Tushare API 限频，可通过 `limit` 控制请求数量。

## 注意事项与改进方向

- 类不平衡：不同指数与时期的上涨概率可能差异较大，建议后续引入采样或权重策略。
- 特征冗余：当前特征较多，后续可基于重要性或相关性做筛选与降维。
- 交叉验证：可引入时间序列交叉验证（如滚动窗口）增强泛化评估。
- 目标定义：`growth_threshold` 与 `forecast_days` 可根据策略风格调参，建议网格或贝叶斯优化。
- 版本兼容：`xgboost` 的早停参数按签名动态适配，若需稳定早停，可锁定到支持 `callbacks` 的版本。