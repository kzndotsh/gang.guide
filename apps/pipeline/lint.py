#!/usr/bin/env python3
"""lint.py — structural validation + quality signals for gang.guide data.

Runs as the gate before build.py. Errors fail the build; warnings are printed.

Usage:
    python3 apps/pipeline/lint.py
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ORGS_DIR = ROOT / "data" / "orgs"
RELS_FILE = ROOT / "data" / "edges.json"
LANES_FILE = ROOT / "data" / "lanes.json"

REQUIRED_FIELDS = {"id", "name", "lane", "description", "founded_year", "sources"}

errors: list[str] = []
warnings: list[str] = []
info: list[str] = []


def load_orgs() -> dict[str, dict]:
    orgs = {}
    for f in sorted(ORGS_DIR.iterdir()):
        if f.suffix != ".json":
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        org_id = d.get("id", "")
        if org_id in orgs:
            errors.append(f"DUPLICATE ID: {org_id} in {f.name} and previous file")
        orgs[org_id] = d
        orgs[org_id]["_file"] = f.name
    return orgs


def load_edges() -> list[dict]:
    if not RELS_FILE.exists():
        return []
    return json.loads(RELS_FILE.read_text(encoding="utf-8"))


def load_lanes() -> set[str]:
    if not LANES_FILE.exists():
        return set()
    cfg = json.loads(LANES_FILE.read_text(encoding="utf-8"))
    return {l["id"] for l in cfg.get("lanes", [])}


# Pairs that have been reviewed and confirmed as distinct (not duplicates)
DUPE_IGNORE = {
    frozenset({"Crips", "Gangster Crips"}),
    frozenset({"Black P. Stone Nation", "Almighty Black P. Stone Nation"}),
    frozenset({"Fruit Town Brims", "Westside Fruit Town Brims"}),
    frozenset({"Hustler Crips", "East Side Hustler Crips"}),
    frozenset({"Asian Boyz", "West Side Asian Boyz"}),
    frozenset({"East Side Pirus (Compton)", "West Side Pirus (Compton)"}),
    frozenset({"Reseda, South Side", "Reseda, West Side"}),
    frozenset({"Almighty Popes", "Insane Popes (South Side)"}),
    frozenset({"Lantana Blocc Compton Crips", "Santana Blocc Compton Crips"}),
    frozenset({"118 East Coast Crips", "1st East Coast Crips"}),
}


def check_fuzzy_dupes(orgs: dict[str, dict]):
    """Detect potential duplicate orgs via word overlap + edit distance."""
    from collections import defaultdict

    def norm(name: str) -> str:
        return re.sub(r'[^a-z0-9 ]', '', name.lower()).strip()

    def word_similarity(a: str, b: str) -> float:
        """Dice coefficient on word sets."""
        a_set = set(a.split())
        b_set = set(b.split())
        if not a_set or not b_set:
            return 0.0
        return 2 * len(a_set & b_set) / (len(a_set) + len(b_set))

    def levenshtein(a: str, b: str) -> int:
        """Standard edit distance."""
        if len(a) < len(b):
            a, b = b, a
        if not b:
            return len(a)
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a):
            curr = [i + 1]
            for j, cb in enumerate(b):
                curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (ca != cb)))
            prev = curr
        return prev[-1]

    def edit_similarity(a: str, b: str) -> float:
        """Normalized edit distance similarity (1.0 = identical)."""
        if not a or not b:
            return 0.0
        dist = levenshtein(a, b)
        return 1.0 - dist / max(len(a), len(b))

    # Group by lane (only compare within same lane)
    by_lane: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for org_id, org in orgs.items():
        by_lane[org.get("lane", "")].append((org["_file"], org.get("name", ""), norm(org.get("name", ""))))

    for lane, items in by_lane.items():
        if len(items) < 2:
            continue
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                f1, name1, norm1 = items[i]
                f2, name2, norm2 = items[j]
                if frozenset({name1, name2}) in DUPE_IGNORE:
                    continue
                # Skip if names too different in length (>2x)
                if len(norm1) > 2 * len(norm2) or len(norm2) > 2 * len(norm1):
                    continue
                wsim = word_similarity(norm1, norm2)
                esim = edit_similarity(norm1, norm2)
                # Flag if either metric is high
                if wsim >= 0.90 or esim >= 0.90:
                    # Skip numbered sets that only differ by street number
                    nums1 = set(re.findall(r'\d+', norm1))
                    nums2 = set(re.findall(r'\d+', norm2))
                    words1 = set(re.sub(r'\d+', '', norm1).split())
                    words2 = set(re.sub(r'\d+', '', norm2).split())
                    if nums1 != nums2 and words1 == words2:
                        continue  # Same name pattern, different numbers = distinct sets
                    best = max(wsim, esim)
                    warnings.append(f"potential dupe ({best:.0%}): {name1} ({f1}) ↔ {name2} ({f2})")


def check_orgs(orgs: dict[str, dict], lane_ids: set[str]):
    names_seen: dict[str, str] = {}

    for org_id, org in orgs.items():
        f = org["_file"]

        # Required fields
        for field in REQUIRED_FIELDS:
            if not org.get(field):
                errors.append(f"{f}: missing required field '{field}'")

        # Lane valid
        lane = org.get("lane", "")
        if lane and lane_ids and lane not in lane_ids:
            errors.append(f"{f}: lane '{lane}' not in lanes.json")

        # Sources have url+title
        for i, s in enumerate(org.get("sources") or []):
            if not s.get("url"):
                errors.append(f"{f}: source[{i}] missing url")
            if not s.get("title"):
                errors.append(f"{f}: source[{i}] missing title")

        # Disbanded before founded
        if org.get("disbanded_year") and org.get("founded_year"):
            if org["disbanded_year"] < org["founded_year"]:
                errors.append(f"{f}: disbanded_year ({org['disbanded_year']}) before founded_year ({org['founded_year']})")

        # --- Warnings ---
        desc = org.get("description", "")
        if len(desc) < 50:
            warnings.append(f"{f}: description under 50 chars ({len(desc)})")
        if "&amp;" in desc or "&#" in desc or "&nbsp;" in desc:
            warnings.append(f"{f}: description contains HTML entities")

        for alias in (org.get("aliases") or []):
            if len(alias) > 60:
                warnings.append(f"{f}: alias too long ({len(alias)} chars): '{alias[:50]}...'")

        colors = org.get("colors") or []
        for c in colors:
            if c.lower() in ("give details", "unknown", ""):
                warnings.append(f"{f}: invalid color value '{c}'")

        # Crip set before 1969
        y = org.get("founded_year")
        if y and y < 1969 and "crip" in org.get("name", "").lower() and "crip" in (org.get("lane") or ""):
            warnings.append(f"{f}: Crip set founded {y} (Crips started 1969)")
        if y and y < 1972 and "piru" in org.get("name", "").lower():
            warnings.append(f"{f}: Piru set founded {y} (Pirus started 1972)")

        # Duplicate names
        name = org.get("name", "")
        if name in names_seen:
            warnings.append(f"{f}: duplicate name '{name}' (also in {names_seen[name]})")
        names_seen[name] = f

        # Name quality checks
        if re.search(r',\s*\d+\s*$', name):
            warnings.append(f"{f}: name ends with ', NUMBER' — move number to front: '{name}'")
        if name != name.strip():
            warnings.append(f"{f}: name has leading/trailing whitespace")
        if '  ' in name:
            warnings.append(f"{f}: name has double spaces: '{name}'")
        if name.startswith('Westside ') or name.startswith('Eastside '):
            if name.replace('Westside ', '').replace('Eastside ', '') in names_seen:
                warnings.append(f"{f}: name has redundant Westside/Eastside prefix (may duplicate)")
        if re.search(r'\(w/s\)|\(e/s\)|\(n/s\)', name, re.IGNORECASE):
            warnings.append(f"{f}: name has junk side abbreviation in parens: '{name}'")
        if re.search(r'\(v\.\s', name):
            warnings.append(f"{f}: name has 'v.' prefix in parens: '{name}'")
        if name.endswith(' gang') or name.endswith(' Gang'):
            if org.get("type") == "street_gang":
                pass  # some legit names end in Gang
        if re.search(r'[:\|]', name):
            warnings.append(f"{f}: name contains colon or pipe: '{name}'")

        # Description quality
        desc = org.get("description", "")
        if desc and desc[0].islower():
            warnings.append(f"{f}: description starts with lowercase")
        if re.search(r'^(Full Name|Also Known As|Name|Acronym|Founded|Origin|Founder|Videos|Territory|Ethnicity|Membership):', desc) or re.search(r'^[A-Z][^.]{0,30}(Also Known As|Founded|Acronym):', desc):
            warnings.append(f"{f}: description starts with infobox pattern (scrape junk)")

        # Type/lane mismatch
        lane = org.get("lane", "")
        if "prison" in lane and org.get("type", "") == "street_gang":
            warnings.append(f"{f}: street_gang in prison lane (should be prison_gang?)")
        if "motorcycle" in lane and org.get("type", "") != "motorcycle_club":
            org_type = org.get('type', '')
            warnings.append(f"{f}: {org_type} in motorcycle lane (should be motorcycle_club?)")

        # --- Info ---
        sources = org.get("sources") or []
        if len(sources) == 1:
            info.append(f"{f}: single source only")

        precision = org.get("founded_year_precision", "")
        if precision in ("estimate", "decade", ""):
            info.append(f"{f}: year precision '{precision or 'empty'}' — could be researched")


def check_edges(edges: list[dict], org_ids: set[str]):
    seen_edges: set[tuple] = set()

    for i, e in enumerate(edges):
        src = e.get("source", "")
        tgt = e.get("target", "")
        etype = e.get("type", "")

        # Broken refs
        if src not in org_ids:
            errors.append(f"edge[{i}]: source '{src}' not in orgs")
        if tgt not in org_ids:
            errors.append(f"edge[{i}]: target '{tgt}' not in orgs")

        # Self-reference
        if src == tgt:
            errors.append(f"edge[{i}]: self-referencing edge ({src})")

        # Duplicates
        key = (src, tgt, etype)
        if key in seen_edges:
            errors.append(f"edge[{i}]: duplicate edge {src} → {tgt} ({etype})")
        seen_edges.add(key)

    # Contradictory edges
    alliance_pairs = {(e["source"], e["target"]) for e in edges if e.get("type") == "alliance"}
    rivalry_pairs = {(e["source"], e["target"]) for e in edges if e.get("type") == "rivalry"}
    both = alliance_pairs & rivalry_pairs
    for src, tgt in both:
        warnings.append(f"contradictory edges: {src} ↔ {tgt} has both alliance AND rivalry")


def check_isolated(orgs: dict[str, dict], edges: list[dict]):
    connected = set()
    for e in edges:
        connected.add(e.get("source", ""))
        connected.add(e.get("target", ""))
    # Also count orgs with nation_affiliation as connected
    for org_id, org in orgs.items():
        if org.get("nation_affiliation"):
            connected.add(org_id)

    isolated = [oid for oid in orgs if oid not in connected]
    if isolated:
        info.append(f"{len(isolated)} orgs with zero edges (isolated nodes)")


def check_descriptions(orgs: dict[str, dict]):
    """Check description quality beyond just length."""
    for org_id, org in orgs.items():
        f = org["_file"]
        desc = org.get("description", "")

        # Description is just the org name repeated
        name = org.get("name", "").lower()
        if desc.lower().startswith(f"{name} is a") and len(desc) < 120:
            info.append(f"{f}: thin boilerplate description")

        # Description contains raw scrape junk
        if any(junk in desc for junk in ("class=", "widget-title", "<div", "href=", ".json", "undefined")):
            warnings.append(f"{f}: description contains code/markup junk")

        # Description has unbalanced quotes or brackets
        if desc.count('"') % 2 != 0:
            info.append(f"{f}: description has unbalanced quotes")

        # Descriptions that end abruptly (likely truncated)
        if len(desc) > 100 and desc[-1] not in '.!?")\' ':
            info.append(f"{f}: description may be truncated (ends with '{desc[-1]}')")


def check_sources(orgs: dict[str, dict]):
    """Check source URL quality."""
    from collections import Counter
    url_counts: Counter = Counter()
    
    for org_id, org in orgs.items():
        f = org["_file"]
        for s in (org.get("sources") or []):
            url = s.get("url", "")
            url_counts[url] += 1
            
            # Suspicious domains
            if any(d in url for d in ("fandom.com/wiki", "answers.yahoo", "quora.com")):
                info.append(f"{f}: low-quality source domain: {url[:60]}")

    # URLs used excessively (same article cited in 10+ orgs = probably wrong)
    for url, count in url_counts.most_common(5):
        if count > 15:
            warnings.append(f"source URL used in {count} orgs (over-cited): {url[:80]}")


def check_id_consistency(orgs: dict[str, dict]):
    """Check that org IDs match filenames."""
    for org_id, org in orgs.items():
        f = org["_file"]
        expected_id = f"org:{f.replace('.json', '')}"
        if org_id != expected_id:
            # Not an error (IDs can differ from filenames) but flag inconsistency
            info.append(f"{f}: ID '{org_id}' doesn't match filename slug")


def check_temporal_logic(orgs: dict[str, dict], edges: list[dict]):
    """Check for impossible temporal relationships."""
    org_years = {oid: org.get("founded_year") for oid, org in orgs.items() if org.get("founded_year")}
    
    for e in edges:
        src = e.get("source", "")
        tgt = e.get("target", "")
        etype = e.get("type", "")
        
        # Spin-off can't be older than parent
        if etype == "spin_off" and src in org_years and tgt in org_years:
            if org_years[src] < org_years[tgt]:
                warnings.append(f"temporal: spin_off {src} ({org_years[src]}) older than parent {tgt} ({org_years[tgt]})")

    # Nation affiliation: org can't be older than its nation
    nation_years = {
        "org:crips": 1969, "org:bloods": 1972, "org:folk-nation": 1978,
        "org:people-nation": 1978, "org:surenos": 1968, "org:nortenos": 1968,
    }
    for org_id, org in orgs.items():
        aff = org.get("nation_affiliation")
        if aff and aff in nation_years and org.get("founded_year"):
            # Org founded before nation existed AND precision is exact/circa = suspicious
            if org["founded_year"] < nation_years[aff] and org.get("founded_year_precision") in ("exact", "circa"):
                info.append(f"{org['_file']}: founded {org['founded_year']} but affiliated with {aff} (est. {nation_years[aff]})")


def main():
    lane_ids = load_lanes()
    orgs = load_orgs()
    edges = load_edges()
    org_ids = set(orgs.keys())

    check_orgs(orgs, lane_ids)
    check_edges(edges, org_ids)
    check_isolated(orgs, edges)
    check_fuzzy_dupes(orgs)
    check_descriptions(orgs)
    check_sources(orgs)
    check_id_consistency(orgs)
    check_temporal_logic(orgs, edges)

    # Print results
    if info:
        print(f"\n{'='*60}")
        print(f"INFO ({len(info)})")
        print(f"{'='*60}")
        for msg in info[:20]:
            print(f"  ℹ {msg}")
        if len(info) > 20:
            print(f"  ... and {len(info) - 20} more")

    if warnings:
        print(f"\n{'='*60}")
        print(f"WARNINGS ({len(warnings)})")
        print(f"{'='*60}")
        for msg in warnings[:30]:
            print(f"  ⚠ {msg}")
        if len(warnings) > 30:
            print(f"  ... and {len(warnings) - 30} more")

    if errors:
        print(f"\n{'='*60}")
        print(f"ERRORS ({len(errors)})")
        print(f"{'='*60}")
        for msg in errors:
            print(f"  ✗ {msg}")
        print(f"\n❌ Lint FAILED with {len(errors)} error(s)")
        sys.exit(1)
    else:
        print(f"\n✓ Lint passed: {len(orgs)} orgs, {len(edges)} edges ({len(warnings)} warnings, {len(info)} info)")


if __name__ == "__main__":
    main()
