"""Acquire historical feeds and orchestrate one Backtrader run per request."""

from datetime import datetime
from pathlib import Path

import backtrader as bt
import pandas as pd
import yfinance as yf

from analyzers.backtest_result import BacktestResult
from dto.backtest_request import BacktestRequest, DataRequest
from dto.backtest_response import BacktestResponse
from services.registry import resolve_params, strategy_by_name, sizer_by_name

def get_data_y_finance(request: DataRequest):
    """Download one ticker's OHLCV data and wrap it in a date-filtered feed.

    Yahoo treats the download end date as exclusive. Provider adjustment
    defaults are left unchanged. Raise ValueError for a missing or empty
    download; other provider failures propagate to the caller.
    """
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
    """Load the bundled AAPL CSV independently of the working directory.

    Optional dates filter the Backtrader feed. This local sample helper is
    separate from the HTTP backtest flow, which downloads prices from Yahoo.
    """
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
    """Run a single-asset simulation and return summary metrics and bar history.

    Resolve strategy and sizer names before downloading data. Each call owns a
    fresh engine and leaves the request unchanged. Percentage slippage takes
    precedence when both slippage modes are supplied.

    Returns and drawdown are percentages; Sharpe may be undefined. Final
    portfolio value includes open positions without forced liquidation. History
    includes end-of-bar close, cash, equity, and drawdown during warm-up too.
    No executed-trade list or result persistence is provided. Resolution and
    strategy ValueErrors propagate for the HTTP layer to translate.
    """
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

    cerebro.addanalyzer(BacktestResult, _name="results")

    strats = cerebro.run()
    strat = strats[0]
    analysis = strat.analyzers.results.get_analysis()
    return BacktestResponse(
        start_cash=analysis["start_cash"],
        end_cash=analysis["end_cash"],
        end_value=analysis["end_value"],
        total_return=analysis["total_return"],
        CAGR=analysis["CAGR"],
        sharpe=analysis["sharpe"],
        closed_trades=analysis["closed_trades"],
        max_drawdown=analysis["max_drawdown"],
        history=analysis["history"],
    )
