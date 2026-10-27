from pydantic import BaseModel


class BacktestResponse(BaseModel):
    start_cash: float
    end_cash: float
    end_value: float
    total_return: float
    CAGR: float
    sharpe: float | None
    closed_trades: float
    max_drawdown: float
