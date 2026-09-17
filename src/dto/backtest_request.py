from datetime import datetime
from typing import Any
from pydantic import BaseModel


class StrategyRequest(BaseModel):
    name: str
    params: dict[str, Any] = {}

class SizerRequest(BaseModel):
    name: str = 'FixedSize'
    params: dict[str, Any] = {}

class SlippagePercentRequest(BaseModel):
    perc: float = 0.0
    slip_open: bool = True
    slip_limit: bool = True
    slip_match: bool = True
    slip_out: bool = False

class SlippageFixedRequest(BaseModel):
    fixed: float = 0.0
    slip_open: bool = True
    slip_limit: bool = True
    slip_match: bool = True
    slip_out: bool = False

class CommissionRequest(BaseModel):
    commission: float = 0.0
    margin: float | None = None
    mult: float = 1.0
    commtype: int | None = None
    percabs: bool = True
    stocklike: bool = False
    interest: float = 0.0
    interest_long: bool = False
    leverage: float = 1.0
    automargin: bool | float = False
    name: str | None = None

class BrokerRequest(BaseModel):
    cash: float = 10_000
    slippage_perc: SlippagePercentRequest | None = None
    slippage_fixed: SlippageFixedRequest | None = None
    commission: CommissionRequest = CommissionRequest()

class BacktestRequest(BaseModel):
    strategy: StrategyRequest
    fromdate: datetime | None = None
    todate: datetime | None = None
    broker: BrokerRequest = BrokerRequest()
    sizer: SizerRequest = SizerRequest()
