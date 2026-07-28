"""Scrape SPLC Extremist Files gang/prison gang profiles.

The Southern Poverty Law Center's Extremist Files section contains detailed
profiles of hate groups including white supremacist prison gangs and related orgs.
Profiles are discovered from the sitemap at splcenter.org/splc_extremist-sitemap.xml.

We filter to organizations directly relevant to the gang.guide dataset:
- White supremacist prison gangs (Aryan Brotherhood, AB of Texas, Aryan Circle, etc.)
- Street gang-adjacent extremist orgs (Proud Boys, skinhead gangs, etc.)
- Black nationalist/Nation of Islam (NOI's intersection with prison system)

The site requires FlareSolverr due to Cloudflare bot protection on individual profiles.
The sitemap itself is accessible without Cloudflare challenge.

Usage:
    python -m apps.pipeline.scrape.splc
    python -m apps.pipeline.scrape.splc --force
    python -m apps.pipeline.scrape.splc --all     # scrape all 271 extremist profiles
"""

import argparse
import json
import re
import time

import httpx

from .common import DATA_RAW, jitter

SOURCE = "splc"
BASE_URL = "https://www.splcenter.org"
SITEMAP_URL = f"{BASE_URL}/splc_extremist-sitemap.xml"
FLARESOLVERR_URL = "http://localhost:8191/v1"

# Slugs relevant to gang.guide dataset:
# white supremacist prison gangs, street gang-adjacent extremist orgs
RELEVANT_SLUGS = {
    # White supremacist prison gangs
    "aryan-brotherhood",
    "aryan-brotherhood-texas",
    "aryan-freedom-network",
    "aryan-nations",
    # Skinhead gangs active in prisons and streets
    "blood-honour",
    "blood-tribe",
    "vinlanders-social-club",
    "racist-skinhead",
    # Neo-Nazi orgs with prison gang ties
    "atomwaffen-division",
    "national-socialist-movement",
    "national-alliance",
    "the-base",
    "keystone-united",
    "rise-above-movement",
    "nationalist-social-club-nsc-131",
    # Black nationalist/prison outreach
    "nation-islam",
    "new-black-panther-party",
    "new-black-panther-party-self-defense",
    # KKK orgs with prison presence
    "ku-klux-klan",
    "imperial-klans-america",
    "knights-ku-klux-klan",
    # Other extremist street/prison-adjacent orgs
    "proud-boys",
    "patriot-front",
    "three-percenters",
    "oath-keepers",
    "phineas-priesthood",
    "creativity-movement-0",
}


def fetch_via_flaresolverr(url: str) -> str | None:
    """Fetch a URL through FlareSolverr. Returns HTML or None."""
    try:
        resp = httpx.post(
            FLARESOLVERR_URL,
            json={"cmd": "request.get", "url": url, "maxTimeout": 60000},
            timeout=90.0,
        )
        data = resp.json()
        if data.get("status") != "ok":
            return None
        return data.get("solution", {}).get("response")
    except (httpx.HTTPError, KeyError, ValueError):
        return None


def discover_slugs_from_sitemap() -> list[tuple[str, str]]:
    """Parse the SPLC extremist sitemap and return (url, slug) pairs."""
    try:
        resp = httpx.get(SITEMAP_URL, headers={"User-Agent": "GangGuideBot/1.0"}, timeout=30.0)
        urls = re.findall(r"<loc>([^<]+)</loc>", resp.text)
    except httpx.HTTPError:
        print("  [sitemap] fetch failed")
        return []

    profiles = []
    seen: set[str] = set()
    for url in urls:
        if "/extremist-files/" not in url:
            continue
        slug = url.rstrip("/").split("/")[-1]
        if not slug or slug == "extremist-files" or slug in seen:
            continue
        seen.add(slug)
        profiles.append((url.rstrip("/") + "/", slug))

    print(f"  [sitemap] found {len(profiles)} extremist file profiles")
    return profiles


def page_exists(slug: str) -> bool:
    return (DATA_RAW / SOURCE / slug / "content.txt").exists()


def save_page(slug: str, url: str, content: str) -> None:
    out_dir = DATA_RAW / SOURCE / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "url.txt").write_text(url + "\n", encoding="utf-8")
    (out_dir / "content.txt").write_text(content, encoding="utf-8")


def is_valid_profile(html: str | None) -> bool:
    """Return True if the page looks like a real extremist file profile."""
    if not html or len(html) < 5000:
        return False
    return any(
        marker in html
        for marker in [
            "extremist-files",
            "Extremist Files",
            "splc_extremist",
            '"@type":"Article"',
        ]
    )


def scrape(force: bool = False, all_profiles: bool = False) -> None:
    profiles = discover_slugs_from_sitemap()
    if not profiles:
        return

    if not all_profiles:
        profiles = [(url, slug) for url, slug in profiles if slug in RELEVANT_SLUGS]
        print(f"  [filter] {len(profiles)} gang-relevant profiles selected")

    print(f"\nScraping {len(profiles)} profiles via FlareSolverr\n")

    scraped = 0
    skipped = 0

    for url, slug in profiles:
        if not force and page_exists(slug):
            skipped += 1
            continue

        html = fetch_via_flaresolverr(url)

        if not is_valid_profile(html):
            print(f"  [skip] {slug} — no valid profile content")
            jitter()
            continue

        save_page(slug, url, html)
        scraped += 1
        print(f"  [{scraped}] {slug}")
        jitter()

    print(f"\nDone: {scraped} scraped, {skipped} skipped")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape SPLC Extremist Files gang profiles")
    parser.add_argument("--force", action="store_true", help="Re-scrape already-saved pages")
    parser.add_argument("--all", action="store_true", dest="all_profiles", help="Scrape all 271 profiles")
    args = parser.parse_args()
    scrape(force=args.force, all_profiles=args.all_profiles)


if __name__ == "__main__":
    main()
