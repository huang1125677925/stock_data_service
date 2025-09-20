import backtrader as bt

class SimpleAdvancedStrategy(bt.Strategy):
    """
    简化的综合技术指标策略
    
    策略逻辑：
    1. 基于均线系统
    2. 动量指标
    3. 主力资金动向判断
    4. 波段交易信号
    """
    
    params = dict(
        short_period=8,    # 短期EMA
        long_period=21,    # 长期EMA
        signal_period=3,   # 信号平滑
        printlog=True
    )

    def __init__(self):
        """
        策略初始化
        """
        # 基础价格
        close = self.data.close
        
        # 1. 均线系统
        self.ema_short = bt.indicators.ExponentialMovingAverage(close, period=self.p.short_period)
        self.ema_long = bt.indicators.ExponentialMovingAverage(close, period=self.p.long_period)
        
        # 2. 动量指标
        # 添加数据长度检查，避免索引越界
        self.momentum = bt.indicators.If(
            bt.indicators.BarsSince(self.data) >= 1,
            close - close(-1),
            0
        )
        self.momentum_ema = bt.indicators.ExponentialMovingAverage(abs(self.momentum), period=6)
        
        # 3. 主力资金指标 (简化版控盘)
        self.control = (self.ema_short - self.ema_long) / self.ema_long * 100
        
        # 4. 波段指标
        self.band_indicator = bt.indicators.MACD(close, period_me1=8, period_me2=21, period_signal=5)
        
        # 5. 成交量指标
        self.volume_ma = bt.indicators.SimpleMovingAverage(self.data.volume, period=5)
        
        # 买入信号：多重条件确认
        # 添加数据长度检查，避免索引越界
        self.price_up = bt.indicators.If(
            bt.indicators.BarsSince(self.data) >= 5,
            close > close(-5),
            False
        )
        
        self.buy_signal = bt.And(
            bt.indicators.CrossUp(self.ema_short, self.ema_long),  # 金叉
            self.price_up,  # 价格上升
            self.data.volume > self.volume_ma * 1.2,  # 放量
            self.band_indicator.macd > self.band_indicator.signal  # MACD金叉
        )
        
        # 卖出信号：多重条件确认
        # 添加数据长度检查，避免索引越界
        self.price_down = bt.indicators.If(
            bt.indicators.BarsSince(self.data) >= 5,
            close < close(-5),
            False
        )
        
        self.sell_signal = bt.And(
            bt.indicators.CrossDown(self.ema_short, self.ema_long),  # 死叉
            self.price_down,  # 价格下降
            self.data.volume > self.volume_ma * 1.2,  # 放量
            self.band_indicator.macd < self.band_indicator.signal  # MACD死叉
        )

    def next(self):
        """
        策略核心逻辑
        """
        current_date = self.data.datetime.date(0)
        current_price = self.data.close[0]
        
        # 获取信号
        buy_sig = self.buy_signal[0]
        sell_sig = self.sell_signal[0]
        
        # 当前无持仓，检查买入信号
        if not self.position:
            if buy_sig:
                # 计算买入数量（使用90%资金）
                available_cash = self.broker.getcash()
                size = int(available_cash * 0.9 / current_price)
                if size > 0:
                    self.log(f'{current_date}: 买入信号触发，买入 {size} 股，价格 {current_price:.2f}')
                    self.buy(size=size)
                    
        # 当前有持仓，检查卖出信号
        else:
            if sell_sig:
                self.log(f'{current_date}: 卖出信号触发，卖出所有持仓，价格 {current_price:.2f}')
                self.close()
            elif self.position.size > 0 and current_price <= self.position.price * 0.95:
                # 止损：下跌5%止损
                self.log(f'{current_date}: 止损触发，卖出所有持仓，价格 {current_price:.2f}')
                self.close()
            elif self.position.size > 0 and current_price >= self.position.price * 1.15:
                # 止盈：上涨15%止盈
                self.log(f'{current_date}: 止盈触发，卖出所有持仓，价格 {current_price:.2f}')
                self.close()

    def log(self, txt, dt=None):
        """日志函数"""
        if self.p.printlog:
            dt = dt or self.data.datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入完成: 价格={order.executed.price:.2f}, '
                        f'数量={order.executed.size}, 成本={order.executed.value:.2f}')
            else:
                self.log(f'卖出完成: 价格={order.executed.price:.2f}, '
                        f'数量={order.executed.size}, 收入={order.executed.value:.2f}')

    def notify_trade(self, trade):
        """交易状态通知"""
        if not trade.isclosed:
            return

        self.log(f'交易结束: 毛收益={trade.pnl:.2f}, 净收益={trade.pnlcomm:.2f}, '
                f'收益率={(trade.pnlcomm/trade.price)*100:.2f}%')

    def stop(self):
        """策略结束时调用"""
        portfolio_value = self.broker.getvalue()
        total_return = (portfolio_value - 100000) / 100000 * 100
        self.log(f'策略结束: 最终资金={portfolio_value:.2f}, 总收益率={total_return:.2f}%')