from copy import deepcopy
from unittest.mock import patch

import backtrader as bt
import pandas as pd
import pytest

from backtest import run_backtest_config
from precoded_strategies.single_asset.ma_cross import MACrossOver
from registry import indicator_by_name, resolve_params


@pytest.fixture
def frame():
    prices = [10, 11, 12, 13, 12, 11, 10, 9, 10, 11, 12, 13,
              14, 13, 12, 11, 10, 9, 10, 11, 12, 13, 12, 11]
    return pd.DataFrame(
        {"open": prices, "high": prices, "low": prices, "close": prices,
         "volume": 100},
        index=pd.date_range("2024-01-01", periods=len(prices)),
    )


@pytest.fixture
def config():
    return {
        "data": {"path": "prices.csv"},
        "strategy": {"name": "MACrossOver", "params": {
            "fast": 2, "slow": 3, "movav": "EMA",
        }},
        "sizer": {"name": "FixedSize", "params": {"stake": 2}},
    }


@pytest.mark.parametrize("stake", [None, 2], ids=["default-sizer", "configured-sizer"])
def test_configured_classes_and_parameters_execute_real_backtest(frame, config, stake):
    if stake is None:
        del config["sizer"]
    original = deepcopy(config)
    with patch("backtest.feed_from_conf", return_value=bt.feeds.PandasData(dataname=frame)):
        result = run_backtest_config(config)

    expected = bt.Cerebro()
    expected.adddata(bt.feeds.PandasData(dataname=frame))
    expected.addstrategy(MACrossOver, fast=2, slow=3, movav=bt.indicators.EMA)
    if stake is not None:
        expected.addsizer(bt.sizers.FixedSize, stake=stake)
    expected.broker.set_cash(10000)
    expected.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    strategy = expected.run()[0]

    assert result["end_cash"] == expected.broker.getcash()
    assert result["end_value"] == expected.broker.getvalue()
    assert result["total_return"] == 100 * (expected.broker.getvalue() / 10000 - 1)
    assert result["max_drawdown"] == strategy.analyzers.drawdown.get_analysis().max.drawdown
    assert result["closed_trades"] > 0
    assert result["end_value"] != result["start_cash"]
    assert config == original


def test_config_runner_resolves_indicator_names(frame, config):
    with patch("backtest.feed_from_conf", return_value=bt.feeds.PandasData(dataname=frame)):
        named = run_backtest_config(config)
    config["strategy"]["params"]["movav"] = bt.indicators.EMA
    with patch("backtest.feed_from_conf", return_value=bt.feeds.PandasData(dataname=frame)):
        direct = run_backtest_config(config)

    assert named == direct


@pytest.mark.parametrize("section, params", [
    ("strategy", {"movav": "missing"}),
    ("strategy", {"typo": 1}),
    ("sizer", {"typo": 1}),
])
def test_invalid_parameters_fail_before_loading_data(config, section, params):
    config[section]["params"] = params
    with patch("backtest.feed_from_conf") as load_feed:
        with pytest.raises(ValueError):
            run_backtest_config(config)
        load_feed.assert_not_called()


def test_omitted_parameters_and_no_closed_trades(frame, config):
    config["strategy"] = {"name": "BuyAndHold"}
    config["sizer"] = {"name": "FixedSize"}
    with patch("backtest.feed_from_conf", return_value=bt.feeds.PandasData(dataname=frame)):
        result = run_backtest_config(config)

    assert result["closed_trades"] == 0
    assert result["end_cash"] == 10000 - frame.open.iloc[1]


def test_no_trades_returns_zero_closed_trades(frame, config):
    config["sizer"]["params"]["stake"] = 0
    with patch("backtest.feed_from_conf", return_value=bt.feeds.PandasData(dataname=frame)):
        result = run_backtest_config(config)

    assert result["closed_trades"] == 0
    assert result["end_value"] == result["start_cash"]


def test_indicator_resolution_creates_requested_moving_average(frame):
    indicator_cls = indicator_by_name("BollingerBands")
    params = resolve_params(indicator_cls, {"period": 3, "movav": "EMA"})

    class IndicatorStrategy(bt.Strategy):
        def __init__(self):
            self.bands = indicator_cls(self.data, **params)
            self.expected = bt.indicators.EMA(self.data, period=3)

    cerebro = bt.Cerebro()
    cerebro.adddata(bt.feeds.PandasData(dataname=frame))
    cerebro.addstrategy(IndicatorStrategy)
    strategy = cerebro.run()[0]

    assert strategy.bands.mid[0] == strategy.expected[0]
    assert strategy.bands.p.movav is bt.indicators.EMA
