import asyncio
from dataclasses import dataclass
from time import monotonic, time
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
    def __init__(
        self,
        orchestrator: ScanOrchestrator,
        retention_seconds: int = 900,
        cleanup_interval_seconds: int = 30,
        idempotency_ttl_seconds: int = 600,
    ) -> None:
        self._orchestrator = orchestrator
        self._jobs: dict[str, JobRecord] = {}
        self._idempotency_map: dict[str, tuple[str, float]] = {}
        self._lock = asyncio.Lock()
        self._retention_seconds = retention_seconds
        self._cleanup_interval_seconds = cleanup_interval_seconds
        self._idempotency_ttl_seconds = idempotency_ttl_seconds
        self._cleanup_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        if self._cleanup_task is None:
            return
        self._cleanup_task.cancel()
        try:
            await self._cleanup_task
        except asyncio.CancelledError:
            pass
        self._cleanup_task = None

    async def submit(self, input_url: str, idempotency_key: str | None = None) -> ScanJobStatusResponse:
        if idempotency_key:
            existing = await self._get_by_idempotency_key(idempotency_key)
            if existing is not None:
                return existing

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
            if idempotency_key:
                self._idempotency_map[idempotency_key] = (job_id, monotonic() + self._idempotency_ttl_seconds)
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

    async def cleanup_once(self) -> None:
        now_monotonic = monotonic()
        now_unix = time()
        async with self._lock:
            self._idempotency_map = {
                key: value for key, value in self._idempotency_map.items() if value[1] > now_monotonic
            }
            stale_job_ids = [
                job_id
                for job_id, record in self._jobs.items()
                if (record.state in {"completed", "failed"} and (now_unix - record.updated_at) > self._retention_seconds)
            ]
            for job_id in stale_job_ids:
                self._jobs.pop(job_id, None)

    async def _cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(self._cleanup_interval_seconds)
            await self.cleanup_once()

    async def _get_by_idempotency_key(self, idempotency_key: str) -> ScanJobStatusResponse | None:
        now_monotonic = monotonic()
        async with self._lock:
            existing = self._idempotency_map.get(idempotency_key)
            if existing is None:
                return None
            job_id, expires_at = existing
            if expires_at <= now_monotonic:
                self._idempotency_map.pop(idempotency_key, None)
                return None
            record = self._jobs.get(job_id)
            if record is None:
                self._idempotency_map.pop(idempotency_key, None)
                return None
            return self._to_schema(record)

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
