"""merge.py — Consensus filtering across multiple extraction runs.

Takes 3 extraction outputs per page, keeps only data that appears in 2+ runs.

Usage:
    python -m apps.pipeline.merge --source chicago_history
"""

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_EXTRACTED = ROOT / "data" / "extracted"


def merge_runs(runs: list[dict]) -> dict:
    """Merge 3 extraction runs using consensus rules."""
    if not runs:
        return {}
    if len(runs) == 1:
        return runs[0]

    # Subject org: majority vote
    subjects = [r.get("subject_org") for r in runs if r.get("subject_org")]
    subject = Counter(subjects).most_common(1)[0][0] if subjects else None

    # Founded year: majority vote (2/3 agree)
    years = [r.get("founded_year") for r in runs if r.get("founded_year")]
    year_counts = Counter(years)
    founded_year = year_counts.most_common(1)[0][0] if year_counts and year_counts.most_common(1)[0][1] >= 2 else None

    # Colors: appear in 2+ runs
    all_colors = []
    for r in runs:
        all_colors.extend(r.get("colors") or [])
    color_counts = Counter(c.lower() for c in all_colors)
    colors = sorted(c for c, count in color_counts.items() if count >= 2)

    # Symbols: appear in 2+ runs
    all_symbols = []
    for r in runs:
        all_symbols.extend(r.get("symbols") or [])
    symbol_counts = Counter(all_symbols)
    symbols = sorted(s for s, count in symbol_counts.items() if count >= 2)

    # Membership: median
    memberships = [r.get("membership_estimate") for r in runs if r.get("membership_estimate")]
    membership = sorted(memberships)[len(memberships) // 2] if memberships else None

    # Description: longest version
    descriptions = [r.get("description", "") for r in runs if r.get("description")]
    description = max(descriptions, key=len) if descriptions else ""

    # Edges: same target+type in 2+ runs
    edge_key_counts: Counter = Counter()
    edge_best: dict = {}
    for r in runs:
        for e in (r.get("edges") or []):
            key = (e.get("target", "").lower(), e.get("type", ""))
            edge_key_counts[key] += 1
            # Keep the one with longest evidence quote
            if key not in edge_best or len(e.get("evidence", "")) > len(edge_best[key].get("evidence", "")):
                edge_best[key] = e
    edges = [edge_best[k] for k, count in edge_key_counts.items() if count >= 2]

    # Orgs mentioned: appear in 2+ runs
    all_orgs = []
    for r in runs:
        all_orgs.extend(r.get("orgs_mentioned") or [])
    org_counts = Counter(o.lower() for o in all_orgs)
    orgs_mentioned = sorted(set(o for o in all_orgs if o.lower() in {k for k, c in org_counts.items() if c >= 2}))

    return {
        "subject_org": subject,
        "founded_year": founded_year,
        "colors": colors,
        "symbols": symbols,
        "membership_estimate": membership,
        "description": description,
        "edges": edges,
        "orgs_mentioned": orgs_mentioned,
    }


def process_source(source: str, force: bool = False):
    """Merge all extracted pages for a source."""
    source_dir = DATA_EXTRACTED / source
    if not source_dir.exists():
        print(f"No extractions found for {source}")
        return

    merged_count = 0
    skipped = 0
    for page_dir in sorted(source_dir.iterdir()):
        if not page_dir.is_dir():
            continue

        # Skip if already merged (unless --force)
        out_path = page_dir / "consensus.json"
        if not force and out_path.exists():
            skipped += 1
            continue

        # Prefer adjudicated.json (LLM-resolved conflicts) over algorithmic merge
        adj_path = page_dir / "adjudicated.json"
        if adj_path.exists():
            consensus = json.loads(adj_path.read_text(encoding="utf-8"))
            out_path.write_text(json.dumps(consensus, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            merged_count += 1
            edge_count = len(consensus.get("edges", []))
            print(f"  {page_dir.name}: {edge_count} edges (adjudicated)")
            continue

        # Load runs
        runs = []
        for i in range(1, 4):
            run_path = page_dir / f"run_{i + 1}.json"
            if run_path.exists():
                runs.append(json.loads(run_path.read_text(encoding="utf-8")))

        if len(runs) < 2:
            continue

        # Merge
        consensus = merge_runs(runs)

        # Save
        out_path = page_dir / "consensus.json"
        out_path.write_text(json.dumps(consensus, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        merged_count += 1

        edge_count = len(consensus.get("edges", []))
        print(f"  {page_dir.name}: {edge_count} edges, {len(consensus.get('colors', []))} colors")

    print(f"\nMerged {merged_count} pages" + (f", skipped {skipped} (already done)" if skipped else ""))


def main():
    parser = argparse.ArgumentParser(description="Consensus merge of extraction runs")
    parser.add_argument("--source", required=True, help="Source to merge (e.g. chicago_history)")
    parser.add_argument("--force", action="store_true", help="Re-merge even if consensus.json exists")
    args = parser.parse_args()
    process_source(args.source, force=args.force)


if __name__ == "__main__":
    main()
