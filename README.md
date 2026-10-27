# Hypothiq

Hypothiq runs Backtrader strategies against historical prices downloaded through
`yfinance`. Backtests accept a `BacktestRequest` through
`services.backtest_service.run_backtest_by_request` or the HTTP endpoint
`POST /backtests/run-backtest`.

Use the project virtual environment from the repository root (PowerShell):

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install ".[test]"
$env:PYTHONPATH = "src"
```

For a YAML configuration, save the following as `config.yaml`. Strategy, sizer,
and indicator names are exact and case-sensitive:

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
data_request:
  ticker: AAPL
  start: "2024-01-01"
  end: "2025-01-01"
  interval: 1d
broker:
  cash: 10000
```

Load and validate the configuration before running a backtest:

```python
from config import read_file_config
from dto.backtest_request import BacktestRequest
from services.backtest_service import run_backtest_by_request

request = BacktestRequest.model_validate(read_file_config("config.yaml"))
result = run_backtest_by_request(request)
print(result.model_dump_json(indent=2))
```

JSON configuration files are also supported. The same request structure can be
sent as a JSON body to the HTTP endpoint. To serve the API, install the optional
ASGI server and start it from the repository root:

```powershell
.venv/Scripts/python.exe -m pip install uvicorn
.venv/Scripts/python.exe -m uvicorn main:app --app-dir src
```

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.
Requests use one `data_request.ticker` symbol. `strategy` and `data_request` are
required; `broker` and `sizer` have defaults. Starting cash must be positive.
Yahoo's download end date is exclusive.

Results include starting cash, ending cash, ending portfolio value, total return,
annualized return (`CAGR`), Sharpe ratio, closed trades, and maximum drawdown.
Returns and drawdown are percentages; Sharpe can be `null` when undefined.

The supported strategy names are `BuyAndHold`,
`MACrossOver`, `MeanReversion`, `RSIStrategy`, `DonchianBreakout`,
`SimpleBollingerBandsBreakout`, and `BollingerBreakout`. Sizers and indicators
use names exported by `backtrader.sizers` and `backtrader.indicators`, including
indicator aliases such as `SMA` and `EMA`. Names are not module paths.

`registry.resolve_params(cls, overrides=None)` returns a new dictionary containing
the class's declared defaults (including inherited parameters) and supplied
overrides. The backtest service uses it for strategy and sizer parameters.
Unknown parameter names and unknown class names raise `ValueError` before data
is downloaded.

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

Tests mock market-data downloads and do not require Yahoo access.
