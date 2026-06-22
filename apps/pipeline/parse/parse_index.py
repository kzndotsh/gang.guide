"""Build raw page → org ID mapping.

Fuzzy-matches page slugs/titles to existing org names to create
data/raw/index.json mapping.

Usage:
    python -m apps.pipeline.parse.parse_index
"""

import json
from pathlib import Path

from ..lib.resolve import build_index, normalize

DATA_RAW = Path(__file__).resolve().parent.parent.parent.parent / "data" / "raw"
INDEX_PATH = DATA_RAW / "index.json"


def build_page_index() -> dict[str, str | None]:
    """Build mapping of source/slug → org_id for all raw pages."""
    org_index = build_index()
    page_map: dict[str, str | None] = {}

    for source_dir in DATA_RAW.iterdir():
        if not source_dir.is_dir() or source_dir.name.startswith("_"):
            continue

        source = source_dir.name
        for page in source_dir.iterdir():
            if page.name.startswith("_"):
                continue

            slug = page.stem if page.is_file() else page.name
            key = f"{source}/{slug}"

            # Try to resolve slug as org name
            norm = normalize(slug.replace("-", " ").replace("_", " "))
            org_id = org_index.get(norm)

            page_map[key] = org_id

    return page_map


def main():
    page_map = build_page_index()
    matched = sum(1 for v in page_map.values() if v)
    unmatched = sum(1 for v in page_map.values() if not v)

    INDEX_PATH.write_text(json.dumps(page_map, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Index built: {len(page_map)} pages ({matched} matched, {unmatched} unmatched)")
    print(f"Saved to {INDEX_PATH}")


if __name__ == "__main__":
    main()
