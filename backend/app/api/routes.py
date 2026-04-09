import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import ScanJobCreateResponse, ScanJobStatusResponse, ScanRequest, ScanResponse
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


@router.post("/scan", response_model=ScanResponse)
async def scan_auth_snippet(
    payload: ScanRequest,
    scan_orchestrator: ScanOrchestrator = Depends(get_orchestrator),
) -> ScanResponse:
    request_id = str(uuid.uuid4())
    response, duration_ms = await scan_orchestrator.scan_url(str(payload.url))
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
    payload: ScanRequest,
    manager: ScanJobManager = Depends(get_job_manager),
) -> ScanJobCreateResponse:
    status = await manager.submit(str(payload.url))
    return ScanJobCreateResponse(
        job_id=status.job_id,
        state=status.state,
        message="Scan job accepted. Poll job status endpoint for completion.",
    )


@router.get("/scan/jobs/{job_id}", response_model=ScanJobStatusResponse)
async def get_scan_job(
    job_id: str,
    manager: ScanJobManager = Depends(get_job_manager),
) -> ScanJobStatusResponse:
    status = await manager.get(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return status
