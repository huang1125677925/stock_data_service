import backtrader as bt

class SmaCross(bt.Strategy):
    """
    双均线交叉策略 (Moving Average Crossover Strategy)
    
    策略逻辑：
    1. 当短期均线上穿长期均线（金叉）时买入
    2. 当短期均线下穿长期均线（死叉）时卖出
    
    参数说明：
    - short: 短期均线周期，默认10日
    - long: 长期均线周期，默认30日
    """
    
    # 策略参数定义，可在运行时调整
    params = dict(
        short=10,      # 短期均线周期
        long=30,       # 长期均线周期
        printlog=True  # 是否打印日志
    )

    def __init__(self):
        """
        策略初始化：
        计算两条简单移动平均线(SMA)和交叉信号
        """
        # 计算短期简单移动平均线
        self.sma_short = bt.ind.SMA(
            period=self.p.short, 
            plotname=f'SMA_{self.p.short}'
        )
        
        # 计算长期简单移动平均线
        self.sma_long = bt.ind.SMA(
            period=self.p.long, 
            plotname=f'SMA_{self.p.long}'
        )
        
        # 计算交叉信号：
        # crossover > 0 表示短期均线上穿长期均线（金叉）
        # crossover < 0 表示短期均线下穿长期均线（死叉）
        self.crossover = bt.ind.CrossOver(
            self.sma_short, 
            self.sma_long,
            plotname='Crossover'
        )

    def next(self):
        """
        策略核心逻辑：
        在每个K线结束时执行，根据交叉信号进行交易决策
        """
        current_date = self.data.datetime.date(0)
        
        # 当前无持仓，检查买入信号
        if not self.position:
            if self.crossover > 0:
                # 金叉出现，执行买入
                self.log(f'{current_date}: 金叉信号，买入股票')
                # 使用全部资金买入（可根据需要调整仓位）
                self.buy(size=1000)  # 买入1000股
                
        # 当前有持仓，检查卖出信号
        else:
            if self.crossover < 0:
                # 死叉出现，执行卖出
                self.log(f'{current_date}: 死叉信号，卖出股票')
                self.close()  # 平掉所有持仓

    def log(self, txt, dt=None):
        """日志函数：记录策略执行过程"""
        if self.p.printlog:
            dt = dt or self.data.datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

    def notify_order(self, order):
        """
        订单状态通知：
        当订单提交、接受、完成或取消时调用
        """
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交/已接受，等待执行
            return

        # 检查订单是否完成
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入执行, 价格: {order.executed.price:.2f}, '
                        f'成本: {order.executed.value:.2f}, '
                        f'手续费: {order.executed.comm:.2f}')
            else:  # Sell
                self.log(f'卖出执行, 价格: {order.executed.price:.2f}, '
                        f'价值: {order.executed.value:.2f}, '
                        f'手续费: {order.executed.comm:.2f}')

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/拒绝')

    def notify_trade(self, trade):
        """
        交易状态通知：
        当交易完成时调用，可用于计算收益率
        """
        if not trade.isclosed:
            return

        self.log(f'交易完成, 毛收益: {trade.pnl:.2f}, 净收益: {trade.pnlcomm:.2f}')

    def stop(self):
        """策略结束时调用，可用于最终分析"""
        portfolio_value = self.broker.getvalue()
        self.log(f'策略结束, 最终资金: {portfolio_value:.2f}')