"""Helpers for handling media assets discovered on store pages."""
from __future__ import annotations

import os
import pathlib
import urllib.request
from typing import Callable, Iterable, Optional

from .http_client import AntiScrapingSession


class MediaDownloadError(RuntimeError):
    """Raised when downloading remote media fails."""


BlobFetcher = Callable[[str], bytes]


def _ensure_directory(path: pathlib.Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def download_binary(url: str, *, session: Optional[AntiScrapingSession] = None) -> bytes:
    session = session or AntiScrapingSession()
    response = session.get(url)
    response.raise_for_status()
    return response.content


def download_to_file(url: str, dest_path: pathlib.Path, *, session: Optional[AntiScrapingSession] = None) -> pathlib.Path:
    data = download_binary(url, session=session)
    _ensure_directory(dest_path.parent)
    dest_path.write_bytes(data)
    return dest_path


def save_videos(
    videos: Iterable[str],
    *,
    session: Optional[AntiScrapingSession] = None,
    output_dir: pathlib.Path,
    referer: Optional[str] = None,
    blob_fetcher: Optional[BlobFetcher] = None,
) -> list[pathlib.Path]:
    session = session or AntiScrapingSession()
    saved_paths: list[pathlib.Path] = []
    headers = {"Referer": referer} if referer else None
    for index, video_url in enumerate(videos, start=1):
        suffix = os.path.splitext(video_url.split("?")[0])[1] or ".mp4"
        target_path = output_dir / f"video_{index}{suffix}"

        if video_url.startswith("blob:"):
            if not blob_fetcher:
                raise MediaDownloadError(
                    "Encountered a blob: URL. Provide a blob_fetcher callback that "
                    "can resolve it via a browser context."
                )
            data = blob_fetcher(video_url)
            _ensure_directory(target_path.parent)
            target_path.write_bytes(data)
            saved_paths.append(target_path)
            continue

        request = urllib.request.Request(video_url, headers=headers or {})
        try:
            with urllib.request.urlopen(request, timeout=session.timeout) as response:  # type: ignore[arg-type]
                _ensure_directory(target_path.parent)
                with target_path.open("wb") as file:
                    while True:
                        chunk = response.read(64 * 1024)
                        if not chunk:
                            break
                        file.write(chunk)
        except Exception as exc:  # pragma: no cover - network dependent
            raise MediaDownloadError(f"Failed to download {video_url}: {exc}") from exc
        saved_paths.append(target_path)
    return saved_paths


__all__ = ["MediaDownloadError", "download_to_file", "save_videos"]
