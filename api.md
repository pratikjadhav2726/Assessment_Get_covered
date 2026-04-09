# Backend API reference

The API is served by **FastAPI** (app title: **Auth Snippet Discovery API**). Interactive documentation is generated from the same code this file describes.

## Base URLs

| Environment | Base URL |
|-------------|----------|
| Uvicorn (local) | `http://localhost:8000` (or `APP_HOST` / `APP_PORT`) |
| Docker Compose (Nginx) | `http://localhost` — paths are unchanged; Nginx proxies to the backend |

## Interactive OpenAPI

When the server is running:

| Resource | Path |
|----------|------|
| Swagger UI | `GET /docs` |
| ReDoc | `GET /redoc` |
| OpenAPI JSON | `GET /openapi.json` |

Example with Compose: `http://localhost/docs`

## Rate limiting

All routes listed below are rate-limited per client and per logical endpoint. The key is `{client_host}:{endpoint}` (see `backend/app/api/routes.py`).

| Setting | Default | Env vars |
|---------|---------|----------|
| Max requests | `60` | `RATE_LIMIT_REQUESTS` |
| Window | `60` seconds | `RATE_LIMIT_WINDOW_SECONDS` |

**Response when exceeded:** `429 Too Many Request` with body:

```json
{ "detail": "Rate limit exceeded. Try again later." }
```

## Endpoints

### `GET /health`

Liveness check.

**Response** `200`:

```json
{ "status": "ok" }
```

---

### `GET /metrics`

Snapshot of internal counters and timing metrics (JSON object: string keys → numeric values).

**Response** `200`: JSON map of metric name to `number`.

---

### `POST /api/scan`

Synchronous scan: loads the URL with the browser pipeline, runs auth heuristics, returns a structured result.

**Query parameters**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `debug` | boolean | `false` | When true, response may include a `debug` object with diagnostics |

**Request body** (`application/json`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string (URL) | yes | Public `http` or `https` URL to scan |

**Response** `200`: [`ScanResponse`](#scanresponse)

---

### `POST /api/scan/jobs`

Creates an asynchronous scan job. Poll [`GET /api/scan/jobs/{job_id}`](#get-apiscanjobsjob_id) until `completed` or `failed`.

**Headers (optional)**

| Header | Description |
|--------|-------------|
| `Idempotency-Key` | Same key within the idempotency TTL returns the existing job instead of creating a duplicate. Default TTL: `600` s (`IDEMPOTENCY_TTL_SECONDS`). |

**Request body:** same as [`POST /api/scan`](#postapiscan) — `{ "url": "https://..." }`

**Response** `200`: [`ScanJobCreateResponse`](#scanjobcreateresponse)

---

### `GET /api/scan/jobs/{job_id}`

Returns job metadata and, when finished, `result` or `error`.

**Path parameters**

| Name | Description |
|------|-------------|
| `job_id` | UUID string returned from job creation |

**Responses**

| Status | Body |
|--------|------|
| `200` | [`ScanJobStatusResponse`](#scanjobstatusresponse) |
| `404` | `{"detail": "Job not found."}` |

---

## Data models

Types align with Pydantic models in `backend/app/api/schemas.py`.

### `ScanRequest`

| Field | Type | Description |
|-------|------|-------------|
| `url` | URL | Validated HTTP(S) URL |

### `ResultState`

Values for `ScanResponse.state`:

`found` · `not_found` · `protected_or_blocked` · `invalid_input` · `timeout` · `scan_error`

### `ScanResponse`

| Field | Type | Description |
|-------|------|-------------|
| `input_url` | string | URL that was processed |
| `state` | string | [`ResultState`](#resultstate) |
| `found` | boolean | Whether auth-related UI was inferred |
| `confidence` | number | `0.0`–`1.0` |
| `source` | string | Detector / pipeline label |
| `detection_signals` | string[] | Short labels for signals used |
| `html_snippet` | string \| null | Bounded HTML fragment when applicable |
| `message` | string | Human-readable summary |
| `debug` | object \| null | Optional diagnostics when `debug=true` |

### `JobState`

Values: `queued` · `running` · `completed` · `failed`

### `ScanJobCreateResponse`

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | UUID for polling |
| `state` | string | [`JobState`](#jobstate) |
| `message` | string | e.g. acceptance hint |

### `ScanJobStatusResponse`

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | |
| `state` | string | [`JobState`](#jobstate) |
| `input_url` | string | Submitted URL |
| `created_at` | number | Unix timestamp (seconds) |
| `updated_at` | number | Unix timestamp (seconds) |
| `result` | [`ScanResponse`](#scanresponse) \| null | Present when completed successfully |
| `error` | string \| null | Present when failed |

## CORS

The backend allows browser requests from configured localhost origins (including the Vite dev server). See `CORSMiddleware` in `backend/app/main.py`.

## Related configuration

Timeouts, cache TTL, job retention, Redis vs memory, and rate limits are documented in `.env.example` and `backend/app/core/config.py`.

## Example requests

**Health**

```bash
curl -sS http://127.0.0.1:8000/health
```

**Synchronous scan**

```bash
curl -sS -X POST http://127.0.0.1:8000/api/scan \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://github.com/login"}'
```

**Async job + poll**

```bash
JOB=$(curl -sS -X POST http://127.0.0.1:8000/api/scan/jobs \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://github.com/login"}' | jq -r .job_id)
curl -sS "http://127.0.0.1:8000/api/scan/jobs/$JOB"
```

With Compose, replace `http://127.0.0.1:8000` with `http://localhost`.
