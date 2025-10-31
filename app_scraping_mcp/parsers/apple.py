"""Parser for Apple App Store application pages."""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

_SCRIPT_RE = re.compile(
    r"<script[^>]+id=\"shoebox-media-api-cache-[^\"]+\"[^>]*>(.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)
_META_RE = re.compile(
    r"<meta[^>]+name=\"description\"[^>]+content=\"([^\"]*)\"", re.IGNORECASE
)
_TITLE_RE = re.compile(
    r"<meta[^>]+property=\"og:title\"[^>]+content=\"([^\"]*)\"", re.IGNORECASE
)
_BUNDLE_RE = re.compile(r"bundleId\"\s*:\s*\"([^\"]+)\"")
_IMG_RE = re.compile(r"<img[^>]+srcset=\"([^\"]+)\"", re.IGNORECASE)
_VIDEO_RE = re.compile(r"<video[^>]*>.*?<source[^>]+(?:src|data-src)=\"([^\"]+)\"", re.DOTALL | re.IGNORECASE)


@dataclass
class AppleAppDetails:
    name: str
    bundle_id: Optional[str]
    description: str
    screenshots: List[str]
    videos: List[str]


def _extract_attributes(html_text: str) -> Dict[str, Any]:
    match = _SCRIPT_RE.search(html_text)
    if not match:
        return {}
    script_content = html.unescape(match.group(1))
    try:
        payload = json.loads(script_content)
    except json.JSONDecodeError:
        return {}
    for value in payload.values():
        try:
            return value["data"][0]["attributes"]
        except (KeyError, IndexError, TypeError):
            continue
    return {}


def parse_app_page(html_text: str) -> AppleAppDetails:
    attributes = _extract_attributes(html_text)

    name = attributes.get("name")
    if not name:
        title_match = _TITLE_RE.search(html_text)
        name = title_match.group(1) if title_match else ""

    raw_description = attributes.get("description")
    if not raw_description:
        match = _META_RE.search(html_text)
        raw_description = match.group(1) if match else ""
    description = re.sub(r"<[^>]+>", " ", raw_description or "").strip()

    bundle_id = attributes.get("bundleId")
    if not bundle_id:
        match = _BUNDLE_RE.search(html_text)
        bundle_id = match.group(1) if match else None

    screenshots: List[str] = []
    platform = attributes.get("platformAttributes") or {}
    if isinstance(platform, dict):
        for value in platform.values():
            if isinstance(value, dict):
                screenshots.extend(value.get("screenshotUrls", []))
    if not screenshots:
        for img_match in _IMG_RE.finditer(html_text):
            first = img_match.group(1).split()[0]
            if first:
                screenshots.append(first)

    videos: List[str] = []
    previews = attributes.get("appPreviews")
    if isinstance(previews, dict):
        for platform in previews.values():
            if not isinstance(platform, dict):
                continue
            for item in platform.get("appPreviews", []):
                url = item.get("previewUrl")
                if url:
                    videos.append(url)
    if not videos:
        for video_match in _VIDEO_RE.finditer(html_text):
            videos.append(video_match.group(1))

    unique_screenshots = sorted(set(filter(None, screenshots)))
    unique_videos = sorted(set(filter(None, videos)))

    return AppleAppDetails(
        name=name.strip(),
        bundle_id=bundle_id,
        description=description,
        screenshots=unique_screenshots,
        videos=unique_videos,
    )


__all__ = ["AppleAppDetails", "parse_app_page"]
