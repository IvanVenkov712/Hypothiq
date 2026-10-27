# Deployment

The repository includes a two-container deployment. The frontend image builds
the React application with Node.js 24 and runs Nginx to serve the resulting
assets and reverse-proxy API requests. The backend image uses Python 3.13 and
runs FastAPI with Uvicorn as a non-root user. No database, API key, or persistent
volume is required.

```text
Browser -> host:8080 -> frontend (Nginx :80)
                         /          -> built React assets
                         /api/*     -> backend (Uvicorn :8000), /api removed
```

Only Nginx publishes a host port. Both services share Compose's default network;
the backend retains outbound network access to download prices from Yahoo
Finance. The browser always uses the Nginx origin, so CORS configuration and a
build-time API URL are unnecessary.

## Build and start

Install Docker Engine with Docker Compose v2.20 or newer (or Docker Desktop
using Linux containers). Start the Docker engine, then run from the repository
root:

```powershell
docker compose config --quiet
docker compose up --build -d --wait
docker compose ps
```

The first build needs internet access to pull base images and install Python
and npm dependencies. The frontend uses `npm ci` and the committed lockfile.
The backend installs dependencies from `backend/pyproject.toml`, including
Uvicorn; Python dependencies do not yet have a lockfile. Build contexts exclude
local virtual environments, `node_modules`, caches, and unrelated files.

Open <http://localhost:8080> or the Docker host's address on port 8080. Compose
waits for a successful backend `/health` check before starting Nginx. Both
containers have health checks and restart with `unless-stopped`; Docker does
not automatically restart a running container just because it is unhealthy.

Set `HTTP_PORT` to change the published port. For example, in PowerShell:

```powershell
$env:HTTP_PORT = "80"
docker compose up --build -d --wait
```

In a POSIX shell, use `HTTP_PORT=80 docker compose up --build -d --wait`.
Alternatively, create a root `.env` file containing `HTTP_PORT=80`. Use the same
port setting for subsequent Compose commands. The default binding listens on
all host interfaces; restrict network access as appropriate for the host.

## Routing and API documentation

| Public path | Handling |
| --- | --- |
| `/`, `/strategies`, `/backtesting` | Built frontend, with `index.html` fallback for page navigation. |
| `/assets/*` | Built assets; missing files return 404. |
| `/api/health` | Backend `/health`. |
| `/api/strategies` | Backend strategy catalogue. |
| `/api/backtests/run-backtest` | Backend synchronous backtest endpoint. |
| `/api/docs`, `/api/redoc`, `/api/openapi.json` | FastAPI documentation and schema. |

Nginx's API location uses a trailing slash in `proxy_pass` to replace `/api/`
with `/`, as described in the [Nginx proxy documentation](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass).
Uvicorn's `--root-path /api` supplies the public prefix for generated schema and
documentation URLs; see [FastAPI behind a proxy](https://fastapi.tiangolo.com/advanced/behind-a-proxy/).
The backend trusts forwarded headers on the private Compose network. Nginx
sets the client address and scheme and preserves the public Host header,
including a non-default port, for backend redirects.

Nginx waits up to 300 seconds between reads from the backend to accommodate
synchronous downloads and backtests. A timeout returns 504; it does not cancel
work already running in the backend. This is not a background-job deployment.
Nginx uses Docker DNS with a 10-second refresh to follow backend container
replacement; its upstream uses [Nginx's dynamic resolution](https://nginx.org/en/docs/http/ngx_http_upstream_module.html#server).

## Verify the deployment

From the repository root, with the containers running:

```powershell
Invoke-RestMethod http://localhost:8080/api/health
python -m unittest discover -s tests/deployment -v
```

On macOS/Linux, use `curl -f http://localhost:8080/api/health` and `python3`
instead of `python` if needed. The health response is `{"status":"ok"}`.
Python is needed on the host only for the smoke tests, which use the standard
library. For a different origin, set the test URL first:

```powershell
$env:HYPOTHIQ_URL = "http://localhost:80"
python -m unittest discover -s tests/deployment -v
```

The suite checks frontend deep links and built assets, API health and catalogue
JSON, Swagger's public schema URL, OpenAPI's `/api` server, redirects with the
public host and prefix, invalid and unknown-strategy backtest requests, and
missing API/asset paths. No
test downloads prices. To verify a real backtest, open `/backtesting` in the
browser and submit a run, or use the example in the [API reference](api.md)
through `/api/docs`. This requires Yahoo Finance access.

## Logs, updates, and shutdown

```powershell
docker compose logs -f frontend backend
docker compose exec frontend nginx -t
```

After updating the source, rebuild and recreate the services:

```powershell
docker compose up --build -d --wait
```

To refresh base images and rebuild all dependency layers:

```powershell
docker compose build --pull --no-cache
docker compose up -d --wait
```

There is no zero-downtime update guarantee. Rerun the smoke tests after an
update. Stop and remove the containers and Compose network with:

```powershell
docker compose down
```

Backtest results are returned to callers without persistent storage. Container
recreation may also discard transient provider caches; no application data
volume needs migration or backup in the current implementation.

## Public HTTPS

The supplied Compose file exposes HTTP. For public HTTPS, configure Nginx with
the deployment's domain and certificate: adapt `frontend/nginx.conf` with a TLS
listener on 443 and an HTTP-to-HTTPS redirect, mount the certificate and private
key read-only using a Compose override, and publish port 443 in that override.
Keep certificate material outside the images and arrange renewal on the host.
With TLS terminating at this Nginx, `$scheme` forwards `https` to Uvicorn.

If the hosting platform terminates TLS before Nginx instead, configure Nginx to
forward the original HTTPS scheme from that trusted ingress and restrict the
HTTP listener to the ingress. The supplied configuration sets the forwarded
scheme from Nginx's own connection, so an additional TLS proxy requires this
adjustment for correct absolute redirects. The API currently has no
authentication; HTTPS does not add access control.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Docker cannot connect to its daemon | Start Docker Desktop or Docker Engine and select Linux containers. |
| Host port is already allocated | Set `HTTP_PORT` to an unused port and recreate the stack. |
| Backend never becomes healthy | Inspect `docker compose logs backend`; check installation and application startup. |
| Nginx returns 502 | Check backend health, logs, and network resolution; allow for the DNS refresh after recreation. |
| Nginx returns 504 for a backtest | Inspect backend logs, market-data availability, and run duration relative to the 300-second proxy timeout. |
| Catalogue works but a backtest fails | Check Yahoo connectivity and the API response; `/health` does not test the price provider. |
| API documentation loads but requests use the wrong URL | Preserve `--root-path /api`, the public Host header, and the correct forwarded scheme. |
