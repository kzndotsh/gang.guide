"""Scrape InSight Crime criminal organization profiles.

InSight Crime (insightcrime.org) maintains structured, research-quality profiles
of criminal organizations across Latin America. We target the subset with direct
US relevance: transnational street gangs (MS-13, Barrio 18), US-border cartels
(Sinaloa, Zetas, Gulf, Juarez, Barrio Azteca), and Tren de Aragua.

Profiles are discovered from the /criminal-profiles/ index page and filtered
to a curated US-relevant list. Remaining profiles are optionally scraped with
--all for future Latin American expansion.

Usage:
    python -m apps.pipeline.scrape.insightcrime           # US-relevant only (default)
    python -m apps.pipeline.scrape.insightcrime --all     # all 164 profiles
    python -m apps.pipeline.scrape.insightcrime --force   # re-scrape existing
"""

import argparse
import re

from .common import fetch_with_retry, get_client, jitter, page_exists, save_page

SOURCE = "insightcrime"
BASE_URL = "https://insightcrime.org"
PROFILES_INDEX = f"{BASE_URL}/criminal-profiles/"

# Profiles with direct US relevance (active in US, transnational, or US-origin)
US_RELEVANT_SLUGS = {
    # Central American street gangs (US-origin, active in US)
    "mara-salvatrucha-ms-13-profile",
    "barrio-18-profile",
    # Mexico cartels (border operations, US drug supply)
    "sinaloa-cartel-profile",
    "zetas-profile",
    "gulf-cartel-profile",
    "juarez-cartel-profile",
    "tijuana-cartel-profile",
    "jalisco-cartel-new-generation",
    "barrio-azteca-profile",
    "familia-michoacana-mexico-profile",
    "beltran-leyva-organization-profile",
    "knights-templar-profile",
    "northeast-cartel",
    # Venezuela — Tren de Aragua active across US
    "tren-de-aragua",
    # Ecuador — Latin Kings chapter
    "latin-kings-ecuador",
    # Brazil — PCC has US cartel connections
    "first-capital-command-pcc-profile",
}


def discover_profiles(client) -> list[tuple[str, str]]:
    """Fetch the criminal-profiles index and return (url, slug) pairs."""
    resp = fetch_with_retry(client, PROFILES_INDEX)
    if not resp:
        print("  [index] fetch failed")
        return []

    # Extract all country org profile URLs
    links = re.findall(
        r'href="(https://insightcrime\.org/[a-z-]+-organized-crime-news/([a-z0-9-]+)/)"',
        resp.text,
    )
    seen: set[str] = set()
    profiles = []
    for url, slug in links:
        if slug not in seen:
            seen.add(slug)
            profiles.append((url, slug))

    print(f"  [index] found {len(profiles)} profiles")
    return profiles


def scrape(force: bool = False, all_profiles: bool = False) -> None:
    client = get_client()

    profiles = discover_profiles(client)
    if not profiles:
        return

    if not all_profiles:
        profiles = [(url, slug) for url, slug in profiles if slug in US_RELEVANT_SLUGS]
        print(f"  [filter] {len(profiles)} US-relevant profiles selected")

    jitter()

    scraped = 0
    skipped = 0

    for url, slug in profiles:
        if not force and page_exists(SOURCE, slug):
            skipped += 1
            continue

        resp = fetch_with_retry(client, url)
        if not resp:
            print(f"  FAIL: {slug}")
            continue

        # Verify we got actual article content, not a redirect/error
        if len(resp.text) < 10000 or "entry-content" not in resp.text:
            print(f"  [skip] {slug} — no article content")
            continue

        save_page(source=SOURCE, slug=slug, url=url, content=resp.text)
        scraped += 1
        print(f"  [{scraped}] {slug}")
        jitter()

    print(f"\nDone: {scraped} scraped, {skipped} skipped")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape InSight Crime org profiles")
    parser.add_argument("--force", action="store_true", help="Re-scrape already-saved pages")
    parser.add_argument(
        "--all", action="store_true", dest="all_profiles", help="Scrape all profiles, not just US-relevant"
    )
    args = parser.parse_args()
    scrape(force=args.force, all_profiles=args.all_profiles)


if __name__ == "__main__":
    main()
