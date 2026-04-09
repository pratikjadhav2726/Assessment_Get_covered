from app.services.providers import ServiceProviders
from app.services.rate_limiter import InMemoryRateLimiter
from app.services.scan_job_manager import InMemoryScanJobManager


class FakeOrchestrator:
    pass


def test_providers_build_in_memory_by_default() -> None:
    providers = ServiceProviders(orchestrator=FakeOrchestrator())  # type: ignore[arg-type]
    job_manager = providers.build_job_manager()
    limiter = providers.build_rate_limiter()
    assert isinstance(job_manager, InMemoryScanJobManager)
    assert isinstance(limiter, InMemoryRateLimiter)
