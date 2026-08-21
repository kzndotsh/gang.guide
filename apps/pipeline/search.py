"""search.py — multi-source web search for pipeline tools.

Runs queries across all available backends and merges results.
Each tool (enrich.py, clean.py, verify.py) imports `multi_search` and
`fetch_url` from here instead of implementing their own HTTP logic.

Backends (in priority order):
  1. Brave Search API  — structured JSON, independent index, news endpoint
                         requires BRAVE_API_KEY env var
  2. DuckDuckGo HTML   — free, no key, always available as fallback
  3. Wikipedia REST    — keyless, for entity lookups (org names, people, places)

Usage:
    from apps.pipeline.search import multi_search, fetch_url

    results = multi_search("Latin Kings founded 1954 Chicago")
    page_text = fetch_url("https://en.wikipedia.org/wiki/Latin_Kings_(gang)")
"""

from __future__ import annotations

import os
import re
from urllib.parse import quote_plus, urlparse

import httpx

# ── API key loading ────────────────────────────────────────────────────────────

def _load_brave_key() -> str | None:
    """Load BRAVE_API_KEY from environment or .env file."""
    key = os.environ.get("BRAVE_API_KEY", "")
    if key:
        return key
    # Try root .env
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent.parent
    for env_path in [root / ".env", root / "apps" / "pipeline" / ".env"]:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("BRAVE_API_KEY="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        return val
    return None


BRAVE_API_KEY: str | None = _load_brave_key()


def _load_courtlistener_key() -> str | None:
    """Load COURTLISTENER_API_KEY from environment or .env file."""
    key = os.environ.get("COURTLISTENER_API_KEY", "")
    if key:
        return key
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent.parent
    for env_path in [root / ".env", root / "apps" / "pipeline" / ".env"]:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("COURTLISTENER_API_KEY="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        return val
    return None


COURTLISTENER_API_KEY: str | None = _load_courtlistener_key()

# Known domains → human-readable titles for Wikipedia REST fallback
DOMAIN_TITLES = {
    "en.wikipedia.org": "Wikipedia",
    "unitedgangs.com": "UnitedGangs",
    "streetgangs.com": "StreetGangs",
    "www.streetgangs.com": "StreetGangs",
    "chicagoganghistory.com": "Chicago Gang History",
    "www.chicagoganghistory.com": "Chicago Gang History",
    "detroitstreetgangs.com": "Detroit Street Gangs",
    "newyorkcitygangs.com": "New York City Gangs",
    "stonegreasers.com": "StoneGreasers",
    "www.stonegreasers.com": "StoneGreasers",
    "justice.gov": "U.S. Department of Justice",
    "www.justice.gov": "U.S. Department of Justice",
    "fbi.gov": "FBI",
    "www.fbi.gov": "FBI",
    "adl.org": "ADL",
    "www.adl.org": "ADL",
    "splcenter.org": "SPLC",
    "blackpast.org": "BlackPast",
    "web.archive.org": "Wayback Machine",
    "courtlistener.com": "CourtListener",
    "americangang.watch": "American Gang Watch",
    "hiphopdatabase.fandom.com": "Hip Hop Database Wiki",
    "historica.fandom.com": "Historica Wiki",
    "grokipedia.com": "Grokipedia",
}


def domain_title(url: str) -> str:
    """Infer a human-readable source title from a URL."""
    try:
        host = urlparse(url).netloc.lower()
        if host in DOMAIN_TITLES:
            return DOMAIN_TITLES[host]
        # Strip www. and use domain stem
        host = host.removeprefix("www.")
        parts = host.split(".")
        return parts[0].replace("-", " ").title() if parts else host
    except Exception:
        return url


# ── Brave Search ───────────────────────────────────────────────────────────────

def _brave_search(query: str, count: int = 8) -> list[dict]:
    """Search via Brave Search API. Returns list of {title, url, snippet}."""
    if not BRAVE_API_KEY:
        return []
    try:
        resp = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": count, "result_filter": "web,news"},
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": BRAVE_API_KEY,
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        # Web results
        for r in (data.get("web") or {}).get("results") or []:
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("description", ""),
                "source": "brave",
            })
        # News results (often more specific for gang history)
        for r in (data.get("news") or {}).get("results") or []:
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("description", ""),
                "source": "brave_news",
            })
        return results[:count]
    except Exception:
        return []


# ── DuckDuckGo HTML ────────────────────────────────────────────────────────────

