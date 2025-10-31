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
    assert "Sample description" in details.description
    assert details.screenshots == [
        "https://example.com/shot1.png",
        "https://example.com/shot2.png",
    ]
    assert details.videos == ["https://example.com/video.mp4"]


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
