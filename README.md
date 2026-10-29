# Hypothiq

Hypothiq is a platform for researching, sharing, creating, and testing algorithmic
trading strategies. This defines the intended product scope; strategy creation
and sharing are planned capabilities. The current implementation focuses on
historical backtesting: its Python API runs predefined Backtrader strategies
against Yahoo Finance prices and returns performance metrics. The React
interface provides a searchable strategy catalogue and a backtesting workspace.

The project is partway through its first MVP. Running backtests is available
through the API and browser, with summary metrics and interactive equity and
drawdown charts after each run. Trade visualizations are planned. Hypothiq
focuses on research, with no live trading integration.

## What works today

- Browse and search the live strategy catalogue, expand parameter definitions,
  and inspect defaults, suggested values, nullability, and published bounds.
- Start from the home page, browse `/strategies`, and configure a daily-bar
  backtest at `/backtesting`, including strategy parameters and execution costs.
- Run a single-asset backtest through FastAPI using historical OHLCV data
  downloaded with `yfinance`.
- Validate daily requests, strategy/sizing parameters, market-data quality, and
  available warm-up bars, with actionable validation and provider errors.
- Choose a registered strategy and Backtrader position sizer; apply initial cash,
  commissions, and percentage or fixed slippage.
- Receive starting and ending cash, ending portfolio value, total return,
  annualized return, Sharpe ratio, closed-trade count, and maximum drawdown.
- Receive typed per-bar close, cash, equity, and drawdown history through the API,
  including indicator warm-up bars.
- Inspect equity and drawdown charts in the browser with a shared date inspector
  and an initial-cash reference line.
- Run backend tests without contacting Yahoo Finance.

The seven registered strategies are `BuyAndHold`, `MACrossOver`,
`MeanReversion`, `RSIStrategy`, `DonchianBreakout`,
`SimpleBollingerBandsBreakout`, and `BollingerBreakout`.

## Install and run locally

Use Python 3.13 and Node.js 24 with npm as a development baseline. Backend
dependencies are declared in `backend/pyproject.toml`; the frontend uses
`frontend/package-lock.json`. Internet access is needed to install dependencies
and download prices for a backtest. Browsing the catalogue does not download prices.

The following commands use PowerShell. From the repository root, install and
start the backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install ".[test]"
.\.venv\Scripts\python.exe -m uvicorn main:app --app-dir src --reload
```

In a second terminal, start the frontend from the repository root:

```powershell
cd frontend
npm ci
npm run dev
```

Open the URL printed by Vite, normally <http://localhost:5173>. The API listens
at <http://127.0.0.1:8000>; interactive API documentation is at
<http://127.0.0.1:8000/docs>. Use `POST /backtests/run-backtest` there to run a
backtest. `GET /health` should return `{"status":"ok"}`.

On macOS/Linux, use `.venv/bin/python` in place of
`.\.venv\Scripts\python.exe`. No database, account setup, or API key is currently
required. See [development](docs/development.md) for checks and troubleshooting.

## Deploy with Docker Compose

Install Docker with the Compose plugin and start its Linux container engine.
From the repository root:

```powershell
docker compose up --build -d --wait
```

`docker compose up` creates and starts the services defined in `docker-compose.yaml`:

- `--build` builds the images before starting the containers, reusing cached layers where possible.
- `-d` (detached mode) runs the containers in the background.
- `--wait` waits until the services are running or healthy before returning;
  both services here have health checks, so it waits for those checks to pass.

`--wait` already implies detached mode; `-d` makes that behavior explicit.
See the [Docker Compose command reference](https://docs.docker.com/reference/cli/docker/compose/up/).

Open <http://localhost:8080>. Nginx serves the frontend and proxies `/api/*`
to the private backend. API documentation is at <http://localhost:8080/api/docs>.
Python and Node.js are installed inside the build images; host installations
are only needed for local development. See [deployment](docs/deployment.md) for
port configuration, verification, updates, logs, and HTTPS setup.

## Architecture

The React/TypeScript frontend calls a FastAPI backend. A strategy registry and
catalogue provide strategy identities and parameter metadata. The backtest
service downloads prices, creates a fresh Backtrader engine for each request,
applies broker settings, and maps analyzer output to a JSON response.

The Docker Compose deployment uses Nginx to serve the built frontend and
forward same-origin `/api/*` requests to the backend with `/api` removed.
Only Nginx publishes a host port; Uvicorn runs on the internal Compose network.

Backtests run synchronously in the API process. Results are returned to the
caller without persistent storage. See [architecture](docs/architecture.md) for
the component diagram, request flows, and current limitations.

## Plans and next features

The immediate goal is to complete the single-asset MVP:
return executed-trade histories and add a trade list and benchmark alongside
the existing charts. Later phases cover strategy
comparison, multi-asset portfolios, accounts and strategy sharing, and AI-assisted
strategy generation. See the [roadmap](docs/roadmap.md) for completed work and
completion criteria.

## Documentation

- [Architecture](docs/architecture.md): components, boundaries, and execution flow.
- [Development](docs/development.md): workflow, checks, builds, and strategy additions.
- [Deployment](docs/deployment.md): Docker Compose, Nginx routing, and operations.
- [HTTP API](docs/api.md): endpoints, an example request, result units, and errors.
- [Roadmap](docs/roadmap.md): current status and future phases.
- [Frontend](frontend/README.md): catalogue behavior and frontend commands.

The project is distributed under the [MIT license](LICENSE).
