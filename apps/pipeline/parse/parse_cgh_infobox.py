"""Parse CGH info tables → structured fields.

Extracts founded year, colors, affiliations, ethnicity, status from
Chicago Gang History HTML pages.

Usage:
    python -m apps.pipeline.parse.parse_cgh_infobox
"""

import json
import re
from pathlib import Path

DATA_RAW = Path(__file__).resolve().parent.parent.parent.parent / "data" / "raw" / "chicago_history"


def extract_field(html: str, field: str) -> str:
    """Extract a field value from CGH HTML table."""
    pattern = rf'{field}\s*</t[hd]>\s*<td[^>]*>(.*?)</td>'
    m = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
    if m:
        val = re.sub(r'<[^>]+>', ' ', m.group(1))
        return re.sub(r'\s+', ' ', val).strip()
    return ''


def extract_year(founded_str: str) -> int | None:
    m = re.search(r'(\d{4})', founded_str)
    return int(m.group(1)) if m else None


def extract_precision(founded_str: str) -> str:
    if 'c.' in founded_str or 'circa' in founded_str.lower():
        return 'circa'
    return 'exact'


def parse_page(slug: str) -> dict | None:
    """Parse a single CGH page into structured data."""
    path = DATA_RAW / slug
    # Try .txt (old format) or content.txt (new format)
    for fname in ("content.txt", f"{slug}.txt"):
        fpath = DATA_RAW / fname if "/" not in fname else path / fname
        if not fpath.exists():
            fpath = DATA_RAW / f"{slug}.txt"
        if fpath.exists():
            html = fpath.read_text(encoding="utf-8")
            break
    else:
        return None

    founded = extract_field(html, 'Founded')
    colors = extract_field(html, 'Colors') or extract_field(html, 'Color usage')
    affiliations = extract_field(html, 'Affiliations')
    ethnicity = extract_field(html, 'Primary ethnicities')
    status = extract_field(html, 'Status')

    return {
        "slug": slug,
        "founded_year": extract_year(founded),
        "founded_year_precision": extract_precision(founded),
        "colors": colors,
        "affiliations": affiliations,
        "ethnicity": ethnicity,
        "status": status.lower() if status else "",
    }


def parse_all() -> list[dict]:
    """Parse all CGH pages."""
    results = []
    for f in sorted(DATA_RAW.iterdir()):
        if f.suffix == ".txt" and f.stem != "_progress":
            data = parse_page(f.stem)
            if data:
                results.append(data)
    return results


if __name__ == "__main__":
    results = parse_all()
    print(f"Parsed {len(results)} CGH pages")
    for r in results[:5]:
        print(f"  {r['slug']:40s} {r['founded_year']} {r['colors'][:25]}")
