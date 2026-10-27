import backtrader as bt

class BuyAndHold(bt.Strategy):
    """Submit one buy at the first eligible bar and hold without a final exit.

    Position size comes from the configured sizer; this does not automatically
    invest all available cash.
    """

    def __init__(self):
        pass

    def nextstart(self):
        self.buy()
