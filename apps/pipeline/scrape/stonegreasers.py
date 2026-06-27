"""Scrape StoneGreasers.com gang profile pages.

Chicago and NYC historical gang profiles (1950s-70s era).
No sitemap — pages discovered from the /greaser/ index page.

Usage:
    python -m apps.pipeline.scrape.stonegreasers
    python -m apps.pipeline.scrape.stonegreasers --force
"""

import argparse
import re

from .common import fetch_with_retry, get_client, jitter, page_exists, save_page

SOURCE = "stonegreasers"
BASE_URL = "https://www.stonegreasers.com"

# Pages to skip (not gang profiles)
SKIP_SLUGS = {
    "index", "sitemap", "chicago_cold_case_murder", "risingupangry",
    "chicago_gang_study", "NewYorkTattooing", "usa_gangs", "conclay",
    "new_jersey_gangs", "swan",
}


def discover_pages(client) -> list[tuple[str, str]]:
    """Crawl /greaser/ index to find all profile pages."""
    resp = fetch_with_retry(client, BASE_URL + "/greaser/")
    if not resp:
        return []

    # Find all .html links under /greaser/
    urls = re.findall(r'https?://(?:www\.)?stonegreasers\.com/greaser/([^"]+\.html)', resp.text)
    # Also check gaylords712.com links (same site)
    urls += re.findall(r'https?://(?:www\.)?gaylords712\.com/greaser/([^"]+\.html)', resp.text)

    pages = []
    seen = set()
    for filename in urls:
        slug = filename.replace(".html", "")
        if slug in seen or slug in SKIP_SLUGS:
            continue
        seen.add(slug)
        url = f"{BASE_URL}/greaser/{filename}"
        pages.append((url, slug))

    return sorted(pages, key=lambda x: x[1])


def scrape(force: bool = False):
    client = get_client()
    pages = discover_pages(client)
    if not pages:
        print("Failed to discover pages")
        return

    print(f"Found {len(pages)} profile pages")
    scraped = 0
    skipped = 0

    for url, slug in pages:
        if not force and page_exists(SOURCE, slug):
            skipped += 1
            continue

        resp = fetch_with_retry(client, url)
        if not resp:
            print(f"  FAIL: {slug}")
            continue

        save_page(source=SOURCE, slug=slug, url=url, content=resp.text)
        scraped += 1
        print(f"  [{scraped}] {slug}")
        jitter()

    print(f"\nDone: {scraped} scraped, {skipped} skipped (of {len(pages)} total)")


def main():
    parser = argparse.ArgumentParser(description="Scrape StoneGreasers.com")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    scrape(force=args.force)


if __name__ == "__main__":
    main()
