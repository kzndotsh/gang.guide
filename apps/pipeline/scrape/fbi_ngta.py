"""Scrape FBI National Gang Threat Assessment (NGTA) and National Gang Report (NGR) PDFs.

Sources:
  - 2009 NGTA: DOJ/NDIC archive (48 pages)
  - 2011 NGTA: FBI file-repository (100 pages)
  - 2015 NGR:  FBI file-repository (68 pages)

Structure:
  The 2009 NGTA has the richest per-gang profiles in Appendices B, C, D:
    - Appendix B: Street Gangs (18th Street, Latin Kings, Bloods, Crips,
      Florencia 13, Latin Disciples, MS-13, Sureños/Norteños, Tango Blast,
      Tiny Rascal Gangsters, UBN, Vice Lords)
    - Appendix C: Prison Gangs (Aryan Brotherhood, Barrio Azteca, BGF,
      Mexican Mafia, Mexikanemi, Nuestra Familia, Ñeta, Texas Syndicate)
    - Appendix D: OMGs (Bandidos, Hells Angels, Mongols, Outlaws,
      Sons of Silence, Vagos)

  The 2011 and 2015 reports are thematic (no clean per-gang appendices)
  and are saved as single files.

  All appendix pages are split into one file per gang profile.
  Thematic pages (regional summaries, key findings) are saved as a
  single "overview" file per report.

Usage:
    python -m apps.pipeline.scrape.fbi_ngta
    python -m apps.pipeline.scrape.fbi_ngta --force
"""

import argparse
import re

import pypdf

from .common import DATA_RAW, fetch_with_retry, get_client, page_exists

SOURCE = "fbi_ngta"

PDF_SOURCES = [
    {
        "slug_prefix": "ngta-2009",
        "url": "https://www.justice.gov/ndic/pubs32/32146/32146p.pdf",
        "fallback_url": "https://web.archive.org/web/2010/https://www.justice.gov/ndic/pubs32/32146/32146p.pdf",
        "title": "FBI/NDIC: National Gang Threat Assessment 2009",
        # Pages 30-39 (0-indexed) are appendices B, C, D with per-gang profiles
        "appendix_pages": (29, 39),
    },
    {
        "slug_prefix": "ngta-2011",
        "url": "https://www.fbi.gov/file-repository/stats-services-publications-2011-national-gang-threat-assessment-2011%20national%20gang%20threat%20assessment%20%20emerging%20trends.pdf",
        "title": "FBI: National Gang Threat Assessment 2011 — Emerging Trends",
        "appendix_pages": None,  # No clean appendix, save as whole doc
    },
    {
        "slug_prefix": "ngr-2015",
        "url": "https://www.fbi.gov/file-repository/reports-and-publications/stats-services-publications-national-gang-report-2015.pdf",
        "title": "FBI: National Gang Report 2015",
        "appendix_pages": None,  # Thematic report, save as whole doc
    },
]


def extract_pdf_pages(pdf_path: str) -> list[str]:
    """Extract text from each page. Returns list of page strings."""
    try:
        reader = pypdf.PdfReader(pdf_path)
        return [page.extract_text() or "" for page in reader.pages]
    except Exception as e:
        print(f"  [pdf] extraction error: {e}")
        return []


