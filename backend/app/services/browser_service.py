import asyncio
from contextlib import asynccontextmanager

from playwright.async_api import Browser, Playwright, async_playwright

from app.core.config import settings


class BrowserService:
    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._lock = asyncio.Lock()
        self._scan_semaphore = asyncio.Semaphore(settings.max_concurrent_scans)

    async def start(self) -> None:
        async with self._lock:
            if self._playwright is not None and self._browser is not None:
                return
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)

    async def stop(self) -> None:
        async with self._lock:
            if self._browser is not None:
                await self._browser.close()
                self._browser = None
            if self._playwright is not None:
                await self._playwright.stop()
                self._playwright = None

    @asynccontextmanager
    async def page_session(self):
        if self._browser is None:
            raise RuntimeError("BrowserService.start() must be called before scanning.")
        async with self._scan_semaphore:
            context = await self._browser.new_context(ignore_https_errors=False)
            async def _route_handler(route) -> None:
                if route.request.resource_type in {"image", "media", "font"}:
                    await route.abort()
                    return
                await route.continue_()

            await context.route(
                "**/*",
                _route_handler,
            )
            page = await context.new_page()
            try:
                yield page
            finally:
                await context.close()

    async def get_rendered_html(self, url: str) -> tuple[str, str, int]:
        async with self.page_session() as page:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=settings.goto_timeout_ms)
            await page.wait_for_timeout(settings.dom_settle_timeout_ms)
            html = await page.content()
            final_url = page.url
            redirect_hops = 0
            if response is not None:
                request = response.request
                while request.redirected_from is not None:
                    redirect_hops += 1
                    request = request.redirected_from
            return html, final_url, redirect_hops
