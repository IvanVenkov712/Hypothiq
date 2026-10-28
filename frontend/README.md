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
summary metrics, equity and drawdown charts, loading feedback, and API errors.
Percentage inputs use human units: `0.1` means 0.1%.

The responsive SVG charts share a trading-day inspector: hover or drag across
either plot, tap on a touchscreen, or use the labeled slider with keyboard
arrows and Home/End. Exact close, cash, equity, and drawdown values appear
below the plots. The equity chart includes a dashed initial-cash reference;
drawdown uses positive percentage values plotted downward from zero. Flat and
single-bar histories remain visible. Empty history displays a message while
keeping summary metrics. Daily labels preserve the feed's date without browser
timezone conversion or synthetic points. Executed-trade histories are planned.
See the [history contract](../docs/api.md#run-a-backtest) for snapshot timing
and units. Charts use React and native SVG, with no charting dependency.

Parameter labels explain their role and units. Moving-average dropdowns display
SMA, EMA, and Wilder's smoothing with explanations, while submitting the API's
executable choice values. The catalogue uses the same readable option labels.
See the [project README](../README.md) for full installation instructions,
[architecture](../docs/architecture.md) for the request flow, and
[roadmap](../docs/roadmap.md) for implementation status.

## Local development

With the backend project installed in `backend/.venv` (including its declared
`uvicorn` dependency), start
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
`frontend/Dockerfile` builds this bundle in a Node.js build stage, then serves it
with Nginx using `nginx.conf`. Nginx routes same-origin `/api/*` requests to the
backend with `/api` removed and falls back to `index.html` for frontend routes
such as `/strategies` and `/backtesting`. Missing `/assets/*` files return 404.
The development proxy is not included in the static bundle. Run the frontend
and backend together with Docker Compose from the repository root:

```powershell
docker compose up --build -d --wait
```

Open <http://localhost:8080>. See [deployment](../docs/deployment.md) for
configuration and verification. `npm run preview` is only a local bundle preview;
it does not supply the production API proxy.

Run `npm run lint` for Oxlint checks and `npm test` for Playwright browser tests.
Tests start Vite on port 4173 and mock catalogue/backtest HTTP responses, so
neither the backend nor Yahoo access is needed. Windows uses installed Microsoft
Edge in headless mode; macOS/Linux use Playwright Chromium (install it once
with `npx playwright install chromium`). Tests cover date inspection, pointer,
keyboard and touch input, narrow layouts, flat/single-bar/empty histories,
negative equity, drawdown above 100%, and reruns. Desktop and mobile screenshots
are written to the ignored `test-results/` directory. Playwright is a development
dependency for exercising actual SVG layout and browser interactions.
See the [development guide](../docs/development.md) for integration checks
and troubleshooting.
