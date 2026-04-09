import logging
import uuid

from fastapi import APIRouter, Depends

from app.api.schemas import ScanRequest, ScanResponse
from app.services.scan_orchestrator import ScanOrchestrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["scan"])


def get_orchestrator() -> ScanOrchestrator:
    from app.main import orchestrator

    return orchestrator


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
