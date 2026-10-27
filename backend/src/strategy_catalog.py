"""Describe registered strategies without instantiating them or loading market data."""

from typing import Any

import backtrader as bt

from dto.strategy_response import ParameterDefinition, StrategyDefinition
from registry import registered_strategies, resolve_params


_DISPLAY_NAMES = {
    "BuyAndHold": "Buy and hold",
    "MACrossOver": "Moving average crossover",
    "MeanReversion": "Mean reversion",
    "RSIStrategy": "RSI strategy",
    "DonchianBreakout": "Donchian breakout",
    "SimpleBollingerBandsBreakout": "Simple Bollinger bands breakout",
    "BollingerBreakout": "Bollinger squeeze breakout",
}


_DESCRIPTIONS = {
    "BuyAndHold": "Buys once at the first eligible bar and holds the position.",
    "MACrossOver": (
        "Enters when the fast moving average crosses above the slow moving average "
        "and exits when it crosses below."
    ),
    "MeanReversion": (
        "Buys below a multiplier of the moving average and exits at the moving average."
    ),
    "RSIStrategy": "Buys below the lower RSI threshold and exits above the upper threshold.",
    "DonchianBreakout": (
        "Buys above the prior entry-period high and exits below the prior exit-period low."
    ),
    "SimpleBollingerBandsBreakout": (
        "Buys above the upper Bollinger band and sells below the lower band."
    ),
    "BollingerBreakout": (
        "Trades expanding Bollinger-band breakouts following a squeeze, with optional "
        "short entries and contraction or close-based loss exits."
    ),
}

_MOVING_AVERAGES = (
    "MovingAverageSimple",
    "ExponentialMovingAverage",
    "SmoothedMovingAverage",
)

# Only information that cannot be read reliably from declared defaults belongs here.
# Bounds describe existing strategy validation; they do not add execution rules.
_PARAMETER_METADATA: dict[str, dict[str, dict[str, Any]]] = {
    "SimpleBollingerBandsBreakout": {
        "devfactor": {"type": "number"},
    },
    "RSIStrategy": {
        "lower": {"label": "Lower RSI threshold", "type": "number"},
        "upper": {"label": "Upper RSI threshold", "type": "number"},
    },
    "BollingerBreakout": {
        "period": {"minimum": 2},
        "devfactor": {"exclusive_minimum": 0},
        "squeeze_lookback": {"minimum": 2},
        "squeeze_quantile": {"minimum": 0, "maximum": 1},
        "squeeze_bars": {"minimum": 1},
        "entry_window": {"minimum": 1},
        "expansion_rate": {"exclusive_minimum": 0},
        "contraction_bars": {"minimum": 1},
        "stop_loss": {
            "nullable": True,
            "exclusive_minimum": 0,
            "exclusive_maximum": 1,
            "description": (
                "Adverse closing-price fraction relative to the average fill; "
                "0.05 means 5%. Null disables this exit. This is not a resting stop order."
            ),
        },
    },
}


def get_strategy_catalog() -> list[StrategyDefinition]:
    """Combine live defaults with optional descriptions and parameter metadata.

    Choices are suggested form options, not an exhaustive list of accepted aliases.
    Unknown default types need an explicit type in the parameter metadata.
    """
    strategies = []
    for strategy in registered_strategies():
        metadata = _PARAMETER_METADATA.get(strategy.__name__, {})
        parameters = []
        for name, default in resolve_params(strategy).items():
            definition: dict[str, Any] = {
                "name": name,
                "label": name.replace("_", " ").capitalize(),
                "default": default,
                "nullable": default is None,
            }
            if isinstance(default, type) and issubclass(default, bt.Indicator):
                definition.update(type="string", default=default.__name__)
                if name == "movav":
                    definition["choices"] = list(dict.fromkeys(
                        (default.__name__, *_MOVING_AVERAGES)
                    ))
            elif isinstance(default, bool):
                definition["type"] = "boolean"
            elif isinstance(default, int):
                definition["type"] = "integer"
            elif isinstance(default, float):
                definition["type"] = "number"
            elif isinstance(default, str):
                definition["type"] = "string"
            definition.update(metadata.get(name, {}))
            if "type" not in definition:
                raise ValueError(
                    f"{strategy.__name__}.{name} needs explicit parameter type metadata"
                )
            parameters.append(ParameterDefinition(**definition))
        strategies.append(StrategyDefinition(
            class_name=strategy.__name__,
            name=_DISPLAY_NAMES.get(strategy.__name__, strategy.__name__),
            description=_DESCRIPTIONS.get(strategy.__name__, strategy.__doc__ or ""),
            parameters=parameters,
        ))
    return strategies
