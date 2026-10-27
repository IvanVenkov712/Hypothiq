import asyncio
import json
from unittest.mock import patch

import backtrader as bt
import pytest

import services.registry as registry
import services.strategy_catalog as strategy_catalog
from main import app
from precoded_strategies.single_asset.ma_cross import MACrossOver
from services.registry import registered_strategies, resolve_params, strategy_by_name
from services.strategy_catalog import get_strategy_catalog


def test_catalog_covers_registered_strategies_and_declared_defaults():
    definitions = get_strategy_catalog()

    assert {item.class_name for item in definitions} == {
        strategy.__name__ for strategy in registered_strategies()
    }
    for definition in definitions:
        strategy = strategy_by_name(definition.class_name)
        defaults = resolve_params(strategy)
        assert definition.name
        assert definition.description
        assert [parameter.name for parameter in definition.parameters] == list(defaults)
        submitted = {parameter.name: parameter.default for parameter in definition.parameters}
        assert resolve_params(strategy, submitted) == defaults
        for parameter in definition.parameters:
            assert parameter.label
            if parameter.choices is not None:
                assert parameter.default in [choice.value for choice in parameter.choices]
                for choice in parameter.choices:
                    assert choice.label
                    resolve_params(strategy, {parameter.name: choice.value})


def test_buy_and_hold_has_no_parameters():
    definition = next(item for item in get_strategy_catalog() if item.class_name == "BuyAndHold")
    assert definition.parameters == []


def test_display_name_is_distinct_from_the_executable_class_name():
    definition = next(item for item in get_strategy_catalog() if item.class_name == "MACrossOver")

    payload = json.loads(definition.model_dump_json())
    assert payload["class_name"] == "MACrossOver"
    assert payload["name"] == "Moving average crossover"
    assert strategy_by_name(payload["class_name"]) is MACrossOver


def test_catalog_reflects_updated_strategy_declarations(monkeypatch):
    get_strategy_catalog()

    class UpdatedMACrossOver(MACrossOver):
        params = dict(fast=8)

    monkeypatch.setattr(strategy_catalog, "registered_strategies", lambda: (UpdatedMACrossOver,))
    definition = get_strategy_catalog()[0]
    fast = next(parameter for parameter in definition.parameters if parameter.name == "fast")
    assert fast.default == 8


def test_new_strategies_and_inherited_parameters_are_discovered_without_metadata(monkeypatch):
    class Parent(bt.Strategy):
        params = dict(period=10, enabled=True, label="EMA", ratio=0.5)

    class Child(Parent):
        """An automatically discovered strategy."""

        params = dict(period=20, movav=bt.indicators.SMA)

        def __init__(self):
            raise AssertionError("Catalogue discovery must not instantiate strategies")

    monkeypatch.setitem(registry._STRATEGIES, "Child", Child)
    definition = next(item for item in get_strategy_catalog() if item.class_name == "Child")
    parameters = {parameter.name: parameter for parameter in definition.parameters}

    assert definition.description == Child.__doc__
    assert definition.name == "Child"
    assert parameters["period"].default == 20
    assert parameters["period"].type == "integer"
    assert parameters["enabled"].type == "boolean"
    assert parameters["label"].type == "string"
    assert parameters["label"].default == "EMA"
    assert parameters["ratio"].type == "number"
    assert parameters["movav"].default == "SMA"
    assert "SMA" in [choice.value for choice in parameters["movav"].choices]
    assert len(parameters["movav"].choices) == 3
    assert next(choice for choice in parameters["movav"].choices if choice.value == "SMA").label == "Simple moving average (SMA)"


def test_explicit_numeric_type_can_override_an_integer_default():
    definition = next(
        item for item in get_strategy_catalog() if item.class_name == "SimpleBollingerBandsBreakout"
    )
    parameter = next(item for item in definition.parameters if item.name == "devfactor")
    assert parameter.default == 2
    assert parameter.type == "number"


def test_bollinger_constraints_and_nullable_loss_threshold():
    definition = next(item for item in get_strategy_catalog() if item.class_name == "BollingerBreakout")
    parameters = {parameter.name: parameter for parameter in definition.parameters}

    assert parameters["period"].minimum == 2
    assert parameters["squeeze_quantile"].minimum == 0
    assert parameters["squeeze_quantile"].maximum == 1
    assert parameters["expansion_rate"].exclusive_minimum == 0
    assert parameters["stop_loss"].type == "number"
    assert parameters["stop_loss"].default == 0.05
    assert parameters["stop_loss"].nullable is True
    assert parameters["stop_loss"].exclusive_minimum == 0
    assert parameters["stop_loss"].exclusive_maximum == 1
    assert parameters["allow_short"].nullable is False


