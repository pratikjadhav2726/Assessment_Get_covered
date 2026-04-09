import asyncio
from contextlib import asynccontextmanager

from playwright.async_api import Browser, Playwright, TimeoutError as PlaywrightTimeoutError, async_playwright

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
            # Give login widgets and client-side hydration a chance to appear.
            try:
                await page.wait_for_selector("input[type='password']", timeout=min(5000, settings.goto_timeout_ms))
            except PlaywrightTimeoutError:
                pass
            try:
                await page.wait_for_selector(
                    "text=/sign in|log in|continue with|one-time/i",
                    timeout=min(5000, settings.goto_timeout_ms),
                )
            except PlaywrightTimeoutError:
                pass
            try:
                await page.wait_for_load_state("networkidle", timeout=min(5000, settings.goto_timeout_ms))
            except PlaywrightTimeoutError:
                pass
            await page.wait_for_timeout(settings.dom_settle_timeout_ms)

            frame_html_parts: list[str] = []
            for frame in page.frames:
                try:
                    content = await frame.evaluate(
                        """() => {
                            const serialize = (node) => {
                                if (!(node instanceof Element)) return "";
                                let html = node.outerHTML || "";
                                if (node.shadowRoot) {
                                    const children = Array.from(node.shadowRoot.children || []);
                                    const shadowHtml = children.map((child) => serialize(child)).join("");
                                    html += `<shadow-root>${shadowHtml}</shadow-root>`;
                                }
                                return html;
                            };
                            return serialize(document.documentElement);
                        }"""
                    )
                except Exception:
                    continue
                if content:
                    frame_html_parts.append(content)

            html = "\n<!-- frame-split -->\n".join(frame_html_parts) if frame_html_parts else await page.content()
            final_url = page.url
            redirect_hops = 0
            if response is not None:
                request = response.request
                while request.redirected_from is not None:
                    redirect_hops += 1
                    request = request.redirected_from
            return html, final_url, redirect_hops
