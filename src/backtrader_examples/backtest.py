import json
from datetime import datetime

import backtrader as bt
import pandas as pd

from precoded_strategies.single_asset.breakout import SimpleBollingerBandsBreakout

df = pd.read_csv("../../data/AAPL.csv")

df["Date"] = pd.to_datetime(df["Date"])
df.set_index("Date", inplace=True)

data = bt.feeds.PandasData(
    dataname=df,
    open="Open",
    high="High",
    low="Low",
    close="Close",
    volume="Volume",
    openinterest=None,
    fromdate=datetime(2021, 1, 1),
    todate=datetime(2026, 1, 1)
)

cerebro = bt.Cerebro()
cerebro.adddata(data)
cerebro.addstrategy(SimpleBollingerBandsBreakout)

cerebro.addanalyzer(bt.analyzers.AnnualReturn)
cerebro.addanalyzer(bt.analyzers.SharpeRatio)
cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
cerebro.addanalyzer(bt.analyzers.TradeAnalyzer)

strats = cerebro.run()
strat = strats[0]

print(strat.analyzers.drawdown.get_analysis().max.drawdown)

for analyzer in strat.analyzers:
    print(json.dumps(analyzer.get_analysis()))



