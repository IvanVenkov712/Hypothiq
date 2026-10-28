# HTTP API

The local API base URL is `http://127.0.0.1:8000`. FastAPI exposes interactive
documentation at `/docs`, alternate documentation at `/redoc`, and the generated
schema at `/openapi.json`. The generated schema is the detailed field reference.
The current API has no authentication.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Return `{"status":"ok"}`; does not check Yahoo connectivity. |
| `GET` | `/strategies` | List registered strategies with display and parameter metadata. |
| `POST` | `/backtests/run-backtest` | Download prices and synchronously execute a single-asset backtest. |

The frontend uses `/api/strategies`. Its development proxy removes `/api` before
forwarding the request; the backend routes themselves have no `/api` prefix.
The Docker Compose deployment uses Nginx for the same mapping. Its public API
base URL is `http://localhost:8080/api`; documentation is at `/api/docs` and
`/api/redoc`, and the schema is at `/api/openapi.json` on that origin.
The endpoint paths below are relative to the API base URL. See
[deployment](deployment.md) for setup and port configuration.

## Strategy catalogue

`GET /strategies` returns an array of definitions:

```json
[
  {
    "class_name": "BuyAndHold",
    "name": "Buy and hold",
    "description": "Buys once at the first eligible bar and holds the position.",
    "parameters": []
  }
]
```

This excerpt shows one entry; the endpoint returns all registered strategies.
Use `class_name` when submitting `strategy.name` in a backtest. Parameter
definitions include `name`, `label`, `description`, `type`, `default`, `nullable`,
`choices`, and inclusive or exclusive minimum/maximum fields. Choices are
objects with `value`, `label`, and `description`. Display the label and submit
the value; other registered indicator aliases may also be accepted by the API.
For example, the `movav` parameter is labeled “Moving average method” and
includes this option:

```json
{
  "value": "MovingAverageSimple",
  "label": "Simple moving average (SMA)",
  "description": "Gives equal weight to every value in the lookback window."
}
```

Options also include exponential (EMA) and Wilder's smoothed (SMMA) averages.
`default` remains an executable value, so an existing configuration can select
its matching option without converting a display label back into an identifier.
The execution API enforces parameter types and bounds. Choices remain suggested
options rather than an exhaustive list of indicator aliases.

## Run a backtest

In Swagger UI, expand `POST /backtests/run-backtest`, choose **Try it out**, and
submit, for example:

```json
{
  "strategy": {"name": "BuyAndHold"},
  "data_request": {
    "ticker": "AAPL",
    "start": "2024-01-01T00:00:00",
    "end": "2025-01-01T00:00:00",
    "interval": "1d"
  }
}
```

This downloads prices over the network. Yahoo's end date is exclusive. A request
uses one ticker and requires `strategy` and `data_request`. Omitted broker and
sizer fields use 10,000 starting cash, zero commission, no configured slippage,
and Backtrader's `FixedSize` sizer (default stake: one unit).

Only daily bars (`interval: "1d"`) are supported. `start` and `end` must be
timezone-free midnight datetimes, with `start < end`; the end is exclusive.
Supply one ticker of at most 30 characters, without whitespace or commas.

Strategy and sizer parameters use their declared names. Scalar parameter types
are strict: numeric strings and booleans are not accepted as numbers, and
integer parameters require integers. Numeric inputs must be finite. Strategy
lookback periods must be positive integers; the catalogue publishes their
minimums and other enforced bounds. Named indicator aliases remain supported.

Starting cash, commission multipliers, leverage, and supplied margin must be
positive. Commission, interest, and slippage must be nonnegative. Percentage
slippage is a fraction in `[0, 1]`; percentage commission is in `[0, 1]` when
`percabs` is true, or `[0, 100]` otherwise. Fixed commission amounts can exceed
one. `commtype` accepts Backtrader's `0` (percentage), `1` (fixed), or `null`
(infer from margin). `automargin` retains Backtrader's boolean or finite numeric
semantics, including negative values. If both slippage modes are supplied,
percentage slippage takes precedence.

Fixed sizers require a nonnegative integer stake and positive integer tranches;
percentage sizers accept `[0, 100]` and a boolean `retint`. Zero sizing is
allowed for no-trade runs. See `/docs` for the complete request schema.

