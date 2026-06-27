"""Scrape NewYorkCityGangs.com historical gang pages.

WordPress site using page IDs. No sitemap available — we crawl from the homepage
and follow internal links to find all gang pages.

Usage:
    python -m apps.pipeline.scrape.nyc
    python -m apps.pipeline.scrape.nyc --force
"""

import argparse
import re

from .common import fetch_with_retry, get_client, jitter, page_exists, save_page

SOURCE = "nyc_historical"
BASE_URL = "https://newyorkcitygangs.com"


def discover_pages(client) -> list[str]:
    """Crawl homepage and key pages to find all gang page URLs."""
    seen = set()
    to_crawl = [BASE_URL + "/"]
    all_pages = []

    for start_url in to_crawl:
        resp = fetch_with_retry(client, start_url)
        if not resp:
            continue
        urls = re.findall(r'https://newyorkcitygangs\.com/\?page_id=(\d+)', resp.text)
        for pid in urls:
            if pid not in seen:
                seen.add(pid)
                all_pages.append(f"{BASE_URL}/?page_id={pid}")

    return sorted(all_pages)


def slug_from_url(url: str) -> str:
    m = re.search(r'page_id=(\d+)', url)
    return f"page-{m.group(1)}" if m else url.split("/")[-1]


def scrape(force: bool = False):
    client = get_client()
    pages = discover_pages(client)
    if not pages:
        print("Failed to discover pages")
        return

    print(f"Found {len(pages)} pages")
    scraped = 0
    skipped = 0

    for url in pages:
        slug = slug_from_url(url)
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
    parser = argparse.ArgumentParser(description="Scrape NewYorkCityGangs.com")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    scrape(force=args.force)


if __name__ == "__main__":
    main()
