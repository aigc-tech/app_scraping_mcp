"""Model Context Protocol server exposing the scraping functionality."""
from __future__ import annotations

import asyncio
import json
import pathlib
from typing import Optional

from mcp.server.fastmcp import Context, FastMCP, Message

from .blob import sync_resolver
from .scraper import scrape_app


def create_server() -> FastMCP:
    server = FastMCP("app-scraping")

    @server.tool()
    async def scrape(  # type: ignore[misc]
        context: Context,
        url: str,
        *,
        download_videos: bool = False,
        video_dir: Optional[str] = None,
    ) -> Message:
        """Scrape application metadata from the Apple App Store or Google Play.

        Args:
            url: Application detail page.
            download_videos: When ``True`` the server attempts to download preview
                videos. Blob URLs are resolved automatically when Playwright is
                available in the environment.
            video_dir: Optional directory relative to the workspace root where the
                videos should be stored.
        """

        download_path: Optional[pathlib.Path] = None
        if download_videos:
            if video_dir:
                download_path = pathlib.Path(video_dir).expanduser()
            else:
                workspace = pathlib.Path(context.session_options.get("workspace", "."))
                download_path = workspace / "videos"

        blob_fetcher = None
        if download_videos:
            page_url = url

            blob_fetcher = sync_resolver(page_url)

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: scrape_app(
                url,
                download_video_dir=download_path,
                blob_fetcher=blob_fetcher,
            ),
        )

        body = json.dumps(
            {
                "store": result.store,
                "url": result.url,
                "data": result.raw_data,
                "videos": result.videos,
                "screenshots": result.screenshots,
                "downloaded_videos": [str(path) for path in result.downloaded_videos],
            },
            ensure_ascii=False,
            indent=2,
        )
        return Message(content=body, role="tool")

    return server


__all__ = ["create_server"]


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    create_server().run()
