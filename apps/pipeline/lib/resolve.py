"""Entity resolution: extracted names → org IDs.

Fuzzy matches extracted gang names against existing org names and aliases.
Builds and caches a resolution table at data/name_map.json.
"""

import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
NAME_MAP_PATH = DATA_DIR / "name_map.json"


def normalize(name: str) -> str:
    """Normalize a name for fuzzy matching."""
    s = name.lower().strip()
    s = re.sub(r'[^a-z0-9\s]', '', s)
    s = re.sub(r'\s+', ' ', s)
    return s


def build_index() -> dict[str, str]:
    """Build name → org_id index from all org files."""
    index: dict[str, str] = {}
    orgs_dir = DATA_DIR / "orgs"
    for f in orgs_dir.iterdir():
        if f.suffix != ".json":
            continue
        org = json.loads(f.read_text(encoding="utf-8"))
        org_id = org.get("id", "")
        # Index primary name
        index[normalize(org.get("name", ""))] = org_id
        # Index aliases
        for alias in (org.get("aliases") or []):
            index[normalize(alias)] = org_id
    return index


def resolve(name: str, index: dict[str, str] | None = None) -> str | None:
    """Resolve an extracted name to an org ID. Returns None if no match."""
    if index is None:
        index = build_index()

    norm = normalize(name)
    if not norm:
        return None

    # Exact match
    if norm in index:
        return index[norm]

    # Try with common suffixes removed
    for suffix in (' gang', ' crips', ' bloods', ' piru', ' 13', ' nation', ' mc'):
        if norm.endswith(suffix):
            stripped = norm[:-len(suffix)]
            if stripped and stripped in index:
                return index[stripped]

    # Try containment (require >60% overlap to avoid false matches)
    if len(norm) > 5:
        best_match = None
        best_ratio = 0.0
        for key, org_id in index.items():
            if len(key) < 4:
                continue
            if norm in key:
                ratio = len(norm) / len(key)
                if ratio > 0.6 and ratio > best_ratio:
                    best_match = org_id
                    best_ratio = ratio
            elif key in norm:
                ratio = len(key) / len(norm)
                if ratio > 0.6 and ratio > best_ratio:
                    best_match = org_id
                    best_ratio = ratio
        return best_match

    return None


def load_name_map() -> dict[str, str]:
    """Load cached name → org_id map."""
    if NAME_MAP_PATH.exists():
        return json.loads(NAME_MAP_PATH.read_text(encoding="utf-8"))
    return {}


def save_name_map(name_map: dict[str, str]):
    """Save name → org_id map."""
    NAME_MAP_PATH.write_text(json.dumps(name_map, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
