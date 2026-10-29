"""Validate resolved strategy and sizer values before requesting market data."""

from math import isfinite
from typing import Any

import backtrader as bt

from services.strategy_catalog import get_strategy_parameters


def validate_strategy_params(strategy: type[bt.Strategy], params: dict[str, Any]) -> None:
    """Check resolved scalar values against published catalogue types and bounds."""
    scalar_types = {"integer": (int,), "number": (int, float), "boolean": (bool,), "string": (str,)}
    for parameter in get_strategy_parameters(strategy):
        value = params[parameter.name]
        if value is None and parameter.nullable:
            continue
        # Class parameters have already been checked and resolved by the registry.
        if isinstance(value, type) and issubclass(value, bt.Indicator):
            continue
        name = f"{strategy.__name__}.{parameter.name}"
        if type(value) not in scalar_types[parameter.type]:
            raise ValueError(f"{name}: expected {parameter.type}")
        if isinstance(value, float) and not isfinite(value):
            raise ValueError(f"{name}: must be finite")
        if parameter.minimum is not None and value < parameter.minimum:
            raise ValueError(f"{name}: must be >= {parameter.minimum}")
        if parameter.maximum is not None and value > parameter.maximum:
            raise ValueError(f"{name}: must be <= {parameter.maximum}")
        if parameter.exclusive_minimum is not None and value <= parameter.exclusive_minimum:
            raise ValueError(f"{name}: must be > {parameter.exclusive_minimum}")
        if parameter.exclusive_maximum is not None and value >= parameter.exclusive_maximum:
            raise ValueError(f"{name}: must be < {parameter.exclusive_maximum}")


def validate_sizer_params(sizer: type[bt.Sizer], params: dict[str, Any]) -> None:
    """Check resolved parameters of Backtrader's fixed and percentage sizers."""
    for name, value in params.items():
        if name == "retint":
            valid = type(value) is bool
            requirement = "a boolean"
        elif name == "percents":
            valid = type(value) in (int, float) and 0 <= value <= 100
            requirement = "a number between 0 and 100"
        else:
            minimum = 1 if name == "tranches" else 0
            valid = type(value) is int and value >= minimum
            requirement = f"an integer >= {minimum}"
        if not valid:
            raise ValueError(f"{sizer.__name__}.{name}: must be {requirement}")
