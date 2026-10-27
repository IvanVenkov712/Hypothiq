import backtrader as bt
import backtrader.indicators as btind

class MeanReversion(bt.Strategy):
    params = dict(
        multiplier=0.95,
        period=20,
        movav=btind.MovingAverageSimple
    )

    def __init__(self):
        self.ma = self.p.movav(period=self.p.period)

    def next(self):
        if not self.position:
            if self.data.close < self.ma * self.p.multiplier:
                self.buy()

        elif self.data.close >= self.ma:
            self.close()