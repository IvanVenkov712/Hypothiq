"""Resolve configured Backtrader classes and their declared parameters."""

from typing import Any

import backtrader as bt

from precoded_strategies.single_asset.bollinger_breakout import BollingerBreakout
from precoded_strategies.single_asset.breakout import (
    DonchianBreakout,
    SimpleBollingerBandsBreakout,
)
from precoded_strategies.single_asset.buy_and_hold import BuyAndHold
from precoded_strategies.single_asset.ma_cross import MACrossOver
from precoded_strategies.single_asset.mean_reversion import MeanReversion
from precoded_strategies.single_asset.rsi_strategy import RSIStrategy


_STRATEGIES = {
    cls.__name__: cls
    for cls in (
        BollingerBreakout,
        DonchianBreakout,
        SimpleBollingerBandsBreakout,
        BuyAndHold,
        MACrossOver,
        MeanReversion,
        RSIStrategy,
    )
}


def _class_by_name(name: str, namespace: dict[str, Any], base: type) -> type:
    if not isinstance(name, str) or not name:
        raise ValueError(f"{base.__name__} name must be a non-empty string")
    cls = namespace.get(name)
    if not isinstance(cls, type) or not issubclass(cls, base):
        raise ValueError(f"Unknown {base.__name__} name: {name!r}")
    return cls


def strategy_by_name(name: str) -> type[bt.Strategy]:
    """Look up a project strategy by its exact class name."""
    return _class_by_name(name, _STRATEGIES, bt.Strategy)


def sizer_by_name(name: str) -> type[bt.Sizer]:
    """Look up a sizer exported by Backtrader, including its aliases."""
    return _class_by_name(name, vars(bt.sizers), bt.Sizer)


def indicator_by_name(name: str) -> type[bt.Indicator]:
    """Look up an indicator exported by Backtrader, including its aliases."""
    return _class_by_name(name, vars(bt.indicators), bt.Indicator)


def resolve_params(cls: type, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Merge declared defaults with overrides without instantiating the class.

    Inherited parameters are included. Defaults that are strategy, sizer, or
    indicator classes identify class-valued parameters: overrides must be names
    in the corresponding namespace or actual classes of the same category.
    Ordinary values are passed through; their domain validation belongs to the
    component itself. Neither overrides nor the class's defaults are modified.
    """
    if not isinstance(cls, type) or not issubclass(
        cls, (bt.Strategy, bt.Sizer, bt.Indicator)
    ):
        raise TypeError("Expected a Backtrader strategy, sizer, or indicator class")
    if overrides is None:
        overrides = {}
    if not isinstance(overrides, dict):
        raise TypeError(f"{cls.__name__} parameters must be a dictionary")

    resolved = dict(cls.params._getitems())
    for name, value in overrides.items():
        if name not in resolved:
            raise ValueError(f"Unknown parameter {name!r} for {cls.__name__}")
        default = resolved[name]
        if isinstance(default, type):
            for base, lookup in (
                (bt.Strategy, strategy_by_name),
                (bt.Sizer, sizer_by_name),
                (bt.Indicator, indicator_by_name),
            ):
                if issubclass(default, base):
                    if isinstance(value, str):
                        try:
                            value = lookup(value)
                        except ValueError as exc:
                            raise ValueError(f"{cls.__name__}.{name}: {exc}") from exc
                    if not isinstance(value, type) or not issubclass(value, base):
                        raise ValueError(
                            f"{cls.__name__}.{name} must be a {base.__name__} "
                            "class or a registered name"
                        )
                    break
        resolved[name] = value
    return resolved
