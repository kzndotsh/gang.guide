"""ignore.py — parser for .gangguideignore rule files.

Reads .gangguideignore (or any path) and exposes structured rule sets
that enrich.py, apply.py, verify.py, and lint.py can query.

File format
-----------
Lines starting with '#' are comments. Blank lines are ignored.

Sections:
  [enrich:skip]       org IDs to skip entirely in enrich.py
  [enrich:skip-field] org-id  field   suppress one issue for one org in enrich.py
  [apply:skip-org]    org IDs apply.py should never write to
  [apply:skip-edge]   source  target  type  edge patterns apply.py should never add
                      (use '*' as wildcard for any single field)
  [verify:skip]       source  target  type  edge patterns verify.py should skip
                      (use '*' as wildcard for any single field)
  [lint:suppress]     org-id  check   suppress one lint check for one org
                      (use '*' as org-id to suppress globally)

Usage
-----
    from apps.pipeline.ignore import load_ignore_rules, IgnoreRules

    rules = load_ignore_rules()                   # loads ROOT/.gangguideignore
    rules = load_ignore_rules("/path/to/file")    # loads explicit path

    # enrich.py
    rules.should_skip_org("org:denver-lane-bloods")
    rules.filter_issues("org:spanish-cobras", ["no_membership", "no_symbols"])

    # apply.py
    rules.should_skip_apply_org("org:some-org")
    rules.should_skip_apply_edge("org:crips", "org:bloods", "alliance")

    # verify.py
    rules.should_skip_verify_edge("org:crips", "*", "nation")

    # lint.py
    rules.is_lint_suppressed("org:bloods", "cross_metro")
    rules.is_lint_suppressed("*", "cross_metro")   # global suppression
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_IGNORE_FILE = ROOT / ".gangguideignore"


@dataclass
class IgnoreRules:
    """Parsed ignore rules from a .gangguideignore file."""

    # [enrich:skip] — org IDs to skip entirely
    enrich_skip: set[str] = field(default_factory=set)

    # [enrich:skip-field] — {org_id: set of issue names}
    enrich_skip_fields: dict[str, set[str]] = field(default_factory=dict)

    # [apply:skip-org] — org IDs apply.py must not write to
    apply_skip_orgs: set[str] = field(default_factory=set)

    # [apply:skip-edge] — list of (source, target, type) patterns; '*' = wildcard
    apply_skip_edges: list[tuple[str, str, str]] = field(default_factory=list)

    # [verify:skip] — list of (source, target, type) patterns; '*' = wildcard
    verify_skip_edges: list[tuple[str, str, str]] = field(default_factory=list)

    # [lint:suppress] — {org_id: set of check names}; '*' = global
    lint_suppress: dict[str, set[str]] = field(default_factory=dict)

    # ── enrich ────────────────────────────────────────────────────────────────

    def should_skip_org(self, org_id: str) -> bool:
        """Return True if this org should be skipped entirely in enrich.py."""
        return org_id in self.enrich_skip

    def should_skip_field(self, org_id: str, field_name: str) -> bool:
        """Return True if this specific field/issue should be skipped for this org."""
        return field_name in self.enrich_skip_fields.get(org_id, set())

    def filter_issues(self, org_id: str, issues: list[str]) -> list[str]:
        """Remove any issues suppressed for this org via [enrich:skip-field]."""
        suppressed = self.enrich_skip_fields.get(org_id, set())
        return [i for i in issues if i not in suppressed]

    # ── apply ─────────────────────────────────────────────────────────────────

    def should_skip_apply_org(self, org_id: str) -> bool:
        """Return True if apply.py should not write to this org."""
        return org_id in self.apply_skip_orgs

    def should_skip_apply_edge(self, source: str, target: str, edge_type: str) -> bool:
        """Return True if apply.py should not add this edge."""
        return self._matches_edge_patterns(self.apply_skip_edges, source, target, edge_type)

    # ── verify ────────────────────────────────────────────────────────────────

    def should_skip_verify_edge(self, source: str, target: str, edge_type: str) -> bool:
        """Return True if verify.py should skip this edge (treat as supported)."""
        return self._matches_edge_patterns(self.verify_skip_edges, source, target, edge_type)

    # ── lint ──────────────────────────────────────────────────────────────────

    def is_lint_suppressed(self, org_id: str, check_name: str) -> bool:
        """Return True if this lint check is suppressed for this org (or globally)."""
        if check_name in self.lint_suppress.get("*", set()):
            return True
        return check_name in self.lint_suppress.get(org_id, set())

    # ── internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _matches_edge_patterns(
        patterns: list[tuple[str, str, str]],
        source: str,
        target: str,
        edge_type: str,
    ) -> bool:
        for pat_src, pat_tgt, pat_type in patterns:
            if (
                (pat_src == "*" or pat_src == source)
                and (pat_tgt == "*" or pat_tgt == target)
                and (pat_type == "*" or pat_type == edge_type)
            ):
                return True
        return False


def load_ignore_rules(path: str | Path | None = None, validate: bool = False) -> IgnoreRules:
    """Parse a .gangguideignore file and return an IgnoreRules instance.

    If path is None, looks for .gangguideignore at the project root.
    If the file does not exist, returns empty rules (no-op).

    If validate=True, warns about any org IDs that don't exist in data/orgs/.
    """
    ignore_path = Path(path) if path else DEFAULT_IGNORE_FILE

    rules = IgnoreRules()

    if not ignore_path.exists():
        return rules

    current_section: str | None = None

    for lineno, raw_line in enumerate(ignore_path.read_text().splitlines(), start=1):
        # Strip inline comments and whitespace
        line = raw_line.split("#")[0].strip()
        if not line:
            continue

        # Section header
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].lower()
            continue

        if current_section is None:
            continue

        parts = line.split()

        if current_section == "enrich:skip":
            if len(parts) >= 1:
                rules.enrich_skip.add(parts[0])

        elif current_section == "enrich:skip-field":
            if len(parts) >= 2:
                rules.enrich_skip_fields.setdefault(parts[0], set()).add(parts[1])
            else:
                _warn(ignore_path, lineno, f"enrich:skip-field needs 'org-id field', got: {line!r}")

        elif current_section == "apply:skip-org":
            if len(parts) >= 1:
                rules.apply_skip_orgs.add(parts[0])

        elif current_section == "apply:skip-edge":
            if len(parts) >= 3:
                rules.apply_skip_edges.append((parts[0], parts[1], parts[2]))
            else:
                _warn(ignore_path, lineno, f"apply:skip-edge needs 'source target type', got: {line!r}")

        elif current_section == "verify:skip":
            if len(parts) >= 3:
                rules.verify_skip_edges.append((parts[0], parts[1], parts[2]))
            else:
                _warn(ignore_path, lineno, f"verify:skip needs 'source target type', got: {line!r}")

        elif current_section == "lint:suppress":
            if len(parts) >= 2:
                rules.lint_suppress.setdefault(parts[0], set()).add(parts[1])
            else:
                _warn(ignore_path, lineno, f"lint:suppress needs 'org-id check-name', got: {line!r}")

        else:
            _warn(ignore_path, lineno, f"unknown section [{current_section}], skipping: {line!r}")

    if validate:
        _validate_org_ids(ignore_path, rules)

    return rules


def _validate_org_ids(ignore_path: Path, rules: IgnoreRules) -> None:
    """Warn about org IDs in the ignore file that don't exist in data/orgs/."""
    import json

    orgs_dir = ROOT / "data" / "orgs"
    if not orgs_dir.exists():
        return

    real_ids: set[str] = set()
    for f in orgs_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            real_ids.add(data["id"])
        except (json.JSONDecodeError, KeyError):
            pass

    # Collect all org IDs referenced in the ignore file
    all_ids: set[str] = set()
    all_ids |= rules.enrich_skip
    all_ids |= rules.apply_skip_orgs
    all_ids |= {oid for oid in rules.enrich_skip_fields}
    all_ids |= {oid for oid in rules.lint_suppress if oid != "*"}
    for src, tgt, _ in rules.apply_skip_edges:
        if src != "*":
            all_ids.add(src)
        if tgt != "*":
            all_ids.add(tgt)
    for src, tgt, _ in rules.verify_skip_edges:
        if src != "*":
            all_ids.add(src)
        if tgt != "*":
            all_ids.add(tgt)

    missing = sorted(all_ids - real_ids)
    if missing:
        import sys

        print(f"\n  ⚠ {ignore_path.name}: {len(missing)} org ID(s) not found in data/orgs/:", file=sys.stderr)
        for oid in missing:
            print(f"    {oid}", file=sys.stderr)


def _warn(path: Path, lineno: int, msg: str) -> None:
    import sys

    print(f"  ⚠ {path.name}:{lineno}: {msg}", file=sys.stderr)


if __name__ == "__main__":
    # Run validation: python3 -m apps.pipeline.ignore
    rules = load_ignore_rules(validate=True)
    print(f"Loaded {len(rules.enrich_skip)} enrich:skip, {len(rules.lint_suppress)} lint:suppress orgs")
    print("Validation complete.")
