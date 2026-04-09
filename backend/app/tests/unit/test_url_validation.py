import pytest

from app.security.url_validation import URLValidationError, URLValidator


def test_rejects_non_http_scheme() -> None:
    with pytest.raises(URLValidationError):
        URLValidator.validate_syntax("ftp://example.com")


def test_rejects_private_ip_host() -> None:
    with pytest.raises(URLValidationError):
        URLValidator.validate_host_not_ip_blocked("127.0.0.1")


def test_allows_public_hostname() -> None:
    URLValidator.validate_syntax("https://example.com/login")


def test_normalize_preserves_query_and_path() -> None:
    normalized = URLValidator.normalize("https://Example.com/login?a=1")
    assert normalized == "https://example.com/login?a=1"


def test_rejects_excessive_redirect_hops() -> None:
    with pytest.raises(URLValidationError):
        URLValidator.validate_redirect_hops(99)
