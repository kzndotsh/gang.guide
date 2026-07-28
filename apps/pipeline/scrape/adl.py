"""Scrape ADL extremist/gang profiles and reports.

Sources:
  1. "White Supremacist Prison Gangs in the United States: A Preliminary Inventory"
     (ADL, 2016) — 24-page state-by-state inventory of ~100 white supremacist prison
     gangs. Downloaded from Wayback Machine (ADL direct URL is Cloudflare-blocked).
     Split into per-state files (one file per state section).

  2. "Bigotry Behind Bars" (ADL, 1998) — archived overview of racist prison gangs
     covering Aryan Brotherhood, Nazi Low Riders. Single file.

  3. Hate symbol pages at adl.org/resources/hate-symbol/{slug} — 44 gang/prison gang
     entries (state AB chapters, Aryan Circle, Nazi Low Riders, peckerwoods, skinhead
     gangs, etc.) with symbols, tattoo descriptions, and founding context. Fetched via
     Wayback Machine since ADL pages are JS-rendered.

  4. Individual ADL profile pages at adl.org/resources/profiles/{slug} — deep
     narrative profiles with explicit rival/ally sections. Requires FlareSolverr
     (ADL is behind Cloudflare). Note: these are JS-rendered and may return empty
     shells; content quality varies.

Usage:
    python -m apps.pipeline.scrape.adl
    python -m apps.pipeline.scrape.adl --force
    python -m apps.pipeline.scrape.adl --no-profiles   # skip individual profile pages
"""

import argparse
import re

import httpx
import pypdf

from .common import DATA_RAW, fetch_with_retry, get_client, jitter, page_exists, save_page

SOURCE = "adl"
BASE_URL = "https://www.adl.org"
FLARESOLVERR_URL = "http://localhost:8191/v1"

# States that appear in the 2016 PDF
PDF_STATES = {
    "ALABAMA",
    "ALASKA",
    "ARIZONA",
    "ARKANSAS",
    "CALIFORNIA",
    "COLORADO",
    "CONNECTICUT",
    "FLORIDA",
    "GEORGIA",
    "IDAHO",
    "INDIANA",
    "IOWA",
    "KANSAS",
    "KENTUCKY",
    "MASSACHUSETTS",
    "MICHIGAN",
    "MINNESOTA",
    "MISSISSIPPI",
    "MISSOURI",
    "NEBRASKA",
    "NEVADA",
    "NEW HAMPSHIRE",
    "NEW JERSEY",
    "NORTH CAROLINA",
    "OHIO",
    "OKLAHOMA",
    "OREGON",
    "PENNSYLVANIA",
    "TENNESSEE",
    "TEXAS",
    "UTAH",
    "VIRGINIA",
    "WYOMING",
    "FEDERAL",
}

# Table column header noise to exclude from table_noise check
TABLE_NOISE = {
    "GANG",
    "NAME",
    "SIZE",
    "PRIMARY",
    "NOTES",
    "ACTIVITY",
    "LOCATION",
    "CONSIDERABLE",
    "OVERALL",
    "OTHER",
    "ANTI-DEFAMATION LEAGUE",
    "CENTER ON EXTREMISM",
}

# Lines to strip from state sections (column headers, noise)
STRIP_LINES = {
    "GANG",
    "NAME",
    "OVERALL",
    "SIZE",
    "PRIMARY",
    "STATE",
    "LOCATION",
    "OTHER",
    "STATES WITH",
    "CONSIDERABLE",
    "ACTIVITY",
    "NOTES",
    "GANG ",
    "OVERALL ",
    "PRIMARY ",
    "STATE  ",
    "STATES WITH  ",
    "CONSIDERABLE ",
}

PDF_SOURCES = [
    {
        "filename": "adl-ws-prison-gangs-2016.pdf",
        # ADL direct URL is Cloudflare-blocked — use Wayback Machine archive
        "url": "https://web.archive.org/web/20250124071640/https://www.adl.org/sites/default/files/CR_4499_WhiteSupremacist-Report_web_vff.pdf",
        "title": "ADL: White Supremacist Prison Gangs in the United States (2016)",
        "split_by_state": True,
    },
    {
        "filename": "adl-bigotry-behind-bars-1998.pdf",
        "url": "https://www.adl.org/sites/default/files/Bigotry-Behind-Bars-Racist-Groups-in-US-Prisons.pdf",
        "title": "ADL: Bigotry Behind Bars - Racist Groups in US Prisons (1998)",
        "split_by_state": False,
        "slug": "adl-bigotry-behind-bars-1998",
    },
]