def split_appendix_profiles(pages: list[str], title: str) -> dict[str, str]:
    """Split appendix pages into per-gang profile files.

    The 2009 NGTA appendices have profiles structured as:
        GANG NAME (header in small caps / title case)
        [1-3 paragraphs of description]
        NEXT GANG NAME
        ...

    Returns {slug: content} mapping.
    """
    # Combine appendix pages into one block
    text = "\n".join(pages)
    lines = text.split("\n")

    chunks: dict[str, str] = {}
    current_name: str = ""
    current_lines: list[str] = []

    # Known gang name patterns in these appendices
    # Headers appear as short lines (5-50 chars) that are the org name
    # They're often in small-caps rendering: 'ar y a n br o t h e r h o o d'
    # or mixed: '18t h st r e e t (na t i o n a l)'
    NAME_RE = re.compile(
        r"^(?:"
        r"18t\s*h\s*st|al\s*m\s*i\s*g|bl\s*o\s*o|cr\s*i\s*p|fl\s*o\s*r|"
        r"la\s*t\s*i\s*n\s*d|la\s*t\s*i\s*n\s*k|ma\s*r\s*a|"
        r"su\s*r\s*e|ti\s*n\s*y|un\s*i\s*t\s*e|vi\s*c\s*e|"
        r"ar\s*y\s*a\s*n\s*b|ba\s*r\s*r\s*i\s*o\s*a|bl\s*a\s*c\s*k\s*g|"
        r"me\s*x\s*i\s*c\s*a\s*n\s*m|me\s*x\s*i\s*k|nu\s*e\s*s\s*t|"
        r"ñe\s*t\s*a|te\s*x\s*a\s*s\s*s|"
        r"ba\s*n\s*d\s*i|he\s*l\s*l\s*s|mo\s*n\s*g|ou\s*t\s*l\s*a|"
        r"so\s*n\s*s\s*o|va\s*g\s*o\s*s"
        r")",
        re.I,
    )

    # Lookup table for small-caps mangled names → proper names
    NAME_LOOKUP = {
        "18t h st r e e t": "18th Street Gang",
        "al m i g h t y la t i n Ki n g a n d Qu e e n na t i o n": "Almighty Latin King And Queen Nation",
        "bl a cK P . st o n e na t i o n": "Black P Stone Nation",
        "bl o o d s": "Bloods",
        "cr iPs": "Crips",
        "Fl o r e n c i a 13": "Florencia 13",
        "la t i n di s c iPl e s": "Latin Disciples",
        "ma r a sa l v a t r u c h a": "Mara Salvatrucha",
        "su r e ñ o s a n d no r t e ñ o s": "Sureños And Norteños",
        "ti n y ra s c a l ga n g s t e r s": "Tiny Rascal Gangsters",
        "un i t e d bl o o d na t i o n": "United Blood Nation",
        "vi c e lo r d na t i o n": "Vice Lord Nation",
        "ar y a n br o t h e r h o o d": "Aryan Brotherhood",
        "ba r r i o az t e c a": "Barrio Azteca",
        "bl a cK gu e r r i l l a Fa m i l y": "Black Guerrilla Family",
        "me x iKa n e m i": "Mexikanemi",
        "me x i c a n maFi a": "Mexican Mafia",
        "ñe t a": "Ñeta",
        "nu e s t r a Fa m i l i a": "Nuestra Familia",
        "t e x a s sy n d i c a t e": "Texas Syndicate",
        "ba n d i d o s": "Bandidos",
        "he l l s an g e l s": "Hells Angels",
        "mo n g o l s": "Mongols",
        "ou t l a w s": "Outlaws",
        "so n s oF si l e n c e": "Sons Of Silence",
        "va g o s": "Vagos",
    }

    def flush() -> None:
        nonlocal current_name, current_lines
        if current_name and current_lines:
            raw = re.sub(r"\s+", " ", current_name).strip()
            # Check lookup first
            name = NAME_LOOKUP.get(raw)
            if not name:
                # Try stripping parenthetical suffix then check again
                base = re.sub(r"\s*\([^)]+\)\s*$", "", raw).strip()
                name = NAME_LOOKUP.get(base, base.title())
            # Remove parenthetical level indicators
            name = re.sub(r"\s*\((national|regional|local)\)\s*$", "", name, flags=re.I).strip()
            slug = "fbi-ngta-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            content_text = "\n".join(current_lines).strip()
            if len(content_text.split()) > 20:
                chunks[slug] = f"{title} — {name}\n\nGang: {name}\n\n{content_text}"
        current_name = ""
        current_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check if this line looks like a gang name header
        if NAME_RE.match(stripped) and len(stripped) < 60:
            flush()
            current_name = stripped
            continue

        if current_name:
            current_lines.append(stripped)

    flush()
    return chunks


def save_content(slug: str, url: str, content: str) -> None:
    out_dir = DATA_RAW / SOURCE / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "content.txt").write_text(content, encoding="utf-8")
    (out_dir / "url.txt").write_text(url + "\n", encoding="utf-8")


def scrape(force: bool = False) -> None:
    client = get_client()

    for doc in PDF_SOURCES:
        prefix = doc["slug_prefix"]
        pdf_path = DATA_RAW / SOURCE / f"{prefix}.pdf"

        # Download PDF if not cached
        if not pdf_path.exists():
            url = doc["url"]
            resp = fetch_with_retry(client, url)
            if not resp or not resp.content.startswith(b"%PDF"):
                fallback = doc.get("fallback_url")
                if fallback:
                    resp = fetch_with_retry(client, fallback)
                if not resp or not resp.content.startswith(b"%PDF"):
                    print(f"  [fail] {prefix} — could not download PDF")
                    continue
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            pdf_path.write_bytes(resp.content)
            print(f"  [dl] {prefix} ({len(resp.content) // 1024}KB)")

        pages = extract_pdf_pages(str(pdf_path))
        if not pages:
            print(f"  [fail] {prefix} — text extraction failed")
            continue

        ap = doc.get("appendix_pages")

        if ap:
            # Save overview (non-appendix pages) as one file
            overview_slug = f"{prefix}-overview"
            if force or not page_exists(SOURCE, overview_slug):
                overview_text = "\n\n".join(p.strip() for p in pages[: ap[0]] if p.strip())
                save_content(overview_slug, doc["url"], f"{doc['title']} — Overview\n\n{overview_text}")
                print(f"  [ok] {overview_slug} ({len(overview_text.split()):,} words)")

            # Split appendix pages into per-gang profiles
            appendix_pages = pages[ap[0] : ap[1] + 1]
            gang_files = split_appendix_profiles(appendix_pages, doc["title"])

            saved = 0
            for slug, content in gang_files.items():
                if not force and page_exists(SOURCE, slug):
                    continue
                save_content(slug, doc["url"], content)
                saved += 1
            print(f"  [ok] {prefix} appendix → {saved} gang profiles ({len(gang_files)} total)")
        else:
            # Save whole document as one file
            if force or not page_exists(SOURCE, prefix):
                full_text = "\n\n".join(p.strip() for p in pages if p.strip())
                save_content(prefix, doc["url"], f"{doc['title']}\n\n{full_text}")
                print(f"  [ok] {prefix} ({len(full_text.split()):,} words)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape FBI National Gang Threat Assessment PDFs")
    parser.add_argument("--force", action="store_true", help="Re-scrape already-saved pages")
    args = parser.parse_args()
    scrape(force=args.force)


if __name__ == "__main__":
    main()
