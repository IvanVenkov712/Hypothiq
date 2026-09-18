import fastapi
from fastapi import HTTPException
from pydantic import BaseModel

from dto.backtest_request import BacktestRequest
from dto.backtest_response import BacktestResponse
from services.backtest_service import run_backtest_by_request

backtests_router = fastapi.APIRouter(
    prefix='/backtests',
    tags=['backtests']
)

@backtests_router.post("run-backtest", response_model=BacktestResponse)
def run_backtest(request: BacktestRequest) -> BacktestResponse:
    try:
        return run_backtest_by_request(request)

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )