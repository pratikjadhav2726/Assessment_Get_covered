import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

from app.security.url_validation import URLValidationError


class NetworkSafetyChecker:
    @staticmethod
    async def validate_public_dns(url: str) -> None:
        parsed = urlparse(url)
        host = parsed.hostname
        if not host:
            raise URLValidationError("URL host is missing.")

        loop = asyncio.get_running_loop()
        try:
            infos = await loop.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise URLValidationError(f"Unable to resolve host: {host}") from exc

        for info in infos:
            addr = info[4][0]
            ip = ipaddress.ip_address(addr)
            if not ip.is_global:
                raise URLValidationError("Resolved host points to non-public network space.")
