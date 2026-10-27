# Development guide

Follow the [root quickstart](../README.md#install-and-run-locally) to create
`backend/.venv`, install dependencies, and run both applications. The documented
development baseline is Python 3.13 and Node.js 24 with npm. The backend does not
declare a supported Python-version range or a dependency lockfile yet.

## Working directories

Backend project metadata and pytest settings live in `backend/pyproject.toml`.
Run Python installation and test commands from `backend`, and npm commands from
`frontend`. The backend source uses top-level imports from `src`; Uvicorn's
`--app-dir src` and pytest's configured `pythonpath` make those imports available.

From the repository root, the API can also be started with:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend/src --reload
```

For standalone Python scripts that import backend modules, run from `backend`
with `$env:PYTHONPATH = "src"` in PowerShell, or `PYTHONPATH=src` on macOS/Linux.
The API and test commands above do not require setting this variable.

## Checks

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Tests cover file readers, name/parameter resolution, catalogue metadata and its
HTTP response, broker settings and metric mapping, missing downloads, and RSI
behavior on flat or one-directional prices. Market-data downloads are mocked;
tests do not need Yahoo access. Dedicated tests do not yet cover every strategy.

From `frontend`:

```powershell
npm run lint
npm run build
```

Lint uses Oxlint. The build runs TypeScript checks followed by Vite bundling.
There is no frontend automated test script yet. For a manual integration check,
start both servers and verify catalogue loading, search, expanded parameter
details, and retry after an API outage. An API test run can be submitted through
`http://127.0.0.1:8000/docs`; this requires network access for prices.

## Adding a predefined strategy

1. Add a `bt.Strategy` subclass under
   `backend/src/precoded_strategies/single_asset/`. Declare Backtrader `params`
   and document signal rules, execution assumptions, and any constraints.
2. Import and add the class to `_STRATEGIES` in `backend/src/registry.py`.
   Merely adding a Python file does not register it.
3. Add a display name and description in `strategy_catalog.py` when useful.
   Unspecified display names fall back to the class name and descriptions to
   the class docstring. Defaults and inherited parameters are discovered
   from the class rather than duplicated in metadata.
4. Supply `_PARAMETER_METADATA` when a type cannot be inferred, for example for a
   `None` default, or when bounds, labels, or numeric type overrides are needed.
   Enforce actual domain constraints in the strategy; catalogue bounds do not
   enforce them during execution.
5. Test signal and order behavior with small deterministic data and verify that
   catalogue defaults round-trip through the registry. Avoid live price downloads
   in automated tests.

If the public API shape changes, update Pydantic DTOs, the frontend interfaces in
`frontend/src/api/strategies.ts`, the affected UI, and [API documentation](api.md)
together.

## Production frontend build

`npm run build` writes static assets to `frontend/dist/`. `npm run preview`
provides a local build preview; it is not a production deployment setup. Only the
development server has an explicitly configured API proxy.

Production hosting must serve the static assets and route `/api/*` to FastAPI,
stripping `/api`. The backend currently neither serves the frontend bundle nor
configures CORS. No working production container or deployment recipe is included;
`backend/Dockerfile` is a placeholder.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Imports such as `routers` fail | Use `--app-dir` relative to your working directory; run pytest from `backend`. |
| Catalogue is unavailable | Check `GET http://127.0.0.1:8000/health`, API logs, and that Vite can reach port 8000. |
| Catalogue works but backtesting fails | Inspect API error details; Yahoo availability, symbol/date/interval combinations, and indicator warm-up requirements affect execution. |
| Browser requests fail after deployment | Configure the production `/api` reverse proxy; the development proxy is not bundled. |
| PowerShell blocks activation scripts | Use the virtual environment's Python executable directly, as in the quickstart; activation is unnecessary. |
