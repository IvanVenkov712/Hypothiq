import backtrader as bt
import backtrader.indicators as btind

class MACrossOver(bt.Strategy):
    """Enter long on a fast/slow average cross up and close on a cross down.

    The movav parameter is a Backtrader indicator class resolved by the registry
    when supplied by name through the API.
    """

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
