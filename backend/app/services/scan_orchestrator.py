from dataclasses import dataclass
import asyncio
from time import perf_counter
from urllib.parse import urlparse

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.api.schemas import ScanResponse
from app.services.auth_detector import AuthDetector
from app.services.browser_service import BrowserService
from app.services.dom_service import DOMService
from app.services.formatter import ResponseFormatter
from app.services.snippet_extractor import SnippetExtractor
from app.services.result_cache import ResultCache
from app.security.network_safety import NetworkSafetyChecker
from app.security.url_validation import URLValidationError, URLValidator
from app.core.config import settings


@dataclass(frozen=True)
class ScanServices:
    browser_service: BrowserService
    dom_service: DOMService
    auth_detector: AuthDetector
    snippet_extractor: SnippetExtractor
    formatter: ResponseFormatter
    url_validator: URLValidator
    network_safety: NetworkSafetyChecker
    result_cache: ResultCache


class ScanOrchestrator:
    def __init__(self, services: ScanServices) -> None:
        self.services = services

    async def scan_url(self, input_url: str, debug: bool = False) -> tuple[ScanResponse, float]:
        started = perf_counter()
        try:
            self.services.url_validator.validate_syntax(input_url)
            normalized_input = self.services.url_validator.normalize(input_url)

            cached = await self.services.result_cache.get(normalized_input)
            if cached is not None:
                duration_ms = (perf_counter() - started) * 1000
                return cached, duration_ms

            response = await asyncio.wait_for(
                self._scan_core(input_url, normalized_input, debug=debug),
                timeout=settings.request_timeout_ms / 1000.0,
            )
        except URLValidationError as exc:
            response = self.services.formatter.failure(input_url, "invalid_input", str(exc))
        except (PlaywrightTimeoutError, TimeoutError, asyncio.TimeoutError):
            response = self.services.formatter.failure(input_url, "timeout", "Scan timed out while loading website.")
        except PlaywrightError:
            response = self.services.formatter.failure(
                input_url, "protected_or_blocked", "Website blocked automated access or requires protections."
            )
        except Exception:
            response = self.services.formatter.failure(input_url, "scan_error", "Unexpected scan error occurred.")

        duration_ms = (perf_counter() - started) * 1000
        return response, duration_ms

    async def _scan_core(self, input_url: str, normalized_input: str, debug: bool = False) -> ScanResponse:
        parsed = urlparse(input_url)
        if parsed.hostname:
            self.services.url_validator.validate_host_not_ip_blocked(parsed.hostname)
        await self.services.network_safety.validate_public_dns(input_url)

        html, final_url, redirect_hops = await self.services.browser_service.get_rendered_html(input_url)
        self.services.url_validator.validate_redirect_hops(redirect_hops)
        self.services.url_validator.validate_syntax(final_url)

        final_parsed = urlparse(final_url)
        if final_parsed.hostname:
            self.services.url_validator.validate_host_not_ip_blocked(final_parsed.hostname)
        await self.services.network_safety.validate_public_dns(final_url)

        blocked_reasons = self._blocked_reasons(html=html, final_url=final_url)
        page_title = self._extract_title(html)
        diagnostics = self._debug_payload(
            input_url=input_url,
            final_url=final_url,
            page_title=page_title,
            html=html,
            blocked_reasons=blocked_reasons,
        )

        if self._should_classify_blocked(blocked_reasons):
            response = self.services.formatter.failure(
                input_url=input_url,
                state="protected_or_blocked",
                message="Website returned a protection/captcha/challenge page instead of login markup.",
                debug=diagnostics if debug else None,
            )
            await self.services.result_cache.set(normalized_input, response)
            return response

        soup = self.services.dom_service.parse(html)
        candidates = self.services.dom_service.iter_candidate_containers(soup)
        detection = self.services.auth_detector.score(candidates)

        if detection.container is None or detection.confidence < 0.4:
            response = self.services.formatter.not_found(
                input_url=input_url,
                source=final_url,
                debug=diagnostics if debug else None,
            )
        else:
            snippet = self.services.snippet_extractor.extract(detection.container)
            if not snippet:
                response = self.services.formatter.not_found(
                    input_url=input_url,
                    source=final_url,
                    debug=diagnostics if debug else None,
                )
                await self.services.result_cache.set(normalized_input, response)
                return response
            response = self.services.formatter.found(
                input_url=input_url,
                source=final_url,
                confidence=detection.confidence,
                detection_signals=detection.signals,
                html_snippet=snippet,
                debug=diagnostics if debug else None,
            )

        await self.services.result_cache.set(normalized_input, response)
        return response

    @staticmethod
    def _blocked_reasons(html: str, final_url: str) -> list[str]:
        low = html.lower()
        url_low = final_url.lower()
        checks = {
            "just_a_moment": "just a moment" in low,
            "cloudflare_challenge": "cf-challenge" in low or "challenge-error-text" in low,
            "captcha_delivery": "captcha-delivery" in low,
            "captcha_url": any(m in url_low for m in ("js_challenge", "captcha", "challenge")),
            "captcha_widget": any(m in low for m in ("recaptcha", "hcaptcha", "/captcha/")),
            "human_verification": any(m in low for m in ("are you human", "verify you are human", "security check")),
            "enable_js_cookies": "please enable javascript and cookies" in low,
        }
        return [name for name, passed in checks.items() if passed]

    @staticmethod
    def _should_classify_blocked(blocked_reasons: list[str]) -> bool:
        return len(blocked_reasons) >= 2

    @staticmethod
    def _extract_title(html: str) -> str:
        low = html.lower()
        start = low.find("<title>")
        end = low.find("</title>")
        if start == -1 or end == -1 or end <= start:
            return ""
        return html[start + len("<title>") : end].strip()[:200]

    @staticmethod
    def _debug_payload(
        input_url: str,
        final_url: str,
        page_title: str,
        html: str,
        blocked_reasons: list[str],
    ) -> dict[str, str | int | float | bool | list[str] | None]:
        low = html.lower()
        markers = {
            "has_password_input": "type=\"password\"" in low,
            "has_sign_in_text": "sign in" in low or "log in" in low,
            "has_continue_with": "continue with" in low,
            "has_one_time": "one-time" in low or "magic link" in low,
        }
        return {
            "input_url": input_url,
            "final_url": final_url,
            "page_title": page_title,
            "html_length": len(html),
            "blocked_reasons": blocked_reasons,
            "html_preview": html[:1200].replace("\n", " "),
            "has_password_input": markers["has_password_input"],
            "has_sign_in_text": markers["has_sign_in_text"],
            "has_continue_with": markers["has_continue_with"],
            "has_one_time": markers["has_one_time"],
        }
