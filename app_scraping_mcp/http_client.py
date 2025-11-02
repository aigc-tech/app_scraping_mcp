"""HTTP client utilities tailored for resilient web scraping."""
from __future__ import annotations

import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping, MutableMapping, Optional


_DEFAULT_USER_AGENTS: tuple[str, ...] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
)


@dataclass
class HttpResponse:
    status_code: int
    headers: Mapping[str, str]
    content: bytes

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")

    def raise_for_status(self) -> None:
        if 200 <= self.status_code < 400:
            return
        raise urllib.error.HTTPError(
            url="",
            code=self.status_code,
            msg="HTTP error",
            hdrs=None,
            fp=None,
        )


@dataclass
class AntiScrapingSession:
    """Wrapper around ``urllib`` with anti-bot mitigations."""

    timeout: int = 25
    max_retries: int = 5
    backoff_factor: float = 1.6
    user_agents: Iterable[str] = _DEFAULT_USER_AGENTS
    proxies: Optional[Mapping[str, str]] = None
    default_headers: Dict[str, str] = field(
        default_factory=lambda: {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }
    )

    def _choose_user_agent(self) -> str:
        agents = tuple(self.user_agents)
        return random.choice(agents) if agents else _DEFAULT_USER_AGENTS[0]

    def _build_headers(self, headers: Optional[Mapping[str, str]]) -> MutableMapping[str, str]:
        merged: Dict[str, str] = dict(self.default_headers)
        merged["User-Agent"] = self._choose_user_agent()
        if headers:
            merged.update(headers)
        return merged

    def get(self, url: str, *, headers: Optional[Mapping[str, str]] = None) -> HttpResponse:
        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            delay = self.backoff_factor * random.uniform(0.8, 1.2) * (attempt - 1 or 0.2)
            if delay:
                time.sleep(delay)
            request = urllib.request.Request(url, headers=self._build_headers(headers))
            opener = urllib.request.build_opener()
            if self.proxies:
                proxy_handler = urllib.request.ProxyHandler(dict(self.proxies))
                opener.add_handler(proxy_handler)
            try:
                with opener.open(request, timeout=self.timeout) as response:
                    content = response.read()
                    status = getattr(response, "status", 200)
                    resp_headers = {k.lower(): v for k, v in response.headers.items()}
                    if status in {403, 429}:
                        last_error = urllib.error.HTTPError(url, status, "blocked", response.headers, None)
                        continue
                    return HttpResponse(status_code=status, headers=resp_headers, content=content)
            except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:  # pragma: no cover - network dependent
                last_error = exc
                continue
        raise RuntimeError(f"Failed to fetch {url!r} after {self.max_retries} attempts") from last_error


__all__ = ["AntiScrapingSession", "HttpResponse"]
