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


def clean_state_text(text: str) -> str:
    """Clean PDF-extracted state section text for better LLM parsing.

    pypdf splits gang names across lines (e.g. 'Aryan \\nBrotherhood \\nof Texas')
    and leaves table noise. This joins name fragments and produces readable prose.
    """
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        # Skip empty lines and column header noise
        if not stripped:
            i += 1
            continue

        # A line is a "name fragment" if it's short (<= 20 chars), title-case-ish,
        # ends with a trailing space (from PDF), and the next line continues it
        is_name_frag = (
            len(stripped) <= 25
            and not stripped[0].isdigit()
            and stripped not in {"See Notes", "BOP"}
            and not re.match(r"^(Large|Medium|Small|[A-Z]{2}(?:,\s*[A-Z]{2,3})*)\b", stripped)
        )

        # Peek ahead: join consecutive name fragments into one line
        if is_name_frag and i + 1 < len(lines):
            next_stripped = lines[i + 1].strip()
            next_is_frag = (
                len(next_stripped) <= 25
                and next_stripped not in {"See Notes", "BOP", ""}
                and not re.match(r"^(Large|Medium|Small|[A-Z]{2}(?:,\s*[A-Z]{2,3})*)\b", next_stripped)
            )
            if next_is_frag:
                # Accumulate name parts
                name_parts = [stripped]
                j = i + 1
                while j < len(lines):
                    ns = lines[j].strip()
                    if not ns or re.match(r"^(Large|Medium|Small)\b", ns):
                        break
                    if len(ns) <= 25:
                        name_parts.append(ns)
                        j += 1
                    else:
                        break
                out.append(" ".join(name_parts))
                i = j
                continue

        out.append(stripped)
        i += 1

    return "\n".join(out)


