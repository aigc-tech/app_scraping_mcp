"""Parser for Google Play Store application pages."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

_JSON_LD_RE = re.compile(
    r"<script[^>]+type=\"application/ld\+json\"[^>]*>(.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)
_JSON_CALLBACK_RE = re.compile(r"AF_initDataCallback\((\{.*?\})\);?", re.DOTALL)
_SOFTWARE_APP_RE = re.compile(r"\{\"@type\":\"SoftwareApplication\".*?\}", re.DOTALL)
_PACKAGE_RE = re.compile(r"/store/apps/details\?id=([\w.]+)")
_DESCRIPTION_RE = re.compile(r"<div[^>]+itemprop=\"description\"[^>]*>(.*?)</div>", re.DOTALL | re.IGNORECASE)
_IMG_RE = re.compile(r"<img[^>]+(?:src|data-src|srcset|data-srcset)=\"([^\"]+)\"", re.IGNORECASE)
_IFRAME_RE = re.compile(r"<iframe[^>]+allow=\"[^\"]*autoplay[^\"]*\"[^>]+src=\"([^\"]+)\"", re.IGNORECASE)
_BUTTON_RE = re.compile(r"<button[^>]+data-trailer-url=\"([^\"]+)\"", re.IGNORECASE)
_META_VIDEO_RE = re.compile(r"<meta[^>]+itemprop=\"video\"[^>]+content=\"([^\"]+)\"", re.IGNORECASE)
_TITLE_RE = re.compile(r"<h1[^>]*><span>([^<]+)</span>", re.IGNORECASE)


@dataclass
class GooglePlayDetails:
    name: str
    package: Optional[str]
    description: str
    screenshots: List[str]
    videos: List[str]


def _extract_json_candidates(html_text: str) -> Iterable[Dict[str, Any]]:
    for match in _JSON_LD_RE.finditer(html_text):
        try:
            yield json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
    for match in _JSON_CALLBACK_RE.finditer(html_text):
        snippet = match.group(1)
        start = snippet.find("{")
        end = snippet.rfind("}") + 1
        try:
            yield json.loads(snippet[start:end])
        except json.JSONDecodeError:
            continue
    for match in _SOFTWARE_APP_RE.finditer(html_text):
        try:
            yield json.loads(match.group(0))
        except json.JSONDecodeError:
            continue


def _pick_payload(html_text: str) -> Dict[str, Any]:
    for candidate in _extract_json_candidates(html_text):
        if isinstance(candidate, dict) and candidate.get("@type") == "SoftwareApplication":
            return candidate
    return {}


def _clean_html(raw: str) -> str:
    return re.sub(r"<[^>]+>", " ", raw or "").strip()


def parse_app_page(html_text: str) -> GooglePlayDetails:
    payload = _pick_payload(html_text)

    name = payload.get("name")
    if not name:
        title = _TITLE_RE.search(html_text)
        name = title.group(1) if title else ""

    package = payload.get("applicationId")
    if not package:
        match = _PACKAGE_RE.search(html_text)
        package = match.group(1) if match else None

    description = ""
    if "description" in payload:
        description = _clean_html(payload["description"])
    else:
        match = _DESCRIPTION_RE.search(html_text)
        description = _clean_html(match.group(1)) if match else ""

    screenshots: List[str] = []
    for img_match in _IMG_RE.finditer(html_text):
        src = img_match.group(1)
        if " " in src:
            src = src.split()[0]
        if "?" in src:
            src = src.split("?", 1)[0]
        if "=w" in src:
            src = src.split("=w")[0]
        screenshots.append(src)

    videos: List[str] = []
    videos.extend(match.group(1) for match in _IFRAME_RE.finditer(html_text))
    videos.extend(match.group(1) for match in _BUTTON_RE.finditer(html_text))
    videos.extend(match.group(1) for match in _META_VIDEO_RE.finditer(html_text))

    def _unique(seq: Iterable[str]) -> List[str]:
        seen = set()
        out: List[str] = []
        for item in seq:
            if not item or item in seen:
                continue
            seen.add(item)
            out.append(item)
        return out

    return GooglePlayDetails(
        name=name.strip(),
        package=package,
        description=description,
        screenshots=_unique(screenshots),
        videos=_unique(videos),
    )


__all__ = ["GooglePlayDetails", "parse_app_page"]