# Individual ADL profile pages — slugs verified via Wayback CDX API.
# URL pattern varies: some use /profile/{slug}, others /profiles/{slug}.
# scrape_profiles() tries both variants via Wayback Machine.
PROFILE_SLUGS = [
    # White supremacist prison gangs
    "aryan-brotherhood-texas",  # CDX confirmed (not -of-texas)
    "aryan-circle",  # CDX confirmed
    "nazi-low-riders",  # CDX confirmed
    "public-enemy-number-1-peni",  # CDX confirmed (not public-enemy-no-1)
    "hammerskin-nation",  # CDX confirmed
    "volksfront",  # CDX confirmed
    # White supremacist orgs with street/prison presence
    "national-alliance",  # CDX confirmed
    "national-socialist-movement",  # CDX confirmed
    "creativity-movement-formerly-world-church-creator",  # CDX confirmed
    "aryan-nationschurch-jesus-christ-christian",  # CDX confirmed (Aryan Nations)
    # Other
    "nation-islam",  # CDX confirmed
]

# Hate symbol pages — gang/prison gang specific entries.
# Fetched from Wayback Machine (2023/2024 snapshots) since ADL direct URLs are JS-rendered.
# Wayback URL pattern: https://web.archive.org/web/2024/{adl_url}
HATE_SYMBOL_SLUGS = [
    # White supremacist prison gangs — state-specific chapters
    "alabama-aryan-brotherhood",
    "aryan-brotherhood",
    "aryan-brotherhood-texas",
    "aryan-circle",
    "aryan-cowboy-brotherhood",
    "aryan-freedom-network",
    "aryan-knights",
    "aryan-nations-tennessee-prison-gang",
    "aryan-renaissance-society",
    "aryan-terror-brigade",
    "aryan-warriors",
    "crew-1488",
    "crazy-white-boy",
    "european-kindred",
    "featherwood",
    "firm-22",
    "georgia-aryan-brotherhood",
    "indiana-aryan-brotherhood",
    "mississippi-aryan-brotherhood",
    "new-aryan-empire",
    "nazi-low-riders",
    "ohio-aryan-brotherhood",
    "oklahoma-aryan-brotherhood",
    "peckerwood",
    "peckerwood-midwest",
    "peni",
    "sacred-separatist-group",
    "sadistic-souls",
    "silent-aryan-warriors",
    "soldiers-aryan-culture",
    "solid-wood-soldiers",
    "southern-brotherhood",
    "supreme-white-alliance",
    "unforgiven",
    "universal-aryan-brotherhood",
    "vinlanders-social-club",
    "volksfront",
    "war-arkansas-prison-gang",
    "white-aryan-resistance",
    "white-knights",
    "women-aryan-unity",
    # Skinhead gangs
    "211-crew",
    "blood-honour",
    "blood-tribe",
    "hammerskins",
    "keystone-state-skinheads",
]


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


def extract_pdf_text(pdf_path: str) -> list[str]:
    """Extract text from each page of a PDF. Returns list of page strings."""
    try:
        reader = pypdf.PdfReader(pdf_path)
        return [page.extract_text() or "" for page in reader.pages]
    except Exception as e:
        print(f"  [pdf] extraction error: {e}")
        return []


def split_by_state(pages: list[str], title: str) -> dict[str, str]:
    """Split PDF text into per-state chunks.

    Each state section becomes one pipeline file. The column header noise
    (GANG NAME / OVERALL SIZE / etc.) is stripped for cleaner LLM input.

    Returns {slug: content} mapping.
    """
    full_text = "\n".join(pages)
    lines = full_text.split("\n")

    # Find state header line indices
    state_boundaries: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped in PDF_STATES and stripped not in TABLE_NOISE:
            state_boundaries.append((i, stripped))

    if not state_boundaries:
        return {"adl-ws-gangs-full": f"{title}\n\n{full_text}"}

    chunks: dict[str, str] = {}

    # Intro = everything before first state header
    intro_text = "\n".join(lines[: state_boundaries[0][0]]).strip()
    if intro_text:
        chunks["adl-ws-gangs-intro"] = f"{title} — Introduction\n\n{intro_text}"

    for state_idx, (state_line, state_name) in enumerate(state_boundaries):
        end_line = state_boundaries[state_idx + 1][0] if state_idx + 1 < len(state_boundaries) else len(lines)

        # Strip column header noise, keep gang content
        section_lines = [ln for ln in lines[state_line + 1 : end_line] if ln.strip() and ln.strip() not in STRIP_LINES]
        section_text = "\n".join(section_lines).strip()

        slug = "adl-ws-gangs-" + state_name.lower().replace(" ", "-")
        chunks[slug] = f"{title} — {state_name}\n\nState: {state_name}\n\n{section_text}"

    return chunks


def save_chunk(slug: str, url: str, content: str) -> None:
    out_dir = DATA_RAW / SOURCE / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "content.txt").write_text(content, encoding="utf-8")
    (out_dir / "url.txt").write_text(url + "\n", encoding="utf-8")


