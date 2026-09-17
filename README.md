# Hypothiq

Backtrader configuration uses exact, case-sensitive class names:

```yaml
strategy:
  name: MACrossOver
  params:
    fast: 10
    slow: 30
    movav: ExponentialMovingAverage
sizer:
  name: FixedSize
  params:
    stake: 5
```

These sections can be passed to `run_backtest_config` alongside its `data` and
optional `broker` configuration. The supported strategy names are `BuyAndHold`,
`MACrossOver`, `MeanReversion`, `RSIStrategy`, `DonchianBreakout`,
`SimpleBollingerBandsBreakout`, and `BollingerBreakout`. Sizers and indicators
use names exported by `backtrader.sizers` and `backtrader.indicators`, including
indicator aliases such as `SMA` and `EMA`. Names are not module paths.

`registry.resolve_params(cls, overrides=None)` returns a new dictionary containing
the class's declared defaults (including inherited parameters) and supplied
overrides. Both backtest runners use it for strategy and sizer parameters.
Unknown parameter names and unknown class names raise `ValueError` before data
is loaded by the configuration runner.

A parameter whose default is a Backtrader strategy, sizer, or indicator class
accepts a name from the corresponding category. Python callers can also supply
the class itself. Ordinary values, including strings and `None`, are preserved;
numeric ranges and other domain constraints remain the component's responsibility.
The resolver does not instantiate classes or mutate the supplied dictionary or
class defaults. Use it directly when constructing indicators:

```python
from registry import indicator_by_name, resolve_params

indicator = indicator_by_name("BollingerBands")
params = resolve_params(indicator, {"period": 10, "movav": "EMA"})
# Inside a strategy's __init__:
bands = indicator(self.data, **params)
```

Run the tests from the repository root with the project virtual environment
(PowerShell):

```powershell
.venv/Scripts/python.exe -m pip install pytest
.venv/Scripts/python.exe -m pytest
```
