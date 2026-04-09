import asyncio

import pytest

from app.api.schemas import ScanResponse
from app.services.scan_job_manager import ScanJobManager


class FakeOrchestrator:
    async def scan_url(self, input_url: str) -> tuple[ScanResponse, float]:
        await asyncio.sleep(0.01)
        return (
            ScanResponse(
                input_url=input_url,
                state="not_found",
                found=False,
                confidence=0.0,
                source=input_url,
                detection_signals=[],
                html_snippet=None,
                message="No auth found.",
            ),
            10.0,
        )


@pytest.mark.anyio
async def test_scan_job_manager_submit_and_poll() -> None:
    manager = ScanJobManager(orchestrator=FakeOrchestrator())  # type: ignore[arg-type]
    accepted = await manager.submit("https://example.com")
    assert accepted.state in {"queued", "running"}

    for _ in range(30):
        status = await manager.get(accepted.job_id)
        assert status is not None
        if status.state == "completed":
            assert status.result is not None
            assert status.result.input_url == "https://example.com"
            return
        await asyncio.sleep(0.01)

    pytest.fail("Job did not complete within expected time window.")


@pytest.mark.anyio
async def test_scan_job_idempotency_returns_same_job() -> None:
    manager = ScanJobManager(orchestrator=FakeOrchestrator(), idempotency_ttl_seconds=60)  # type: ignore[arg-type]
    first = await manager.submit("https://example.com", idempotency_key="same-key")
    second = await manager.submit("https://example.com", idempotency_key="same-key")
    assert first.job_id == second.job_id


@pytest.mark.anyio
async def test_scan_job_cleanup_removes_stale_completed_jobs() -> None:
    manager = ScanJobManager(
        orchestrator=FakeOrchestrator(),  # type: ignore[arg-type]
        retention_seconds=0,
        cleanup_interval_seconds=60,
    )
    accepted = await manager.submit("https://example.com")
    for _ in range(30):
        status = await manager.get(accepted.job_id)
        assert status is not None
        if status.state == "completed":
            break
        await asyncio.sleep(0.01)
    await manager.cleanup_once()
    status_after = await manager.get(accepted.job_id)
    assert status_after is None
