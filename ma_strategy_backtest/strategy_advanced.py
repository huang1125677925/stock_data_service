import backtrader as bt
import numpy as np

class AdvancedStrategy(bt.Strategy):
    """
    高级技术指标综合策略
    
    策略逻辑：
    1. 基于自定义加权价格计算趋势指标
    2. 使用动量指标(MTM)和动向指标(DX)判断买卖点
    3. 控盘指标判断主力资金动向
    4. 波段买卖指标结合均线系统
    5. 涨跌停过滤机制
    """
    
    params = dict(
        p=21,           # EMA长周期
        s=8,            # EMA短周期
        m1=3,           # EMA平滑周期
        printlog=True   # 是否打印日志
    )

    def __init__(self):
        """
        策略初始化：计算所有需要的技术指标
        """
        # 基础价格数据
        self.close = self.data.close
        self.open = self.data.open
        self.high = self.data.high
        self.low = self.data.low
        
        # 1. 自定义加权价格 A0
        self.A0 = (3 * self.close + self.low + self.open + self.high) / 6
        
        # 2. 加权移动平均线 X (21日加权平均)
        weights = np.array([20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 
                           10, 9, 8, 7, 6, 5, 4, 3, 2, 1])
        weights = weights / weights.sum()
        self.X = bt.indicators.WMA(self.A0, period=21)
        
        # 3. 动量指标 MTM
        self.MTM = self.close - bt.indicators.Delay(self.close, period=1)
        
        # 4. 动向指标 DX
        abs_mtm = bt.indicators.Abs(self.MTM)
        ema_mtm = bt.indicators.EMA(self.MTM, period=6)
        ema_abs_mtm = bt.indicators.EMA(abs_mtm, period=6)
        self.DX = 100 * bt.indicators.EMA(ema_mtm, period=6) / bt.indicators.EMA(ema_abs_mtm, period=6)
        
        # 5. CB2 指标 (X的13日EMA)
        self.CB2 = bt.indicators.EMA(self.X, period=13)
        
        # 6. 控盘指标
        self.VAW1 = bt.indicators.EMA(bt.indicators.EMA(self.close, period=13), period=13)
        self.控盘 = (self.VAW1 - bt.indicators.Delay(self.VAW1, period=1)) / bt.indicators.Delay(self.VAW1, period=1) * 1000
        
        # 7. 波段买卖指标
        self.财 = (bt.indicators.EMA(self.close, period=self.p.s) - bt.indicators.EMA(self.close, period=self.p.p)) * 50
        self.神 = bt.indicators.EMA(self.财, period=self.p.m1)
        
        # 8. 均线系统
        self.MA5 = bt.indicators.SMA(self.close, period=5)
        self.MA10 = bt.indicators.SMA(self.close, period=10)
        self.MA20 = bt.indicators.SMA(self.close, period=20)
        self.MA30 = bt.indicators.SMA(self.close, period=30)
        self.MA60 = bt.indicators.SMA(self.close, period=60)
        
        # 9. 涨跌停判断
        self.AA1 = ((self.close - bt.indicators.Delay(self.close, period=1)) / bt.indicators.Delay(self.close, period=1) >= 0.058) & \
                   ((self.close - bt.indicators.Delay(self.close, period=1)) / bt.indicators.Delay(self.close, period=1) < 0.095)
        self.AA2 = (self.close - bt.indicators.Delay(self.close, period=1)) / bt.indicators.Delay(self.close, period=1) >= 0.098
        
        # 信号标记
        self.卖出信号 = bt.And(
            bt.indicators.Highest(self.DX, period=2) == bt.indicators.Highest(self.DX, period=7),
            bt.indicators.Sum(self.DX > 50, period=2) >= 1,
            bt.indicators.CrossDown(bt.indicators.SMA(self.DX, period=2), self.DX)
        )
        
        self.买1信号 = bt.And(
            bt.indicators.Lowest(self.DX, period=2) == bt.indicators.Lowest(self.DX, period=7),
            bt.indicators.Sum(self.DX < 0, period=2) >= 1,
            bt.indicators.CrossUp(self.DX, bt.indicators.SMA(self.DX, period=2))
        )
        
        # 控盘条件
        self.无庄控盘 = self.控盘 < 0
        self.有庄控盘 = bt.And(self.控盘 > bt.indicators.Delay(self.控盘, period=1), self.控盘 > 0)
        
        # 价格偏离条件
        self.JJ = self.data.close  # 简化为当日收盘价
        self.BTJ1 = (self.close - self.JJ) / self.JJ < -0.03
        self.BTJ11 = (self.close - self.JJ) / self.JJ < -0.03
        self.BTJ12 = bt.And(
            bt.indicators.LaguerreFilter(self.JJ >= bt.indicators.Delay(self.JJ, period=1), period=5) >= 1,
            (self.close - self.JJ) / self.JJ < 0.005
        )
        self.STJ1 = (self.close - self.JJ) / self.JJ > 0.005
        
        # 控盘买卖条件
        self.STJ01 = bt.And(self.控盘 < bt.indicators.Delay(self.控盘, period=1), self.控盘 > 0.5)
        self.STJ02 = self.控盘 > 0
        self.BTJ2 = bt.And(self.控盘 > bt.indicators.Delay(self.控盘, period=1), self.控盘 < -0.2)
        self.BTJ22 = bt.And(self.控盘 > bt.indicators.Delay(self.控盘, period=1), self.控盘 < 0)
        
        # 波段买卖条件
        self.BTJ3 = bt.And(bt.indicators.CrossUp(self.财, self.神), self.财 < -0.3)
        self.BTJ32 = bt.And(bt.indicators.CrossUp(self.财, self.神), self.财 < -0.1)
        self.STJ31 = bt.indicators.CrossDown(self.神, self.财)
        self.STJ32 = bt.And(bt.indicators.CrossDown(self.神, self.财), self.财 > 1.618)
        
        # 最终信号
        self.BTJ81 = bt.And(self.BTJ1, self.BTJ2, self.BTJ3)
        self.BTJ811 = bt.And(self.BTJ11, self.BTJ2, self.BTJ3)
        self.BTJ82 = bt.And(self.BTJ12, self.BTJ22, self.BTJ32)
        self.STJ81 = bt.And(self.STJ1, self.STJ01, self.STJ31)
        self.STJ82 = bt.And(self.STJ02, self.STJ32)
        self.STJ83 = bt.And(self.STJ81, self.STJ82)
        
        # 庄信号
        self.庄 = bt.And(self.BTJ11, self.BTJ2, self.BTJ3)
        self.有庄 = self.庄

    def next(self):
        """
        策略核心逻辑：根据综合指标信号进行交易决策
        """
        current_date = self.data.datetime.date(0)
        
        # 获取当前信号值
        buy_signal = self.有庄[0]
        sell_signal = self.STJ83[0]
        
        # 当前无持仓，检查买入信号
        if not self.position:
            if buy_signal:
                # 有庄信号出现，执行买入
                self.log(f'{current_date}: 有庄信号，买入股票')
                # 使用50%资金买入
                available_cash = self.broker.getcash()
                size = int(available_cash * 0.5 / self.close[0])
                if size > 0:
                    self.buy(size=size)
                    
        # 当前有持仓，检查卖出信号
        else:
            if sell_signal:
                # 卖出信号出现，执行卖出
                self.log(f'{current_date}: 卖出信号，卖出股票')
                self.close()  # 平掉所有持仓
            elif self.AA2[0]:
                # 涨停时考虑卖出
                self.log(f'{current_date}: 涨停信号，考虑卖出')
                self.close()

    def log(self, txt, dt=None):
        """日志函数：记录策略执行过程"""
        if self.p.printlog:
            dt = dt or self.data.datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入执行, 价格: {order.executed.price:.2f}, '
                        f'数量: {order.executed.size}, '
                        f'成本: {order.executed.value:.2f}, '
                        f'手续费: {order.executed.comm:.2f}')
            else:
                self.log(f'卖出执行, 价格: {order.executed.price:.2f}, '
                        f'数量: {order.executed.size}, '
                        f'价值: {order.executed.value:.2f}, '
                        f'手续费: {order.executed.comm:.2f}')

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/拒绝')

    def notify_trade(self, trade):
        """交易状态通知"""
        if not trade.isclosed:
            return

        self.log(f'交易完成, 毛收益: {trade.pnl:.2f}, 净收益: {trade.pnlcomm:.2f}')

    def stop(self):
        """策略结束时调用"""
        portfolio_value = self.broker.getvalue()
        self.log(f'策略结束, 最终资金: {portfolio_value:.2f}')