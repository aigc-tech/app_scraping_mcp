"""Command line entrypoint for manual scraping sessions."""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Optional

from .blob import sync_resolver
from .scraper import scrape_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="App detail page URL")
    parser.add_argument(
        "--download-videos",
        action="store_true",
        help="Download preview videos to disk.",
    )
    parser.add_argument(
        "--video-dir",
        type=pathlib.Path,
        help="Directory to store downloaded videos. Defaults to ./videos",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    download_dir = args.video_dir if args.download_videos else None
    if args.download_videos and download_dir is None:
        download_dir = pathlib.Path("videos")

    blob_fetcher = None
    if args.download_videos:

        blob_fetcher = sync_resolver(args.url)

    result = scrape_app(
        args.url,
        download_video_dir=download_dir,
        blob_fetcher=blob_fetcher,
    )

    output = {
        "store": result.store,
        "url": result.url,
        "data": result.raw_data,
        "videos": result.videos,
        "screenshots": result.screenshots,
        "downloaded_videos": [str(path) for path in result.downloaded_videos],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
