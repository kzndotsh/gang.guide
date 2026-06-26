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


class TestChunkTextEdgeCases:
    def test_exactly_at_limit(self):
        text = "word " * 50000
        chunks = chunk_text(text.strip())
        assert len(chunks) == 1

    def test_one_over_limit(self):
        text = "word " * 50001
        chunks = chunk_text(text.strip())
        assert len(chunks) == 2

    def test_preserves_all_words(self):
        text = "word " * 100
        chunks = chunk_text(text.strip())
        total_words = sum(len(c.split()) for c in chunks)
        assert total_words == 100


class TestMergeChunksEdgeCases:
    def test_empty_list(self):
        result = merge_chunks([])
        assert result["edges"] == []
        assert result["subject_org"] is None

    def test_dedupes_colors(self):
        c1 = {"subject_org": "X", "edges": [], "colors": ["Blue"], "symbols": [], "orgs_mentioned": []}
        c2 = {"subject_org": "X", "edges": [], "colors": ["BLUE", "black"], "symbols": [], "orgs_mentioned": []}
        result = merge_chunks([c1, c2])
        assert result["colors"].count("blue") == 1

    def test_picks_longest_description(self):
        c1 = {"subject_org": "X", "edges": [], "colors": [], "symbols": [], "orgs_mentioned": [], "description": "Short."}
        c2 = {"subject_org": "X", "edges": [], "colors": [], "symbols": [], "orgs_mentioned": [], "description": "A much longer and more detailed description."}
        result = merge_chunks([c1, c2])
        assert "longer" in result["description"]

    def test_membership_takes_last(self):
        c1 = {"subject_org": "X", "edges": [], "colors": [], "symbols": [], "orgs_mentioned": [], "membership_estimate": 5000}
        c2 = {"subject_org": "X", "edges": [], "colors": [], "symbols": [], "orgs_mentioned": [], "membership_estimate": 8000}
        result = merge_chunks([c1, c2])
        assert result["membership_estimate"] == 8000


class TestChunkTextAdversarial:
    def test_single_word(self):
        assert chunk_text("hello") == ["hello"]

    def test_only_spaces(self):
        result = chunk_text("     ")
        assert result == ["     "] or result == [""]

    def test_newlines_only(self):
        result = chunk_text("\n\n\n")
        assert isinstance(result, list)

    def test_unicode_words(self):
        text = "café " * 100
        chunks = chunk_text(text)
        assert len(chunks) == 1


class TestMergeChunksAdversarial:
    def test_chunks_with_none_fields(self):
        chunks = [
            {"subject_org": None, "founded_year": None, "edges": None, "colors": None, "symbols": None, "orgs_mentioned": None, "description": None, "membership_estimate": None},
        ]
        result = merge_chunks(chunks)
        assert result["subject_org"] is None

    def test_very_long_description(self):
        chunks = [
            {"subject_org": "X", "edges": [], "colors": [], "symbols": [], "orgs_mentioned": [], "description": "x" * 100000},
        ]
        result = merge_chunks(chunks)
        assert len(result["description"]) == 100000
