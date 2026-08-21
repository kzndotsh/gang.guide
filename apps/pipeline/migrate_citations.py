#!/usr/bin/env python3
"""One-time migration: convert legacy evidence/source_url/sources fields to citations[].

Run once, then delete this script.

Usage:
    python3 apps/pipeline/migrate_citations.py
    python3 apps/pipeline/migrate_citations.py --dry-run
"""

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent.parent
EDGES_FILE = ROOT / "data" / "edges.json"

DOMAIN_TITLES: dict[str, str] = {
    "en.wikipedia.org": "Wikipedia",
    "unitedgangs.com": "UnitedGangs",
    "www.unitedgangs.com": "UnitedGangs",
    "streetgangs.com": "StreetGangs",
    "www.streetgangs.com": "StreetGangs",
    "chicagoganghistory.com": "Chicago Gang History",
    "www.chicagoganghistory.com": "Chicago Gang History",
    "detroitstreetgangs.com": "Detroit Street Gangs",
    "www.detroitstreetgangs.com": "Detroit Street Gangs",
    "newyorkcitygangs.com": "New York City Gangs",
    "www.newyorkcitygangs.com": "New York City Gangs",
    "stonegreasers.com": "StoneGreasers",
    "www.stonegreasers.com": "StoneGreasers",
    "justice.gov": "U.S. Department of Justice",
    "www.justice.gov": "U.S. Department of Justice",
    "fbi.gov": "FBI",
    "www.fbi.gov": "FBI",
    "adl.org": "ADL",
    "www.adl.org": "ADL",
    "splcenter.org": "SPLC",
    "www.splcenter.org": "SPLC",
    "blackpast.org": "BlackPast",
    "www.blackpast.org": "BlackPast",
    "web.archive.org": "Wayback Machine",
    "ngcrc.com": "NGCRC",
    "www.ngcrc.com": "NGCRC",
    "nagia.org": "NAGIA",
    "www.nagia.org": "NAGIA",
    "gangenforcement.com": "Gang Enforcement",
    "www.gangenforcement.com": "Gang Enforcement",
    "stophoustongangs.org": "StopHoustonGangs",
    "www.stophoustongangs.org": "StopHoustonGangs",
    "courtlistener.com": "CourtListener",
    "www.courtlistener.com": "CourtListener",
}


def infer_title(url: str) -> str:
    """Infer a human-readable title from a URL using domain mapping."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain in DOMAIN_TITLES:
            return DOMAIN_TITLES[domain]
        # Strip www. prefix and use the base domain as a fallback
        bare = domain.removeprefix("www.")
        return DOMAIN_TITLES.get(bare, bare)
    except Exception:
        return ""


def migrate_edge(edge: dict) -> dict:
    """Convert a single edge from legacy fields to citations[]."""
    evidence = edge.get("evidence", "")
    source_url = edge.get("source_url", "")
    legacy_sources = edge.get("sources")

    # Build citations list
    citations: list[dict] = []

    if legacy_sources:
        # Convert legacy sources[] — each has url + title
        # Add top-level evidence to the first source if present
        for i, src in enumerate(legacy_sources):
            url = src.get("url", "")
            title = src.get("title", "") or infer_title(url)
            citation: dict = {}
            if url:
                citation["url"] = url
            if title:
                citation["title"] = title
            # Attach top-level evidence to first citation
            if i == 0 and evidence:
                citation["evidence"] = evidence
            else:
                citation["evidence"] = ""
            citations.append(citation)
    elif evidence or source_url:
        # Convert flat evidence/source_url to a single citation
        citation = {
            "url": source_url,
            "title": infer_title(source_url),
            "evidence": evidence,
        }
        citations.append(citation)
    # else: no evidence at all → citations stays []

    # Build new edge without legacy fields
    new_edge: dict = {}
    for k, v in edge.items():
        if k in ("evidence", "source_url", "sources"):
            continue
        new_edge[k] = v
    new_edge["citations"] = citations

    return new_edge


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate edges to citations[] schema")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    edges = json.loads(EDGES_FILE.read_text(encoding="utf-8"))

    migrated = []
    stats = {"total": 0, "had_evidence": 0, "had_sources": 0, "had_neither": 0}

    for edge in edges:
        stats["total"] += 1
        had_evidence = bool(edge.get("evidence") or edge.get("source_url"))
        had_sources = bool(edge.get("sources"))
        if had_evidence or had_sources:
            if had_sources:
                stats["had_sources"] += 1
            else:
                stats["had_evidence"] += 1
        else:
            stats["had_neither"] += 1

        migrated.append(migrate_edge(edge))

    print(f"Migration stats:")
    print(f"  Total edges: {stats['total']}")
    print(f"  Had evidence/source_url: {stats['had_evidence']}")
    print(f"  Had sources[]: {stats['had_sources']}")
    print(f"  Had neither: {stats['had_neither']}")

    if args.dry_run:
        print(f"\n[DRY RUN] Would write {len(migrated)} migrated edges to {EDGES_FILE}")
        # Show a sample
        sample = [e for e in migrated if e.get("citations")][:2]
        for s in sample:
            print(f"\nSample: {json.dumps(s, indent=2)}")
        return

    EDGES_FILE.write_text(json.dumps(migrated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n✓ Migrated {len(migrated)} edges → {EDGES_FILE}")


if __name__ == "__main__":
    main()
