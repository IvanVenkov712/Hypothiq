import unittest

import backtrader as bt

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


class ClassLookupTests(unittest.TestCase):
    def test_project_strategies(self):
        for name in (
            "BollingerBreakout", "DonchianBreakout", "SimpleBollingerBandsBreakout",
            "BuyAndHold", "MACrossOver", "MeanReversion", "RSIStrategy",
        ):
            with self.subTest(name=name):
                cls = strategy_by_name(name)
                self.assertTrue(issubclass(cls, bt.Strategy))
                self.assertEqual(cls.__name__, name)
        self.assertIs(strategy_by_name("MACrossOver"), MACrossOver)

    def test_backtrader_names_and_aliases(self):
        self.assertIs(sizer_by_name("FixedSize"), bt.sizers.FixedSize)
        self.assertIs(sizer_by_name("SizerFix"), bt.sizers.FixedSize)
        self.assertIs(sizer_by_name("PercentSizer"), bt.sizers.PercentSizer)
        self.assertIs(
            indicator_by_name("MovingAverageSimple"), bt.indicators.MovingAverageSimple,
        )
        self.assertIs(indicator_by_name("SMA"), bt.indicators.SMA)
        self.assertIs(indicator_by_name("EMA"), bt.indicators.EMA)

    def test_invalid_names_and_non_class_exports_are_rejected(self):
        for lookup in (strategy_by_name, sizer_by_name, indicator_by_name):
            for name in (None, 42, [], "", "missing", "sma", "__name__", "os.system"):
                with self.subTest(lookup=lookup.__name__, name=name):
                    with self.assertRaises(ValueError):
                        lookup(name)


class ParameterResolutionTests(unittest.TestCase):
    def test_inherited_defaults_and_overrides(self):
        params = resolve_params(ChildStrategy, {"label": "EMA", "period": 5})
        self.assertEqual(params, dict(
            period=5, label="EMA", optional=None, movav=bt.indicators.SMA,
        ))
        self.assertEqual(resolve_params(ParentStrategy)["period"], 10)
        self.assertEqual(resolve_params(ChildStrategy)["period"], 20)

    def test_defaults_for_all_component_categories(self):
        self.assertEqual(resolve_params(BuyAndHold), {})
        self.assertEqual(resolve_params(bt.sizers.FixedSize), dict(stake=1, tranches=1))
        params = resolve_params(bt.indicators.BollingerBands, {"period": 5})
        self.assertEqual(params["period"], 5)
        self.assertEqual(params["devfactor"], 2.0)
        self.assertIs(params["movav"], bt.indicators.MovingAverageSimple)

    def test_indicator_class_parameters_on_each_component_category(self):
        for cls, name in (
            (MACrossOver, "movav"),
            (IndicatorSizer, "indicator"),
            (bt.indicators.BollingerBands, "movav"),
        ):
            with self.subTest(cls=cls.__name__):
                self.assertIs(resolve_params(cls, {name: "EMA"})[name], bt.indicators.EMA)

    def test_strategy_and_sizer_class_parameters(self):
        params = resolve_params(ClassParameterStrategy, {
            "strategy": "MACrossOver", "sizer": "PercentSizer",
        })
        self.assertIs(params["strategy"], MACrossOver)
        self.assertIs(params["sizer"], bt.sizers.PercentSizer)

    def test_actual_classes_are_supported_for_python_callers(self):
        self.assertIs(
            resolve_params(MACrossOver, {"movav": bt.indicators.EMA})["movav"],
            bt.indicators.EMA,
        )

    def test_inputs_and_defaults_are_not_modified(self):
        overrides = {"movav": "EMA", "fast": 3}
        params = resolve_params(MACrossOver, overrides)
        params["slow"] = 100
        self.assertEqual(overrides, {"movav": "EMA", "fast": 3})
        self.assertEqual(resolve_params(MACrossOver)["slow"], 50)
        self.assertIs(MACrossOver.params.movav, bt.indicators.MovingAverageSimple)

    def test_unknown_parameter_reports_component_and_parameter(self):
        for cls in (MACrossOver, bt.sizers.FixedSize, bt.indicators.SMA):
            with self.subTest(cls=cls.__name__):
                with self.assertRaisesRegex(ValueError, f"'typo'.*{cls.__name__}"):
                    resolve_params(cls, {"typo": 1})

    def test_invalid_class_override_reports_parameter_context(self):
        for value in ("missing", "FixedSize", "", 12, None, {}, bt.sizers.FixedSize):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, r"MACrossOver\.movav"):
                    resolve_params(MACrossOver, {"movav": value})

    def test_invalid_parameter_containers(self):
        for value in ([], [("fast", 3)], "fast=3", 42):
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "parameters must be a dictionary"):
                    resolve_params(MACrossOver, value)

    def test_invalid_component(self):
        for value in (None, "MACrossOver", object, bt.sizers.FixedSize()):
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "Backtrader"):
                    resolve_params(value)


if __name__ == "__main__":
    unittest.main()