def _ddg_search(query: str, count: int = 6) -> list[dict]:
    """Search via DuckDuckGo HTML scraping. Free, no key, always-on fallback."""
    try:
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (compatible; gang-guide/2.0)"},
            timeout=10.0,
            follow_redirects=True,
        )
        resp.raise_for_status()
        results = []
        for match in re.finditer(
            r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?'
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
            resp.text,
            re.DOTALL,
        ):
            raw_url = match.group(1)
            title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            snippet = re.sub(r"<[^>]+>", "", match.group(3)).strip()

            # Decode DDG redirect URLs → direct destination URLs
            # DDG returns //duckduckgo.com/l/?uddg=https%3A%2F%2F...
            url = raw_url
            uddg_match = re.search(r"[?&]uddg=([^&]+)", raw_url)
            if uddg_match:
                from urllib.parse import unquote
                url = unquote(uddg_match.group(1))
            elif raw_url.startswith("//"):
                url = "https:" + raw_url

            if title and snippet:
                results.append({"title": title, "url": url, "snippet": snippet, "source": "ddg"})
            if len(results) >= count:
                break
        if not results:
            # Fallback: bare snippet extraction
            for s in re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', resp.text, re.DOTALL)[:count]:
                clean = re.sub(r"<[^>]+>", "", s).strip()
                if clean:
                    results.append({"title": "", "url": "", "snippet": clean, "source": "ddg"})
        return results
    except Exception:
        return []


# ── CourtListener ──────────────────────────────────────────────────────────────

def _courtlistener_search(query: str, count: int = 4) -> list[dict]:
    """Search CourtListener for federal court opinions and PACER dockets.

    Particularly valuable for:
    - Gang founding dates (RICO indictments often cite exact formation years)
    - Membership estimates (sentencing docs include FBI estimates)
    - Alias lists (indictments enumerate all known aliases)
    - Confirmed rivalries/alliances (evidence sections describe gang relationships)
    """
    if not COURTLISTENER_API_KEY:
        return []
    results = []
    try:
        # Search opinions (case law — RICO convictions, gang injunctions, etc.)
        resp = httpx.get(
            "https://www.courtlistener.com/api/rest/v4/search/",
            params={
                "q": query,
                "type": "o",  # opinions
                "order_by": "score desc",
                "stat_Precedential": "on",
            },
            headers={
                "Authorization": f"Token {COURTLISTENER_API_KEY}",
                "User-Agent": "gang-guide-pipeline/2.0",
            },
            timeout=12.0,
        )
        resp.raise_for_status()
        data = resp.json()
        for r in (data.get("results") or [])[:count]:
            case_name = r.get("caseName") or r.get("case_name", "")
            court = r.get("court_id", "").upper()
            date = (r.get("dateFiled") or r.get("date_filed") or "")[:10]
            url = f"https://www.courtlistener.com{r['absolute_url']}" if r.get("absolute_url") else ""

            # snippet lives in opinions[0].snippet, not top-level
            snippet = ""
            opinions = r.get("opinions") or []
            if opinions and opinions[0].get("snippet"):
                snippet = opinions[0]["snippet"]
            if not snippet:
                # Fallback to posture/syllabus
                snippet = r.get("posture") or r.get("syllabus") or ""
            # Clean HTML
            snippet = re.sub(r"<[^>]+>", " ", snippet)
            snippet = re.sub(r"\s+", " ", snippet).strip()

            if case_name and snippet:
                title = f"{case_name} ({court}, {date})" if court and date else case_name
                results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet[:400],
                    "source": "courtlistener",
                })
    except Exception:
        pass

    # Also search PACER dockets (indictments, plea agreements, sentencing docs)
    try:
        resp = httpx.get(
            "https://www.courtlistener.com/api/rest/v4/search/",
            params={
                "q": query,
                "type": "r",  # RECAP/PACER dockets
                "order_by": "score desc",
            },
            headers={
                "Authorization": f"Token {COURTLISTENER_API_KEY}",
                "User-Agent": "gang-guide-pipeline/2.0",
            },
            timeout=12.0,
        )
        resp.raise_for_status()
        data = resp.json()
        for r in (data.get("results") or [])[:max(2, count - len(results))]:
            case_name = r.get("caseName") or r.get("case_name", "")
            court = r.get("court_id", "").upper()
            date = (r.get("dateFiled") or "")[:10]
            nature = r.get("suitNature") or r.get("cause") or ""
            url = f"https://www.courtlistener.com{r['docket_absolute_url']}" if r.get("docket_absolute_url") else ""

            # PACER dockets don't have text snippets — build one from metadata
            if case_name and nature:
                snippet = f"Federal case: {nature}. Filed {date}."
                title = f"{case_name} ({court}, {date})" if court and date else case_name
                results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                    "source": "courtlistener_pacer",
                })
    except Exception:
        pass

    return results


