"""Scrape DetroitStreetGangs.com gang profile pages.

Fetches all gang profile pages from the sitemap, skipping non-profile pages
(glossary, maps, meta pages).

Usage:
    python -m apps.pipeline.scrape.dsg
    python -m apps.pipeline.scrape.dsg --force
"""

import argparse
import re

from .common import fetch_with_retry, get_client, jitter, page_exists, save_page

SOURCE = "detroit_dsg"
BASE_URL = "https://detroitstreetgangs.com"
SITEMAP_URL = f"{BASE_URL}/page-sitemap.xml"

# Pages to skip (non-profile meta/reference pages)
SKIP_SLUGS = {
    "glossary-of-gang-related-terms-activities-and-identifiers",
    "urban-map-review-detroits-gang-street-geography-maps",
    "tagger-crews-street-groups-in-detroit",
    "hybrid-gangs-mixed-affiliation-groups",
    "major-neighborhood-based-gang-street-cliques-profiles",
    "historical-defunct-sets-detroit-mi",
    "the-5s-and-the-4s",
}


def get_pages_from_sitemap(client) -> list[str]:
    """Parse page URLs from the WordPress sitemap."""
    resp = fetch_with_retry(client, SITEMAP_URL)
    if not resp:
        return []
    urls = re.findall(r"<!\[CDATA\[(https://detroitstreetgangs\.com/[^]]+)\]\]>", resp.text)
    # Filter to profile pages only (no images, no homepage, no skip slugs)
    return [
        u for u in urls
        if u != f"{BASE_URL}/"
        and slug_from_url(u) not in SKIP_SLUGS
        and not re.search(r"\.(jpg|jpeg|png|gif|webp|svg)$", u, re.IGNORECASE)
    ]


def slug_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def scrape(force: bool = False):
    client = get_client()
    pages = get_pages_from_sitemap(client)
    if not pages:
        print("Failed to fetch sitemap")
        return

    print(f"Found {len(pages)} profile pages")
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
    parser = argparse.ArgumentParser(description="Scrape DetroitStreetGangs.com")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    scrape(force=args.force)


if __name__ == "__main__":
    main()
