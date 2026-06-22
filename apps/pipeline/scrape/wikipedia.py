"""Scrape Wikipedia gang articles via MediaWiki API.

Usage:
    python -m apps.pipeline.scrape.wikipedia --categories "Crips sets" "Bloods sets" "Street gangs in Chicago"
    python -m apps.pipeline.scrape.wikipedia --urls urls.txt
    python -m apps.pipeline.scrape.wikipedia --discover
"""

import argparse
import json
import re
from pathlib import Path

from .common import get_client, jitter, fetch_with_retry, save_page, page_exists

MEDIAWIKI_API = "https://en.wikipedia.org/w/api.php"
SOURCE = "wikipedia"


def fetch_article(client, title: str) -> dict | None:
    """Fetch article text + revision ID via MediaWiki API."""
    params = {
        "action": "parse",
        "page": title,
        "prop": "text|revid|categories",
        "format": "json",
        "disabletoc": "true",
    }
    resp = fetch_with_retry(client, f"{MEDIAWIKI_API}?{'&'.join(f'{k}={v}' for k,v in params.items())}")
    if not resp:
        return None
    data = resp.json()
    if "error" in data:
        return None
    parse = data.get("parse", {})
    return {
        "title": parse.get("title", title),
        "revid": parse.get("revid"),
        "html": parse.get("text", {}).get("*", ""),
        "categories": [c["*"] for c in parse.get("categories", [])],
    }


def fetch_category_members(client, category: str, limit: int = 500) -> list[str]:
    """Get all article titles in a Wikipedia category."""
    titles = []
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": str(min(limit, 500)),
        "cmtype": "page",
        "format": "json",
    }
    url = f"{MEDIAWIKI_API}?{'&'.join(f'{k}={v}' for k,v in params.items())}"
    resp = fetch_with_retry(client, url)
    if resp:
        data = resp.json()
        for member in data.get("query", {}).get("categorymembers", []):
            titles.append(member["title"])
    return titles


def slug_from_title(title: str) -> str:
    s = re.sub(r'[^a-z0-9\s]', '', title.lower())
    return re.sub(r'\s+', '-', s.strip())[:80]


def scrape_articles(titles: list[str], force: bool = False):
    """Scrape a list of Wikipedia articles."""
    client = get_client()
    scraped = 0
    skipped = 0

    for title in titles:
        slug = slug_from_title(title)
        if not force and page_exists(SOURCE, slug):
            skipped += 1
            continue

        article = fetch_article(client, title)
        if not article:
            print(f"  FAIL: {title}")
            continue

        url = f"https://en.wikipedia.org/?oldid={article['revid']}" if article['revid'] else f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"

        save_page(
            source=SOURCE,
            slug=slug,
            url=url,
            content=article["html"],
            metadata={
                "title": article["title"],
                "revid": article["revid"],
                "categories": article["categories"],
            },
        )
        scraped += 1
        print(f"  [{scraped}] {title}")
        jitter()

    print(f"\nDone: {scraped} scraped, {skipped} skipped (already exist)")


GANG_CATEGORIES = [
    "Crips sets",
    "Bloods sets",
    "Street gangs in Chicago",
    "Latino street gangs",
    "African-American gangs",
    "Gangs in Los Angeles",
    "Gangs in New York City",
    "Outlaw motorcycle clubs",
    "Prison gangs in the United States",
    "White supremacist groups in the United States",
    "Organized crime groups in the United States",
]


def discover_articles(client) -> list[str]:
    """Auto-discover gang articles via Wikipedia categories."""
    all_titles = set()
    for cat in GANG_CATEGORIES:
        print(f"  Category: {cat}")
        titles = fetch_category_members(client, cat)
        all_titles.update(titles)
        print(f"    → {len(titles)} articles")
        jitter()
    return sorted(all_titles)


def main():
    parser = argparse.ArgumentParser(description="Scrape Wikipedia gang articles")
    parser.add_argument("--categories", nargs="+", help="Wikipedia categories to scrape")
    parser.add_argument("--urls", type=Path, help="File with one Wikipedia URL per line")
    parser.add_argument("--discover", action="store_true", help="Auto-discover via gang categories")
    parser.add_argument("--force", action="store_true", help="Re-scrape existing pages")
    args = parser.parse_args()

    if args.discover:
        client = get_client()
        titles = discover_articles(client)
        print(f"\nDiscovered {len(titles)} articles. Scraping...")
        scrape_articles(titles, force=args.force)
    elif args.categories:
        client = get_client()
        titles = []
        for cat in args.categories:
            titles.extend(fetch_category_members(client, cat))
        scrape_articles(titles, force=args.force)
    elif args.urls:
        titles = []
        for line in args.urls.read_text().strip().split("\n"):
            line = line.strip()
            if "/wiki/" in line:
                titles.append(line.split("/wiki/")[-1].replace("_", " "))
        scrape_articles(titles, force=args.force)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
