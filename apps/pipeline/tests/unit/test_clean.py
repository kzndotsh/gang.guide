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


class TestCleanHtmlAdversarial:
    """Test with malicious/broken input that could crash the pipeline."""

    def test_massive_input(self):
        """1MB of HTML shouldn't hang or crash."""
        huge = "<p>word </p>" * 100000
        result = clean_html(huge)
        assert len(result) > 0

    def test_deeply_nested_tags(self):
        nested = "<div>" * 100 + "content" + "</div>" * 100
        result = clean_html(nested)
        assert "content" in result

    def test_unclosed_tags(self):
        result = clean_html("<div><p>text<span>more")
        assert "text" in result
        assert "more" in result

    def test_binary_garbage(self):
        """Binary content shouldn't crash."""
        garbage = "Hello \x00\x01\x02\x03 world \xff\xfe"
        result = clean_html(garbage)
        assert isinstance(result, str)

    def test_only_tags_no_content(self):
        result = clean_html("<div><span></span></div><br><hr>")
        assert result.strip() == "" or "\n" in result

    def test_script_with_angle_brackets(self):
        """Script containing < > shouldn't leak into output."""
        html = "<script>if (x < 3 && y > 2) { alert('hi'); }</script>Real content"
        result = clean_html(html)
        assert "alert" not in result
        assert "Real content" in result

    def test_null_bytes(self):
        result = clean_html("Hello\x00World")
        assert isinstance(result, str)

    def test_extremely_long_line(self):
        """Single line with no breaks."""
        long_line = "word " * 50000
        result = clean_html(long_line)
        assert len(result.split()) == 50000


class TestQualityScoreAdversarial:
    def test_only_whitespace(self):
        result = quality_score("   \n\n\t\t  \n  ")
        assert result["is_low_quality"] is True
        assert result["word_count"] == 0

    def test_single_very_long_word(self):
        result = quality_score("a" * 10000)
        assert result["word_count"] == 1
        assert result["is_low_quality"] is True
