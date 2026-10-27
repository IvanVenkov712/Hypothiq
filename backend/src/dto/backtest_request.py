"""HTTP input models; strategy-specific domain checks belong to strategies."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class StrategyRequest(BaseModel):
    """Select a strategy by registry identifier and override declared parameters."""

    name: str
    params: dict[str, Any] = {}

class SizerRequest(BaseModel):
    """Select a Backtrader sizer; omitted settings use FixedSize defaults."""

    name: str = 'FixedSize'
    params: dict[str, Any] = {}

class DataRequest(BaseModel):
    """Request one Yahoo ticker and date window, with an exclusive download end.

    Interval validity and date ordering are not checked by this model.
    """

    ticker: str
    start: datetime
    end: datetime
    interval: str = "1d"

class SlippagePercentRequest(BaseModel):
    """Pass percentage slippage and bar-matching flags to the Backtrader broker."""

    perc: float = 0.0
    slip_open: bool = True
    slip_limit: bool = True
    slip_match: bool = True
    slip_out: bool = False

class SlippageFixedRequest(BaseModel):
    """Pass slippage in price units and matching flags to the Backtrader broker."""

    fixed: float = 0.0
    slip_open: bool = True
    slip_limit: bool = True
    slip_match: bool = True
    slip_out: bool = False

class CommissionRequest(BaseModel):
    """Mirror Backtrader broker commission options without changing their semantics."""

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
    """Set positive initial cash and costs; percentage slippage takes precedence."""

    cash: float = Field(
        default=10000, gt=0, title="The initial cash for the backtest", description='Cash must be greater than 0'
    )
    slippage_perc: SlippagePercentRequest | None = None
    slippage_fixed: SlippageFixedRequest | None = None
    commission: CommissionRequest = CommissionRequest()

class BacktestRequest(BaseModel):
    """Describe one synchronous, single-asset run with default broker and sizer."""

    strategy: StrategyRequest
    data_request: DataRequest
    broker: BrokerRequest = BrokerRequest()
    sizer: SizerRequest = SizerRequest()
