import asyncio
from dataclasses import dataclass
from time import monotonic

from app.api.schemas import ScanResponse


@dataclass
class CacheEntry:
    expires_at: float
    response: ScanResponse


class ResultCache:
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._entries: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> ScanResponse | None:
        async with self._lock:
            entry = self._entries.get(key)
            now = monotonic()
            if entry is None:
                return None
            if entry.expires_at <= now:
                self._entries.pop(key, None)
                return None
            return entry.response.model_copy(deep=True)

    async def set(self, key: str, response: ScanResponse) -> None:
        async with self._lock:
            self._entries[key] = CacheEntry(
                expires_at=monotonic() + self._ttl_seconds,
                response=response.model_copy(deep=True),
            )