# ── Wikipedia REST ─────────────────────────────────────────────────────────────

def _wikipedia_search(query: str) -> list[dict]:
    """Search Wikipedia and return matching article summaries.

    Uses the CirrusSearch fulltext API (action=query&list=search) rather than
    opensearch — opensearch is prefix-only/typeahead, CirrusSearch finds articles
    by content AND title using Elasticsearch, much better for research queries.

    Then fetches the REST summary for each match for clean extracted text.
    Only called for queries that look like entity names.
    """
    results = []

    # Extract a short entity name from longer queries for the search
    search_term = query
    words = query.split()
    if len(words) >= 2:
        entity_words = []
        for w in words:
            if w and w[0].isupper() and not w.isdigit():
                entity_words.append(w)
            elif entity_words:
                break
        if len(entity_words) >= 1:
            search_term = " ".join(entity_words[:3])

    try:
        # CirrusSearch fulltext search — finds by title AND content
        resp = httpx.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": search_term,
                "srnamespace": "0",         # articles only
                "srlimit": "3",
                "srprop": "snippet|titlesnippet",
                "format": "json",
            },
            headers={"User-Agent": "gang-guide-pipeline/2.0"},
            timeout=8.0,
        )
        resp.raise_for_status()
        data = resp.json()
        hits = (data.get("query") or {}).get("search") or []

        # Fetch REST summary for each match
        for hit in hits[:2]:
            title = hit.get("title", "")
            if not title:
                continue
            try:
                title_encoded = title.replace(" ", "_")
                summary_resp = httpx.get(
                    f"https://en.wikipedia.org/api/rest_v1/page/summary/{title_encoded}",
                    headers={"User-Agent": "gang-guide-pipeline/2.0"},
                    timeout=8.0,
                    follow_redirects=True,
                )
                if summary_resp.status_code == 200:
                    s = summary_resp.json()
                    extract = s.get("extract", "")
                    if extract and len(extract) > 50:
                        results.append({
                            "title": f"{s.get('title', title)} — Wikipedia",
                            "url": s.get("content_urls", {}).get("desktop", {}).get("page", ""),
                            "snippet": extract[:600],
                            "source": "wikipedia",
                        })
            except Exception:
                continue
    except Exception:
        pass
    return results


# ── Main multi_search ──────────────────────────────────────────────────────────

