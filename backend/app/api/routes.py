import logging
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.api.schemas import ScanJobCreateResponse, ScanJobStatusResponse, ScanRequest, ScanResponse
from app.services.metrics_service import MetricsService
from app.services.rate_limiter import RateLimiter
from app.services.scan_job_manager import ScanJobManager
from app.services.scan_orchestrator import ScanOrchestrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["scan"])


def get_orchestrator() -> ScanOrchestrator:
    from app.main import orchestrator

    return orchestrator


def get_job_manager() -> ScanJobManager:
    from app.main import job_manager

    return job_manager


def get_rate_limiter() -> RateLimiter:
    from app.main import rate_limiter

    return rate_limiter


def get_metrics() -> MetricsService:
    from app.main import metrics

    return metrics


def _client_key(request: Request, endpoint: str) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"{client_host}:{endpoint}"


async def _enforce_rate_limit(request: Request, endpoint: str, limiter: RateLimiter, metrics: MetricsService) -> None:
    allowed = await limiter.allow(_client_key(request, endpoint))
    if not allowed:
        await metrics.increment("rate_limit_rejected_total")
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")


@router.post("/scan", response_model=ScanResponse)
async def scan_auth_snippet(
    request: Request,
    payload: ScanRequest,
    scan_orchestrator: ScanOrchestrator = Depends(get_orchestrator),
    limiter: RateLimiter = Depends(get_rate_limiter),
    metrics: MetricsService = Depends(get_metrics),
) -> ScanResponse:
    await _enforce_rate_limit(request, "scan", limiter, metrics)
    request_id = str(uuid.uuid4())
    response, duration_ms = await scan_orchestrator.scan_url(str(payload.url))
    await metrics.record_scan(response.state, duration_ms)
    logger.info(
        "scan_completed",
        extra={
            "request_id": request_id,
            "url": str(payload.url),
            "result_state": response.state,
            "confidence": response.confidence,
            "duration_ms": round(duration_ms, 2),
        },
    )
    return response


@router.post("/scan/jobs", response_model=ScanJobCreateResponse)
async def create_scan_job(
    request: Request,
    payload: ScanRequest,
    manager: ScanJobManager = Depends(get_job_manager),
    limiter: RateLimiter = Depends(get_rate_limiter),
    metrics: MetricsService = Depends(get_metrics),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ScanJobCreateResponse:
    await _enforce_rate_limit(request, "scan_jobs_create", limiter, metrics)
    status = await manager.submit(str(payload.url), idempotency_key=idempotency_key)
    await metrics.increment("scan_jobs_submitted_total")
    return ScanJobCreateResponse(
        job_id=status.job_id,
        state=status.state,
        message="Scan job accepted. Poll job status endpoint for completion.",
    )


@router.get("/scan/jobs/{job_id}", response_model=ScanJobStatusResponse)
async def get_scan_job(
    request: Request,
    job_id: str,
    manager: ScanJobManager = Depends(get_job_manager),
    limiter: RateLimiter = Depends(get_rate_limiter),
    metrics: MetricsService = Depends(get_metrics),
) -> ScanJobStatusResponse:
    await _enforce_rate_limit(request, "scan_jobs_get", limiter, metrics)
    await metrics.increment("scan_jobs_polled_total")
    status = await manager.get(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return status
