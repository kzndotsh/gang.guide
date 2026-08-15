"""Unit tests for apps/pipeline/ignore.py"""

import textwrap
from pathlib import Path

import pytest

from apps.pipeline.ignore import IgnoreRules, load_ignore_rules


# ── helpers ───────────────────────────────────────────────────────────────────


def write_ignore(tmp_path: Path, content: str) -> Path:
    """Write a .gangguideignore file and return its path."""
    p = tmp_path / ".gangguideignore"
    p.write_text(textwrap.dedent(content))
    return p


# ── load_ignore_rules ─────────────────────────────────────────────────────────


def test_missing_file_returns_empty_rules(tmp_path):
    rules = load_ignore_rules(tmp_path / "nonexistent")
    assert rules.enrich_skip == set()
    assert rules.enrich_skip_fields == {}
    assert rules.apply_skip_orgs == set()
    assert rules.apply_skip_edges == []
    assert rules.verify_skip_edges == []
    assert rules.lint_suppress == {}


def test_empty_file_returns_empty_rules(tmp_path):
    p = write_ignore(tmp_path, "")
    rules = load_ignore_rules(p)
    assert rules.enrich_skip == set()


def test_comments_and_blank_lines_ignored(tmp_path):
    p = write_ignore(
        tmp_path,
        """
        # this is a comment
        
        # another comment
        """,
    )
    rules = load_ignore_rules(p)
    assert rules.enrich_skip == set()


def test_inline_comments_stripped(tmp_path):
    p = write_ignore(
        tmp_path,
        """
        [enrich:skip]
        org:bloods  # no membership data
        """,
    )
    rules = load_ignore_rules(p)
    assert "org:bloods" in rules.enrich_skip


# ── enrich:skip ───────────────────────────────────────────────────────────────


def test_enrich_skip_single_org(tmp_path):
    p = write_ignore(
        tmp_path,
        """
        [enrich:skip]
        org:denver-lane-bloods
        """,
    )
    rules = load_ignore_rules(p)
    assert rules.should_skip_org("org:denver-lane-bloods")
    assert not rules.should_skip_org("org:crips")


def test_enrich_skip_multiple_orgs(tmp_path):
    p = write_ignore(
        tmp_path,
        """
        [enrich:skip]
        org:gangster-crips
        org:main-street-mafia-crips
        org:simon-city-royals
        """,
    )
    rules = load_ignore_rules(p)
    assert rules.should_skip_org("org:gangster-crips")
    assert rules.should_skip_org("org:main-street-mafia-crips")
    assert rules.should_skip_org("org:simon-city-royals")
    assert not rules.should_skip_org("org:crips")


# ── enrich:skip-field ─────────────────────────────────────────────────────────


def test_enrich_skip_field(tmp_path):
    p = write_ignore(
        tmp_path,
        """
        [enrich:skip-field]
        org:spanish-cobras  no_membership
        """,
    )
    rules = load_ignore_rules(p)
    assert rules.should_skip_field("org:spanish-cobras", "no_membership")
    assert not rules.should_skip_field("org:spanish-cobras", "no_symbols")
    assert not rules.should_skip_field("org:crips", "no_membership")


def test_filter_issues_removes_suppressed(tmp_path):
    p = write_ignore(
        tmp_path,
        """
        [enrich:skip-field]
        org:some-org  no_membership
        org:some-org  imprecise_year
        """,
    )
    rules = load_ignore_rules(p)
    issues = ["no_membership", "imprecise_year", "no_symbols"]
    filtered = rules.filter_issues("org:some-org", issues)
    assert filtered == ["no_symbols"]


def test_filter_issues_unaffected_org(tmp_path):
    p = write_ignore(
        tmp_path,
        """
        [enrich:skip-field]
        org:some-org  no_membership
        """,
    )
    rules = load_ignore_rules(p)
    issues = ["no_membership", "no_symbols"]
    assert rules.filter_issues("org:other-org", issues) == issues


# ── apply:skip-org ────────────────────────────────────────────────────────────


def test_apply_skip_org(tmp_path):
    p = write_ignore(
        tmp_path,
        """
        [apply:skip-org]
        org:protected-org
        """,
    )
    rules = load_ignore_rules(p)
    assert rules.should_skip_apply_org("org:protected-org")
    assert not rules.should_skip_apply_org("org:other-org")


# ── apply:skip-edge ───────────────────────────────────────────────────────────


