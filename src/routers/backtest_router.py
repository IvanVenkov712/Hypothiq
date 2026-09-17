import fastapi
from pydantic import BaseModel

from dto.backtest_request import BacktestRequest
from dto.backtest_response import BacktestResponse
from services.backtest_service import run_backtest_by_request

router = fastapi.APIRouter(
    prefix='/backtests',
    tags=['backtests']
)

@router.get("run-backtest")
def run_backtest(request: BacktestRequest) -> BacktestResponse:
    return run_backtest_by_request(request)