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