def _looks_like_entity(query: str) -> bool:
    """Heuristic: does the query look like an org/person name worth Wikipedia-searching?"""
    # Mostly title-cased words, short enough to be a name
    words = query.split()
    if len(words) > 8:
        return False
    title_cased = sum(1 for w in words if w and w[0].isupper())
    return title_cased >= max(1, len(words) // 2)


def _dedup_results(results: list[dict]) -> list[dict]:
    """Remove duplicate results by URL domain+path, keeping first occurrence."""
    seen_urls: set[str] = set()
    seen_snippets: set[str] = set()
    deduped = []
    for r in results:
        url = r.get("url", "")
        snippet_key = r.get("snippet", "")[:60].lower()
        # Normalize URL for dedup (strip query params)
        url_key = re.sub(r"\?.*$", "", url).rstrip("/").lower()
        if url_key and url_key in seen_urls:
            continue
        if snippet_key and snippet_key in seen_snippets:
            continue
        if url_key:
            seen_urls.add(url_key)
        if snippet_key:
            seen_snippets.add(snippet_key)
        deduped.append(r)
    return deduped


def _format_results(results: list[dict]) -> str:
    """Format merged results into readable text for LLM context."""
    if not results:
        return "No results found."
    lines = []
    for r in results:
        title = r.get("title", "")
        url = r.get("url", "")
        snippet = r.get("snippet", "")
        if title and url:
            lines.append(f"[{title}]({url})\n{snippet}")
        elif title:
            lines.append(f"[{title}]\n{snippet}")
        elif snippet:
            lines.append(snippet)
    return "\n\n".join(lines) if lines else "No results found."


def multi_search(query: str, count: int = 8) -> str:
    """Search across all available backends and return merged, deduplicated results.

    Priority:
      1. Brave Search (structured, independent index, news)
      2. DuckDuckGo HTML (free fallback, always available)
      3. Wikipedia REST (for entity queries only)
      4. CourtListener (for legal/court queries — RICO, indictments, gang history)

    Returns a formatted string suitable for LLM context.
    """
    all_results: list[dict] = []

    # 1. Brave (best quality, structured JSON)
    brave = _brave_search(query, count=count)
    all_results.extend(brave)

    # 2. DuckDuckGo (always run — catches what Brave misses)
    ddg = _ddg_search(query, count=max(4, count - len(brave)))
    all_results.extend(ddg)

    # 3. Wikipedia (only for entity-like queries)
    if _looks_like_entity(query):
        wiki = _wikipedia_search(query)
        all_results.extend(wiki)

    # 4. CourtListener (for queries mentioning legal/criminal context)
    COURT_SIGNALS = {"gang", "racketeering", "rico", "indictment", "convicted",
                     "sentenced", "federal", "doj", "fbi", "founded", "history",
                     "membership", "members", "prison", "criminal"}
    query_words = set(query.lower().split())
    if query_words & COURT_SIGNALS and COURTLISTENER_API_KEY:
        court = _courtlistener_search(query, count=3)
        all_results.extend(court)

    # Deduplicate and format
    deduped = _dedup_results(all_results)
    return _format_results(deduped[:count + 4])  # slight buffer before format


def court_search(query: str, count: int = 5) -> str:
    """Search CourtListener specifically — use when you need court docs.

    Useful when web search isn't finding primary source material for
    founding dates, membership estimates, or confirmed relationships.
    Returns formatted string of case excerpts with citations.
    """
    results = _courtlistener_search(query, count=count)
    return _format_results(results) if results else "No court records found."


# ── fetch_url ──────────────────────────────────────────────────────────────────

def fetch_url(url: str, max_chars: int = 6000) -> str:
    """Fetch a URL and return clean readable text.

    For Wikipedia URLs, uses the REST API for cleaner extraction.
    For all other URLs, fetches HTML and strips tags.
    """
    # Wikipedia: use REST API for cleaner output
    wiki_match = re.match(r"https?://en\.wikipedia\.org/wiki/(.+)", url)
    if wiki_match:
        title = wiki_match.group(1)  # already URL-encoded from the source URL
        try:
            resp = httpx.get(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
                headers={"User-Agent": "gang-guide-pipeline/2.0"},
                timeout=10.0,
                follow_redirects=True,
            )
            if resp.status_code == 200:
                data = resp.json()
                extract = data.get("extract", "")
                if extract:
                    # Also try to get more than just the intro via the full sections
                    sections_resp = httpx.get(
                        f"https://en.wikipedia.org/api/rest_v1/page/mobile-sections/{title}",
                        headers={"User-Agent": "gang-guide-pipeline/2.0"},
                        timeout=10.0,
                        follow_redirects=True,
                    )
                    if sections_resp.status_code == 200:
                        sections = sections_resp.json()
                        lead = sections.get("lead", {}).get("sections", [{}])[0].get("text", "")
                        lead_text = re.sub(r"<[^>]+>", " ", lead)
                        lead_text = re.sub(r"\s+", " ", lead_text).strip()
                        if len(lead_text) > len(extract):
                            return lead_text[:max_chars]
                    return extract[:max_chars]
        except Exception:
            pass  # fall through to regular fetch

    # Standard HTML fetch
    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; gang-guide/2.0)"},
            timeout=15.0,
            follow_redirects=True,
        )
        resp.raise_for_status()
        content = resp.text
        content = re.sub(r"<script[^>]*>.*?</script>", " ", content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r"<style[^>]*>.*?</style>", " ", content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r"<[^>]+>", " ", content)
        content = re.sub(r"\s+", " ", content).strip()
        return content[:max_chars]
    except Exception as e:
        return f"Fetch failed: {e}"


# ── CLI test mode ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Latin Kings gang founded Chicago history"
    print(f"Query: {query}")
    print(f"Brave key:         {'✓' if BRAVE_API_KEY else '✗ (not found)'}")
    print(f"CourtListener key: {'✓' if COURTLISTENER_API_KEY else '✗ (not found)'}")
    print()
    print(multi_search(query))
