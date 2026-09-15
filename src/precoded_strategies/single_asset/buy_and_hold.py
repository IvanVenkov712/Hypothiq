import backtrader as bt

class BuyAndHold(bt.Strategy):
    def __init__(self):
        pass

    def nextstart(self):
        self.buy()
