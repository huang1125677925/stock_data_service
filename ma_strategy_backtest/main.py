import backtrader as bt
import pandas as pd
import datetime as dt
from strategy_ma_cross import SmaCross
import akshare as ak

# 加载数据
df = ak.stock_zh_a_hist(symbol="w", start_date="20240101", end_date="20251231")

df.rename(columns={
    '日期': 'trade_date', 
    '股票代码': 'code', 
    '开盘': 'open', 
    '收盘': 'close', 
    '最高': 'high', 
    '最低': 'low', 
    '成交量': 'volume', 
    '成交额': 'amount', 
    '振幅': 'amplitude', 
    '涨跌幅': 'pct_chg', 
    '涨跌额': 'change', 
    '换手率': 'turnover'
}, inplace=True)

# 确保日期是 pandas Timestamp 类型
df['trade_date'] = pd.to_datetime(df['trade_date'])
df.set_index('trade_date', inplace=True)

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
        # 额外的字段
        ('amount', 'amount'),
        ('amplitude', 'amplitude'),
        ('pct_chg', 'pct_chg'),
        ('change', 'change'),
        ('turnover', 'turnover'),
        ('code', 'code'),
    )

# 定义回测函数
def run_backtest(data_df, period_name):
    # 创建数据源
    data = PandasData(dataname=data_df)
    
    # 回测引擎 Cerebro
    cerebro = bt.Cerebro()
    cerebro.addstrategy(SmaCross)
    cerebro.adddata(data)
    cerebro.broker.set_cash(100000)
    cerebro.broker.setcommission(commission=0.001)  # 0.1%手续费
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    
    # 运行回测
    initial_value = cerebro.broker.getvalue()
    result = cerebro.run()
    final_value = cerebro.broker.getvalue()
    
    # 计算收益率
    return_rate = (final_value - initial_value) / initial_value * 100
    
    # 获取策略实例
    strategy = result[0]
    
    # 获取分析结果
    sharpe = strategy.analyzers.sharpe.get_analysis()
    drawdown = strategy.analyzers.drawdown.get_analysis()
    returns = strategy.analyzers.returns.get_analysis()
    
    # 详细分析
    sharpe_ratio = sharpe.get('sharperatio', 0) or 0
    max_drawdown = drawdown.max.drawdown or 0
    annual_return = returns.get('rnorm100', 0) or 0
    
    analysis = {
        '回测周期': period_name,
        '初始资金': initial_value,
        '最终资金': final_value,
        '总收益': final_value - initial_value,
        '收益率': return_rate,
        '夏普比率': sharpe_ratio,
        '最大回撤': max_drawdown,
        '年化收益率': annual_return
    }
    
    # 分析持仓情况
    print(f'\n=== {period_name}回测结果汇总 ===')
    for key, value in analysis.items():
        if key in ['收益率', '最大回撤', '年化收益率']:
            print(f'{key}: {value:.2f}%')
        elif key == '夏普比率':
            print(f'{key}: {value:.3f}')
        elif key == '回测周期':
            print(f'{key}: {value}')
        else:
            print(f'{key}: {value:.2f}')
    
    # 检查是否有持仓
    if cerebro.broker.getposition(data):
        pos = cerebro.broker.getposition(data)
        print(f'当前持仓: {pos.size}股, 成本价: {pos.price:.2f}')
    else:
        print('当前无持仓')
    
    return analysis

# 获取数据的日期范围
min_date = df.index.min()
max_date = df.index.max()
print(f'\n数据范围: {min_date.strftime("%Y-%m-%d")} 至 {max_date.strftime("%Y-%m-%d")}')

# 计算数据集包含的总年数
data_years = (max_date.year - min_date.year) + 1
print(f'数据集包含约 {data_years} 年的数据')

# 对不同年份范围的数据进行回测
results = []

# 对全部数据进行回测
print('\n开始对全部数据进行回测...')
all_data_result = run_backtest(df, '全部数据')
results.append(all_data_result)

# 逐年回测所有年份
for year in range(1, data_years + 1):
    # 计算起始日期
    start_date = max_date - pd.DateOffset(years=year)
    # 获取该时间段的数据
    period_data = df[df.index >= start_date]
    
    if len(period_data) > 30:  # 确保有足够的数据进行回测
        print(f'\n开始对最近{year}年数据进行回测 ({start_date.strftime("%Y-%m-%d")} 至 {max_date.strftime("%Y-%m-%d")})...')
        year_result = run_backtest(period_data, f'最近{year}年')
        results.append(year_result)
    else:
        print(f'\n最近{year}年数据不足，跳过回测')

# 按照年份从小到大排序结果（除了全部数据）
results_sorted = [results[0]] + sorted(results[1:], key=lambda x: int(x['回测周期'].replace('最近', '').replace('年', '')))

# 比较不同时间段的回测结果
print('\n=== 不同时间段回测结果比较 ===')
print(f"{'回测周期':<12} {'收益率':<10} {'夏普比率':<10} {'最大回撤':<10} {'年化收益率':<10}")
for result in results_sorted:
    period = result['回测周期']
    return_rate = f"{result['收益率']:.2f}%"
    sharpe = f"{result['夏普比率']:.3f}"
    drawdown = f"{result['最大回撤']:.2f}%"
    annual = f"{result['年化收益率']:.2f}%"
    print(f"{period:<12} {return_rate:<10} {sharpe:<10} {drawdown:<10} {annual:<10}")