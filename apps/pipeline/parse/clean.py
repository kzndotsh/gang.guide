"""clean.py — HTML → clean plaintext.

First step of the parse layer. Turns raw HTML into clean text that
parsers and the LLM can work with. All downstream scripts read
content.txt, never raw HTML directly.

Usage:
    python -m apps.pipeline.parse.clean --source chicago_history
"""

import re
import html as html_lib
from pathlib import Path


def clean_html(raw: str) -> str:
    """Convert raw HTML to clean plaintext."""
    text = raw

    # Remove script/style blocks
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # Remove HTML comments
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)

    # Convert common block elements to newlines
    text = re.sub(r'<(?:br|hr|/p|/div|/tr|/li|/h[1-6])[^>]*>', '\n', text, flags=re.IGNORECASE)

    # Remove all remaining HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)

    # Decode HTML entities
    text = html_lib.unescape(text)

    # Remove citation markers [1] [2] [citation needed]
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\[citation needed\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[edit\]', '', text, flags=re.IGNORECASE)

    # Fix mojibake patterns
    text = text.replace('Ã©', 'é').replace('Ã±', 'ñ').replace('Ã³', 'ó')
    text = text.replace('â€™', "'").replace('â€"', '—').replace('â€œ', '"').replace('â€\x9d', '"')

    # Collapse whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' +\n', '\n', text)
    text = '\n'.join(line.strip() for line in text.split('\n'))

    return text.strip()


def quality_score(text: str) -> dict:
    """Compute quality metrics for cleaned text."""
    words = text.split()
    lines = text.split('\n')
    prose_lines = [l for l in lines if len(l.split()) > 5]
    return {
        "word_count": len(words),
        "line_count": len(lines),
        "prose_ratio": len(prose_lines) / max(len(lines), 1),
        "is_low_quality": len(words) < 50 or (len(prose_lines) / max(len(lines), 1)) < 0.3,
    }
