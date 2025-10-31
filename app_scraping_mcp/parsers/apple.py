"""Parser for Apple App Store application pages."""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set

_SCRIPT_RE = re.compile(
    r"<script[^>]+id=\"shoebox-media-api-cache-[^\"]+\"[^>]*>(.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)
_JSON_SCRIPT_RE = re.compile(
    r"<script[^>]+type=\"application/json\"[^>]*>(.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)
_LD_JSON_RE = re.compile(
    r"<script[^>]+type=\"application/ld\+json\"[^>]*>(.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)
_FASTBOOT_RE = re.compile(
    r"<script[^>]+type=\"fastboot/shoebox\"[^>]*>(.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)
_META_RE = re.compile(
    r"<meta[^>]+name=\"description\"[^>]+content=\"([^\"]*)\"", re.IGNORECASE
)
_TITLE_RE = re.compile(
    r"<meta[^>]+property=\"og:title\"[^>]+content=\"([^\"]*)\"", re.IGNORECASE
)
_BUNDLE_RE = re.compile(r"bundleId\"\s*:\s*\"([^\"]+)\"")
_IMG_ATTR_RE = re.compile(
    r"<img[^>]+?(?:data-(?:src|screenshot-url)|src|srcset|data-srcset)=\"([^\"]+)\"",
    re.IGNORECASE,
)
_IMG_DATA_RE = re.compile(
    r"data-(?:screenshot-url|gallery-item-url)=\"([^\"]+)\"", re.IGNORECASE
)
_VIDEO_SOURCE_RE = re.compile(
    r"<(?:video|source)[^>]+?(?:src|data-src|data-video-url|data-preview-url|data-hls-url)=\"([^\"]+)\"",
    re.IGNORECASE,
)
_VIDEO_DATA_RE = re.compile(
    r"data-(?:video-url|preview-url|hls-url|stream-url)=\"([^\"]+)\"",
    re.IGNORECASE,
)

_APP_STATE_MARKER = "window.__APP_STORE_STATE__"


@dataclass
class AppleAppDetails:
    name: str
    bundle_id: Optional[str]
    description: str
    screenshots: List[str]
    videos: List[str]


def _extract_attributes(html_text: str) -> Dict[str, Any]:
    collected: Dict[str, Any] = {"screenshots": [], "videos": []}
    for blob in _iter_json_blobs(html_text):
        payload = _parse_json_blob(blob)
        if payload is None:
            continue
        _collect_from_json(payload, collected)
    return collected


def _iter_json_blobs(html_text: str) -> Iterable[str]:
    seen: Set[str] = set()
    for blob in _extract_app_state_json(html_text):
        if blob and blob not in seen:
            seen.add(blob)
            yield blob
    for regex in (_SCRIPT_RE, _JSON_SCRIPT_RE, _LD_JSON_RE, _FASTBOOT_RE):
        for match in regex.finditer(html_text):
            blob = html.unescape(match.group(1)).strip()
            if blob and blob not in seen:
                seen.add(blob)
                yield blob


def _extract_app_state_json(html_text: str) -> Iterable[str]:
    start = 0
    while True:
        marker_index = html_text.find(_APP_STATE_MARKER, start)
        if marker_index == -1:
            break
        assign_index = html_text.find("=", marker_index)
        if assign_index == -1:
            break
        json_text = _extract_json_object(html_text, assign_index + 1)
        if not json_text:
            break
        yield json_text
        start = assign_index + len(json_text)


def _extract_json_object(text: str, start: int) -> Optional[str]:
    length = len(text)
    while start < length and text[start] not in "{[":
        start += 1
    if start >= length:
        return None
    opening = text[start]
    closing = "}" if opening == "{" else "]"
    depth = 0
    for index in range(start, length):
        char = text[index]
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def _parse_json_blob(blob: str) -> Optional[Any]:
    cleaned = blob.strip()
    if cleaned.startswith("<!--") and cleaned.endswith("-->"):
        cleaned = cleaned[4:-3].strip()
    candidates = (cleaned, cleaned.rstrip(";"))
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _collect_from_json(data: Any, collected: Dict[str, Any], *, context: Optional[str] = None, visited: Optional[Set[int]] = None) -> None:
    if visited is None:
        visited = set()
    obj_id = id(data)
    if obj_id in visited:
        return
    visited.add(obj_id)

    if isinstance(data, dict):
        for key, value in data.items():
            lower = key.lower()
            if lower == "name" and isinstance(value, str) and not collected.get("name"):
                collected["name"] = value
            elif lower in {"bundleid", "bundleidentifier"}:
                string_value = _extract_string(value)
                if string_value and not collected.get("bundleId"):
                    collected["bundleId"] = string_value
            elif lower in {"description", "standarddescription", "softwaredescription"}:
                text_value = _extract_string(value)
                if text_value and not collected.get("description"):
                    collected["description"] = text_value

            new_context = context
            if "screenshot" in lower or "artwork" in lower and "url" not in lower:
                new_context = "screenshot"
            elif "preview" in lower or "video" in lower or "trailer" in lower:
                new_context = "video"

            if isinstance(value, str):
                if new_context == "screenshot":
                    _extend_media(collected.setdefault("screenshots", []), value)
                    continue
                if new_context == "video":
                    _extend_media(collected.setdefault("videos", []), value)
                    continue

            if lower in {"url", "source", "src", "srcurl", "asseturl", "contenturl", "hlsurl", "previewurl"}:
                if context == "screenshot":
                    _extend_media(collected.setdefault("screenshots", []), value)
                    _collect_from_json(value, collected, context=context, visited=visited)
                    continue
                if context == "video":
                    _extend_media(collected.setdefault("videos", []), value)
                    _collect_from_json(value, collected, context=context, visited=visited)
                    continue

            _collect_from_json(value, collected, context=new_context, visited=visited)
    elif isinstance(data, list):
        for item in data:
            _collect_from_json(item, collected, context=context, visited=visited)
    else:
        if context == "screenshot":
            _extend_media(collected.setdefault("screenshots", []), data)
        elif context == "video":
            _extend_media(collected.setdefault("videos", []), data)


def _extract_string(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for nested in value.values():
            extracted = _extract_string(nested)
            if extracted:
                return extracted
    elif isinstance(value, list):
        for nested in value:
            extracted = _extract_string(nested)
            if extracted:
                return extracted
    return None


def _extend_media(target: List[str], value: Any) -> None:
    if isinstance(value, str):
        target.extend(_split_media_value(value))
    elif isinstance(value, dict):
        for nested in value.values():
            _extend_media(target, nested)
    elif isinstance(value, (list, tuple, set)):
        for nested in value:
            _extend_media(target, nested)


def _split_media_value(value: str) -> List[str]:
    urls: List[str] = []
    for part in value.split(","):
        candidate = part.strip().split()[0] if part.strip() else ""
        normalized = _normalize_url(candidate)
        if normalized:
            urls.append(normalized)
    return urls or ([normalized] if (normalized := _normalize_url(value)) else [])


def _normalize_url(url: str) -> Optional[str]:
    if not url:
        return None
    cleaned = url.strip()
    if not cleaned:
        return None
    if cleaned.startswith("//"):
        cleaned = "https:" + cleaned
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        return cleaned
    return None


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

    screenshots = _merge_media_lists(
        _dedupe_media(attributes.get("screenshots")),
        _extract_screenshots_from_html(html_text),
    )

    videos = _merge_media_lists(
        _dedupe_media(attributes.get("videos")),
        _extract_videos_from_html(html_text),
    )

    unique_screenshots = sorted(set(screenshots))
    unique_videos = sorted(set(videos))

    return AppleAppDetails(
        name=name.strip(),
        bundle_id=bundle_id,
        description=description,
        screenshots=unique_screenshots,
        videos=unique_videos,
    )


def _dedupe_media(value: Any) -> List[str]:
    if not value:
        return []
    collected: List[str] = []
    _extend_media(collected, value)
    return [item for index, item in enumerate(collected) if item and item not in collected[:index]]


def _extract_screenshots_from_html(html_text: str) -> List[str]:
    urls: List[str] = []
    for match in _IMG_ATTR_RE.finditer(html_text):
        urls.extend(_split_media_value(match.group(1)))
    for match in _IMG_DATA_RE.finditer(html_text):
        url = _normalize_url(match.group(1))
        if url:
            urls.append(url)
    return [item for index, item in enumerate(urls) if item and item not in urls[:index]]


def _extract_videos_from_html(html_text: str) -> List[str]:
    urls: List[str] = []
    for match in _VIDEO_SOURCE_RE.finditer(html_text):
        urls.extend(_split_media_value(match.group(1)))
    for match in _VIDEO_DATA_RE.finditer(html_text):
        url = _normalize_url(match.group(1))
        if url:
            urls.append(url)
    return [item for index, item in enumerate(urls) if item and item not in urls[:index]]


def _merge_media_lists(primary: List[str], secondary: List[str]) -> List[str]:
    if not primary and not secondary:
        return []
    merged = list(primary)
    for item in secondary:
        if item and item not in merged:
            merged.append(item)
    return merged


__all__ = ["AppleAppDetails", "parse_app_page"]
