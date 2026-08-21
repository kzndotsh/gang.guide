"""Unit tests for apps.pipeline.lint checks."""

import pytest

from apps.pipeline import lint


@pytest.fixture(autouse=True)
def _reset_lint_buckets():
    lint.errors.clear()
    lint.warnings.clear()
    lint.info.clear()
    yield
    lint.errors.clear()
    lint.warnings.clear()
    lint.info.clear()


def _org(org_id: str, **overrides) -> dict:
    slug = org_id.removeprefix("org:")
    base = {
        "id": org_id,
        "name": slug.replace("-", " ").title(),
        "description": "X is a street gang based in Chicago with a documented founding and several known rivalries.",
        "sources": [{"url": "https://example.com", "title": "Example"}],
        "type": "street_gang",
        "lane": "chicago-folk",
        "founded_year": 1980,
        "_file": f"{slug}.json",
    }
    base.update(overrides)
    return base


def test_invalid_type_is_error():
    lint.check_orgs({"org:x": _org("org:x", type="terrorist_organization")}, {"chicago-folk"})
    assert any("invalid type" in m for m in lint.errors)


def test_dangling_nation_affiliation_is_error():
    lint.check_orgs({"org:x": _org("org:x", nation_affiliation="org:missing")}, {"chicago-folk"})
    assert any("nation_affiliation" in m and "does not match" in m for m in lint.errors)


def test_unknown_field_is_error():
    lint.check_orgs({"org:x": _org("org:x", extra_field=1)}, {"chicago-folk"})
    assert any("unknown field 'extra_field'" in m for m in lint.errors)


def test_description_over_800_is_error():
    lint.check_orgs({"org:x": _org("org:x", description="A" * 801)}, {"chicago-folk"})
    assert any("over 800 chars" in m for m in lint.errors)


def test_prison_lane_wrong_type_is_warning():
    lint.check_orgs({"org:x": _org("org:x", type="street_gang", lane="prison")}, {"prison"})
    assert any("in prison lane" in m for m in lint.warnings)


def test_edge_start_year_before_founded_is_info():
    orgs = {"org:a": _org("org:a", founded_year=1980), "org:b": _org("org:b")}
    edges = [{"source": "org:a", "target": "org:b", "type": "alliance", "start_year": 1960}]
    lint.check_edges(edges, orgs)
    assert any("start_year 1960 is well before org:a founded (1980)" in m for m in lint.info)


def test_alliance_source_must_be_alphabetically_smaller():
    orgs = {"org:a": _org("org:a"), "org:z": _org("org:z")}
    lint.check_edges([{"source": "org:z", "target": "org:a", "type": "alliance"}], orgs)
    assert any("alphabetically smaller" in m for m in lint.errors)


def test_invalid_edge_type_is_error():
    orgs = {"org:a": _org("org:a"), "org:b": _org("org:b")}
    lint.check_edges([{"source": "org:a", "target": "org:b", "type": "nation"}], orgs)
    assert any("invalid edge type" in m for m in lint.errors)


def test_citation_missing_evidence_is_warning():
    orgs = {"org:a": _org("org:a"), "org:b": _org("org:b")}
    edges = [
        {
            "source": "org:a",
            "target": "org:b",
            "type": "rivalry",
            "citations": [{"url": "https://example.com", "title": "Example", "evidence": ""}],
        }
    ]
    lint.check_edges(edges, orgs)
    assert any("citation missing evidence" in m for m in lint.warnings)


def test_alias_matches_other_org_name():
    orgs = {
        "org:a": _org("org:a", name="Vice Lords", aliases=["Almighty Vice Lord Nation"]),
        "org:b": _org("org:b", name="Almighty Vice Lord Nation", aliases=[]),
    }
    lint.check_alias_name_collisions(orgs)
    assert any("matches canonical name" in m for m in lint.warnings)


def test_folk_lane_missing_nation_affiliation():
    orgs = {"org:x": _org("org:x", lane="chicago-folk", type="street_gang", nation_affiliation=None)}
    lint.check_member_of_usage(orgs, [])
    assert any("Folk-lane org missing nation_affiliation" in m for m in lint.warnings)


def test_united_blood_nation_is_not_a_gang_nation_source():
    orgs = {
        "org:united-blood-nation": _org("org:united-blood-nation", name="United Blood Nation"),
        "org:bloods": _org("org:bloods", name="Bloods"),
    }
    edges = [{"source": "org:united-blood-nation", "target": "org:bloods", "type": "member_of"}]
    lint.check_member_of_usage(orgs, edges)
    assert not any("gang nation" in m for m in lint.warnings)
