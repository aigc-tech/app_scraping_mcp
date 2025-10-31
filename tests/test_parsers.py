from __future__ import annotations

from pathlib import Path

from app_scraping_mcp.parsers.apple import parse_app_page as parse_apple
from app_scraping_mcp.parsers.google_play import parse_app_page as parse_play

FIXTURES = Path(__file__).parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_apple_fixture():
    html = read_fixture("apple_app.html")
    details = parse_apple(html)
    assert details.name == "Sample App"
    assert details.bundle_id == "com.example.sample"
    assert details.description == "Sample description"
    expected_screenshots = sorted(
        [
            "https://example.com/state-shot1.png",
            "https://example.com/state-shot2.png",
            "https://example.com/type-shot.png",
            "https://example.com/type-json-shot.png",
            "https://example.com/ld-shot1.png",
            "https://example.com/ld-shot2.png",
            "https://example.com/html-shot1.jpg",
            "https://example.com/html-shot2.jpg",
            "https://example.com/html-shot3.jpg",
            "https://example.com/html-shot4.jpg",
            "https://example.com/html-shot5.jpg",
            "https://example.com/style-shot.png",
            "https://example.com/poster-shot.jpg",
        ]
    )
    expected_videos = sorted(
        [
            "https://example.com/state-video.mp4",
            "https://example.com/state-video.m3u8",
            "https://example.com/type-video.mp4",
            "https://example.com/type-video.m3u8",
            "https://example.com/type-json-video.mp4",
            "https://example.com/ld-video.mp4",
            "https://example.com/html-video.mp4",
            "https://example.com/html-video2.mp4",
        ]
    )
    assert details.screenshots == expected_screenshots
    assert details.videos == expected_videos


def test_parse_google_play_fixture():
    html = read_fixture("google_play_app.html")
    details = parse_play(html)
    assert details.name == "Sample Play App"
    assert details.package == "com.example.app"
    assert "Play description" in details.description
    assert details.screenshots == [
        "https://example.com/play1.jpg",
        "https://example.com/play2.jpg",
    ]
    assert details.videos == [
        "https://video.example.com/watch",
        "https://cdn.example.com/trailer.mp4",
    ]
