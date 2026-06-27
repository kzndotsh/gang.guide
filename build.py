#!/usr/bin/env python3
"""Build graph.json from flat org files + relationships.

Usage:
    python build.py              # outputs to apps/web/static/graph.json
    python build.py --out path   # custom output path
"""

import json
import sys
from datetime import datetime, UTC
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ORGS_DIR = ROOT / "data" / "orgs"
EDGES_FILE = ROOT / "data" / "edges.json"
LANES_CONFIG = ROOT / "data" / "lanes.json"
DEFAULT_OUT = ROOT / "apps" / "web" / "static" / "graph.json"


def load_lanes():
    cfg = json.loads(LANES_CONFIG.read_text(encoding="utf-8"))
    lanes = sorted(cfg.get("lanes", []), key=lambda l: l.get("order", 999))
    return {l["id"]: l for l in lanes}, lanes


def build_layout(org, lane_meta, slot):
    lane_id = org.get("lane", "unplaced")
    meta = lane_meta.get(lane_id, {"label": lane_id, "order": 999})

    year = org.get("founded_year")
    precision = org.get("founded_year_precision")

    if not year:
        # No year: deterministic spread across 1965-2005 based on org id
        h = hash(org["id"]) & 0xFFFF
        display_year = 1965 + (h % 40)
    elif precision in ("decade", "circa") or year % 10 == 0:
        # Round/imprecise year: jitter within ±4 years
        h = hash(org["id"]) & 0xFF
        display_year = year + (h % 9) - 4
    else:
        display_year = year

    # Add fractional offset based on slot so same-year nodes don't stack exactly
    display_year = display_year + (slot % 5) * 0.4

    return {
        "lane": lane_id,
        "lane_label": meta.get("label", lane_id),
        "lane_index": meta.get("order", 999),
        "display_year": display_year,
        "slot": slot,
        "overview": False,
    }


def build_node(org, lane_meta, slot):
    layout = build_layout(org, lane_meta, slot)
    data = {
        "standard_name": org.get("name"),
        "aliases": org.get("aliases", []),
        "type": org.get("type"),
        "metro": org.get("metro"),
        "founded_year": org.get("founded_year"),
        "founded_year_precision": org.get("founded_year_precision"),
        "dissolved_year": org.get("dissolved_year"),
        "description": org.get("description"),
        "colors": org.get("colors", []),
        "symbols": org.get("symbols", []),
        "nation_affiliation": org.get("nation_affiliation"),
        "status": org.get("status"),
        "sources": org.get("sources", []),
        "layout": layout,
    }
    # Strip None values
    data = {k: v for k, v in data.items() if v is not None}

    return {
        "id": org["id"],
        "type": "organization",
        "label": org.get("name", org["id"]),
        "detail_level": "skeleton",
        "review_status": "curated",
        "data": data,
    }