def test_apply_skip_edge_exact(tmp_path):
    p = write_ignore(
        tmp_path,
        """
        [apply:skip-edge]
        org:crips  org:bloods  alliance
        """,
    )
    rules = load_ignore_rules(p)
    assert rules.should_skip_apply_edge("org:crips", "org:bloods", "alliance")
    assert not rules.should_skip_apply_edge("org:crips", "org:bloods", "rivalry")
    assert not rules.should_skip_apply_edge("org:bloods", "org:crips", "alliance")


def test_apply_skip_edge_wildcard_target(tmp_path):
    p = write_ignore(
        tmp_path,
        """
        [apply:skip-edge]
        org:crips  *  nation
        """,
    )
    rules = load_ignore_rules(p)
    assert rules.should_skip_apply_edge("org:crips", "org:anyone", "nation")
    assert not rules.should_skip_apply_edge("org:bloods", "org:anyone", "nation")


def test_apply_skip_edge_wildcard_source(tmp_path):
    p = write_ignore(
        tmp_path,
        """
        [apply:skip-edge]
        *  org:bloods  rivalry
        """,
    )
    rules = load_ignore_rules(p)
    assert rules.should_skip_apply_edge("org:anyone", "org:bloods", "rivalry")
    assert not rules.should_skip_apply_edge("org:anyone", "org:crips", "rivalry")


def test_apply_skip_edge_all_wildcards(tmp_path):
    p = write_ignore(
        tmp_path,
        """
        [apply:skip-edge]
        *  *  spin_off
        """,
    )
    rules = load_ignore_rules(p)
    assert rules.should_skip_apply_edge("org:a", "org:b", "spin_off")
    assert not rules.should_skip_apply_edge("org:a", "org:b", "alliance")


# ── verify:skip ───────────────────────────────────────────────────────────────


def test_verify_skip_edge(tmp_path):
    p = write_ignore(
        tmp_path,
        """
        [verify:skip]
        org:crips  *  nation
        """,
    )
    rules = load_ignore_rules(p)
    assert rules.should_skip_verify_edge("org:crips", "org:rollin-60s", "nation")
    assert not rules.should_skip_verify_edge("org:bloods", "org:rollin-60s", "nation")


# ── lint:suppress ─────────────────────────────────────────────────────────────


def test_lint_suppress_org_specific(tmp_path):
    p = write_ignore(
        tmp_path,
        """
        [lint:suppress]
        org:bloods  cross_metro
        """,
    )
    rules = load_ignore_rules(p)
    assert rules.is_lint_suppressed("org:bloods", "cross_metro")
    assert not rules.is_lint_suppressed("org:crips", "cross_metro")
    assert not rules.is_lint_suppressed("org:bloods", "fuzzy_dupe")


def test_lint_suppress_global(tmp_path):
    p = write_ignore(
        tmp_path,
        """
        [lint:suppress]
        *  cross_metro
        """,
    )
    rules = load_ignore_rules(p)
    assert rules.is_lint_suppressed("org:bloods", "cross_metro")
    assert rules.is_lint_suppressed("org:crips", "cross_metro")
    assert rules.is_lint_suppressed("org:anyone", "cross_metro")
    assert not rules.is_lint_suppressed("org:anyone", "fuzzy_dupe")


# ── multi-section ─────────────────────────────────────────────────────────────


def test_multiple_sections_parsed_correctly(tmp_path):
    p = write_ignore(
        tmp_path,
        """
        [enrich:skip]
        org:org-a

        [enrich:skip-field]
        org:org-b  no_membership

        [apply:skip-org]
        org:org-c

        [apply:skip-edge]
        org:org-d  org:org-e  rivalry

        [verify:skip]
        org:org-f  *  nation

        [lint:suppress]
        org:org-g  cross_metro
        """,
    )
    rules = load_ignore_rules(p)
    assert rules.should_skip_org("org:org-a")
    assert rules.should_skip_field("org:org-b", "no_membership")
    assert rules.should_skip_apply_org("org:org-c")
    assert rules.should_skip_apply_edge("org:org-d", "org:org-e", "rivalry")
    assert rules.should_skip_verify_edge("org:org-f", "org:x", "nation")
    assert rules.is_lint_suppressed("org:org-g", "cross_metro")


# ── IgnoreRules direct construction ──────────────────────────────────────────


def test_ignore_rules_dataclass_defaults():
    rules = IgnoreRules()
    assert not rules.should_skip_org("org:anything")
    assert not rules.should_skip_apply_org("org:anything")
    assert not rules.should_skip_apply_edge("org:a", "org:b", "alliance")
    assert not rules.should_skip_verify_edge("org:a", "org:b", "nation")
    assert not rules.is_lint_suppressed("org:a", "cross_metro")
    assert rules.filter_issues("org:a", ["no_membership", "no_symbols"]) == ["no_membership", "no_symbols"]