The downloader relies on yfinance's DataFrame schema, column names, numeric
types, and daily timestamp formatting. It checks source-data values: OHLCV must
be finite and non-missing, prices positive, volume nonnegative, and High/Low
must enclose Open/Close. Unusable bars are rejected without repairing values or
filling gaps. Missing sessions and zero volume are allowed. Only bars in
`[start, end)` are processed.

The selected strategy must have enough downloaded bars to finish warm-up.
Backtrader computes the indicator requirement; `BollingerBreakout` additionally
needs its prior band-width lookback. Insufficient-data errors report the
required and available bar counts and suggest extending the range or reducing
lookbacks. Meeting the minimum permits evaluation, but does not guarantee a
signal or a fill before the end.

The response contains summary metrics and a typed `history` array:

| Field | Meaning and units |
| --- | --- |
| `start_cash` | Initial cash in the instrument's monetary units. |
| `end_cash` | Uninvested cash remaining at the end. |
| `end_value` | Final portfolio value, including open positions. |
| `total_return` | `100 * (end_value / start_cash - 1)`, expressed as a percentage. |
| `CAGR` | Annualized return percentage from Backtrader's Returns analyzer. |
| `sharpe` | Annualized Sharpe ratio using daily analysis and zero risk-free rate; `null` when undefined. |
| `closed_trades` | Number of closed trades; currently serialized as a number from a float-typed field. |
| `max_drawdown` | Maximum portfolio drawdown percentage. |
| `history` | One end-of-bar snapshot per processed bar, including indicator warm-up bars, in feed order. |

Each history point has these required fields. All numeric history values must
be finite; missing values, `NaN`, and infinities are not valid chart points.

| Field | Meaning and units |
| --- | --- |
| `time` | ISO 8601 datetime without a timezone, taken from the feed's bar label; for daily bars, for example, `2024-01-04T00:00:00`. |
| `close` | Instrument closing price from the same feed used by the engine, in price units. |
| `cash` | Uninvested broker cash after executions and costs processed for this bar. |
| `equity` | Total portfolio value, including open positions marked at this bar's close. |
| `drawdown` | Nonnegative percentage below the running peak equity: `100 * (peak - equity) / peak`. `5` means a 5% drawdown, and a new peak gives `0`. |

For example, after buying two units at 100 with no costs, a close at 90 can
produce this point for a portfolio that started with 1,000:

```json
{
  "time": "2024-01-04T00:00:00",
  "close": 90.0,
  "cash": 800.0,
  "equity": 980.0,
  "drawdown": 2.0
}
```

Snapshots represent end-of-bar account values. A market order submitted by a
strategy normally fills on the next bar, so its cash and equity effects appear
on that execution bar. Close prices inherit the download's adjustment policy;
they are not a separate raw-price series.

For daily charts, use the date portion of `time` as the trading-date label.
These labels are not local wall-clock instants and must not be shifted through
browser timezone conversion. History contains only processed feed bars, with
no synthetic points for weekends, missing sessions, or the requested start
date. `start_cash` is the separate initial baseline; the first history point
is the first processed bar, including when the strategy is still warming up.

The final point's `cash` and `equity` match `end_cash` and `end_value`;
the largest history drawdown matches `max_drawdown`. There is no forced final
liquidation, executed-trade list, saved result, or progress identifier.
The feed is explicitly configured as daily with compression one; see
[architecture assumptions](architecture.md#execution-and-data-assumptions).

## Errors

- **422**: Request validation failed, including unsupported intervals, unordered
  dates, timezone-aware or non-midnight dates, invalid tickers, or invalid broker
  numbers. `detail` is an array of errors with `type`, `loc`, and `msg`; rejected
  inputs are not echoed, so even non-finite JSON numbers produce a valid response.
- **400**: Unknown strategy, sizer, indicator, or parameter; invalid strategy/sizer
  values; no prices in the requested range; insufficient warm-up bars; or a
  strategy's own `ValueError`. `detail` is an actionable message string.
- **502**: The download raised an exception, returned no response, or supplied
  malformed OHLCV data. `detail` explains the provider problem and suggests retrying.
- **500**: Unexpected execution failures or invalid result models. `detail` is a
  generic message; exception details are logged on the server.

Non-422 errors retain the body `{"detail":"..."}`. Some provider failures are
reported by `yfinance` as empty tables; the 400 message therefore mentions both
ticker/date checks and possible provider unavailability. There are no automatic
retries or stable machine-readable application error codes.
