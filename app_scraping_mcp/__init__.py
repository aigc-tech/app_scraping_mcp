"""High level package exports for the app scraping MCP server."""
from __future__ import annotations

from .scraper import AppStoreScraper, GooglePlayScraper, scrape_app

__all__ = [
    "create_server",
    "AppStoreScraper",
    "GooglePlayScraper",
    "scrape_app",
]


def create_server():
    from .server import create_server as _create_server

    return _create_server()
