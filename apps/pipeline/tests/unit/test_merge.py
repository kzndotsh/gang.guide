import pytest
"""Tests for apps/pipeline/merge.py"""

from apps.pipeline.merge import merge_runs


class TestMergeRuns:
    def test_single_run_passthrough(self):
        run = {"subject_org": "Test", "founded_year": 1990, "edges": [], "colors": ["blue"]}
        result = merge_runs([run])
        assert result == run

    def test_year_majority_vote(self):
        runs = [
            {"subject_org": "X", "founded_year": 1958, "edges": [], "colors": []},
            {"subject_org": "X", "founded_year": 1958, "edges": [], "colors": []},
            {"subject_org": "X", "founded_year": 1960, "edges": [], "colors": []},
        ]
        result = merge_runs(runs)
        assert result["founded_year"] == 1958

    def test_year_no_consensus(self):
        runs = [
            {"subject_org": "X", "founded_year": 1958, "edges": [], "colors": []},
            {"subject_org": "X", "founded_year": 1960, "edges": [], "colors": []},
            {"subject_org": "X", "founded_year": 1970, "edges": [], "colors": []},
        ]
        result = merge_runs(runs)
        assert result["founded_year"] is None

    def test_colors_consensus(self):
        runs = [
            {"subject_org": "X", "colors": ["blue", "black"], "edges": []},
            {"subject_org": "X", "colors": ["blue", "red"], "edges": []},
            {"subject_org": "X", "colors": ["blue"], "edges": []},
        ]
        result = merge_runs(runs)
        assert "blue" in result["colors"]
        assert "red" not in result["colors"]

    def test_edges_consensus(self):
        edge_a = {"target": "Bloods", "type": "rivalry", "evidence": "They fought"}
        edge_b = {"target": "Bloods", "type": "rivalry", "evidence": "At war since 1972"}
        edge_c = {"target": "Unicorns", "type": "alliance", "evidence": "Made up"}
        runs = [
            {"subject_org": "X", "edges": [edge_a, edge_c], "colors": []},
            {"subject_org": "X", "edges": [edge_b], "colors": []},
            {"subject_org": "X", "edges": [edge_a], "colors": []},
        ]
        result = merge_runs(runs)
        assert len(result["edges"]) == 1
        assert result["edges"][0]["target"] == "Bloods"

    def test_edges_keeps_longest_evidence(self):
        short = {"target": "X", "type": "rivalry", "evidence": "War"}
        long = {"target": "X", "type": "rivalry", "evidence": "They went to war in 1986 over territory on 18th Street"}
        runs = [
            {"subject_org": "A", "edges": [short], "colors": []},
            {"subject_org": "A", "edges": [long], "colors": []},
        ]
        result = merge_runs(runs)
        assert "1986" in result["edges"][0]["evidence"]

    def test_description_picks_longest(self):
        runs = [
            {"subject_org": "X", "description": "Short.", "edges": [], "colors": []},
            {"subject_org": "X", "description": "A much longer description with more detail.", "edges": [], "colors": []},
            {"subject_org": "X", "description": "Medium length desc.", "edges": [], "colors": []},
        ]
        result = merge_runs(runs)
        assert "much longer" in result["description"]

    def test_empty_runs(self):
        result = merge_runs([])
        assert result == {}


class TestMergeRegression:
    """Regression test against golden fixture — catches unintended merge logic changes."""

    def test_merge_matches_golden(self, sample_runs, golden_consensus):
        if golden_consensus is None:
            pytest.skip("Golden fixture not generated yet")
        result = merge_runs(sample_runs)
        assert result["founded_year"] == golden_consensus["founded_year"]
        assert set(result["colors"]) == set(golden_consensus["colors"])
        assert len(result["edges"]) == len(golden_consensus["edges"])
        result_targets = {(e["target"].lower(), e["type"]) for e in result["edges"]}
        golden_targets = {(e["target"].lower(), e["type"]) for e in golden_consensus["edges"]}
        assert result_targets == golden_targets


