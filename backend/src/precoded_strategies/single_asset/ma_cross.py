import backtrader as bt
import backtrader.indicators as btind

class MACrossOver(bt.Strategy):
    params = dict(
        slow=50,
        fast=20,
        movav=btind.MovingAverageSimple
    )

    def __init__(self):
        slow_ma = self.p.movav( period=self.p.slow)
        fast_ma = self.p.movav(period=self.p.fast)
        self.cross = btind.CrossOver(fast_ma, slow_ma)

    def next(self):
        if not self.position:
            if self.cross > 0:
                self.buy()

        elif self.cross < 0:
            self.close()
