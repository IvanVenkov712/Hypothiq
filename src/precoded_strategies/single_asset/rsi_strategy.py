import backtrader as bt
import backtrader.indicators as btind
from backtrader.indicators import SmoothedMovingAverage


class RSIStrategy(bt.Strategy):
    params = dict(
        lower=30,
        upper=70,
        period=14,
        movav=SmoothedMovingAverage
    )

    def __init__(self):
        self.rsi = btind.RelativeStrengthIndex(movav=self.p.movav, period=self.p.period)

    def next(self):
        if not self.position:
            if self.rsi < self.p.lower:
                self.buy()

        elif self.rsi > self.p.upper:
            self.close()