def test_null_default_requires_explicit_type_metadata(monkeypatch):
    class OptionalParameter(bt.Strategy):
        params = dict(optional=None)

    monkeypatch.setitem(registry._STRATEGIES, "OptionalParameter", OptionalParameter)
    with pytest.raises(ValueError, match=r"OptionalParameter\.optional.*explicit.*type"):
        get_strategy_catalog()

    monkeypatch.setitem(strategy_catalog._PARAMETER_METADATA, "OptionalParameter", {
        "optional": {"type": "number"},
    })
    definition = next(item for item in get_strategy_catalog() if item.class_name == "OptionalParameter")
    parameter = definition.parameters[0]
    assert parameter.default is None
    assert parameter.nullable is True
    assert parameter.type == "number"
    assert json.loads(definition.model_dump_json())["parameters"][0]["default"] is None


def test_metadata_only_refers_to_existing_parameters():
    for name, metadata in strategy_catalog._PARAMETER_METADATA.items():
        assert metadata.keys() <= resolve_params(strategy_by_name(name)).keys()


def test_results_are_independent_and_do_not_change_strategy_defaults():
    original = resolve_params(MACrossOver)
    first = next(item for item in get_strategy_catalog() if item.class_name == "MACrossOver")
    moving_average = next(item for item in first.parameters if item.name == "movav")
    moving_average.choices.clear()
    moving_average.default = "changed"

    second = next(item for item in get_strategy_catalog() if item.class_name == "MACrossOver")
    moving_average = next(item for item in second.parameters if item.name == "movav")
    assert moving_average.default == "MovingAverageSimple"
    assert "ExponentialMovingAverage" in [choice.value for choice in moving_average.choices]
    assert resolve_params(MACrossOver) == original


@pytest.mark.parametrize("strategy_name", [
    "MACrossOver", "MeanReversion", "RSIStrategy", "SimpleBollingerBandsBreakout",
])
def test_moving_average_options_have_readable_labels_and_executable_values(strategy_name):
    strategy = strategy_by_name(strategy_name)
    definition = next(item for item in get_strategy_catalog() if item.class_name == strategy_name)
    parameter = next(item for item in definition.parameters if item.name == "movav")

    assert parameter.label == "Moving average method"
    assert [choice.label for choice in parameter.choices] == [
        "Simple moving average (SMA)",
        "Exponential moving average (EMA)",
        "Wilder's smoothed moving average (SMMA)",
    ]
    assert len({choice.value for choice in parameter.choices}) == 3
    for choice, indicator in zip(parameter.choices, (
        bt.indicators.MovingAverageSimple,
        bt.indicators.ExponentialMovingAverage,
        bt.indicators.SmoothedMovingAverage,
    )):
        assert choice.description
        assert resolve_params(strategy, {"movav": choice.value})["movav"] is indicator

    payload = json.loads(definition.model_dump_json())
    moving_average = next(item for item in payload["parameters"] if item["name"] == "movav")
    assert moving_average["choices"][0]["label"] == "Simple moving average (SMA)"
    assert moving_average["choices"][0]["value"] == "MovingAverageSimple"


def test_registered_parameters_have_explanations_and_contextual_labels():
    definitions = {item.class_name: item for item in get_strategy_catalog()}
    for definition in definitions.values():
        for parameter in definition.parameters:
            assert parameter.description, f"{definition.class_name}.{parameter.name} needs an explanation"

    expected_labels = {
        ("MACrossOver", "fast"): "Fast moving average period (bars)",
        ("MACrossOver", "slow"): "Slow moving average period (bars)",
        ("RSIStrategy", "period"): "RSI lookback period (bars)",
        ("SimpleBollingerBandsBreakout", "devfactor"): "Band width (standard deviations)",
        ("BollingerBreakout", "printlog"): "Log order events",
    }
    for (strategy_name, parameter_name), label in expected_labels.items():
        parameter = next(item for item in definitions[strategy_name].parameters if item.name == parameter_name)
        assert parameter.label == label


def test_get_strategies_returns_json_without_running_a_backtest():
    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/strategies",
        "root_path": "",
        "query_string": b"",
        "headers": [],
    }
    with (
        patch("backtrader.Cerebro", side_effect=AssertionError("Unexpected backtest")),
        patch("yfinance.download", side_effect=AssertionError("Unexpected download")),
    ):
        asyncio.run(app(scope, receive, send))

    assert messages[0]["status"] == 200
    assert (b"content-type", b"application/json") in messages[0]["headers"]
    body = b"".join(message.get("body", b"") for message in messages[1:])
    assert json.loads(body) == [item.model_dump(mode="json") for item in get_strategy_catalog()]
    assert "get" in app.openapi()["paths"]["/strategies"]
