from copy import deepcopy
import unittest
from unittest.mock import patch

import backtrader as bt
import pandas as pd

from backtest import run_backtest_config, run_backtest_single_asset
from precoded_strategies.single_asset.ma_cross import MACrossOver
from registry import indicator_by_name, resolve_params


class BacktestParameterTests(unittest.TestCase):
    def setUp(self):
        prices = [10, 11, 12, 13, 12, 11, 10, 9, 10, 11, 12, 13,
                  14, 13, 12, 11, 10, 9, 10, 11, 12, 13, 12, 11]
        self.frame = pd.DataFrame(
            {"open": prices, "high": prices, "low": prices, "close": prices,
             "volume": 100},
            index=pd.date_range("2024-01-01", periods=len(prices)),
        )
        self.config = {
            "data": {"path": "prices.csv"},
            "strategy": {"name": "MACrossOver", "params": {
                "fast": 2, "slow": 3, "movav": "EMA",
            }},
            "sizer": {"name": "FixedSize", "params": {"stake": 2}},
        }

    def test_configured_classes_and_parameters_execute_real_backtest(self):
        original = deepcopy(self.config)
        with patch("backtest.feed_from_conf", return_value=bt.feeds.PandasData(
            dataname=self.frame,
        )):
            result = run_backtest_config(self.config)
        expected = run_backtest_single_asset(
            self.frame, MACrossOver,
            strategy_params=dict(fast=2, slow=3, movav=bt.indicators.EMA),
            sizer_params=dict(stake=2),
        )
        for key in ("end_cash", "end_value", "total_return", "max_drawdown"):
            self.assertEqual(result[key], expected[key])
        self.assertGreater(result["closed_trades"], 0)
        self.assertNotEqual(result["end_value"], result["start_cash"])
        self.assertEqual(self.config, original)

    def test_python_runner_resolves_indicator_names(self):
        named = run_backtest_single_asset(
            self.frame, MACrossOver, strategy_params=dict(fast=2, slow=3, movav="EMA"),
        )
        direct = run_backtest_single_asset(
            self.frame, MACrossOver,
            strategy_params=dict(fast=2, slow=3, movav=bt.indicators.EMA),
        )
        self.assertEqual(named, direct)

    def test_config_uses_default_sizer_when_omitted(self):
        del self.config["sizer"]
        with patch("backtest.feed_from_conf", return_value=bt.feeds.PandasData(
            dataname=self.frame,
        )):
            result = run_backtest_config(self.config)
        expected = run_backtest_single_asset(
            self.frame, MACrossOver, strategy_params=self.config["strategy"]["params"],
        )
        self.assertEqual(result["end_value"], expected["end_value"])

    def test_invalid_parameters_fail_before_loading_data(self):
        for section, params in (
            ("strategy", {"movav": "missing"}),
            ("strategy", {"typo": 1}),
            ("sizer", {"typo": 1}),
        ):
            with self.subTest(section=section, params=params):
                config = deepcopy(self.config)
                config[section]["params"] = params
                with patch("backtest.feed_from_conf") as load_feed:
                    with self.assertRaises(ValueError):
                        run_backtest_config(config)
                    load_feed.assert_not_called()

    def test_omitted_parameters_and_no_closed_trades(self):
        self.config["strategy"] = {"name": "BuyAndHold"}
        self.config["sizer"] = {"name": "FixedSize"}
        with patch("backtest.feed_from_conf", return_value=bt.feeds.PandasData(
            dataname=self.frame,
        )):
            result = run_backtest_config(self.config)
        self.assertEqual(result["closed_trades"], 0)
        self.assertEqual(result["end_cash"], 10000 - self.frame.open.iloc[1])

    def test_no_trades_returns_zero_closed_trades(self):
        self.config["sizer"]["params"]["stake"] = 0
        with patch("backtest.feed_from_conf", return_value=bt.feeds.PandasData(
            dataname=self.frame,
        )):
            result = run_backtest_config(self.config)
        self.assertEqual(result["closed_trades"], 0)
        self.assertEqual(result["end_value"], result["start_cash"])

    def test_indicator_resolution_creates_requested_moving_average(self):
        indicator_cls = indicator_by_name("BollingerBands")
        params = resolve_params(indicator_cls, {"period": 3, "movav": "EMA"})

        class IndicatorStrategy(bt.Strategy):
            def __init__(self):
                self.bands = indicator_cls(self.data, **params)
                self.expected = bt.indicators.EMA(self.data, period=3)

        cerebro = bt.Cerebro()
        cerebro.adddata(bt.feeds.PandasData(dataname=self.frame))
        cerebro.addstrategy(IndicatorStrategy)
        strategy = cerebro.run()[0]
        self.assertEqual(strategy.bands.mid[0], strategy.expected[0])
        self.assertIs(strategy.bands.p.movav, bt.indicators.EMA)


if __name__ == "__main__":
    unittest.main()
