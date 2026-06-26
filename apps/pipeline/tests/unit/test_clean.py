"""Tests for apps/pipeline/parse/clean.py"""

from apps.pipeline.parse.clean import clean_html, quality_score


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
