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
Bounds describe strategy constraints and do not add API validation.

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

Strategy and sizer parameters use their declared names. Starting cash must be
positive. If both percentage and fixed slippage are supplied, percentage
slippage takes precedence. See `/docs` for the complete request schema.

The response contains only aggregate metrics:

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

There is no forced final liquidation, trade list, equity series, saved result,
or progress identifier in this response. Annualization for non-daily intervals
has not been validated; see [architecture assumptions](architecture.md#execution-and-data-assumptions).

## Errors and current validation limits

- **422**: Pydantic request validation failed, such as a missing required field,
  invalid datetime, or non-positive starting cash.
- **400**: Execution raised `ValueError`. Examples include an unknown strategy,
  sizer, indicator, or parameter name; missing/empty data; or a strategy's own
  parameter validation. The body contains `{"detail":"..."}`.
- **500**: Other unhandled download, engine, or serialization errors.

The service does not yet provide comprehensive date-order, interval, numeric
strategy-parameter, or OHLCV validation. Some invalid requests can therefore
reach the engine and fail as server errors. Errors are not yet a stable set of
machine-readable application codes.
