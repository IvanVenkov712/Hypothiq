import backtrader as bt
import backtrader.indicators as btind

class DonchianBreakout(bt.Strategy):
    """Buy above prior highs and close below prior lows using separate windows.

    Channel inputs exclude the current bar so the signal compares its close
    against an already established range.
    """

    params = dict(
        entry_period=20,
        exit_period=10
    )

    def __init__(self):
        self.max = btind.Highest(self.data.high(-1), period=self.p.entry_period)
        self.min = btind.Lowest(self.data.low(-1), period=self.p.exit_period)

    def next(self):
        if not self.position:
            if self.data.close[0] > self.max[0]:
                self.buy()

        elif self.data.close[0] < self.min[0]:
            self.close()

class SimpleBollingerBandsBreakout(bt.Strategy):
    """Buy above the upper band and sell below the lower band on every signal.

    Orders are not gated by position or pending-order state. Repeated signals
    can accumulate exposure, and sells can open shorts rather than just exit.
    """

    params = dict(
        period=20,
        devfactor=2,
        movav=btind.MovingAverageSimple
    )

    def __init__(self):
        self.bands = btind.BollingerBands(
            period=self.p.period,
            devfactor=self.p.devfactor,
            movav=self.p.movav
        )

    def next(self):
        if not self.position:
            if self.data.close[0] > self.bands.top[0]:
                self.buy()

        elif self.data.close[0] < self.bands.bot[0]:
            self.close()
