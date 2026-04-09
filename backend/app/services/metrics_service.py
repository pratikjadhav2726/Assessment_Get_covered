import asyncio
from collections import defaultdict


class MetricsService:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._counters: dict[str, int] = defaultdict(int)
        self._scan_latency_total_ms: float = 0.0
        self._scan_count: int = 0

    async def increment(self, name: str, amount: int = 1) -> None:
        async with self._lock:
            self._counters[name] += amount

    async def record_scan(self, state: str, duration_ms: float) -> None:
        async with self._lock:
            self._counters[f"scan_state_{state}"] += 1
            self._counters["scan_requests_total"] += 1
            self._scan_count += 1
            self._scan_latency_total_ms += duration_ms

    async def snapshot(self) -> dict[str, float | int]:
        async with self._lock:
            average_latency = 0.0
            if self._scan_count > 0:
                average_latency = self._scan_latency_total_ms / self._scan_count
            data: dict[str, float | int] = dict(self._counters)
            data["scan_latency_avg_ms"] = round(average_latency, 2)
            return data