def scrape_pdfs(force: bool = False) -> None:
    client = get_client()

    for doc in PDF_SOURCES:
        pdf_path = DATA_RAW / SOURCE / doc["filename"]

        # Download PDF if not already on disk
        if not pdf_path.exists():
            resp = fetch_with_retry(client, doc["url"])
            if not resp or "html" in resp.headers.get("content-type", "") or not resp.content.startswith(b"%PDF"):
                print(f"  [fail] {doc['filename']} — could not download PDF (try manual download)")
                continue
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            pdf_path.write_bytes(resp.content)
            print(f"  [dl] {doc['filename']} ({len(resp.content) // 1024}KB)")

        # Extract text
        pages = extract_pdf_text(str(pdf_path))
        if not pages:
            print(f"  [fail] {doc['filename']} — no text extracted")
            continue

        if doc.get("split_by_state"):
            chunks = split_by_state(pages, doc["title"])
            saved = 0
            for slug, content in chunks.items():
                if not force and page_exists(SOURCE, slug):
                    continue
                save_chunk(slug, doc["url"], content)
                saved += 1
            total = len(chunks)
            print(f"  [pdf] {doc['filename']} → {saved} chunks saved ({total} total, {total - saved} skipped)")
        else:
            slug = doc["slug"]
            if not force and page_exists(SOURCE, slug):
                print(f"  [skip] {slug}")
                continue
            full_text = doc["title"] + "\n\n" + "\n\n".join(pages)
            save_chunk(slug, doc["url"], full_text)
            print(f"  [pdf] {slug} ({len(full_text)} chars)")


def scrape_profiles(force: bool = False) -> None:
    """Scrape ADL profile pages via Wayback Machine.

    ADL profile pages are JS-rendered and return empty shells via FlareSolverr.
    Wayback Machine snapshots (2024) contain the full static HTML for most profiles.
    Profiles that have no archived content are skipped silently.
    """
    client = get_client()
    scraped = 0
    skipped = 0
    empty = 0

    for slug in PROFILE_SLUGS:
        if not force and page_exists(SOURCE, slug):
            skipped += 1
            continue

        # Try both URL variants via Wayback Machine
        html = None
        url = None
        for path in [f"/resources/profiles/{slug}", f"/resources/profile/{slug}"]:
            adl_url = f"{BASE_URL}{path}"
            wayback_url = f"https://web.archive.org/web/2024/{adl_url}"
            resp = fetch_with_retry(client, wayback_url)
            if resp and len(resp.text) > 5000:
                # Check for real content (not just nav/footer)
                clean = re.sub(r"<[^>]+>", " ", resp.text)
                clean = re.sub(r"\s+", " ", clean).strip()
                has_content = any(
                    clean.find(kw) > 100 for kw in ["founded", "prison", "originated", "California", "members", "gang"]
                )
                if has_content:
                    html = resp.text
                    url = adl_url
                    break
            jitter()

        if not html or not url:
            empty += 1
            continue

        save_page(source=SOURCE, slug=slug, url=url, content=html)
        scraped += 1
        print(f"  [{scraped}] {slug}")
        jitter()

    msg = f"  Profiles: {scraped} scraped"
    if skipped:
        msg += f", {skipped} skipped"
    if empty:
        msg += f", {empty} no archive"
    print(msg)


def scrape_hate_symbols(force: bool = False) -> None:
    """Scrape gang/prison gang hate symbol pages via Wayback Machine.

    ADL hate symbol pages are JS-rendered and not accessible via FlareSolverr.
    Wayback Machine snapshots (2023/2024) contain the full static HTML.
    """
    client = get_client()
    scraped = 0
    skipped = 0
    failed = 0

    for slug in HATE_SYMBOL_SLUGS:
        out_slug = f"hate-symbol-{slug}"
        if not force and page_exists(SOURCE, out_slug):
            skipped += 1
            continue

        adl_url = f"{BASE_URL}/resources/hate-symbol/{slug}"
        wayback_url = f"https://web.archive.org/web/2024/{adl_url}"

        resp = fetch_with_retry(client, wayback_url)
        if not resp or len(resp.text) < 5000:
            # Try 2023 snapshot
            wayback_url = f"https://web.archive.org/web/2023/{adl_url}"
            resp = fetch_with_retry(client, wayback_url)

        if not resp or len(resp.text) < 5000:
            print(f"  [fail] {slug}")
            failed += 1
            jitter()
            continue

        save_page(source=SOURCE, slug=out_slug, url=adl_url, content=resp.text)
        scraped += 1
        print(f"  [{scraped}] {slug}")
        jitter()

    print(f"  Hate symbols: {scraped} scraped, {skipped} skipped, {failed} failed")


def scrape(force: bool = False, no_profiles: bool = False) -> None:
    print("Scraping ADL PDFs...")
    scrape_pdfs(force=force)

    print("\nScraping ADL hate symbol pages (gang/prison gang) via Wayback Machine...")
    scrape_hate_symbols(force=force)

    if not no_profiles:
        print("\nScraping ADL profile pages via FlareSolverr...")
        scrape_profiles(force=force)

    print("\nDone.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape ADL gang/extremist profiles and reports")
    parser.add_argument("--force", action="store_true", help="Re-scrape already-saved pages")
    parser.add_argument("--no-profiles", action="store_true", help="Skip individual ADL profile pages")
    args = parser.parse_args()
    scrape(force=args.force, no_profiles=args.no_profiles)


if __name__ == "__main__":
    main()
