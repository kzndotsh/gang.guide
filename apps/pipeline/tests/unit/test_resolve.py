"""Tests for apps/pipeline/lib/resolve.py"""

import pytest
from apps.pipeline.lib.resolve import normalize, resolve


class TestNormalize:
    @pytest.mark.parametrize("input,expected", [
        ("Latin Kings", "latin kings"),
        ("MS-13", "ms13"),
        ("  hello   world  ", "hello world"),
        ("Almighty Vice Lord Nation", "almighty vice lord nation"),
        ("18th Street Gang!", "18th street gang"),
        ("", ""),
    ])
    def test_normalize(self, input, expected):
        assert normalize(input) == expected


class TestResolve:
    def test_exact_match(self, org_index):
        assert resolve("Latin Kings", org_index) == "org:latin-kings"

    def test_case_insensitive(self, org_index):
        assert resolve("CRIPS", org_index) == "org:crips"

    def test_suffix_stripping(self, org_index):
        assert resolve("Ambrose Gang", org_index) == "org:ambrose"

    def test_no_match_returns_none(self, org_index):
        assert resolve("Nonexistent Gang", org_index) is None

    def test_empty_string(self, org_index):
        assert resolve("", org_index) is None

    def test_containment_match(self, org_index):
        assert resolve("Satan Disciples", org_index) == "org:satan-disciples"

    def test_no_false_containment(self, org_index):
        assert resolve("King", org_index) is None

    @pytest.mark.parametrize("name,expected_id", [
        ("Folk Nation", "org:folk-nation"),
        ("folk nation", "org:folk-nation"),
        ("Bloods", "org:bloods"),
        ("Almighty Ambrose", "org:ambrose"),
        ("Vice Lords", "org:almighty-vice-lord-nation"),
    ])
    def test_known_resolutions(self, org_index, name, expected_id):
        assert resolve(name, org_index) == expected_id


class TestResolveEdgeCases:
    def test_punctuation_stripped_before_match(self, org_index):
        assert resolve("Crips!", org_index) == "org:crips"

    def test_multiple_suffix_stripping(self, org_index):
        assert resolve("Bloods Gang", org_index) == "org:bloods"

    def test_very_long_name(self, org_index):
        assert resolve("A" * 200, org_index) is None

    def test_single_character(self, org_index):
        assert resolve("X", org_index) is None

    def test_numeric_input(self, org_index):
        assert resolve("13", org_index) is None
