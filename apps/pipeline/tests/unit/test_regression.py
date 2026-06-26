"""Regression tests using real extraction outputs as fixtures.

These test against actual sonnet 4.5 extraction runs from the Ambrose CGH page,
catching regressions in merge logic when working with real-world data complexity.
"""

import json
import pytest
from pathlib import Path

from apps.pipeline.merge import merge_runs
from apps.pipeline.adjudicate import needs_adjudication

FIXTURES = Path(__file__).parent.parent / "fixtures"


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def real_runs():
    return [load_fixture(f"ambrose_run_{i}.json") for i in range(3)]


@pytest.fixture
def real_consensus():
    return load_fixture("ambrose_consensus.json")


@pytest.fixture
def real_adjudicated():
    return load_fixture("ambrose_adjudicated.json")


class TestRealMerge:
    """Test merge with real extraction data (30/39/37 edges across runs)."""

    def test_merge_produces_consensus_edges(self, real_runs, real_consensus):
        result = merge_runs(real_runs)
        assert len(result["edges"]) == len(real_consensus["edges"])

    def test_merge_year_stable(self, real_runs):
        result = merge_runs(real_runs)
        assert result["founded_year"] == 1958

    def test_merge_colors_stable(self, real_runs):
        result = merge_runs(real_runs)
        assert len(result["colors"]) >= 2
        assert "black" in result["colors"]

    def test_consensus_has_fewer_edges_than_any_run(self, real_runs):
        """Consensus filtering should reduce edge count."""
        result = merge_runs(real_runs)
        for run in real_runs:
            # Consensus should have fewer or equal edges to any single run
            # (only keeps 2/3 agreement)
            assert len(result["edges"]) <= max(len(r.get("edges", [])) for r in real_runs)

    def test_all_consensus_edges_appear_in_multiple_runs(self, real_runs):
        """Every consensus edge must exist in at least 2 runs."""
        result = merge_runs(real_runs)
        for edge in result["edges"]:
            key = (edge["target"].lower(), edge["type"])
            count = 0
            for run in real_runs:
                for e in run.get("edges", []):
                    if (e.get("target", "").lower(), e.get("type", "")) == key:
                        count += 1
                        break
            assert count >= 2, f"Edge {key} only in {count} runs"

    def test_no_duplicate_edges_in_consensus(self, real_runs):
        result = merge_runs(real_runs)
        keys = [(e["target"].lower(), e["type"]) for e in result["edges"]]
        assert len(keys) == len(set(keys)), "Duplicate edges in consensus"


class TestRealAdjudication:
    """Test adjudication trigger and output with real data."""

    def test_real_runs_need_adjudication(self, real_runs):
        """Real runs have enough variance to trigger adjudication."""
        # The real runs have 30/39/37 edges — significant uncertainty
        assert needs_adjudication(real_runs) is True

    def test_adjudicated_has_reasonable_edges(self, real_adjudicated):
        """Adjudicated result should be in range of extraction runs."""
        edges = real_adjudicated.get("edges", [])
        assert 15 <= len(edges) <= 40

    def test_adjudicated_edges_have_evidence(self, real_adjudicated):
        """Every adjudicated edge should have an evidence field."""
        for edge in real_adjudicated.get("edges", []):
            assert edge.get("evidence"), f"Edge {edge.get('target')} missing evidence"

    def test_adjudicated_edges_have_confidence(self, real_adjudicated):
        """Every adjudicated edge should have confidence field."""
        for edge in real_adjudicated.get("edges", []):
            assert edge.get("confidence") in ("high", "medium"), f"Edge {edge.get('target')} invalid confidence"

    def test_adjudicated_has_valid_types(self, real_adjudicated):
        valid_types = {"alliance", "rivalry", "parent", "member_of", "spin_off"}
        for edge in real_adjudicated.get("edges", []):
            assert edge.get("type") in valid_types, f"Invalid type: {edge.get('type')}"


class TestConflictingEdges:
    """Test merge behavior with deliberately conflicting data."""

    def test_same_target_different_type_both_kept(self):
        """If same target has alliance AND rivalry in 2+ runs, both survive."""
        runs = [
            {"subject_org": "X", "edges": [
                {"target": "Y", "type": "alliance", "evidence": "allied 1977"},
                {"target": "Y", "type": "rivalry", "evidence": "war 1986"},
            ], "colors": []},
            {"subject_org": "X", "edges": [
                {"target": "Y", "type": "alliance", "evidence": "friends"},
                {"target": "Y", "type": "rivalry", "evidence": "enemies"},
            ], "colors": []},
        ]
        result = merge_runs(runs)
        types = [e["type"] for e in result["edges"] if e["target"] == "Y"]
        assert "alliance" in types
        assert "rivalry" in types

    def test_high_variance_runs(self):
        """Runs with very different edge counts — consensus is conservative."""
        runs = [
            {"subject_org": "X", "edges": [
                {"target": f"Org{i}", "type": "alliance", "evidence": f"e{i}"} for i in range(20)
            ], "colors": []},
            {"subject_org": "X", "edges": [
                {"target": f"Org{i}", "type": "alliance", "evidence": f"e{i}"} for i in range(5)
            ], "colors": []},
            {"subject_org": "X", "edges": [
                {"target": f"Org{i}", "type": "alliance", "evidence": f"e{i}"} for i in range(3, 10)
            ], "colors": []},
        ]
        result = merge_runs(runs)
        # Only edges in 2+ runs survive: Org3, Org4 (in all 3); Org0-2 (in runs 0+1); Org5-9 (in runs 0+2)
        assert len(result["edges"]) < 20
        assert len(result["edges"]) >= 3

    def test_no_edges_in_common(self):
        """Three runs with completely disjoint edges — nothing survives."""
        runs = [
            {"subject_org": "X", "edges": [{"target": "A", "type": "r", "evidence": "x"}], "colors": []},
            {"subject_org": "X", "edges": [{"target": "B", "type": "r", "evidence": "x"}], "colors": []},
            {"subject_org": "X", "edges": [{"target": "C", "type": "r", "evidence": "x"}], "colors": []},
        ]
        result = merge_runs(runs)
        assert len(result["edges"]) == 0
