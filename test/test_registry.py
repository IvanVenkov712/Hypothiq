import backtrader as bt
import pytest

from precoded_strategies.single_asset.buy_and_hold import BuyAndHold
from precoded_strategies.single_asset.ma_cross import MACrossOver
from registry import indicator_by_name, resolve_params, sizer_by_name, strategy_by_name


class ParentStrategy(bt.Strategy):
    params = dict(period=10, label="SMA", optional=None)


class ChildStrategy(ParentStrategy):
    params = dict(period=20, movav=bt.indicators.SMA)


class ClassParameterStrategy(bt.Strategy):
    params = dict(strategy=BuyAndHold, sizer=bt.sizers.FixedSize)


class IndicatorSizer(bt.Sizer):
    params = dict(indicator=bt.indicators.SMA)


@pytest.mark.parametrize("name", [
    "BollingerBreakout", "DonchianBreakout", "SimpleBollingerBandsBreakout",
    "BuyAndHold", "MACrossOver", "MeanReversion", "RSIStrategy",
])
def test_project_strategies(name):
    cls = strategy_by_name(name)
    assert issubclass(cls, bt.Strategy)
    assert cls.__name__ == name


@pytest.mark.parametrize("lookup, name, expected", [
    (strategy_by_name, "MACrossOver", MACrossOver),
    (sizer_by_name, "FixedSize", bt.sizers.FixedSize),
    (sizer_by_name, "SizerFix", bt.sizers.FixedSize),
    (sizer_by_name, "PercentSizer", bt.sizers.PercentSizer),
    (indicator_by_name, "MovingAverageSimple", bt.indicators.MovingAverageSimple),
    (indicator_by_name, "SMA", bt.indicators.SMA),
    (indicator_by_name, "EMA", bt.indicators.EMA),
])
def test_component_names_and_aliases(lookup, name, expected):
    assert lookup(name) is expected


@pytest.mark.parametrize("lookup", [strategy_by_name, sizer_by_name, indicator_by_name])
@pytest.mark.parametrize("name", [None, 42, [], "", "missing", "sma", "__name__", "os.system"])
def test_invalid_names_and_non_class_exports_are_rejected(lookup, name):
    with pytest.raises(ValueError):
        lookup(name)


def test_inherited_defaults_and_overrides():
    params = resolve_params(ChildStrategy, {"label": "EMA", "period": 5})
    assert params == dict(period=5, label="EMA", optional=None, movav=bt.indicators.SMA)
    assert resolve_params(ParentStrategy)["period"] == 10
    assert resolve_params(ChildStrategy)["period"] == 20


def test_defaults_for_all_component_categories():
    assert resolve_params(BuyAndHold) == {}
    assert resolve_params(bt.sizers.FixedSize) == dict(stake=1, tranches=1)
    params = resolve_params(bt.indicators.BollingerBands, {"period": 5})
    assert params["period"] == 5
    assert params["devfactor"] == 2.0
    assert params["movav"] is bt.indicators.MovingAverageSimple


@pytest.mark.parametrize("cls, name", [
    (MACrossOver, "movav"),
    (IndicatorSizer, "indicator"),
    (bt.indicators.BollingerBands, "movav"),
])
def test_indicator_class_parameters_on_each_component_category(cls, name):
    assert resolve_params(cls, {name: "EMA"})[name] is bt.indicators.EMA


def test_strategy_and_sizer_class_parameters():
    params = resolve_params(ClassParameterStrategy, {
        "strategy": "MACrossOver", "sizer": "PercentSizer",
    })
    assert params["strategy"] is MACrossOver
    assert params["sizer"] is bt.sizers.PercentSizer


def test_actual_classes_are_supported_for_python_callers():
    assert resolve_params(MACrossOver, {"movav": bt.indicators.EMA})["movav"] is bt.indicators.EMA


def test_inputs_and_defaults_are_not_modified():
    overrides = {"movav": "EMA", "fast": 3}
    params = resolve_params(MACrossOver, overrides)
    params["slow"] = 100
    assert overrides == {"movav": "EMA", "fast": 3}
    assert resolve_params(MACrossOver)["slow"] == 50
    assert MACrossOver.params.movav is bt.indicators.MovingAverageSimple


@pytest.mark.parametrize("cls", [MACrossOver, bt.sizers.FixedSize, bt.indicators.SMA])
def test_unknown_parameter_reports_component_and_parameter(cls):
    with pytest.raises(ValueError, match=f"'typo'.*{cls.__name__}"):
        resolve_params(cls, {"typo": 1})


@pytest.mark.parametrize("value", ["missing", "FixedSize", "", 12, None, {}, bt.sizers.FixedSize])
def test_invalid_class_override_reports_parameter_context(value):
    with pytest.raises(ValueError, match=r"MACrossOver\.movav"):
        resolve_params(MACrossOver, {"movav": value})


@pytest.mark.parametrize("value", [[], [("fast", 3)], "fast=3", 42])
def test_invalid_parameter_containers(value):
    with pytest.raises(TypeError, match="parameters must be a dictionary"):
        resolve_params(MACrossOver, value)


@pytest.mark.parametrize("value", [None, "MACrossOver", object, bt.sizers.FixedSize()])
def test_invalid_component(value):
    with pytest.raises(TypeError, match="Backtrader"):
        resolve_params(value)
