"""Describe registered strategies without instantiating them or loading market data."""

import re
from typing import Any

import backtrader as bt

from dto.strategy_response import ParameterDefinition, StrategyDefinition
from services.registry import registered_strategies, resolve_params


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
    (
        bt.indicators.MovingAverageSimple,
        "Simple moving average (SMA)",
        "Gives equal weight to every value in the lookback window.",
    ),
    (
        bt.indicators.ExponentialMovingAverage,
        "Exponential moving average (EMA)",
        "Gives more weight to recent values, responding faster to changes than an SMA of the same period.",
    ),
    (
        bt.indicators.SmoothedMovingAverage,
        "Wilder's smoothed moving average (SMMA)",
        "Uses Wilder's smoothing, with a weight of 1 / period for each new value. This is the standard RSI smoothing method.",
    ),
)

_COMMON_PARAMETER_METADATA: dict[str, dict[str, Any]] = {
    "movav": {
        "label": "Moving average method",
        "description": "How values are averaged over the selected lookback period.",
    },
    "devfactor": {
        "label": "Band width (standard deviations)",
        "type": "number",
        "description": "Distance from the middle band to each outer band, measured in standard deviations.",
    },
}

# Only information that cannot be read reliably from declared defaults belongs here.
# Bounds describe existing strategy validation; they do not add execution rules.
_PARAMETER_METADATA: dict[str, dict[str, dict[str, Any]]] = {
    "MACrossOver": {
        "fast": {
            "label": "Fast moving average period (bars)",
            "description": "Number of bars used by the faster moving average.",
        },
        "slow": {
            "label": "Slow moving average period (bars)",
            "description": "Number of bars used by the slower moving average.",
        },
    },
    "MeanReversion": {
        "period": {
            "label": "Moving average period (bars)",
            "description": "Number of bars used to calculate the reference moving average.",
        },
        "multiplier": {
            "label": "Entry price multiplier",
            "description": "Buy when the close is below this multiple of the moving average. For example, 0.95 means 5% below it.",
        },
    },
    "DonchianBreakout": {
        "entry_period": {
            "label": "Entry channel lookback (bars)",
            "description": "Buy above the highest high of these prior bars; the current bar is excluded.",
        },
        "exit_period": {
            "label": "Exit channel lookback (bars)",
            "description": "Close below the lowest low of these prior bars; the current bar is excluded.",
        },
    },
    "SimpleBollingerBandsBreakout": {
        "period": {
            "label": "Bollinger band period (bars)",
            "description": "Number of bars used to calculate the middle band and price standard deviation.",
        },
    },
    "RSIStrategy": {
        "lower": {
            "label": "RSI buy threshold",
            "type": "number",
            "description": "Buy when the RSI falls below this value on its 0 to 100 scale.",
        },
        "upper": {
            "label": "RSI exit threshold",
            "type": "number",
            "description": "Close the position when the RSI rises above this value on its 0 to 100 scale.",
        },
        "period": {
            "label": "RSI lookback period (bars)",
            "description": "Number of bars used to smooth gains and losses when calculating RSI.",
        },
        "movav": {"description": "Smoothing method used for the RSI's average gains and losses."},
    },
    "BollingerBreakout": {
        "period": {
            "label": "Bollinger band period (bars)",
            "description": "Number of bars used to calculate the middle band and price standard deviation.",
            "minimum": 2,
        },
        "devfactor": {"exclusive_minimum": 0},
        "squeeze_lookback": {
            "label": "Squeeze reference window (bars)",
            "description": "Number of prior band widths used to determine whether the current bands are unusually narrow.",
            "minimum": 2,
        },
        "squeeze_quantile": {
            "label": "Squeeze threshold (quantile)",
            "description": "Band-width quantile from 0 to 1. For example, 0.2 identifies widths in the lowest 20% of the reference window.",
            "minimum": 0, "maximum": 1,
        },
        "squeeze_bars": {
            "label": "Squeeze confirmation (bars)",
            "description": "Consecutive narrow-band bars required to confirm a squeeze.",
            "minimum": 1,
        },
        "entry_window": {
            "label": "Breakout entry window (bars)",
            "description": "Number of bars after a squeeze during which a breakout can trigger an entry.",
            "minimum": 1,
        },
        "expansion_rate": {
            "label": "Minimum band expansion (fraction)",
            "description": "Required band-width growth from the previous bar. For example, 0.05 means 5% growth.",
            "exclusive_minimum": 0,
        },
        "contraction_bars": {
            "label": "Contraction confirmation (bars)",
            "description": "Consecutive decreases in band width required to confirm contraction.",
            "minimum": 1,
        },
        "exit_on_contraction": {
            "label": "Exit when bands contract",
            "description": "Close the position when band contraction is confirmed.",
        },
        "stop_loss": {
            "label": "Closing-price loss limit (fraction)",
            "nullable": True,
            "exclusive_minimum": 0,
            "exclusive_maximum": 1,
            "description": (
                "Adverse closing-price fraction relative to the average fill; "
                "0.05 means 5%. Null disables this exit. This is not a resting stop order."
            ),
        },
        "allow_short": {
            "label": "Allow short selling",
            "description": "Allow short entries on downward breakouts. When disabled, the strategy only opens long positions.",
        },
        "record_history": {
            "label": "Record indicator history",
            "description": "Keep per-bar indicator and signal history during the run. This history is not included in the current results response.",
        },
        "printlog": {
            "label": "Log order events",
            "description": "Write order status changes to the server log during the run.",
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
                    choices = [
                        {
                            "value": default.__name__ if issubclass(default, indicator) else indicator.__name__,
                            "label": label,
                            "description": description,
                        }
                        for indicator, label, description in _MOVING_AVERAGES
                    ]
                    if not any(choice["value"] == default.__name__ for choice in choices):
                        choices.insert(0, {
                            "value": default.__name__,
                            "label": re.sub(r"(?<=[a-z])(?=[A-Z])", " ", default.__name__),
                        })
                    definition["choices"] = choices
            elif isinstance(default, bool):
                definition["type"] = "boolean"
            elif isinstance(default, int):
                definition["type"] = "integer"
            elif isinstance(default, float):
                definition["type"] = "number"
            elif isinstance(default, str):
                definition["type"] = "string"
            definition.update(_COMMON_PARAMETER_METADATA.get(name, {}))
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
