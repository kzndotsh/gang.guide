"""Scrape Chicago Gang History pages.

Already have 97 pages in data/raw/chicago_history/ from prior session.
This scraper handles incremental updates.

Usage:
    python -m apps.pipeline.scrape.cgh
    python -m apps.pipeline.scrape.cgh --force
"""

import argparse
import re
from pathlib import Path

from .common import get_client, jitter, fetch_with_retry, save_page, page_exists

SOURCE = "chicago_history"
BASE_URL = "https://chicagoganghistory.com"

# Known gang page URLs (from site index)
GANG_PAGES = [
    "/gang/black-disciples/",
    "/gang/gangster-disciples/",
    "/gang/gangster-two-six/",
    "/gang/almighty-latin-kings/",
    "/gang/vice-lords/",
    "/gang/almighty-black-p-stones/",
    "/gang/insane-gangster-satan-disciples/",
    "/gang/almighty-imperial-gangsters/",
    "/gang/maniac-latin-disciples/",
    "/gang/new-breeds/",
    "/gang/almighty-gaylords/",
    "/gang/akrohs-flip-city-kings/",
    "/gang/almighty-ambrose/",
    "/gang/insane-ashland-vikings/",
    "/gang/almighty-bishops/",
    "/gang/black-souls/",
    "/gang/almighty-brazers/",
    "/gang/insane-c-notes/",
    "/gang/chi-west/",
    "/gang/insane-gangster-city-knights/",
    "/gang/insane-cullerton-deuces/",
    "/gang/la-familia-stones/",
    "/gang/four-corner-hustlers/",
    "/gang/puerto-rican-future-stones/",
    "/gang/gangster-stones/",
    "/gang/almighty-harrison-gents/",
    "/gang/insane-deuces/",
    "/gang/insane-dragons/",
    "/gang/insane-majestics/",
    "/gang/almighty-insane-north-side-popes/",
    "/gang/south-side-almighty-insane-popes/",
    "/gang/insane-unknowns/",
    "/gang/insane-king-cobras/",
    "/gang/almighty-krazy-get-down-boys/",
    "/gang/la-raza/",
    "/gang/almighty-latin-angels/",
    "/gang/insane-latin-brothers/",
    "/gang/almighty-insane-latin-counts/",
    "/gang/latin-dragons/",
    "/gang/almighty-latin-eagles/",
    "/gang/insane-latin-jivers/",
    "/gang/universal-insane-latin-lovers/",
    "/gang/almighty-latin-pachucos/",
    "/gang/latin-souls/",
    "/gang/almighty-latin-stones/",
    "/gang/latin-stylers/",
    "/gang/almighty-los-bebe-stones/",
    "/gang/maniac-campbell-boys/",
    "/gang/mickey-cobras/",
    "/gang/milwaukee-kings/",
    "/gang/almighty-noble-knights/",
    "/gang/insane-la-orquestra-albany/",
    "/gang/gangster-party-people/",
    "/gang/almighty-party-players/",
    "/gang/almighty-saints/",
    "/gang/almighty-simon-city-royals/",
    "/gang/sin-city-boys/",
    "/gang/insane-spanish-cobras/",
    "/gang/spanish-gangster-disciples/",
    "/gang/spanish-lords/",
    "/gang/spanish-vice-lords/",
    "/gang/taylor-jousters/",
    "/gang/almighty-twelfth-street-players/",
    "/gang/insane-two-two-boys/",
    "/gang/warlords-wicker-park-la-familia-warlords/",
    "/gang/insane-ylo-cobras/",
    "/gang/maniac-ylo-disciples/",
]


def slug_from_path(path: str) -> str:
    return path.strip("/").split("/")[-1]


def scrape(force: bool = False):
    client = get_client()
    scraped = 0
    skipped = 0

    for path in GANG_PAGES:
        slug = slug_from_path(path)
        if not force and page_exists(SOURCE, slug):
            skipped += 1
            continue

        url = BASE_URL + path
        resp = fetch_with_retry(client, url)
        if not resp:
            print(f"  FAIL: {slug}")
            continue

        save_page(source=SOURCE, slug=slug, url=url, content=resp.text)
        scraped += 1
        print(f"  [{scraped}] {slug}")
        jitter()

    print(f"\nDone: {scraped} scraped, {skipped} skipped")


def main():
    parser = argparse.ArgumentParser(description="Scrape Chicago Gang History")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    scrape(force=args.force)


if __name__ == "__main__":
    main()
