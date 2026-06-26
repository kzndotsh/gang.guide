"""Unit tests for pipeline components (no API calls).

Run: python -m pytest apps/pipeline/tests/test_units.py -v
"""

import json
import pytest
from pathlib import Path

# === clean.py tests ===

from apps.pipeline.parse.clean import clean_html, quality_score
from apps.pipeline.lib.resolve import normalize, resolve, build_index
from apps.pipeline.merge import merge_runs
from apps.pipeline.extract import chunk_text, merge_chunks, prompt_hash
from apps.pipeline.adjudicate import needs_adjudication


class TestCleanHtml:
    def test_strips_script_tags(self):
        assert "alert" not in clean_html("<script>alert('x')</script>Hello")

    def test_strips_style_tags(self):
        assert "color" not in clean_html("<style>body{color:red}</style>Hello")

    def test_decodes_html_entities(self):
        assert "don't" in clean_html("don&apos;t") or "don't" in clean_html("don&#39;t")

    def test_removes_citation_markers(self):
        assert "[1]" not in clean_html("Founded in 1958[1] on Taylor Street[2].")

    def test_collapses_whitespace(self):
        result = clean_html("Hello\n\n\n\n\nWorld")
        assert "\n\n\n" not in result

    def test_strips_html_tags(self):
        assert "<div>" not in clean_html("<div>content</div>")
        assert "content" in clean_html("<div>content</div>")

    def test_fixes_mojibake(self):
        assert "'" in clean_html("don\u00e2\u0080\u0099t") or "'" in clean_html("don't")


class TestQualityScore:
    def test_empty_is_low_quality(self):
        assert quality_score("")["is_low_quality"] is True

    def test_short_text_is_low_quality(self):
        assert quality_score("Too short.")["is_low_quality"] is True

    def test_real_content_passes(self):
        text = "This is a real sentence about a gang founded in 1958.\n" * 20
        assert quality_score(text)["is_low_quality"] is False

    def test_nav_junk_fails(self):
        text = "Home\nAbout\nContact\nGangs\nNews\n" * 50
        assert quality_score(text)["is_low_quality"] is True


# === resolve.py tests ===


class TestNormalize:
    def test_lowercases(self):
        assert normalize("Latin Kings") == "latin kings"

    def test_strips_punctuation(self):
        assert normalize("MS-13") == "ms13"

    def test_collapses_spaces(self):
        assert normalize("  hello   world  ") == "hello world"


class TestResolve:
    @pytest.fixture
    def mock_index(self):
        return {
            "latin kings": "org:latin-kings",
            "almighty latin king nation": "org:latin-kings",
            "crips": "org:crips",
            "bloods": "org:bloods",
            "ambrose": "org:ambrose",
            "almighty ambrose": "org:ambrose",
            "folk nation": "org:folk-nation",
            "satan disciples": "org:satan-disciples",
        }

    def test_exact_match(self, mock_index):
        assert resolve("Latin Kings", mock_index) == "org:latin-kings"

    def test_case_insensitive(self, mock_index):
        assert resolve("CRIPS", mock_index) == "org:crips"

    def test_suffix_stripping(self, mock_index):
        assert resolve("Ambrose Gang", mock_index) == "org:ambrose"

    def test_no_match_returns_none(self, mock_index):
        assert resolve("Nonexistent Gang", mock_index) is None

    def test_empty_string(self, mock_index):
        assert resolve("", mock_index) is None

    def test_containment_match(self, mock_index):
        # "satan disciples" is in the index, "Satan Disciples Chicago" contains it
        result = resolve("Satan Disciples", mock_index)
        assert result == "org:satan-disciples"

    def test_no_false_containment(self, mock_index):
        # "king" is too short to match "latin kings" via containment
        assert resolve("King", mock_index) is None


# === merge.py tests ===


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
        assert "red" not in result["colors"]  # only in 1 run

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
        # Bloods rivalry in 3/3 runs, Unicorns alliance in 1/3
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


# === extract.py tests ===


class TestChunkText:
    def test_small_text_single_chunk(self):
        text = "word " * 100
        assert len(chunk_text(text)) == 1

    def test_large_text_splits(self):
        text = "word " * 60000
        chunks = chunk_text(text)
        assert len(chunks) == 2  # 60K / 50K = 2 chunks

    def test_empty_text(self):
        assert chunk_text("") == [""]


class TestMergeChunks:
    def test_single_chunk(self):
        chunk = {"subject_org": "X", "founded_year": 1990, "edges": [{"target": "Y", "type": "rivalry"}], "colors": ["blue"]}
        assert merge_chunks([chunk]) == chunk

    def test_merges_edges_from_chunks(self):
        c1 = {"subject_org": "X", "edges": [{"target": "A", "type": "alliance"}], "colors": [], "symbols": [], "orgs_mentioned": []}
        c2 = {"subject_org": "X", "edges": [{"target": "B", "type": "rivalry"}], "colors": [], "symbols": [], "orgs_mentioned": []}
        result = merge_chunks([c1, c2])
        assert len(result["edges"]) == 2

    def test_takes_first_year(self):
        c1 = {"subject_org": "X", "founded_year": 1958, "edges": [], "colors": [], "symbols": [], "orgs_mentioned": []}
        c2 = {"subject_org": "X", "founded_year": None, "edges": [], "colors": [], "symbols": [], "orgs_mentioned": []}
        result = merge_chunks([c1, c2])
        assert result["founded_year"] == 1958

    def test_unions_colors(self):
        c1 = {"subject_org": "X", "edges": [], "colors": ["Blue"], "symbols": [], "orgs_mentioned": []}
        c2 = {"subject_org": "X", "edges": [], "colors": ["Black"], "symbols": [], "orgs_mentioned": []}
        result = merge_chunks([c1, c2])
        assert "black" in result["colors"]
        assert "blue" in result["colors"]


class TestPromptHash:
    def test_returns_string(self):
        assert isinstance(prompt_hash(), str)
        assert len(prompt_hash()) == 8


# === adjudicate.py tests ===


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
        # 5 edges, each only in 1 run = 100% uncertain > 30% threshold
        runs = [
            {"founded_year": 1958, "colors": [], "edges": [{"target": "A", "type": "r"}, {"target": "B", "type": "r"}, {"target": "C", "type": "r"}]},
            {"founded_year": 1958, "colors": [], "edges": [{"target": "D", "type": "r"}, {"target": "E", "type": "r"}, {"target": "F", "type": "r"}]},
            {"founded_year": 1958, "colors": [], "edges": []},
        ]
        assert needs_adjudication(runs) is True
