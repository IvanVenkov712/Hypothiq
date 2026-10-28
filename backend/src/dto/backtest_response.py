from pydantic import BaseModel, Field, FiniteFloat, NaiveDatetime


class BacktestHistoryPoint(BaseModel):
    """End-of-bar snapshot, including bars during indicator warm-up.

    Time is the feed's timezone-free bar label, not a local wall-clock instant.
    Equity includes positions marked at the bar's close. Drawdown is a
    nonnegative percentage below the running peak equity, not a fraction.
    """

    time: NaiveDatetime
    close: FiniteFloat
    cash: FiniteFloat
    equity: FiniteFloat
    drawdown: FiniteFloat = Field(ge=0)


class BacktestResponse(BaseModel):
    """Summary metrics and one history point per processed bar, in feed order.

    End value includes open positions; end cash is uninvested cash. CAGR is
    the Returns analyzer's annualized percentage. Sharpe may be None when
    undefined, and closed_trades counts completed round trips only.
    History has no synthetic initial point; start_cash is the initial baseline.
    """

    start_cash: float
    end_cash: float
    end_value: float
    total_return: float
    CAGR: float
    sharpe: float | None
    closed_trades: float
    max_drawdown: float
    history: list[BacktestHistoryPoint]
