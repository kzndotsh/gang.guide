"""Scrape NGCRC gang profile pages.

The site has no sitemap or directory listing. Profiles are linked from
/profile/profile.html and the reports page. We maintain a known list.

Usage:
    python -m apps.pipeline.scrape.ngcrc
    python -m apps.pipeline.scrape.ngcrc --force
"""

import argparse

from .common import fetch_with_retry, get_client, jitter, page_exists, save_page

SOURCE = "ngcrc"
BASE_URL = "https://www.ngcrc.com"

# Gang profiles with actual relationship data (manually curated from site crawl)
PROFILE_PAGES = [
    ("/ngcrc/bpsn2003.htm", "bpsn-black-p-stone-nation"),
    ("/ngcrc/bdprofile.html", "bd-black-disciples"),
    ("/ngcrc/page14.htm", "gd-gangster-disciples-federal"),
    ("/ngcrc/page15.htm", "lk-latin-kings"),
    ("/ngcrc/sataprof.htm", "sd-satan-disciples"),
    ("/ngcrc/viceprof.htm", "vl-vice-lords"),
]


def scrape(force: bool = False):
    client = get_client()
    scraped = 0
    skipped = 0

    for path, slug in PROFILE_PAGES:
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
    parser = argparse.ArgumentParser(description="Scrape NGCRC gang profiles")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    scrape(force=args.force)


if __name__ == "__main__":
    main()
