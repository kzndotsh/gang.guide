"""Tests for apps/pipeline/adjudicate.py"""

from apps.pipeline.adjudicate import needs_adjudication


class TestNeedsAdjudication:
    def test_agreeing_runs_no_adjudication(self):
        runs = [
            {"founded_year": 1958, "colors": ["blue"], "edges": [{"target": "X", "type": "rivalry"}]},
            {"founded_year": 1958, "colors": ["blue"], "edges": [{"target": "X", "type": "rivalry"}]},
            {"founded_year": 1958, "colors": ["blue"], "edges": [{"target": "X", "type": "rivalry"}]},
        ]
        assert needs_adjudication(runs) is False

    def test_year_disagreement(self):
        runs = [
            {"founded_year": 1958, "colors": [], "edges": []},
            {"founded_year": 1960, "colors": [], "edges": []},
            {"founded_year": 1958, "colors": [], "edges": []},
        ]
        assert needs_adjudication(runs) is True

    def test_color_disagreement(self):
        runs = [
            {"founded_year": 1958, "colors": ["blue", "black"], "edges": []},
            {"founded_year": 1958, "colors": ["red", "black"], "edges": []},
        ]
        assert needs_adjudication(runs) is True

    def test_single_run_no_adjudication(self):
        assert needs_adjudication([{"edges": []}]) is False

    def test_many_uncertain_edges(self):
        runs = [
            {"founded_year": 1958, "colors": [], "edges": [{"target": "A", "type": "r"}, {"target": "B", "type": "r"}, {"target": "C", "type": "r"}]},
            {"founded_year": 1958, "colors": [], "edges": [{"target": "D", "type": "r"}, {"target": "E", "type": "r"}, {"target": "F", "type": "r"}]},
            {"founded_year": 1958, "colors": [], "edges": []},
        ]
        assert needs_adjudication(runs) is True


class TestNeedsAdjudicationEdgeCases:
    def test_empty_runs(self):
        assert needs_adjudication([]) is False

    def test_all_none_years(self):
        runs = [
            {"founded_year": None, "colors": [], "edges": []},
            {"founded_year": None, "colors": [], "edges": []},
        ]
        assert needs_adjudication(runs) is False

    def test_few_uncertain_edges_no_trigger(self):
        """Less than 3 uncertain edges should not trigger adjudication."""
        runs = [
            {"founded_year": 1958, "colors": [], "edges": [
                {"target": "A", "type": "r"}, {"target": "B", "type": "r"},
                {"target": "C", "type": "r"}, {"target": "D", "type": "r"},
            ]},
            {"founded_year": 1958, "colors": [], "edges": [
                {"target": "A", "type": "r"}, {"target": "B", "type": "r"},
                {"target": "C", "type": "r"}, {"target": "E", "type": "r"},
            ]},
            {"founded_year": 1958, "colors": [], "edges": [
                {"target": "A", "type": "r"}, {"target": "B", "type": "r"},
                {"target": "C", "type": "r"}, {"target": "F", "type": "r"},
            ]},
        ]
        # D, E, F each in 1 run = 3 uncertain out of 12 total = 25% < 30%
        assert needs_adjudication(runs) is False

    def test_identical_colors_no_trigger(self):
        runs = [
            {"founded_year": 1958, "colors": ["blue", "black"], "edges": []},
            {"founded_year": 1958, "colors": ["blue", "black"], "edges": []},
        ]
        assert needs_adjudication(runs) is False


class TestNeedsAdjudicationAdversarial:
    def test_runs_with_no_edges_key(self):
        """Missing edges key shouldn't crash."""
        runs = [
            {"founded_year": 1958, "colors": []},
            {"founded_year": 1958, "colors": []},
        ]
        assert needs_adjudication(runs) is False

    def test_very_many_runs(self):
        """More than 3 runs (future-proofing)."""
        runs = [{"founded_year": 1958, "colors": ["blue"], "edges": [{"target": "X", "type": "r"}]}] * 10
        assert needs_adjudication(runs) is False

    def test_mixed_empty_and_full(self):
        """One run has 50 edges, others have 0."""
        runs = [
            {"founded_year": 1958, "colors": [], "edges": [{"target": f"O{i}", "type": "r"} for i in range(50)]},
            {"founded_year": 1958, "colors": [], "edges": []},
            {"founded_year": 1958, "colors": [], "edges": []},
        ]
        # 50 uncertain edges out of 50 total = 100% > 30%, and >= 3
        assert needs_adjudication(runs) is True
