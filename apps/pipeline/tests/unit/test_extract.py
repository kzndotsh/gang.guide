"""Tests for apps/pipeline/extract.py"""

from apps.pipeline.extract import chunk_text, merge_chunks, prompt_hash


class TestChunkText:
    def test_small_text_single_chunk(self):
        text = "word " * 100
        assert len(chunk_text(text)) == 1

    def test_large_text_splits(self):
        text = "word " * 60000
        chunks = chunk_text(text)
        assert len(chunks) == 2

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
