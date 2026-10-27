from typing import Any

from pydantic import BaseModel


class BacktestResponse(BaseModel):
    """Aggregate results, with returns and drawdown expressed as percentages.

    End value includes open positions; end cash is uninvested cash. CAGR is
    the Returns analyzer's annualized percentage. Sharpe may be None when
    undefined, and closed_trades counts completed round trips only.
    """

    start_cash: float
    end_cash: float
    end_value: float
    total_return: float
    CAGR: float
    sharpe: float | None
    closed_trades: float
    max_drawdown: float
    history: list[dict[str, Any]]
