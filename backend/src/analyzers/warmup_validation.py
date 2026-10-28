"""Reject runs that cannot finish their strategy's indicator warm-up."""

import backtrader as bt

from precoded_strategies.single_asset.bollinger_breakout import BollingerBreakout


class WarmupValidation(bt.Analyzer):
    """Check preloaded daily bars before Backtrader evaluates its indicators."""

    def start(self):
        # Backtrader computes this after constructing the indicator graph and
        # before starting analyzers, so aliases and nested averages are covered.
        required = self.strategy._minperiod
        if isinstance(self.strategy, BollingerBreakout):
            # This strategy collects prior widths inside next(), outside the
            # indicator graph, before it can evaluate its first signal.
            required += self.strategy.p.squeeze_lookback
        available = self.data.buflen()
        if available < required:
            raise ValueError(
                f"{type(self.strategy).__name__} requires at least {required} daily bars "
                f"to finish warm-up; received {available}. "
                "Choose an earlier start date or reduce the strategy lookback periods."
            )
