from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.security.network_safety import NetworkSafetyChecker
from app.security.url_validation import URLValidator
from app.services.auth_detector import AuthDetector
from app.services.browser_service import BrowserService
from app.services.dom_service import DOMService
from app.services.formatter import ResponseFormatter
from app.services.scan_orchestrator import ScanOrchestrator, ScanServices
from app.services.snippet_extractor import SnippetExtractor
from app.services.result_cache import ResultCache
from app.services.metrics_service import MetricsService
from app.services.ports import RateLimiterPort, ScanJobManagerPort
from app.services.providers import ServiceProviders
from app.services.rate_limiter import InMemoryRateLimiter
from app.services.scan_job_manager import InMemoryScanJobManager

configure_logging()

browser_service = BrowserService()
orchestrator = ScanOrchestrator(
    services=ScanServices(
        browser_service=browser_service,
        dom_service=DOMService(),
        auth_detector=AuthDetector(),
        snippet_extractor=SnippetExtractor(),
        formatter=ResponseFormatter(),
        url_validator=URLValidator(),
        network_safety=NetworkSafetyChecker(),
        result_cache=ResultCache(ttl_seconds=settings.result_cache_ttl_seconds),
    )
)
service_providers = ServiceProviders(orchestrator=orchestrator)
job_manager: ScanJobManagerPort = InMemoryScanJobManager(
    orchestrator=orchestrator,
    retention_seconds=settings.job_retention_seconds,
    cleanup_interval_seconds=settings.job_cleanup_interval_seconds,
    idempotency_ttl_seconds=settings.idempotency_ttl_seconds,
)
rate_limiter: RateLimiterPort = InMemoryRateLimiter(
    max_requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)
metrics = MetricsService()


@asynccontextmanager
async def lifespan(_: FastAPI):
    global job_manager, rate_limiter
    await browser_service.start()
    await service_providers.start()
    job_manager = service_providers.build_job_manager()
    rate_limiter = service_providers.build_rate_limiter()
    await job_manager.start()
    try:
        yield
    finally:
        await job_manager.stop()
        await service_providers.stop()
        await browser_service.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allow_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
async def get_metrics() -> dict[str, float | int]:
    return await metrics.snapshot()
