"""FastAPI entry point for strategy discovery and synchronous backtests."""

from fastapi import FastAPI

from routers.backtest_router import backtests_router
from routers.strategy_router import strategies_router

app = FastAPI()
app.include_router(backtests_router)
app.include_router(strategies_router)

@app.get("/health")
def health():
    """Report API liveness without checking the external market-data provider."""
    return {"status": "ok"}