def build_graph(out_path=None):
    out_path = Path(out_path) if out_path else DEFAULT_OUT
    lane_meta, lanes_list = load_lanes()

    # Load all orgs
    orgs = []
    for f in sorted(ORGS_DIR.glob("*.json")):
        orgs.append(json.loads(f.read_text(encoding="utf-8")))

    # Group by lane and assign slots (sorted by year so adjacent slots have adjacent years)
    from collections import defaultdict
    lane_orgs = defaultdict(list)
    for org in orgs:
        lane = org.get("lane", "unplaced")
        lane_orgs[lane].append(org)

    nodes = []
    for lane, lane_org_list in lane_orgs.items():
        # Sort by display year so nearby years get sequential slots (= different rows)
        lane_org_list.sort(key=lambda o: (o.get("founded_year") or 1980, o.get("name", "")))
        for slot, org in enumerate(lane_org_list):
            nodes.append(build_node(org, lane_meta, slot))

    # Load relationships
    node_ids = {n["id"] for n in nodes}
    edges = []
    if EDGES_FILE.exists():
        raw_edges = json.loads(EDGES_FILE.read_text(encoding="utf-8"))
        for e in raw_edges:
            if e["source"] in node_ids and e["target"] in node_ids:
                edge = {
                    "source": e["source"],
                    "target": e["target"],
                    "type": e["type"],
                }
                if e.get("start_year"):
                    edge["start_year"] = e["start_year"]
                if e.get("end_year"):
                    edge["end_year"] = e["end_year"]
                if e.get("sources"):
                    edge["sources"] = e["sources"]
                edges.append(edge)

    # Generate nation edges from nation_affiliation field (field is source of truth)
    for n in nodes:
        affiliation = n.get("data", {}).get("nation_affiliation")
        if affiliation and affiliation in node_ids:
            edges.append({"source": n["id"], "target": affiliation, "type": "nation"})

    # Split into slim graph (for rendering) and details (loaded on demand)
    details = {"nodes": {}}
    slim_nodes = []
    for n in nodes:
        data = n.get("data", {})
        # Extract heavy fields
        details["nodes"][n["id"]] = {
            "description": data.get("description"),
            "sources": data.get("sources", []),
        }
        # Keep only rendering fields
        slim_data = {k: v for k, v in data.items() if k not in ("description", "sources") and v is not None}
        slim_nodes.append({**n, "data": slim_data})

    # Compute coverage stats
    nodes_with_year = sum(1 for n in nodes if n.get("data", {}).get("founded_year"))
    nodes_exact_circa = sum(1 for n in nodes if n.get("data", {}).get("founded_year_precision") in ("exact", "circa"))
    nodes_decade = sum(1 for n in nodes if n.get("data", {}).get("founded_year_precision") == "decade")
    nodes_estimate = sum(1 for n in nodes if n.get("data", {}).get("founded_year_precision") in ("estimate", None) and n.get("data", {}).get("founded_year"))
    nodes_with_colors = sum(1 for n in nodes if n.get("data", {}).get("colors"))
    nodes_with_desc = sum(1 for n in nodes if len(n.get("data", {}).get("description", "")) > 50)
    nodes_with_aliases = sum(1 for n in nodes if n.get("data", {}).get("aliases"))
    nodes_with_metro = sum(1 for n in nodes if n.get("data", {}).get("metro"))
    nodes_active = sum(1 for n in nodes if n.get("data", {}).get("status") == "active")
    nodes_inactive = sum(1 for n in nodes if n.get("data", {}).get("status") == "inactive")

    # Source stats
    total_sources = sum(len(n.get("data", {}).get("sources", [])) for n in nodes)
    nodes_multi_source = sum(1 for n in nodes if len(n.get("data", {}).get("sources", [])) >= 2)
    source_domains = {}
    for n in nodes:
        for s in n.get("data", {}).get("sources", []):
            url = s.get("url", "")
            if "/" in url and len(url.split("/")) > 2:
                domain = url.split("/")[2].replace("www.", "").replace("en.", "")
                source_domains[domain] = source_domains.get(domain, 0) + 1
    top_domains = sorted(source_domains.items(), key=lambda x: -x[1])[:10]

    # Edge stats
    edge_types = {}
    for e in edges:
        t = e.get("type", "unknown")
        edge_types[t] = edge_types.get(t, 0) + 1

    # Lane stats
    lane_counts = {}
    for n in nodes:
        lid = n.get("data", {}).get("layout", {}).get("lane", "unplaced")
        lane_counts[lid] = lane_counts.get(lid, 0) + 1

    graph = {
        "nodes": slim_nodes,
        "edges": edges,
        "meta": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "lanes": [{"id": l["id"], "label": l["label"], "order": l.get("order"), "group": l.get("group", "Other")} for l in lanes_list],
            "visibility": {
                "exported": {
                    "nodes": len(nodes),
                    "edges": len(edges),
                    "nodes_with_founded_year": nodes_with_year,
                    "nodes_exact_circa": nodes_exact_circa,
                    "nodes_decade_estimated": nodes_decade,
                    "nodes_estimate_only": nodes_estimate,
                    "nodes_with_colors": nodes_with_colors,
                    "nodes_with_description": nodes_with_desc,
                    "nodes_with_aliases": nodes_with_aliases,
                    "nodes_with_metro": nodes_with_metro,
                    "nodes_active": nodes_active,
                    "nodes_inactive": nodes_inactive,
                    "nodes_multi_source": nodes_multi_source,
                    "total_sources": total_sources,
                    "linked_events": 0,
                    "dated_events": 0,
                },
                "excluded": {
                    "mention_only_entities": 0,
                    "relationships_off_graph": 0,
                    "relationships_geo_filtered": 0,
                    "events_unlinked": 0,
                    "events_undated_or_noise": 0,
                },
                "registry": {"claims": 0},
                "edge_types": edge_types,
                "top_source_domains": top_domains,
                "lane_counts": lane_counts,
            },
        },
        "exported_at": datetime.now(UTC).isoformat(),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(graph, ensure_ascii=False) + "\n", encoding="utf-8")

    details_path = out_path.parent / "details.json"
    details_path.write_text(json.dumps(details, ensure_ascii=False) + "\n", encoding="utf-8")

    # Changelog: accumulate build history
    changelog_path = out_path.parent / "changelog.json"
    history = []
    if changelog_path.exists():
        raw = json.loads(changelog_path.read_text(encoding="utf-8"))
        history = raw if isinstance(raw, list) else [raw] if raw.get("nodes") else []
    prev = history[-1] if history else {}
    entry = {
        "nodes": len(nodes),
        "edges": len(edges),
        "sources": total_sources,
        "delta_nodes": len(nodes) - prev.get("nodes", 0) if prev else 0,
        "delta_edges": len(edges) - prev.get("edges", 0) if prev else 0,
        "delta_sources": total_sources - prev.get("sources", 0) if prev else 0,
        "built_at": datetime.now(UTC).isoformat(),
    }
    # Only add if stats changed
    if not prev or entry["nodes"] != prev.get("nodes") or entry["edges"] != prev.get("edges") or entry["sources"] != prev.get("sources"):
        history.append(entry)
    changelog_path.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")

    print(f"Built graph.json: {len(nodes)} nodes, {len(edges)} edges → {out_path}")
    print(f"Built details.json: {len(details['nodes'])} profiles → {details_path}")
    if prev:
        print(f"Δ nodes: {entry['delta_nodes']:+d}, Δ edges: {entry['delta_edges']:+d}, Δ sources: {entry['delta_sources']:+d}")


if __name__ == "__main__":
    out = None
    if "--out" in sys.argv:
        idx = sys.argv.index("--out")
        out = sys.argv[idx + 1]
    build_graph(out)
