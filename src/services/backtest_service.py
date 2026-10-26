from datetime import datetime
from pathlib import Path

import backtrader as bt
import backtrader.analyzers as btanalyzers
import pandas as pd
import yfinance as yf

from dto.backtest_request import BacktestRequest, DataRequest
from dto.backtest_response import BacktestResponse
from registry import resolve_params, strategy_by_name, sizer_by_name

def get_data_y_finance(request: DataRequest):
    df = yf.download(
        tickers=request.ticker,
        interval=request.interval,
        start=request.start,
        end=request.end,
        multi_level_index=False,
    )

    if df is None:
        raise ValueError('An error occurred during yfinance data download')
    
    if df.empty:
        raise ValueError("There are no records")

    data = bt.feeds.PandasData(
        dataname=df,
        fromdate=request.start,
        todate=request.end
    )
    return data

def get_data(fromdate: datetime | None = None, todate: datetime | None = None):
    df = pd.read_csv(Path(__file__).resolve().parents[2] / 'data' / 'AAPL.csv')
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    data = bt.feeds.PandasData(
        dataname=df,
        fromdate=fromdate,
        todate=todate,
    )
    return data

def run_backtest_by_request(request: BacktestRequest) -> BacktestResponse:
    strategy = strategy_by_name(request.strategy.name)
    strategy_params = resolve_params(strategy, request.strategy.params)
    sizer = sizer_by_name(request.sizer.name)
    sizer_params = resolve_params(sizer, request.sizer.params)
    cerebro = bt.Cerebro()

    cerebro.adddata(get_data_y_finance(request.data_request))
    cerebro.addstrategy(strategy, **strategy_params)
    cerebro.addsizer(sizer, **sizer_params)

    cash = request.broker.cash
    cerebro.broker.set_cash(cash)

    if request.broker.slippage_perc is not None:
        cerebro.broker.set_slippage_perc(
            **request.broker.slippage_perc.model_dump()
        )
    elif request.broker.slippage_fixed is not None:
        cerebro.broker.set_slippage_fixed(
            **request.broker.slippage_fixed.model_dump()
        )

    cerebro.broker.setcommission(**request.broker.commission.model_dump())

    cerebro.addanalyzer(btanalyzers.Returns, _name='returns')
    cerebro.addanalyzer(
        btanalyzers.SharpeRatio,
        _name="sharpe",
        timeframe=bt.TimeFrame.Days,
        annualize=True,
        riskfreerate=0.0,
    )
    cerebro.addanalyzer(btanalyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(btanalyzers.DrawDown, _name='drawdown')

    strats = cerebro.run()
    strat = strats[0]
    return BacktestResponse(
        start_cash=cash,
        end_cash=cerebro.broker.get_cash(),
        end_value=cerebro.broker.get_value(),
        total_return=100 * (cerebro.broker.get_value() / cash - 1),
        CAGR=strat.analyzers.returns.get_analysis()['rnorm100'],
        sharpe=strat.analyzers.sharpe.get_analysis()['sharperatio'],
        closed_trades=strat.analyzers.trades.get_analysis().get('total', {}).get('closed', 0),
        max_drawdown=strat.analyzers.drawdown.get_analysis().max.drawdown,
    )
