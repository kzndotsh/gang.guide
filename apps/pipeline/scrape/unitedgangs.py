"""Scrape UnitedGangs.com gang profile pages.

LA-focused gang profiles with alliances, rivalries, and territories.
Uses Jetpack sitemap (sitemap-1.xml, sitemap-2.xml).

Usage:
    python -m apps.pipeline.scrape.unitedgangs
    python -m apps.pipeline.scrape.unitedgangs --force
"""

import argparse
import re

from .common import fetch_with_retry, get_client, jitter, page_exists, save_page

SOURCE = "unitedgangs"
BASE_URL = "https://unitedgangs.com"
SITEMAP_URLS = [
    f"{BASE_URL}/sitemap-1.xml",
    f"{BASE_URL}/sitemap-2.xml",
]

# Pages to skip (not gang profiles)
SKIP_PATTERNS = re.compile(
    r"/(about|contact|privacy|terms|category|tag|author|page/|wp-content|wp-json|feed)"
    r"|^https://unitedgangs\.com/?$"
)


def get_pages_from_sitemaps(client) -> list[str]:
    """Fetch all gang profile URLs from sitemaps."""
    urls = []
    for sitemap_url in SITEMAP_URLS:
        resp = fetch_with_retry(client, sitemap_url)
        if not resp:
            continue
        found = re.findall(r"<loc>([^<]+)</loc>", resp.text)
        urls.extend(found)

    # Filter to gang profile pages only
    return [u for u in urls if not SKIP_PATTERNS.search(u)]


def slug_from_url(url: str) -> str:
    """Extract slug from URL path."""
    path = url.rstrip("/").split("/")[-1]
    return path


def scrape(force: bool = False):
    client = get_client()
    pages = get_pages_from_sitemaps(client)
    if not pages:
        print("Failed to fetch sitemaps")
        return

    print(f"Found {len(pages)} profile pages")
    scraped = 0
    skipped = 0

    for url in pages:
        slug = slug_from_url(url)
        if not slug:
            continue
        if not force and page_exists(SOURCE, slug):
            skipped += 1
            continue

        resp = fetch_with_retry(client, url)
        if not resp:
            print(f"  FAIL: {slug}")
            continue

        save_page(source=SOURCE, slug=slug, url=url, content=resp.text)
        scraped += 1
        if scraped % 50 == 0:
            print(f"  [{scraped}] {slug}")
        jitter()

    print(f"\nDone: {scraped} scraped, {skipped} skipped (of {len(pages)} total)")


def main():
    parser = argparse.ArgumentParser(description="Scrape UnitedGangs.com")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    scrape(force=args.force)


if __name__ == "__main__":
    main()
