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
        close = self.data.close
        open_price = self.data.open
        high = self.data.high
        low = self.data.low
        
        # 1. 自定义加权价格 A0
        self.A0 = (3 * close + low + open_price + high) / 6
        
        # 2. 加权移动平均线 X (根据通达信公式计算)
        # X:=(20*A0+19*REF(A0,1)+18*REF(A0,2)+17*REF(A0,3)+16*REF(A0,4)+15*REF(A0,5)+
        # 14*REF(A0,6)+13*REF(A0,7)+12*REF(A0,8)+11*REF(A0,9)+10*REF(A0,10)+9*REF(A0,11)+8*REF(A0,12)
        # +7*REF(A0,13)+6*REF(A0,14)+5*REF(A0,15)+4*REF(A0,16)+3*REF(A0,17)+2*REF(A0,18)+
        # REF(A0,20))/210;
        self.X = (20*self.A0 + 19*self.A0(-1) + 18*self.A0(-2) + 17*self.A0(-3) + 16*self.A0(-4) + 15*self.A0(-5) +
                 14*self.A0(-6) + 13*self.A0(-7) + 12*self.A0(-8) + 11*self.A0(-9) + 10*self.A0(-10) + 9*self.A0(-11) + 8*self.A0(-12) +
                 7*self.A0(-13) + 6*self.A0(-14) + 5*self.A0(-15) + 4*self.A0(-16) + 3*self.A0(-17) + 2*self.A0(-18) +
                 self.A0(-20)) / 210
        
        # 3. 动量指标 MTM
        self.MTM = close - close(-1)
        
        # 4. 动向指标 DX
        abs_mtm = abs(self.MTM)
        ema_mtm = bt.indicators.ExponentialMovingAverage(self.MTM, period=6)
        ema_abs_mtm = bt.indicators.ExponentialMovingAverage(abs_mtm, period=6)
        self.DX = 100 * bt.indicators.ExponentialMovingAverage(ema_mtm, period=6) / bt.indicators.ExponentialMovingAverage(ema_abs_mtm, period=6)
        
        # 5. CB2 指标 (X的13日EMA)
        self.CB2 = bt.indicators.ExponentialMovingAverage(self.X, period=13)
        
        # 6. 控盘指标
        ema13 = bt.indicators.ExponentialMovingAverage(close, period=13)
        self.VAW1 = bt.indicators.ExponentialMovingAverage(ema13, period=13)
        self.控盘 = (self.VAW1 - self.VAW1(-1)) / self.VAW1(-1) * 1000
        
        # 7. 波段买卖指标
        ema_short = bt.indicators.ExponentialMovingAverage(close, period=self.p.s)
        ema_long = bt.indicators.ExponentialMovingAverage(close, period=self.p.p)
        self.财 = (ema_short - ema_long) * 50
        self.神 = bt.indicators.ExponentialMovingAverage(self.财, period=self.p.m1)
        
        # 8. 均线系统
        self.MA5 = bt.indicators.SimpleMovingAverage(close, period=5)
        self.MA10 = bt.indicators.SimpleMovingAverage(close, period=10)
        self.MA20 = bt.indicators.SimpleMovingAverage(close, period=20)
        self.MA30 = bt.indicators.SimpleMovingAverage(close, period=30)
        self.MA60 = bt.indicators.SimpleMovingAverage(close, period=60)
        
        # 9. 涨跌停判断
        price_change = (close - close(-1)) / close(-1)
        self.AA1 = bt.And(price_change >= 0.058, price_change < 0.095)
        self.AA2 = price_change >= 0.098
        
        # 信号标记 - 简化版
        # 买入信号：综合条件
        # 买1:=IF(LLV(DX,2)=LLV(DX,7) AND COUNT(DX<0,2) AND CROSS(DX,MA(DX,2)),1,0);
        self.买入信号 = bt.And(
            bt.indicators.Lowest(self.DX, period=2) == bt.indicators.Lowest(self.DX, period=7),  # DX近2日创7日新低
            bt.Or(self.DX(-1) < 0, self.DX < 0),  # 近2日内DX有小于0的情况
            bt.indicators.CrossUp(self.DX, bt.indicators.SimpleMovingAverage(self.DX, period=2)),  # DX上穿2日均线
            self.控盘 > self.控盘(-1),  # 控盘上升
            self.财 < -0.3,  # 波段指标超卖
            bt.indicators.CrossUp(self.财, self.神)  # 波段金叉
        )
        
        # 卖出信号：综合条件
        # 卖:=IF(HHV(DX,2)=HHV(DX,7) AND COUNT(DX>50,2) AND CROSS(MA(DX,2),DX),1,0);
        self.卖出信号 = bt.And(
            bt.indicators.Highest(self.DX, period=2) == bt.indicators.Highest(self.DX, period=7),  # DX近2日创7日新高
            bt.Or(self.DX(-1) > 50, self.DX > 50),  # 近2日内DX有大于50的情况
            bt.indicators.CrossDown(bt.indicators.SimpleMovingAverage(self.DX, period=2), self.DX),  # DX下穿2日均线
            self.控盘 < self.控盘(-1),  # 控盘下降
            self.财 > 1.618,  # 波段指标超买
            bt.indicators.CrossDown(self.神, self.财)  # 波段死叉
        )

    def next(self):
        """
        策略核心逻辑：根据综合指标信号进行交易决策
        """
        current_date = self.data.datetime.date(0)
        
        # 获取当前信号值
        buy_signal = self.买入信号[0]
        sell_signal = self.卖出信号[0]
        
        # 当前无持仓，检查买入信号
        if not self.position:
            if buy_signal:
                # 买入信号出现，执行买入
                self.log(f'{current_date}: 综合买入信号触发，买入股票')
                # 使用50%资金买入
                available_cash = self.broker.getcash()
                size = int(available_cash * 0.5 / self.data.close[0])
                if size > 0:
                    self.buy(size=size)
                    
        # 当前有持仓，检查卖出信号
        else:
            if sell_signal:
                # 卖出信号出现，执行卖出
                self.log(f'{current_date}: 综合卖出信号触发，卖出股票')
                self.close()  # 平掉所有持仓
            elif self.AA2[0]:
                # 涨停时考虑卖出
                self.log(f'{current_date}: 涨停信号，获利了结')
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