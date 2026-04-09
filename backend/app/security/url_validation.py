import ipaddress
from urllib.parse import urlparse

from app.core.config import settings


class URLValidationError(ValueError):
    pass


class URLValidator:
    @staticmethod
    def normalize(url: str) -> str:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        scheme = parsed.scheme.lower()
        port = f":{parsed.port}" if parsed.port else ""
        path = parsed.path or "/"
        query = f"?{parsed.query}" if parsed.query else ""
        return f"{scheme}://{host}{port}{path}{query}"

    @staticmethod
    def validate_syntax(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise URLValidationError("Only http and https URLs are allowed.")
        if not parsed.netloc:
            raise URLValidationError("URL must include a host.")

    @staticmethod
    def validate_host_not_ip_blocked(host: str) -> None:
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            return

        if not ip.is_global:
            raise URLValidationError("Private or non-public IP addresses are blocked.")

    @staticmethod
    def validate_redirect_hops(redirect_hops: int) -> None:
        if redirect_hops > settings.max_redirect_hops:
            raise URLValidationError("Too many redirects for this scan request.")
