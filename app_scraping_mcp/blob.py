"""Utilities for resolving blob: URLs via Playwright."""
from __future__ import annotations

import asyncio
from typing import Callable


async def resolve_blob_with_playwright(page_url: str, blob_url: str) -> bytes:
    """Fetch blob URLs by evaluating JavaScript in a headless browser."""

    try:
        from playwright.async_api import async_playwright
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "Playwright is required to resolve blob: URLs but is not installed."
        ) from exc

    async with async_playwright() as pw:  # pragma: no cover - optional dependency
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(page_url, wait_until="networkidle")
        data = await page.evaluate(
            """
            async (blobUrl) => {
                const response = await fetch(blobUrl);
                const buffer = await response.arrayBuffer();
                return Array.from(new Uint8Array(buffer));
            }
            """,
            blob_url,
        )
        await browser.close()
    return bytes(data)


def sync_resolver(page_url: str) -> Callable[[str], bytes]:
    """Return a synchronous callable suitable for ``blob_fetcher`` arguments."""

    def _fetch(blob: str) -> bytes:
        return asyncio.run(resolve_blob_with_playwright(page_url, blob))

    return _fetch


__all__ = ["resolve_blob_with_playwright", "sync_resolver"]
