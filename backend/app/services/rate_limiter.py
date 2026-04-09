import asyncio
from collections import deque
from time import monotonic

from app.services.ports import RateLimiterPort

class InMemoryRateLimiter(RateLimiterPort):
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    async def allow(self, key: str) -> bool:
        now = monotonic()
        boundary = now - self._window_seconds
        async with self._lock:
            bucket = self._requests.setdefault(key, deque())
            while bucket and bucket[0] <= boundary:
                bucket.popleft()
            if len(bucket) >= self._max_requests:
                return False
            bucket.append(now)
            return True


RateLimiter = InMemoryRateLimiter