class TestMergeEdgeCases:
    def test_symbols_consensus(self):
        runs = [
            {"subject_org": "X", "symbols": ["star", "pitchfork"], "edges": [], "colors": []},
            {"subject_org": "X", "symbols": ["star", "crown"], "edges": [], "colors": []},
            {"subject_org": "X", "symbols": ["star"], "edges": [], "colors": []},
        ]
        result = merge_runs(runs)
        assert "star" in result["symbols"]
        assert "crown" not in result["symbols"]

    def test_membership_median(self):
        runs = [
            {"subject_org": "X", "membership_estimate": 1000, "edges": [], "colors": []},
            {"subject_org": "X", "membership_estimate": 5000, "edges": [], "colors": []},
            {"subject_org": "X", "membership_estimate": 2000, "edges": [], "colors": []},
        ]
        result = merge_runs(runs)
        assert result["membership_estimate"] == 2000

    def test_orgs_mentioned_consensus(self):
        runs = [
            {"subject_org": "X", "orgs_mentioned": ["A", "B", "C"], "edges": [], "colors": []},
            {"subject_org": "X", "orgs_mentioned": ["A", "B"], "edges": [], "colors": []},
            {"subject_org": "X", "orgs_mentioned": ["A", "D"], "edges": [], "colors": []},
        ]
        result = merge_runs(runs)
        assert "A" in result["orgs_mentioned"]
        assert "B" in result["orgs_mentioned"]
        assert "D" not in result["orgs_mentioned"]

    def test_edge_type_matters(self):
        """Same target but different type = different edges."""
        runs = [
            {"subject_org": "X", "edges": [
                {"target": "Y", "type": "alliance", "evidence": "allies"},
                {"target": "Y", "type": "rivalry", "evidence": "rivals"},
            ], "colors": []},
            {"subject_org": "X", "edges": [
                {"target": "Y", "type": "alliance", "evidence": "friends"},
            ], "colors": []},
        ]
        result = merge_runs(runs)
        # Alliance appears in 2/2 runs, rivalry only in 1/2
        types = [e["type"] for e in result["edges"]]
        assert "alliance" in types
        assert "rivalry" not in types


class TestMergeAdversarial:
    """Test merge with broken/adversarial extraction outputs."""

    def test_missing_fields(self):
        """Runs with missing optional fields shouldn't crash."""
        runs = [
            {"subject_org": "X"},
            {"subject_org": "X", "edges": []},
            {},
        ]
        result = merge_runs(runs)
        assert isinstance(result, dict)

    def test_null_values_everywhere(self):
        runs = [
            {"subject_org": None, "founded_year": None, "colors": None, "edges": None, "description": None},
            {"subject_org": None, "founded_year": None, "colors": None, "edges": None, "description": None},
        ]
        result = merge_runs(runs)
        assert result.get("founded_year") is None
        assert result.get("edges") == [] or result.get("edges") is not None

    def test_extremely_many_edges(self):
        """1000 edges per run shouldn't hang."""
        edges = [{"target": f"Org{i}", "type": "alliance", "evidence": f"e{i}"} for i in range(1000)]
        runs = [
            {"subject_org": "X", "edges": edges, "colors": []},
            {"subject_org": "X", "edges": edges, "colors": []},
        ]
        result = merge_runs(runs)
        assert len(result["edges"]) == 1000  # all in consensus (2/2)

    def test_edges_with_empty_target(self):
        """Empty target shouldn't crash consensus logic."""
        runs = [
            {"subject_org": "X", "edges": [{"target": "", "type": "rivalry", "evidence": "x"}], "colors": []},
            {"subject_org": "X", "edges": [{"target": "", "type": "rivalry", "evidence": "y"}], "colors": []},
        ]
        result = merge_runs(runs)
        # Empty target edge exists in 2/2 runs — it passes consensus
        assert len(result["edges"]) == 1

    def test_unicode_in_edge_targets(self):
        runs = [
            {"subject_org": "X", "edges": [{"target": "Sureños", "type": "rivalry", "evidence": "x"}], "colors": []},
            {"subject_org": "X", "edges": [{"target": "Sureños", "type": "rivalry", "evidence": "y"}], "colors": []},
        ]
        result = merge_runs(runs)
        assert len(result["edges"]) == 1

    def test_case_sensitivity_in_targets(self):
        """'BLOODS' and 'bloods' should merge as same edge."""
        runs = [
            {"subject_org": "X", "edges": [{"target": "BLOODS", "type": "rivalry", "evidence": "x"}], "colors": []},
            {"subject_org": "X", "edges": [{"target": "bloods", "type": "rivalry", "evidence": "y"}], "colors": []},
        ]
        result = merge_runs(runs)
        assert len(result["edges"]) == 1

    def test_two_runs_not_three(self):
        """Only 2 runs (e.g., one failed) — 2/2 agreement = consensus."""
        runs = [
            {"subject_org": "X", "edges": [{"target": "A", "type": "r", "evidence": "x"}], "colors": ["blue"]},
            {"subject_org": "X", "edges": [{"target": "A", "type": "r", "evidence": "y"}], "colors": ["blue"]},
        ]
        result = merge_runs(runs)
        assert len(result["edges"]) == 1
        assert "blue" in result["colors"]
