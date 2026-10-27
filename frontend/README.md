# Hypothiq frontend

The React + TypeScript frontend displays the live strategy catalogue from the
FastAPI backend. Search by strategy name, identifier, description, or parameter.
Expand a strategy to inspect its parameter types, default values,
suggested choices, nullability, and published bounds.

The home page at `/` explains the platform and links to the catalogue at
`/strategies` and backtesting at `/backtesting`. Shared navigation is available
on every page. A catalogue strategy's “Backtest this strategy” link preselects it.

The backtesting form uses live parameter metadata and accepts a ticker, date
range (exclusive end), initial cash, fixed or percentage sizing, commission,
and percentage or fixed slippage. It submits daily-bar backtests and displays
summary metrics, loading feedback, and API errors. Percentage inputs use human
units: `0.1` means 0.1%. Equity curves and trade histories are planned.

Parameter labels explain their role and units. Moving-average dropdowns display
SMA, EMA, and Wilder's smoothing with explanations, while submitting the API's
executable choice values. The catalogue uses the same readable option labels.
See the [project README](../README.md) for full installation instructions,
[architecture](../docs/architecture.md) for the request flow, and
[roadmap](../docs/roadmap.md) for implementation status.

## Local development

With the backend dependencies and `uvicorn` installed in `backend/.venv`, start
the API from the repository root:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend/src
```

In a second terminal, start the frontend:

```powershell
cd frontend
npm ci
npm run dev
```

Open the URL printed by Vite, normally `http://localhost:5173`.
Vite proxies `/api/*` to `http://127.0.0.1:8000/*`, so no
development CORS configuration is needed. Strategy data comes exclusively from
the backend; the page handles loading, errors with retry, and empty results.

## Build

```powershell
npm run build
```

This runs TypeScript checks and writes the production bundle to `dist/`.
Production deployment assumes a reverse proxy, most likely Nginx, serving the
frontend assets and routing same-origin `/api/*` requests to the backend with
the `/api` prefix removed. Frontend routes such as `/strategies` and
`/backtesting` must fall back to `index.html`. The proxy choice remains open; see the
[deployment assumptions](../docs/architecture.md#deployment-assumptions).
The development proxy is not included in the static bundle.

Run `npm run lint` for Oxlint checks. There is no frontend automated test script
yet. See the [development guide](../docs/development.md) for integration checks
and troubleshooting.
