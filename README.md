# Auth Snippet Discovery API

Backend service that accepts a public HTTPS URL, loads the page with headless Chromium (Playwright), analyzes the rendered DOM, and returns whether authentication-related markup was found along with a bounded HTML snippet when possible.

The design follows **FastAPI + async**, layered services, **URL safety checks**, rate limiting, optional **Redis-backed** state (jobs + rate limits), and **Nginx** as a single-entry reverse proxy when deployed via Docker.

## Architecture (high level)

```text
Client → Nginx (:80) → FastAPI (:8000) → Scan orchestrator
                                    ↓
              Playwright (render) → DOM parse → Auth heuristics → Snippet extract
                                    ↓
                    Redis (optional): scan jobs, idempotency, rate limits
```

- **Stateful pieces** (jobs, rate limit counters) are behind interfaces so `STATE_BACKEND` can switch between in-memory and Redis without changing route handlers.
- **Scans** default to synchronous `POST /api/scan`; heavy workloads can use **async jobs** (`POST /api/scan/jobs` + poll).

## Tech stack

- **Python 3.12+**, **FastAPI**, **Pydantic**
- **Playwright** (Chromium) for JS-rendered pages
- **BeautifulSoup + lxml** for DOM analysis
- **Redis** (optional) for distributed-friendly rate limiting and job metadata
- **uv** for dependency management (`pyproject.toml` + `uv.lock`)
- **Docker Compose**: Nginx + API + Redis

## Repository layout

```text
.
├── backend/
│   ├── Dockerfile              # Playwright base image + uv sync
│   └── app/
│       ├── main.py             # FastAPI app, lifespan, wiring
│       ├── api/                # routes, schemas
│       ├── core/               # settings, logging
│       ├── security/           # URL validation, DNS safety
│       └── services/           # browser, DOM, detector, orchestrator, cache, jobs
├── nginx/
│   └── nginx.conf              # Reverse proxy to backend
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
├── .env.example
├── Plan.md                     # original product/architecture notes
└── README.md
```

## Quick start (local, no Docker)

1. Install [uv](https://docs.astral.sh/uv/) and **Playwright browsers** (Chromium):

   ```bash
   uv sync
   uv run playwright install chromium
   ```

2. Run the API (uses `STATE_BACKEND=memory` unless you set Redis in env):

   ```bash
   uv run uvicorn app.main:app --app-dir backend --reload
   ```

3. Health check:

   ```bash
   curl http://127.0.0.1:8000/health
   ```

4. Scan (example):

   ```bash
   curl -sS -X POST http://127.0.0.1:8000/api/scan \
     -H 'Content-Type: application/json' \
     -d '{"url":"https://github.com/login"}'
   ```

## Docker Compose (recommended for demos)

Compose runs **Nginx on port 80**, **API** (internal), and **Redis**. Environment is loaded from `.env` if present, otherwise from `.env.example`.

```bash
cp .env.example .env   # optional: edit values
docker compose up -d --build
```

- Public API base URL: `http://localhost`
- Health: `GET http://localhost/health`
- Metrics (JSON): `GET http://localhost/metrics` (via Nginx → backend)

To tear down (and remove Redis volume):

```bash
docker compose down -v
```

## Environment variables

See `.env.example` for the full set. Important knobs:

| Variable | Purpose |
|----------|---------|
| `REQUEST_TIMEOUT_MS` | Overall scan wall-clock budget (orchestrator) |
| `GOTO_TIMEOUT_MS` | Playwright navigation timeout |
| `DOM_SETTLE_TIMEOUT_MS` | Extra settle wait after navigation |
| `MAX_CONCURRENT_SCANS` | Semaphore limiting concurrent browser sessions |
| `MAX_REDIRECT_HOPS` | Reject scans after too many redirects |
| `RESULT_CACHE_TTL_SECONDS` | Short-TTL cache of scan results by normalized URL |
| `STATE_BACKEND` | `memory` or `redis` |
| `REDIS_URL` | e.g. `redis://redis:6379/0` in Compose |
| `RATE_LIMIT_*` | Per-client sliding window for API endpoints |

## API reference

### `POST /api/scan`

Synchronous scan.

**Body:**

```json
{ "url": "https://example.com/login" }
```

**Query:**

- `debug=true` — includes a `debug` object (final URL, title snippet, HTML preview, blocked reasons, simple markers).

**Response (`ScanResponse`):**

- `state`: `found` | `not_found` | `protected_or_blocked` | `invalid_input` | `timeout` | `scan_error`
- `found`, `confidence`, `detection_signals`, `html_snippet` (when `found`), `message`, optional `debug`

### `POST /api/scan/jobs`

Enqueue a job. Optional header: `Idempotency-Key` (dedup within TTL).

### `GET /api/scan/jobs/{job_id}`

Poll job status and result.

### `GET /health`

Liveness.

### `GET /metrics`

Simple counters and average scan latency (JSON).

## Safety notes

The URL boundary is treated as **untrusted**:

- Only `http`/`https`
- Host and resolved IPs must be **public** (no loopback/private ranges)
- Redirect hop limit
- Read-only navigation (no credential submission)

Do **not** use this service to probe internal networks or evade site protections.

## Why some sites differ from your browser

Bots and datacenter IPs often see **challenge / CAPTCHA / “just a moment”** pages that your personal browser does not. The `debug=true` flag helps compare what the server actually rendered versus what you see locally. `protected_or_blocked` is returned when multiple strong signals indicate a challenge page rather than login markup.

## Tests

```bash
uv sync
uv run pytest
```

## License / product

This repository is built for an assessment/demo (see `Plan.md` for product intent). Adjust licensing as needed for your organization.
