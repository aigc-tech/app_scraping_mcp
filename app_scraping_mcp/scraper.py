"""High level scraping utilities that orchestrate HTTP fetching and parsing."""
from __future__ import annotations

import dataclasses
import pathlib
from dataclasses import dataclass
from typing import Any, Optional

from .http_client import AntiScrapingSession
from .media import BlobFetcher, save_videos
from .parsers.apple import AppleAppDetails, parse_app_page as parse_apple_page
from .parsers.google_play import GooglePlayDetails, parse_app_page as parse_google_play_page


@dataclass
class ScrapeResult:
    store: str
    url: str
    raw_data: dict[str, Any]
    videos: list[str]
    screenshots: list[str]
    downloaded_videos: list[pathlib.Path]


class BaseScraper:
    store: str

    def __init__(self, *, session: Optional[AntiScrapingSession] = None) -> None:
        self.session = session or AntiScrapingSession()

    def fetch(self, url: str) -> str:
        response = self.session.get(url)
        response.raise_for_status()
        return response.text

    def parse(self, html: str):  # pragma: no cover - interface
        raise NotImplementedError

    def scrape(
        self,
        url: str,
        *,
        download_video_dir: Optional[pathlib.Path] = None,
        blob_fetcher: Optional[BlobFetcher] = None,
    ) -> ScrapeResult:
        html = self.fetch(url)
        parsed = self.parse(html)
        data = dataclasses.asdict(parsed)

        videos = data.pop("videos", [])
        screenshots = data.pop("screenshots", [])
        downloaded: list[pathlib.Path] = []
        if download_video_dir and videos:
            downloaded = save_videos(
                videos,
                output_dir=download_video_dir,
                session=self.session,
                referer=url,
                blob_fetcher=blob_fetcher,
            )

        data.update({"screenshots": screenshots, "videos": videos})
        return ScrapeResult(
            store=self.store,
            url=url,
            raw_data=data,
            videos=videos,
            screenshots=screenshots,
            downloaded_videos=downloaded,
        )


class AppStoreScraper(BaseScraper):
    store = "apple"

    def parse(self, html: str) -> AppleAppDetails:
        return parse_apple_page(html)


class GooglePlayScraper(BaseScraper):
    store = "google_play"

    def parse(self, html: str) -> GooglePlayDetails:
        return parse_google_play_page(html)


def scrape_app(
    url: str,
    *,
    session: Optional[AntiScrapingSession] = None,
    download_video_dir: Optional[pathlib.Path] = None,
    blob_fetcher: Optional[BlobFetcher] = None,
) -> ScrapeResult:
    session = session or AntiScrapingSession()
    scraper: BaseScraper
    if "apps.apple.com" in url:
        scraper = AppStoreScraper(session=session)
    elif "play.google.com" in url:
        scraper = GooglePlayScraper(session=session)
    else:
        raise ValueError("Unsupported store URL")
    return scraper.scrape(
        url,
        download_video_dir=download_video_dir,
        blob_fetcher=blob_fetcher,
    )


__all__ = [
    "ScrapeResult",
    "BaseScraper",
    "AppStoreScraper",
    "GooglePlayScraper",
    "scrape_app",
]
