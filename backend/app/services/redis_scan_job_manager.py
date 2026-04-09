import asyncio
import uuid
from time import time

from redis.asyncio import Redis

from app.api.schemas import ScanJobStatusResponse, ScanResponse
from app.services.ports import ScanJobManagerPort
from app.services.scan_orchestrator import ScanOrchestrator


class RedisScanJobManager(ScanJobManagerPort):
    def __init__(
        self,
        orchestrator: ScanOrchestrator,
        redis: Redis,
        retention_seconds: int = 900,
        idempotency_ttl_seconds: int = 600,
    ) -> None:
        self._orchestrator = orchestrator
        self._redis = redis
        self._retention_seconds = retention_seconds
        self._idempotency_ttl_seconds = idempotency_ttl_seconds

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def submit(self, input_url: str, idempotency_key: str | None = None) -> ScanJobStatusResponse:
        if idempotency_key:
            existing = await self._get_by_idempotency_key(idempotency_key)
            if existing is not None:
                return existing

        now = time()
        job_id = str(uuid.uuid4())
        job_key = self._job_key(job_id)
        await self._redis.hset(
            job_key,
            mapping={
                "job_id": job_id,
                "state": "queued",
                "input_url": input_url,
                "created_at": str(now),
                "updated_at": str(now),
            },
        )
        if idempotency_key:
            await self._redis.set(
                self._idempotency_key(idempotency_key),
                job_id,
                ex=self._idempotency_ttl_seconds,
            )
        asyncio.create_task(self._run_job(job_id))
        return ScanJobStatusResponse(
            job_id=job_id,
            state="queued",
            input_url=input_url,
            created_at=now,
            updated_at=now,
            result=None,
            error=None,
        )

    async def get(self, job_id: str) -> ScanJobStatusResponse | None:
        data = await self._redis.hgetall(self._job_key(job_id))
        if not data:
            return None
        result_payload = data.get("result")
        result = ScanResponse.model_validate_json(result_payload) if result_payload else None
        return ScanJobStatusResponse(
            job_id=data["job_id"],
            state=data["state"],  # type: ignore[arg-type]
            input_url=data["input_url"],
            created_at=float(data["created_at"]),
            updated_at=float(data["updated_at"]),
            result=result,
            error=data.get("error"),
        )

    async def _run_job(self, job_id: str) -> None:
        job_key = self._job_key(job_id)
        data = await self._redis.hgetall(job_key)
        if not data:
            return

        input_url = data["input_url"]
        await self._redis.hset(job_key, mapping={"state": "running", "updated_at": str(time())})
        try:
            result, _ = await self._orchestrator.scan_url(input_url)
            await self._redis.hset(
                job_key,
                mapping={
                    "state": "completed",
                    "updated_at": str(time()),
                    "result": result.model_dump_json(),
                },
            )
        except Exception as exc:
            await self._redis.hset(
                job_key,
                mapping={"state": "failed", "updated_at": str(time()), "error": str(exc)},
            )
        finally:
            await self._redis.expire(job_key, self._retention_seconds)

    async def _get_by_idempotency_key(self, idempotency_key: str) -> ScanJobStatusResponse | None:
        job_id = await self._redis.get(self._idempotency_key(idempotency_key))
        if not job_id:
            return None
        return await self.get(job_id)

    @staticmethod
    def _job_key(job_id: str) -> str:
        return f"scan_job:{job_id}"

    @staticmethod
    def _idempotency_key(key: str) -> str:
        return f"scan_idempotency:{key}"
