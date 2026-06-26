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
