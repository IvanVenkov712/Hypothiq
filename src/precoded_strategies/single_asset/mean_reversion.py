import backtrader as bt
import backtrader.indicators as btind

class MeanReversion(bt.Strategy):
    params = dict(
        multiplier=0.99,
        period=20,
        movav=btind.MovingAverageSimple
    )

    def __init__(self):
        self.ma = self.p.movav(period=self.p.period)

    def next(self):
        if self.data.close < self.ma * self.p.multiplier:
                self.buy()

        elif self.position and self.data.close >= self.ma:
            self.close()