import logging

import fastapi
from fastapi import HTTPException
from pydantic import ValidationError

from dto.backtest_request import BacktestRequest
from dto.backtest_response import BacktestResponse
from services.backtest_service import run_backtest_by_request
from services.market_data import MarketDataError


logger = logging.getLogger(__name__)

backtests_router = fastapi.APIRouter(
    prefix='/backtests',
    tags=['backtests']
)

@backtests_router.post("/run-backtest", response_model=BacktestResponse, responses={
    400: {"description": "Invalid strategy/sizer parameters, unavailable prices, or insufficient warm-up bars."},
    502: {"description": "Market-data download failed or returned malformed OHLCV data."},
    500: {"description": "Unexpected execution failure or invalid backtest result."},
})
def run_backtest(request: BacktestRequest) -> BacktestResponse:
    """Return actionable request/provider errors and log unexpected failures."""
    try:
        return run_backtest_by_request(request)

    except MarketDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValidationError as exc:
        # Response validation failures are server faults, not invalid requests.
        logger.exception("Invalid backtest result")
        raise HTTPException(
            status_code=500, detail="The backtest produced an invalid result. Please report the strategy and date range."
        ) from exc
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        ) from e
    except Exception as exc:
        logger.exception("Unexpected backtest failure")
        raise HTTPException(
            status_code=500,
            detail="The backtest failed unexpectedly. Please retry; if it persists, report the strategy and date range.",
        ) from exc
