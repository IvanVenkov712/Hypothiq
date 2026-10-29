"""FastAPI entry point for strategy discovery and synchronous backtests."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from routers.backtest_router import backtests_router
from routers.strategy_router import strategies_router

app = FastAPI()
app.include_router(backtests_router)
app.include_router(strategies_router)


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError):
    """Keep field locations/messages without echoing non-JSON numeric inputs."""
    # NaN and Infinity can be parsed from request JSON, but cannot be serialized
    # by the default validation response when it echoes the rejected input.
    return JSONResponse(status_code=422, content={
        "detail": [
            {key: error[key] for key in ("type", "loc", "msg")}
            for error in exc.errors()
        ],
    })

@app.get("/health")
def health():
    """Report API liveness without checking the external market-data provider."""
    return {"status": "ok"}
