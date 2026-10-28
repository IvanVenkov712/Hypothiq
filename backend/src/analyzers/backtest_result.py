import backtrader.analyzers as btanalyzers
import backtrader as bt


class BacktestResult(bt.Analyzer):
    def __init__(self):
        self.drawdown = bt.analyzers.DrawDown(fund=False)
        self.returns = bt.analyzers.Returns()
        self.trades = bt.analyzers.TradeAnalyzer()
        self.sharpe = bt.analyzers.SharpeRatio(
            timeframe=bt.TimeFrame.Days,
            annualize=True,
            riskfreerate=0.0,
        )

    def start(self):
        self.start_cash = self.strategy.broker.getcash()
        self.rets["history"] = []

    def next(self):
        self.rets["history"].append({
            "time": self.data.datetime.datetime(0).isoformat(),
            "close": self.data.close[0],
            "cash": self.strategy.broker.getcash(),
            "equity": self.strategy.broker.getvalue(),
            "drawdown": self.drawdown.get_analysis()["drawdown"],
        })

    def stop(self):
        broker = self.strategy.broker

        self.rets["start_cash"] = self.start_cash
        self.rets["end_cash"] = broker.getcash()
        self.rets["end_value"] = broker.getvalue()

        self.rets["total_return"] = (
                100 * (broker.getvalue() / self.start_cash - 1)
        )
        self.rets["CAGR"] = self.returns.get_analysis()["rnorm100"]
        self.rets["sharpe"] = self.sharpe.get_analysis()["sharperatio"]
        self.rets["closed_trades"] = (
            self.trades.get_analysis().get("total", {}).get("closed", 0)
        )
        self.rets["max_drawdown"] = (
            self.drawdown.get_analysis()["max"]["drawdown"]
        )
