from redis.asyncio import Redis

from app.core.config import settings
from app.services.ports import RateLimiterPort, ScanJobManagerPort
from app.services.rate_limiter import InMemoryRateLimiter
from app.services.redis_rate_limiter import RedisRateLimiter
from app.services.redis_scan_job_manager import RedisScanJobManager
from app.services.scan_job_manager import InMemoryScanJobManager
from app.services.scan_orchestrator import ScanOrchestrator


class ServiceProviders:
    def __init__(self, orchestrator: ScanOrchestrator) -> None:
        self._orchestrator = orchestrator
        self._redis_client: Redis | None = None

    async def start(self) -> None:
        if settings.state_backend != "redis":
            return
        self._redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
        await self._redis_client.ping()

    async def stop(self) -> None:
        if self._redis_client is not None:
            await self._redis_client.close()
            self._redis_client = None

    def build_job_manager(self) -> ScanJobManagerPort:
        if settings.state_backend == "redis":
            if self._redis_client is None:
                raise RuntimeError("Redis backend selected but Redis client is not started.")
            return RedisScanJobManager(
                orchestrator=self._orchestrator,
                redis=self._redis_client,
                retention_seconds=settings.job_retention_seconds,
                idempotency_ttl_seconds=settings.idempotency_ttl_seconds,
            )
        return InMemoryScanJobManager(
            orchestrator=self._orchestrator,
            retention_seconds=settings.job_retention_seconds,
            cleanup_interval_seconds=settings.job_cleanup_interval_seconds,
            idempotency_ttl_seconds=settings.idempotency_ttl_seconds,
        )

    def build_rate_limiter(self) -> RateLimiterPort:
        if settings.state_backend == "redis":
            if self._redis_client is None:
                raise RuntimeError("Redis backend selected but Redis client is not started.")
            return RedisRateLimiter(
                redis=self._redis_client,
                max_requests=settings.rate_limit_requests,
                window_seconds=settings.rate_limit_window_seconds,
            )
        return InMemoryRateLimiter(
            max_requests=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )
