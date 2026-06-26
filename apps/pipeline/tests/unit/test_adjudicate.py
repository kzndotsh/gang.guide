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
