import backtrader as bt
import pandas as pd
from strategy_simple import SimpleAdvancedStrategy

# 加载数据
df = pd.read_csv('data/000001.csv', parse_dates=['trade_date'])
df.set_index('trade_date', inplace=True)
df.rename(columns={'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'vol': 'volume'}, inplace=True)

# 转换为 Backtrader 数据格式
class PandasData(bt.feeds.PandasData):
    params = (
        ('datetime', None),
        ('open', 'open'),
        ('high', 'high'),
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
        ('openinterest', -1),
    )

data = PandasData(dataname=df)

# 回测引擎 Cerebro
cerebro = bt.Cerebro()
cerebro.addstrategy(SimpleAdvancedStrategy)
cerebro.adddata(data)
cerebro.broker.set_cash(100000)
cerebro.broker.setcommission(commission=0.001)  # 0.1%手续费

# 添加分析器
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

# 运行回测
print('=== 开始回测 ===')
print('初始资金: %.2f' % cerebro.broker.getvalue())

result = cerebro.run()
strategy = result[0]

final_value = cerebro.broker.getvalue()
print('回测结束资金: %.2f' % final_value)

# 计算收益率
initial_value = 100000
return_rate = (final_value - initial_value) / initial_value * 100
print('总收益率: %.2f%%' % return_rate)

# 获取分析结果
sharpe = strategy.analyzers.sharpe.get_analysis()
drawdown = strategy.analyzers.drawdown.get_analysis()
returns = strategy.analyzers.returns.get_analysis()
trades = strategy.analyzers.trades.get_analysis()

# 分析持仓情况
print('\n=== 持仓分析 ===')
print('最终持仓价值: %.2f' % cerebro.broker.getvalue())

if cerebro.broker.getposition(data):
    pos = cerebro.broker.getposition(data)
    print(f'当前持仓: {pos.size}股, 成本价: {pos.price:.2f}')
else:
    print('当前无持仓')

# 交易统计
print('\n=== 交易统计 ===')
if trades.total.total:
    print(f'总交易次数: {trades.total.total}')
    print(f'盈利交易: {trades.won.total}')
    print(f'亏损交易: {trades.lost.total}')
    if trades.won.total > 0:
        print(f'平均盈利: {trades.won.pnl.average:.2f}')
    if trades.lost.total > 0:
        print(f'平均亏损: {trades.lost.pnl.average:.2f}')
    print(f'胜率: {(trades.won.total/trades.total.total)*100:.2f}%')
else:
    print('无交易记录')

# 详细分析
sharpe_ratio = sharpe.get('sharperatio', 0) or 0
max_drawdown = drawdown.max.drawdown or 0
annual_return = returns.get('rnorm100', 0) or 0

analysis = {
    '初始资金': initial_value,
    '最终资金': final_value,
    '总收益': final_value - initial_value,
    '收益率': return_rate,
    '夏普比率': sharpe_ratio,
    '最大回撤': max_drawdown,
    '年化收益率': annual_return
}

print('\n=== 回测结果汇总 ===')
for key, value in analysis.items():
    if key in ['收益率', '最大回撤', '年化收益率']:
        print(f'{key}: {value:.2f}%')
    elif key == '夏普比率':
        print(f'{key}: {value:.3f}')
    else:
        print(f'{key}: {value:.2f}')

# 绘制结果
if final_value != initial_value:
    print('\n=== 绘制回测图表 ===')
    cerebro.plot(style='candlestick')
else:
    print('\n=== 策略未产生交易，无图表可绘制 ===')