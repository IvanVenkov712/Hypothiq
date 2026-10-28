"""Load and validate daily market data before building Backtrader feeds."""

import logging
from datetime import datetime
from pathlib import Path

import backtrader as bt
import pandas as pd
import yfinance as yf

from dto.backtest_request import DataRequest


logger = logging.getLogger(__name__)


class MarketDataError(RuntimeError):
    """The market-data provider failed or returned malformed OHLCV data."""

    def __init__(self, message: str):
        super().__init__(f"{message} Please retry shortly.")


def get_data_y_finance(request: DataRequest) -> bt.feeds.PandasData:
    """Build a daily feed for [start, end), retaining provider adjustment defaults.

    Empty date ranges raise ValueError. Provider failures or malformed bars raise
    MarketDataError; prices are never filled, sorted, or coerced to repair them.
    """
    try:
        df = yf.download(
            tickers=request.ticker,
            interval=request.interval,
            start=request.start,
            end=request.end,
            multi_level_index=False,
        )
    except Exception as exc:
        logger.exception("Market-data download failed for %s", request.ticker)
        raise MarketDataError(
            f"Could not download daily prices for {request.ticker}. "
            "The market-data provider may be unavailable."
        ) from exc

    if df is None:
        raise MarketDataError(
            f"The market-data provider returned no response for {request.ticker}."
        )
    if df.empty:
        raise ValueError(
            f"No daily prices were returned for {request.ticker} in the requested date range. "
            "Check the ticker and dates; if they are correct, the provider may be unavailable. Try again later."
        )

    values = df[["Open", "High", "Low", "Close", "Volume"]]
    if values.isna().any().any() or values.isin([float("inf"), -float("inf")]).any().any():
        raise MarketDataError("Invalid market data: OHLCV values must be finite and non-missing.")
    prices = values.drop(columns="Volume")
    if (prices <= 0).any().any() or (df["Volume"] < 0).any():
        raise MarketDataError("Invalid market data: prices must be positive and volume nonnegative.")
    if (df["High"] < prices.max(axis=1)).any() or (df["Low"] > prices.min(axis=1)).any():
        raise MarketDataError("Invalid market data: High and Low must enclose Open and Close.")

    df = df.loc[(df.index >= request.start) & (df.index < request.end)]
    if df.empty:
        raise ValueError(
            "No daily bars fall within the requested date range. Choose a different date range."
        )

    return bt.feeds.PandasData(
        dataname=df,
        timeframe=bt.TimeFrame.Days,
        compression=1,
    )


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
