"""HTTP input contracts for daily data, capital, and execution costs."""

from datetime import datetime
from typing import Annotated, Any, Literal, Self
from pydantic import BaseModel, Field, FiniteFloat, NaiveDatetime, field_validator, model_validator


class StrategyRequest(BaseModel):
    """Select a strategy by registry identifier and override declared parameters."""

    name: str
    params: dict[str, Any] = {}

class SizerRequest(BaseModel):
    """Select a Backtrader sizer; omitted settings use FixedSize defaults."""

    name: str = 'FixedSize'
    params: dict[str, Any] = {}

class DataRequest(BaseModel):
    """Request daily bars for one ticker between naive midnights; end is exclusive."""

    ticker: str = Field(min_length=1, max_length=30, pattern=r"^[^\s,]+$")
    start: NaiveDatetime
    end: NaiveDatetime
    interval: Literal["1d"] = "1d"

    @field_validator("start", "end")
    @classmethod
    def daily_boundary(cls, value: datetime) -> datetime:
        if value.time() != datetime.min.time():
            raise ValueError("Daily date boundaries must be at midnight, without a timezone")
        return value

    @model_validator(mode="after")
    def ordered_dates(self) -> Self:
        if self.start >= self.end:
            raise ValueError("The end date must be after the start date (end is exclusive)")
        return self

class SlippagePercentRequest(BaseModel):
    """Pass percentage slippage and bar-matching flags to the Backtrader broker."""

    perc: FiniteFloat = Field(default=0.0, ge=0, le=1, strict=True)
    slip_open: bool = True
    slip_limit: bool = True
    slip_match: bool = True
    slip_out: bool = False

class SlippageFixedRequest(BaseModel):
    """Pass slippage in price units and matching flags to the Backtrader broker."""

    fixed: FiniteFloat = Field(default=0.0, ge=0, strict=True)
    slip_open: bool = True
    slip_limit: bool = True
    slip_match: bool = True
    slip_out: bool = False

class CommissionRequest(BaseModel):
    """Validate costs while retaining Backtrader's percentage/fixed commission modes."""

    commission: FiniteFloat = Field(default=0.0, ge=0, strict=True)
    margin: Annotated[FiniteFloat, Field(gt=0, strict=True)] | None = None
    mult: FiniteFloat = Field(default=1.0, gt=0, strict=True)
    commtype: Annotated[int, Field(strict=True, ge=0, le=1)] | None = None
    percabs: bool = True
    stocklike: bool = False
    interest: FiniteFloat = Field(default=0.0, ge=0, strict=True)
    interest_long: bool = False
    leverage: FiniteFloat = Field(default=1.0, gt=0, strict=True)
    automargin: Annotated[bool, Field(strict=True)] | Annotated[FiniteFloat, Field(strict=True)] = False
    name: str | None = None

    @model_validator(mode="after")
    def percentage_cost(self) -> Self:
        # Backtrader infers percentage mode when neither commtype nor margin is set.
        percentage = self.commtype == 0 or (self.commtype is None and self.margin is None)
        maximum = 1 if self.percabs else 100
        if percentage and self.commission > maximum:
            raise ValueError(f"Percentage commission must be between 0 and {maximum}")
        return self

class BrokerRequest(BaseModel):
    """Set positive initial cash and costs; percentage slippage takes precedence."""

    cash: FiniteFloat = Field(
        default=10000, gt=0, strict=True,
        title="The initial cash for the backtest", description='Cash must be finite and greater than 0'
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
