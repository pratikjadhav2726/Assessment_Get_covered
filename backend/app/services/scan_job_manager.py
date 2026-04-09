import asyncio
from dataclasses import dataclass
from time import time
import uuid

from app.api.schemas import ScanJobStatusResponse, ScanResponse
from app.services.scan_orchestrator import ScanOrchestrator


@dataclass
class JobRecord:
    job_id: str
    state: str
    input_url: str
    created_at: float
    updated_at: float
    result: ScanResponse | None
    error: str | None


class ScanJobManager:
    def __init__(self, orchestrator: ScanOrchestrator) -> None:
        self._orchestrator = orchestrator
        self._jobs: dict[str, JobRecord] = {}
        self._lock = asyncio.Lock()

    async def submit(self, input_url: str) -> ScanJobStatusResponse:
        now = time()
        job_id = str(uuid.uuid4())
        record = JobRecord(
            job_id=job_id,
            state="queued",
            input_url=input_url,
            created_at=now,
            updated_at=now,
            result=None,
            error=None,
        )
        async with self._lock:
            self._jobs[job_id] = record
        asyncio.create_task(self._run_job(job_id))
        return self._to_schema(record)

    async def get(self, job_id: str) -> ScanJobStatusResponse | None:
        async with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return None
            return self._to_schema(record)

    async def _run_job(self, job_id: str) -> None:
        async with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return
            record.state = "running"
            record.updated_at = time()
            input_url = record.input_url

        try:
            result, _ = await self._orchestrator.scan_url(input_url)
            async with self._lock:
                current = self._jobs.get(job_id)
                if current is None:
                    return
                current.state = "completed"
                current.result = result
                current.updated_at = time()
        except Exception as exc:
            async with self._lock:
                current = self._jobs.get(job_id)
                if current is None:
                    return
                current.state = "failed"
                current.error = str(exc)
                current.updated_at = time()

    @staticmethod
    def _to_schema(record: JobRecord) -> ScanJobStatusResponse:
        return ScanJobStatusResponse(
            job_id=record.job_id,
            state=record.state,  # type: ignore[arg-type]
            input_url=record.input_url,
            created_at=record.created_at,
            updated_at=record.updated_at,
            result=record.result,
            error=record.error,
        )
