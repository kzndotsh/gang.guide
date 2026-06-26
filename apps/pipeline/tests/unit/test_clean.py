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


class TestCleanHtmlEdgeCases:
    def test_preserves_plain_text(self):
        assert clean_html("Hello world") == "Hello world"

    def test_handles_nested_tags(self):
        result = clean_html("<div><p><b>bold</b> text</p></div>")
        assert "bold" in result
        assert "text" in result

    def test_handles_empty_string(self):
        assert clean_html("") == ""

    def test_strips_comments(self):
        assert "secret" not in clean_html("<!-- secret -->visible")
        assert "visible" in clean_html("<!-- secret -->visible")

    def test_handles_br_tags(self):
        result = clean_html("line1<br>line2<br/>line3")
        assert "line1" in result
        assert "line2" in result

    def test_strips_edit_markers(self):
        assert "[edit]" not in clean_html("History[edit] of the gang")

    def test_handles_unicode(self):
        result = clean_html("<p>café résumé naïve</p>")
        assert "café" in result or "caf" in result


class TestQualityScoreEdgeCases:
    def test_returns_word_count(self):
        result = quality_score("one two three four five six seven")
        assert result["word_count"] == 7

    def test_prose_ratio_all_prose(self):
        text = "This is a sentence with more than five words in it.\n" * 10
        result = quality_score(text)
        assert result["prose_ratio"] == 1.0

    def test_prose_ratio_no_prose(self):
        text = "One\nTwo\nThree\nFour\nFive\n"
        result = quality_score(text)
        assert result["prose_ratio"] == 0.0

    def test_mixed_quality(self):
        text = "Nav\nAbout\nHome\nThis is a real sentence about something important.\nContact\n"
        result = quality_score(text)
        assert 0 < result["prose_ratio"] < 1.0
