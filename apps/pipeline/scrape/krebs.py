"""Scrape KrebsOnSecurity.com cybercrime reporting.

Targets the most relevant categories for criminal organization profiling:
  - neer-do-well-news  — named criminal actors, group profiles, prosecutions
  - ransomware         — ransomware gang coverage
  - data-breaches      — breach attribution and group identification
  - web-fraud-2-0      — carding, fraud networks, organized crime

Respects robots.txt Crawl-Delay: 35 seconds between requests.

Usage:
    python -m apps.pipeline.scrape.krebs
    python -m apps.pipeline.scrape.krebs --categories neer-do-well-news ransomware
    python -m apps.pipeline.scrape.krebs --force
    python -m apps.pipeline.scrape.krebs --limit 50
"""

import argparse
import re
import time

from .common import fetch_with_retry, get_client, page_exists, save_page

SOURCE = "krebs"
BASE_URL = "https://krebsonsecurity.com"

# Crawl-Delay from robots.txt — must be respected
CRAWL_DELAY = 36.0  # slightly over the 35s minimum

# Categories that contain cybercrime group coverage
# Ordered by signal quality for gang.guide
DEFAULT_CATEGORIES = [
    "neer-do-well-news",   # named criminal actor profiles — highest signal
    "ransomware",          # ransomware gang coverage
    "web-fraud-2-0",       # carding forums, fraud networks
    "spam-nation",         # spam/botnet criminal organizations
    "ddos-for-hire",       # DDoS-as-a-service criminal groups
]

# Skip content that isn't criminal organization coverage
SKIP_PATTERNS = re.compile(
    r"/category/|/tag/|/author/|/page/|\?|#|"
    r"/(patches|how-to-break-into-security|security-tools|"
    r"internet-of-things-iot|ashley-madison|doge|employment-fraud)/"
)


def get_category_pages(client, category: str) -> list[str]:
    """Fetch all article URLs from a category via pagination."""
    urls = []
    page = 1

    while True:
        cat_url = f"{BASE_URL}/category/{category}/" + (f"page/{page}/" if page > 1 else "")
        resp = fetch_with_retry(client, cat_url)
        if not resp or resp.status_code == 404:
            break

        # Extract article URLs from the category listing
        found = re.findall(
            r'<h2[^>]*class="[^"]*entry-title[^"]*"[^>]*>.*?<a[^>]*href="([^"]*)"',
            resp.text,
            re.DOTALL,
        )
        if not found:
            # Try alternate pattern
            found = re.findall(
                r'href="(https://krebsonsecurity\.com/\d{4}/\d{2}/[^"]+)"',
                resp.text,
            )
            found = list(set(found))  # dedupe

        if not found:
            break

        # Filter to article URLs only
        article_urls = [
            u for u in found
            if re.match(r"https://krebsonsecurity\.com/\d{4}/\d{2}/[^/]+/?$", u)
            and not SKIP_PATTERNS.search(u)
        ]
        urls.extend(article_urls)

        # Check if there's a next page
        if f"/page/{page + 1}/" not in resp.text and "next" not in resp.text.lower():
            break

        page += 1
        time.sleep(CRAWL_DELAY)

    return list(dict.fromkeys(urls))  # preserve order, dedupe


def slug_from_url(url: str) -> str:
    """Extract a clean slug from a Krebs article URL.

    e.g. https://krebsonsecurity.com/2026/08/who-runs-the-gentlemen/
      → 2026-08-who-runs-the-gentlemen
    """
    m = re.match(r"https://krebsonsecurity\.com/(\d{4})/(\d{2})/([^/]+)/?$", url)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return url.rstrip("/").split("/")[-1]


def scrape(
    categories: list[str] | None = None,
    force: bool = False,
    limit: int = 0,
):
    """Scrape Krebs articles from specified categories."""
    if categories is None:
        categories = DEFAULT_CATEGORIES

    client = get_client()
    all_urls: list[str] = []

    print(f"Fetching article lists from {len(categories)} categories...")
    for cat in categories:
        print(f"  Scanning /{cat}/...")
        urls = get_category_pages(client, cat)
        print(f"    Found {len(urls)} articles")
        all_urls.extend(urls)
        time.sleep(CRAWL_DELAY)

    # Deduplicate (same article may appear in multiple categories)
    all_urls = list(dict.fromkeys(all_urls))
    print(f"\nTotal unique articles: {len(all_urls)}")

    if limit:
        all_urls = all_urls[:limit]
        print(f"Limiting to {limit} articles")

    scraped = 0
    skipped = 0

    for url in all_urls:
        slug = slug_from_url(url)
        if not slug:
            continue

        if not force and page_exists(SOURCE, slug):
            skipped += 1
            continue

        resp = fetch_with_retry(client, url)
        if not resp:
            print(f"  FAIL: {url}")
            time.sleep(CRAWL_DELAY)
            continue

        # Extract article metadata from the HTML
        title_m = re.search(r'<title>([^<]+)</title>', resp.text)
        raw_title = title_m.group(1) if title_m else slug
        # Decode HTML entities in title
        import html
        title = html.unescape(raw_title).replace(" – Krebs on Security", "").replace(" — Krebs on Security", "").strip()

        date_m = re.search(r'<time[^>]*datetime="([^"]+)"', resp.text)
        pub_date = date_m.group(1)[:10] if date_m else ""

        # Extract categories/tags for this article
        cats_raw = re.findall(r'rel="category tag"[^>]*>([^<]+)<', resp.text)

        metadata = {
            "title": title,
            "pub_date": pub_date,
            "categories": cats_raw,
            "source_url": url,
        }

        save_page(source=SOURCE, slug=slug, url=url, content=resp.text, metadata=metadata)
        scraped += 1
        print(f"  [{scraped}] {title[:65]}")

        # Respect crawl delay
        time.sleep(CRAWL_DELAY)

    print(f"\nDone: {scraped} scraped, {skipped} already cached (of {len(all_urls)} total)")
    print(f"Source key: '{SOURCE}' — run: just pipeline {SOURCE}")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape KrebsOnSecurity.com cybercrime reporting"
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        default=DEFAULT_CATEGORIES,
        help=f"Categories to scrape (default: {DEFAULT_CATEGORIES})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-scrape even if already cached",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max articles to scrape (0 = all)",
    )
    args = parser.parse_args()
    scrape(categories=args.categories, force=args.force, limit=args.limit)


if __name__ == "__main__":
    main()
