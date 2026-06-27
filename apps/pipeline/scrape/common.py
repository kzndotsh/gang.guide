"""Shared scraping utilities: rate limiting, retry, headers, output format."""

import os
import time
import random
import hashlib
import json
from pathlib import Path

import httpx

USER_AGENT = "GangGuideBot/1.0 (+https://gang.guide)"
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 5

DATA_RAW = Path(__file__).resolve().parent.parent.parent.parent / "data" / "raw"


def get_client() -> httpx.Client:
    return httpx.Client(
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
        },
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
    )


def jitter():
    """Random delay between requests."""
    time.sleep(random.uniform(1.0, 4.0))


def fetch_with_retry(client: httpx.Client, url: str) -> httpx.Response | None:
    """Fetch URL with exponential backoff on retryable errors."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.get(url)
            if resp.status_code == 200:
                return resp
            if resp.status_code in (429, 503):
                wait = min(2 ** attempt, 16)
                if resp.status_code == 429:
                    wait = max(wait, 15 * (attempt + 1))
                time.sleep(wait)
                continue
            if resp.status_code in (404, 403, 410):
                return None  # permanent failure
            resp.raise_for_status()
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            if attempt >= MAX_RETRIES - 1:
                return None
            wait = min(2 ** attempt, 16)
            time.sleep(wait)
    return None


def save_page(source: str, slug: str, url: str, content: str, metadata: dict | None = None):
    """Save a scraped page to data/raw/{source}/{slug}/."""
    out_dir = DATA_RAW / source / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "url.txt").write_text(url + "\n", encoding="utf-8")
    (out_dir / "content.txt").write_text(content, encoding="utf-8")
    if metadata:
        (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def content_hash(text: str) -> str:
    """SHA256 of content for dedup."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def page_exists(source: str, slug: str) -> bool:
    """Check if a page has already been scraped."""
    return (DATA_RAW / source / slug / "content.txt").exists()
