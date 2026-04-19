"""Playwright wrapper that fetches a page's rendered HTML.

A single browser instance is reused across requests for performance.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Optional

from playwright.async_api import Browser, async_playwright


class BrowserPool:
    """Lazy singleton browser. Safe to use across FastAPI request handlers."""

    def __init__(self) -> None:
        self._pw = None
        self._browser: Optional[Browser] = None

    async def start(self) -> None:
        if self._browser:
            return
        self._pw = await async_playwright().start()
        headless = os.getenv("HEADLESS", "true").lower() != "false"
        self._browser = await self._pw.chromium.launch(headless=headless)

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._pw:
            await self._pw.stop()
            self._pw = None

    async def fetch_html(self, url: str) -> str:
        if not self._browser:
            await self.start()
        assert self._browser is not None

        context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            locale="en-US",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()
        timeout = int(os.getenv("NAV_TIMEOUT_MS", "30000"))
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            # Give dynamic content a moment to settle
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            html = await page.content()
            return html
        finally:
            await context.close()


pool = BrowserPool()


@asynccontextmanager
async def lifespan_browser():
    await pool.start()
    try:
        yield
    finally:
        await pool.stop()
