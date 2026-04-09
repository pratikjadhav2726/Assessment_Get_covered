from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = "Auth Snippet Discovery API"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_log_level: str = "INFO"
    request_timeout_ms: int = 20000
    goto_timeout_ms: int = 12000
    dom_settle_timeout_ms: int = 2000
    max_snippet_chars: int = 6000
    max_concurrent_scans: int = 5
    max_redirect_hops: int = 5
    result_cache_ttl_seconds: int = 90

    @staticmethod
    def from_env() -> "Settings":
        return Settings(
            app_name=os.getenv("APP_NAME", "Auth Snippet Discovery API"),
            app_env=os.getenv("APP_ENV", "dev"),
            app_host=os.getenv("APP_HOST", "0.0.0.0"),
            app_port=int(os.getenv("APP_PORT", "8000")),
            app_log_level=os.getenv("APP_LOG_LEVEL", "INFO").upper(),
            request_timeout_ms=int(os.getenv("REQUEST_TIMEOUT_MS", "20000")),
            goto_timeout_ms=int(os.getenv("GOTO_TIMEOUT_MS", "12000")),
            dom_settle_timeout_ms=int(os.getenv("DOM_SETTLE_TIMEOUT_MS", "2000")),
            max_snippet_chars=int(os.getenv("MAX_SNIPPET_CHARS", "6000")),
            max_concurrent_scans=int(os.getenv("MAX_CONCURRENT_SCANS", "5")),
            max_redirect_hops=int(os.getenv("MAX_REDIRECT_HOPS", "5")),
            result_cache_ttl_seconds=int(os.getenv("RESULT_CACHE_TTL_SECONDS", "90")),
        )


settings = Settings.from_env()
