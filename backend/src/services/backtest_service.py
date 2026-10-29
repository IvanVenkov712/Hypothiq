"""Coordinate parameter checks, data loading, and one Backtrader run."""

import backtrader as bt

from analyzers.backtest_result import BacktestResult
from analyzers.warmup_validation import WarmupValidation
from dto.backtest_request import BacktestRequest
from dto.backtest_response import BacktestResponse
from services.market_data import get_data_y_finance
from services.parameter_validation import validate_sizer_params, validate_strategy_params
from services.registry import resolve_params, sizer_by_name, strategy_by_name


def run_backtest_by_request(request: BacktestRequest) -> BacktestResponse:
    """Run one validated daily backtest with a fresh engine.

    Parameter errors fail before downloading prices. Percentage slippage takes
    precedence over fixed slippage. Final equity includes open positions.
    """
    strategy = strategy_by_name(request.strategy.name)
    strategy_params = resolve_params(strategy, request.strategy.params)
    sizer = sizer_by_name(request.sizer.name)
    sizer_params = resolve_params(sizer, request.sizer.params)
    validate_strategy_params(strategy, strategy_params)
    validate_sizer_params(sizer, sizer_params)
    cerebro = bt.Cerebro()

    cerebro.adddata(get_data_y_finance(request.data_request))
    cerebro.addstrategy(strategy, **strategy_params)
    cerebro.addsizer(sizer, **sizer_params)

    cerebro.broker.set_cash(request.broker.cash)

    if request.broker.slippage_perc is not None:
        cerebro.broker.set_slippage_perc(
            **request.broker.slippage_perc.model_dump()
        )
    elif request.broker.slippage_fixed is not None:
        cerebro.broker.set_slippage_fixed(
            **request.broker.slippage_fixed.model_dump()
        )

    cerebro.broker.setcommission(**request.broker.commission.model_dump())

    cerebro.addanalyzer(WarmupValidation)
    cerebro.addanalyzer(BacktestResult, _name="results")

    strategy_result = cerebro.run()[0]
    analysis = strategy_result.analyzers.results.get_analysis()
    return BacktestResponse.model_validate(analysis)
