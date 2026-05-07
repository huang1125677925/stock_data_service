# 交易利润记录功能使用说明

## 功能概述

在量化策略基类 `BaseQuantStrategy` 中，交易利润数据（毛利润和净利润）现已直接整合到买入卖出点数据中，无需单独存储。

## 主要修改

### 1. 数据结构整合

- 移除了独立的 `self.trade_profits` 属性
- 利润信息直接整合到 `self.trade_records` 中
- 交易记录现在包含利润相关字段

### 2. 交易记录结构

每个交易记录现在包含：
```python
{
    'datetime': '2023-01-16T00:00:00',  # 交易日期时间
    'type': 'sell',                       # 交易类型（buy/sell）
    'price': 82.15,                       # 交易价格
    'size': 100.0,                        # 交易数量
    'value': 8215.0,                     # 交易价值
    'commission': 17.23,                   # 手续费
    'pnl': -793.48,                       # 毛利润（交易关闭时更新，买入交易为None）
    'pnlcomm': -810.71,                   # 净利润（交易关闭时更新，买入交易为None）
    'trade_closed': True,                 # 交易是否已关闭
}
```

### 3. 数据更新机制

- 在 `notify_order` 中创建交易记录时，利润字段初始化为 None
- 在 `notify_trade` 中找到对应的卖出交易记录并更新利润信息
- 通过 `trade_closed` 标志避免重复更新

### 4. 使用方法

在策略运行结束后，可以通过以下方式获取包含利润的交易数据：

```python
# 获取策略实例
strategy = cerebro.run()[0]

# 获取所有交易记录（包含利润信息）
trade_records = strategy.trade_records

# 获取观测器数据中的买卖信号（包含利润）
observer_buysell = strategy.observer_data['buysell']

# 获取计算的交易统计数据（优先使用真实利润）
trades_data = strategy.observer_data['trades']
```

### 5. 交易统计数据增强

 `_calculate_trades_data()` 方法优先使用交易记录中的真实利润数据：

```python
{
    'buy_datetime': '2023-01-11T00:00:00',
    'sell_datetime': '2023-01-16T00:00:00',
    'buy_price': 90.08,
    'sell_price': 82.15,
    'size': 100.0,
    'pnl': -793.48,          # 使用真实的毛利润
    'pnlcomm': -810.71,      # 使用真实的净利润
    'pnl_pct': -8.81         # 收益率百分比
}
```

## 日志输出

策略运行时会显示交易记录数量：
```
观测器数据收集完成: broker=30, buysell=3, trades=1, timereturn=30, drawdown=30, benchmark=0
```

## 注意事项

1. 利润数据只在交易关闭时更新到对应的卖出交易记录中
2. 买入交易的利润字段始终为 None
3. 可以通过检查 `trade_closed` 字段判断利润是否已更新
4. 如果利润数据为 None，系统会自动回退到计算的利润数据（兼容旧数据）

## 示例输出

```python
# 访问包含利润信息的交易记录
for record in strategy.trade_records:
    if record['type'] == 'sell' and record['trade_closed']:
        print(f"时间: {record['datetime']}")
        print(f"卖出价格: {record['price']:.2f}")
        print(f"毛利润: {record['pnl']:.2f}")
        print(f"净利润: {record['pnlcomm']:.2f}")
        print()
```

这个整合功能使得策略回测结果更加完整和准确，便于进行详细的交易分析和绩效评估。