# Hypothiq frontend

The React + TypeScript frontend displays the live strategy catalogue from the
FastAPI backend. Search by strategy name, identifier, description, or parameter.
Expand a strategy to inspect its parameter types, default values,
suggested choices, nullability, and published bounds.

## Local development

With the backend dependencies and `uvicorn` installed in `backend/.venv`, start
the API from the repository root:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend/src
```

In a second terminal, start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite, normally `http://localhost:5173`.
Vite proxies `/api/strategies` to `http://127.0.0.1:8000/strategies`, so no
development CORS configuration is needed. Strategy data comes exclusively from
the backend; the page handles loading, errors with retry, and empty results.

## Build

```powershell
npm run build
```

This runs TypeScript checks and writes the production bundle to `dist/`.
Production hosting must route `/api/*` to the backend with the `/api` prefix
removed, alongside serving the frontend assets. The development proxy is not
included in the static bundle.