def split_into_gang_files(pages: list[str], title: str) -> dict[str, str]:
    """Split PDF text into one file per gang entry.

    After clean_state_text(), each entry looks like:

        Gang Name [possibly multi-word on one line after joining]
        Large STATE_ABBREVS notes text...
        continuation of notes...

    OR (when name+size on same line):
        Gang Name Large STATE_ABBREVS notes...
        continuation...

    Strategy: scan cleaned lines. A new gang starts when we see a name line
    (title-case, short) followed by a size keyword either on the next line or
    inline on the same line. Accumulate notes until next gang entry.

    Returns {slug: content} mapping — one entry per gang.
    """
    SIZE_RE = re.compile(r"\b(Large|Medium|Small)\b")

    full_text = "\n".join(pages)
    lines = full_text.split("\n")

    # Find state header boundaries
    state_boundaries: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped in PDF_STATES and stripped not in TABLE_NOISE:
            state_boundaries.append((i, stripped))

    if not state_boundaries:
        return {}

    chunks: dict[str, str] = {}

    # Intro file (context for all entries)
    intro_lines = lines[: state_boundaries[0][0]]
    intro_text = clean_state_text("\n".join(intro_lines)).strip()

    for state_idx, (state_line, state_name) in enumerate(state_boundaries):
        end_line = state_boundaries[state_idx + 1][0] if state_idx + 1 < len(state_boundaries) else len(lines)

        # Clean the state section
        section_lines = [ln for ln in lines[state_line + 1 : end_line] if ln.strip() and ln.strip() not in STRIP_LINES]
        section_text = clean_state_text("\n".join(section_lines))
        cleaned_lines = section_text.split("\n")

        # Parse into (name, size, notes) entries
        entries: list[tuple[str, str, str]] = []
        i = 0
        while i < len(cleaned_lines):
            line = cleaned_lines[i].strip()
            if not line:
                i += 1
                continue

            # Pattern A: size keyword is INLINE on this line
            # e.g. "Aryan Circle Large TX MO, OK notes..."
            inline = SIZE_RE.search(line)
            if inline:
                size_pos = inline.start()
                name_part = line[:size_pos].strip()
                size = inline.group(1)
                notes_part = line[size_pos + len(size) :].strip()

                # Accumulate continuation lines as notes
                j = i + 1
                while j < len(cleaned_lines):
                    next_line = cleaned_lines[j].strip()
                    if not next_line:
                        j += 1
                        continue
                    # Stop at next entry (size keyword or short name line followed by size)
                    if SIZE_RE.search(next_line):
                        break
                    # State abbreviation continuation lines (e.g. "NM, TN, IN,")
                    if re.match(r"^[A-Z]{2}(?:,\s*[A-Z]{2,3})*,?\s*$", next_line):
                        j += 1
                        continue
                    notes_part += " " + next_line
                    j += 1

                if name_part and len(name_part) > 2:
                    entries.append((name_part, size, notes_part.strip()))
                i = j
                continue

            # Pattern B: name on this line, size+notes on NEXT line
            # e.g. line[i] = "Aryan Brotherhood of Texas"
            #      line[i+1] = "Large TX NM, OK, BOP Started in 1984..."
            if i + 1 < len(cleaned_lines):
                next_line = cleaned_lines[i + 1].strip()
                next_match = re.match(r"^(Large|Medium|Small)\b(.*)$", next_line)
                if next_match:
                    name_part = line
                    size = next_match.group(1)
                    notes_part = next_match.group(2).strip()

                    # Accumulate continuation notes
                    j = i + 2
                    while j < len(cleaned_lines):
                        cont = cleaned_lines[j].strip()
                        if not cont:
                            j += 1
                            continue
                        # Stop at next entry
                        if SIZE_RE.search(cont):
                            break
                        if re.match(r"^[A-Z]{2}(?:,\s*[A-Z]{2,3})*,?\s*$", cont):
                            j += 1
                            continue
                        # Check if it's a new name line (next line after has a size keyword)
                        if (
                            len(cont) <= 50
                            and j + 1 < len(cleaned_lines)
                            and re.match(
                                r"^(Large|Medium|Small)\b",
                                cleaned_lines[j + 1].strip() if j + 1 < len(cleaned_lines) else "",
                            )
                        ):
                            break
                        notes_part += " " + cont
                        j += 1

                    if name_part and len(name_part) > 2:
                        entries.append((name_part, size, notes_part.strip()))
                    i = j
                    continue

            i += 1

        # Save one file per unique gang name
        seen: set[str] = set()
        for gang_name, size, notes in entries:
            # Clean up state abbreviations from notes start
            # e.g. "TX NM, OK, BOP Started in 1984..." → "Started in 1984..."
            notes_clean = re.sub(r"^[A-Z]{2,3}(?:,\s*[A-Z]{2,3})*\s*", "", notes).strip()
            notes_clean = re.sub(r"^(BOP\s*,?\s*)*", "", notes_clean).strip()

            # Validate gang name — reject obvious garbage
            # Real gang names: title-case words, no verbs, no sentences
            name_lower = gang_name.lower()
            is_garbage = (
                len(gang_name) > 60  # too long
                or gang_name.endswith(".")  # sentence fragment
                or gang_name.endswith(",")  # list fragment
                or any(
                    w in name_lower
                    for w in [
                        "has broken",
                        "have killed",
                        "today ",
                        "white supremacist gangs are",
                        "prison systems",
                        "in the federal",
                        "as well as",
                    ]
                )
            )
            if is_garbage:
                continue
                # Skip entries with no meaningful notes (just size/state data)
                continue

            slug = "adl-ws-gang-" + re.sub(r"[^a-z0-9]+", "-", gang_name.lower()).strip("-")

            content = (
                f"{title} — {gang_name}\n\n"
                f"Gang: {gang_name}\n"
                f"Size: {size}\n"
                f"Primary State: {state_name}\n\n"
                f"{notes_clean}\n\n"
                f"--- Source context ---\n"
                f"{intro_text[:800]}"
            )

            if slug in seen:
                # Same gang appears multiple times in this state (e.g. BOP section)
                slug = slug + "-" + state_name.lower().replace(" ", "-")
            elif slug in chunks:
                # Same gang in multiple states — append
                chunks[slug] += f"\n\n--- Also active in {state_name} ---\n{notes_clean}"
                seen.add(slug)
                continue

            chunks[slug] = content
            seen.add(slug)

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
            chunks = split_into_gang_files(pages, doc["title"])
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
