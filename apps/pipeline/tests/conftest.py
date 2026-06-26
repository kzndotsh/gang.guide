"""Shared fixtures for pipeline tests."""

import json
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def org_index():
    """Mock org name → ID index for resolve tests."""
    return {
        "latin kings": "org:latin-kings",
        "almighty latin king nation": "org:latin-kings",
        "crips": "org:crips",
        "bloods": "org:bloods",
        "ambrose": "org:ambrose",
        "almighty ambrose": "org:ambrose",
        "folk nation": "org:folk-nation",
        "satan disciples": "org:satan-disciples",
        "gangster disciples": "org:gangster-disciples",
        "vice lords": "org:almighty-vice-lord-nation",
        "simon city royals": "org:simon-city-royals",
        "rampants": "org:rampants",
        "latin counts": "org:almighty-insane-latin-counts",
    }


@pytest.fixture
def sample_extraction():
    """A realistic single extraction run result."""
    return {
        "subject_org": "Ambrose",
        "founded_year": 1958,
        "colors": ["black", "light blue"],
        "symbols": ["spear", "knight's helmet"],
        "membership_estimate": None,
        "description": "Ambrose is a Latino street gang founded in 1958 on Chicago's Near West Side.",
        "edges": [
            {"target": "Folk Nation", "type": "member_of", "evidence": "Joined Folk Nation circa 1979", "period": "1979-2000"},
            {"target": "Rampants", "type": "alliance", "evidence": "Ambrose had no war with Rampants and were close allies", "period": None},
            {"target": "Latin Counts", "type": "rivalry", "evidence": "Reno of the Latin Counts was shot by Ambrose", "period": None},
            {"target": "Satan Disciples", "type": "rivalry", "evidence": "In 1986 Ambrose was at war with Satan Disciples", "period": "1986-present"},
        ],
        "orgs_mentioned": ["Folk Nation", "Rampants", "Latin Counts", "Satan Disciples", "Taylor Street Dukes"],
    }


@pytest.fixture
def sample_runs(sample_extraction):
    """Three extraction runs with slight variation (simulating multi-temp)."""
    run0 = sample_extraction.copy()
    run1 = {
        **sample_extraction,
        "colors": ["black", "blue"],
        "edges": sample_extraction["edges"] + [
            {"target": "Gangster Disciples", "type": "alliance", "evidence": "Connected through Folk Nation", "period": None},
        ],
    }
    run2 = {
        **sample_extraction,
        "founded_year": 1958,
        "edges": sample_extraction["edges"][:3],  # missing one edge
    }
    return [run0, run1, run2]


@pytest.fixture
def sample_org():
    """A sample org JSON file content."""
    return {
        "id": "org:ambrose",
        "name": "Almighty Ambrose",
        "aliases": ["Ambrose"],
        "type": "street_gang",
        "lane": "chicago-sets",
        "metro": "Chicago",
        "founded_year": 1960,
        "founded_year_precision": "decade",
        "description": "Latino street gang from Chicago.",
        "colors": [],
        "nation_affiliation": "org:folk-nation",
        "status": "active",
        "sources": [{"url": "https://chicagoganghistory.com/gang/almighty-ambrose/", "title": "Ambrose — CGH"}],
    }


@pytest.fixture
def golden_consensus():
    """Expected output from merging sample_runs — used for regression testing."""
    path = FIXTURES_DIR / "golden_consensus.json"
    if path.exists():
        return json.loads(path.read_text())
    return None
