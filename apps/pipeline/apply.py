"""apply.py — Conservative upgrade of org data from extractions.

Only overwrites fields that are currently weaker. Never downgrades quality.
Runs lint.py as final gate — rejects changes if lint fails.

Usage:
    python -m apps.pipeline.apply --source chicago_history
    python -m apps.pipeline.apply --source chicago_history --dry-run
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .lib.resolve import build_index, resolve

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_EXTRACTED = ROOT / "data" / "extracted"
DATA_ORGS = ROOT / "data" / "orgs"
DATA_RELS = ROOT / "data" / "edges.json"


def load_org_by_id(org_id: str, org_path_index: dict) -> tuple[Path | None, dict | None]:
    """Find and load an org file by ID using prebuilt index."""
    path = org_path_index.get(org_id)
    if path and path.exists():
        return path, json.loads(path.read_text(encoding="utf-8"))
    return None, None


def build_org_path_index() -> dict[str, Path]:
    """Build org_id → file path index."""
    index = {}
    for f in DATA_ORGS.iterdir():
        if f.suffix != ".json":
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        index[d.get("id", "")] = f
    return index


def apply_extraction(consensus: dict, org_id: str, org_path_index: dict, dry_run: bool = False) -> list[str]:
    """Apply consensus extraction to an org. Returns list of changes made."""
    path, org = load_org_by_id(org_id, org_path_index)
    if not org:
        return []

    changes = []

    # Year: only if more precise
    if consensus.get("founded_year") and org.get("founded_year_precision") in ("decade", "estimate", "circa"):
        if not dry_run:
            org["founded_year"] = consensus["founded_year"]
            org["founded_year_precision"] = "circa"
        changes.append(f"year: {org.get('founded_year')} → {consensus['founded_year']}")

    # Description: only if current is thin
    if consensus.get("description") and len(org.get("description", "")) < 100 and len(consensus["description"]) > 150:
        if not dry_run:
            org["description"] = consensus["description"]
        changes.append(f"description: upgraded ({len(consensus['description'])} chars)")

    # Colors: only if empty
    if consensus.get("colors") and not org.get("colors"):
        if not dry_run:
            org["colors"] = consensus["colors"]
        changes.append(f"colors: {consensus['colors']}")

    # Symbols: only if empty
    if consensus.get("symbols") and not org.get("symbols"):
        if not dry_run:
            org["symbols"] = consensus["symbols"]
        changes.append(f"symbols: {consensus['symbols']}")

    # Membership: only if not set
    if consensus.get("membership_estimate") and not org.get("membership_estimate"):
        if not dry_run:
            org["membership_estimate"] = consensus["membership_estimate"]
        changes.append(f"membership: {consensus['membership_estimate']}")

    if changes and not dry_run and path:
        path.write_text(json.dumps(org, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return changes


def apply_edges(consensus: dict, org_id: str, org_index: dict, edges_list: list, existing_keys: set, dry_run: bool = False) -> list[str]:
    """Apply extracted edges. Mutates edges_list and existing_keys in place."""
    edges_added = []

    for edge in consensus.get("edges", []):
        target_name = edge.get("target", "")
        target_id = resolve(target_name, org_index)
        if not target_id:
            continue

        etype = edge.get("type", "alliance")
        if target_id == org_id:
            continue  # skip self-references
        key = (org_id, target_id, etype)
        if key in existing_keys:
            continue

        # Skip contradictions without temporal data
        # (alliance where rivalry exists, or vice versa)
        if etype in ("alliance", "rivalry"):
            opposite = "rivalry" if etype == "alliance" else "alliance"
            has_contradiction = (
                (org_id, target_id, opposite) in existing_keys
                or (target_id, org_id, opposite) in existing_keys
            )
            if has_contradiction and not edge.get("start_year") and not edge.get("period"):
                continue

        new_edge = {"source": org_id, "target": target_id, "type": etype}
        if edge.get("evidence"):
            new_edge["evidence"] = edge["evidence"]
        if edge.get("period"):
            # Convert "1977-1992" string to start_year/end_year ints
            import re as _re
            m = _re.match(r"(\d{4})\s*[-–]\s*(\d{4}|present)", edge["period"])
            if m:
                new_edge["start_year"] = int(m.group(1))
                if m.group(2) != "present":
                    new_edge["end_year"] = int(m.group(2))

        if not dry_run:
            edges_list.append(new_edge)
            existing_keys.add(key)
        edges_added.append(f"{etype}: {org_id} → {target_id}")

    return edges_added


def run_lint() -> bool:
    """Run lint.py and return True if it passes."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "apps" / "pipeline" / "lint.py")],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Apply extractions to org data")
    parser.add_argument("--source", required=True, help="Source to apply (e.g. chicago_history)")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing files")
    args = parser.parse_args()

    source_dir = DATA_EXTRACTED / args.source
    if not source_dir.exists():
        print(f"No extractions for {args.source}")
        return

    # Build org index for entity resolution
    org_index = build_index()
    org_path_index = build_org_path_index()

    # Load page→org mapping
    index_path = ROOT / "data" / "raw" / "index.json"
    page_map = json.loads(index_path.read_text()) if index_path.exists() else {}

    # Load edges once
    edges_list = json.loads(DATA_RELS.read_text(encoding="utf-8"))
    existing_keys = {(e["source"], e["target"], e["type"]) for e in edges_list}

    total_changes = 0
    total_edges = 0

    for page_dir in sorted(source_dir.iterdir()):
        if not page_dir.is_dir():
            continue
        consensus_path = page_dir / "consensus.json"
        if not consensus_path.exists():
            continue

        consensus = json.loads(consensus_path.read_text(encoding="utf-8"))
        slug = page_dir.name
        org_id = page_map.get(f"{args.source}/{slug}")

        if not org_id:
            # Try resolving subject_org name
            org_id = resolve(consensus.get("subject_org", ""), org_index)

        if not org_id:
            continue

        changes = apply_extraction(consensus, org_id, org_path_index, dry_run=args.dry_run)
        edges = apply_edges(consensus, org_id, org_index, edges_list, existing_keys, dry_run=args.dry_run)

        if changes or edges:
            prefix = "[DRY] " if args.dry_run else ""
            print(f"  {prefix}{slug} → {org_id}")
            for c in changes:
                print(f"    {c}")
            for e in edges:
                print(f"    + {e}")
            total_changes += len(changes)
            total_edges += len(edges)

    # Write edges once at end
    if not args.dry_run and total_edges > 0:
        DATA_RELS.write_text(json.dumps(edges_list, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Applied: {total_changes} field updates, {total_edges} new edges")

    # Run lint as final gate
    if not args.dry_run and (total_changes > 0 or total_edges > 0):
        print("\nRunning lint...")
        if run_lint():
            print("✓ Lint passed — changes accepted")
        else:
            print("❌ Lint FAILED — changes may have introduced errors")
            sys.exit(1)


if __name__ == "__main__":
    main()
