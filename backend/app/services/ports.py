from typing import Protocol

from app.api.schemas import ScanJobStatusResponse


class RateLimiterPort(Protocol):
    async def allow(self, key: str) -> bool:
        ...


class ScanJobManagerPort(Protocol):
    async def start(self) -> None:
        ...

    async def stop(self) -> None:
        ...

    async def submit(self, input_url: str, idempotency_key: str | None = None) -> ScanJobStatusResponse:
        ...

    async def get(self, job_id: str) -> ScanJobStatusResponse | None:
        ...
