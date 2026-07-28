"""Scrape StopHoustonGangs.org gang profile pages via FlareSolverr.

The site is behind Cloudflare managed challenge. We route requests through
a local FlareSolverr instance (https://github.com/FlareSolverr/FlareSolverr)
which uses a real headless Chrome to solve the challenge.

Start FlareSolverr before running:
    docker run -d --name flaresolverr -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest

Profile URLs follow a sequential numeric ID pattern:
    https://stophoustongangs.org/default.aspx?act=gangprofile.aspx&gangprofileID={N}&menugroup=Home

Strategy:
  1. Fetch the listings page to discover all known profile IDs.
  2. Probe IDs 1..MAX_PROBE for any not in the listing.
  3. Stop probing after 5 consecutive misses past the last known ID.

Usage:
    python -m apps.pipeline.scrape.stophoustongangs
    python -m apps.pipeline.scrape.stophoustongangs --force
    python -m apps.pipeline.scrape.stophoustongangs --max-id 60
"""

import argparse
import re
import time

import httpx

from .common import DATA_RAW, jitter

SOURCE = "stophoustongangs"
BASE_URL = "https://stophoustongangs.org"
LISTINGS_URL = f"{BASE_URL}/default.aspx?act=ganglistings.aspx&menugroup=Home"
PROFILE_URL_TMPL = f"{BASE_URL}/default.aspx?act=gangprofile.aspx&gangprofileID={{id}}&menugroup=Home"

FLARESOLVERR_URL = "http://localhost:8191/v1"
FLARESOLVERR_TIMEOUT = 60000  # ms

DEFAULT_MAX_PROBE = 60


def fetch_via_flaresolverr(target_url: str) -> str | None:
    """Fetch a URL through FlareSolverr. Returns HTML string or None."""
    try:
        resp = httpx.post(
            FLARESOLVERR_URL,
            json={"cmd": "request.get", "url": target_url, "maxTimeout": FLARESOLVERR_TIMEOUT},
            timeout=90.0,
        )
        data = resp.json()
        if data.get("status") != "ok":
            return None
        return data.get("solution", {}).get("response")
    except (httpx.HTTPError, KeyError, ValueError):
        return None


def page_exists(slug: str) -> bool:
    return (DATA_RAW / SOURCE / slug / "content.txt").exists()


def save_page(slug: str, url: str, content: str) -> None:
    out_dir = DATA_RAW / SOURCE / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "url.txt").write_text(url + "\n", encoding="utf-8")
    (out_dir / "content.txt").write_text(content, encoding="utf-8")


def discover_ids_from_listing() -> list[int]:
    """Fetch the gang listings page and extract all profile IDs from links."""
    print("  [listings] fetching via FlareSolverr…")
    html = fetch_via_flaresolverr(LISTINGS_URL)
    if not html:
        print("  [listings] fetch failed — will use sequential probe")
        return []

    save_page("ganglistings", LISTINGS_URL, html)
    print("  [listings] saved")

    ids = sorted({int(m) for m in re.findall(r"gangprofileID=(\d+)", html)})
    print(f"  [listings] found {len(ids)} profile IDs: {ids}")
    return ids


def gang_name_from_html(html: str) -> str:
    m = re.search(r'id="GangProfileTitle">(?:Gang Profile\s*-\s*)?([^<]+)<', html)
    return m.group(1).strip() if m else "unknown"


def is_valid_profile(html: str | None) -> bool:
    """Return True only if the page has a non-empty GangProfileTitle.

    The site returns its shell page (with an empty GangProfileTitle div) for
    nonexistent IDs rather than a 404, so we must check the content of the div.
    """
    if not html or len(html) < 500:
        return False
    m = re.search(r'id="GangProfileTitle">([^<]+)<', html)
    return bool(m and m.group(1).strip())


def scrape(force: bool = False, max_id: int = DEFAULT_MAX_PROBE) -> None:
    # Step 1: discover IDs from the listing page
    discovered_ids = discover_ids_from_listing()
    jitter()

    # Step 2: build probe set — always cover 1..max_id plus anything from listing
    probe_ids = sorted(set(range(1, max_id + 1)) | set(discovered_ids))
    known_ceiling = max(discovered_ids) if discovered_ids else 30
    print(f"\nWill probe {len(probe_ids)} IDs (1–{max(probe_ids)})\n")

    scraped = 0
    skipped = 0
    missing = 0
    consecutive_missing = 0

    for pid in probe_ids:
        slug = f"gangprofile-{pid}"

        if not force and page_exists(slug):
            skipped += 1
            consecutive_missing = 0
            continue

        url = PROFILE_URL_TMPL.format(id=pid)
        html = fetch_via_flaresolverr(url)

        if not is_valid_profile(html):
            missing += 1
            consecutive_missing += 1
            print(f"  [skip] ID {pid} — no valid profile")
            if pid > known_ceiling and consecutive_missing >= 5:
                print(f"  5 consecutive misses past known ceiling ({known_ceiling}) — stopping")
                break
            jitter()
            continue

        consecutive_missing = 0
        name = gang_name_from_html(html)
        save_page(slug, url, html)
        scraped += 1
        print(f"  [{scraped}] ID {pid}: {name}")
        jitter()

    print(f"\nDone: {scraped} scraped, {skipped} skipped, {missing} missing/invalid")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape StopHoustonGangs.org via FlareSolverr")
    parser.add_argument("--force", action="store_true", help="Re-scrape already-saved pages")
    parser.add_argument(
        "--max-id",
        type=int,
        default=DEFAULT_MAX_PROBE,
        help=f"Maximum profile ID to probe (default: {DEFAULT_MAX_PROBE})",
    )
    args = parser.parse_args()
    scrape(force=args.force, max_id=args.max_id)


if __name__ == "__main__":
    main()
