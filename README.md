# app_scraping_mcp

An experimental [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server
that extracts structured metadata from Apple App Store and Google Play application
detail pages. The scraper is tuned to avoid common anti-bot countermeasures by using
rotating user agents, configurable retries, and optional Playwright-powered blob video
downloads.

## Features

- Robust HTTP client with retry/backoff and user-agent rotation.
- Store-specific parsers that surface the app name, bundle or package identifier,
  full description, screenshots, and preview videos.
- Optional video downloader that stores previews locally. Blob URLs are resolved via
  Playwright when available.
- CLI for ad-hoc scraping and an MCP server endpoint for tool integrations.

## Installation

```bash
pip install -e .
```

To enable blob video downloads install Playwright extras and ensure the browsers are
installed:

```bash
pip install playwright
playwright install chromium
```

## Usage

### CLI

```bash
app-scraping-mcp "https://play.google.com/store/apps/details?id=com.example"
```

Add `--download-videos` to persist preview videos to disk.

### MCP Server

Launch the server via `python -m app_scraping_mcp.server` within an MCP-compatible
runtime, or instantiate it programmatically:

```python
from app_scraping_mcp import create_server

server = create_server()
server.run()
```

The exposed MCP tool is named `scrape` and accepts the parameters:

- `url`: required app detail URL.
- `download_videos`: optional boolean toggle.
- `video_dir`: optional destination directory for downloaded videos.

The tool returns a JSON payload containing the parsed metadata and any downloaded
video paths.
