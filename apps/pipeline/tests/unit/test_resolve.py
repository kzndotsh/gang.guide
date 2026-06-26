"""Tests for apps/pipeline/lib/resolve.py"""

import pytest
from apps.pipeline.lib.resolve import normalize, resolve


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
        result = resolve("Satan Disciples", mock_index)
        assert result == "org:satan-disciples"

    def test_no_false_containment(self, mock_index):
        assert resolve("King", mock_index) is None
