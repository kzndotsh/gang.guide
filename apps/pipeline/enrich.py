"""enrich.py — identify weak org profiles and enrich them via LLM.

Scores all orgs by weakness (missing fields, stub descriptions) weighted by
graph connectivity. High-connectivity stubs are enriched first since they
impact the most edges on the map.

Usage:
    python3 -m apps.pipeline.enrich --limit 20 --dry-run
    python3 -m apps.pipeline.enrich --limit 50
    python3 -m apps.pipeline.enrich --org org:rollin-60s-neighborhood-crips
"""

import argparse
import json
import os
import re
import subprocess
import time
from collections import Counter
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_ORGS = ROOT / "data" / "orgs"
DATA_EDGES = ROOT / "data" / "edges.json"
DATA_RAW = ROOT / "data" / "raw"

KIRO_URL = os.environ.get("KIRO_GATEWAY_URL", "http://127.0.0.1:9000")
KIRO_KEY = os.environ.get("KIRO_GATEWAY_API_KEY", os.environ.get("PROXY_API_KEY", ""))
MODEL = os.environ.get("ENRICH_MODEL", "claude-sonnet-4.5")

# Max chars of raw context to include in the prompt
MAX_CONTEXT_CHARS = 8000

SYSTEM_PROMPT = """You are a research assistant specializing in US criminal organizations. Given an org's name, location, and existing data, fill in missing fields.

You have access to tools:
- web_search: Search the web for information about the org (founding dates, membership, colors, etc.)
- fetch_url: Read a specific URL for detailed information

WORKFLOW:
1. If source material is provided in the prompt, check it first for answers.
2. If you still need information, use web_search to find it.
3. If a search result points to a useful page, use fetch_url to read it.
4. Once you have enough information, respond with the final JSON.

Rules:
- Base answers on source material and web search results. Do NOT guess from training data alone.
- Only provide information supported by evidence you found. Use null for uncertain fields.
- Descriptions must be factual, 2-3 sentences, with founding context and notable characteristics.
- Do NOT fabricate relationships, membership numbers, or founding dates you aren't sure about.
- Colors must be real color words (red, blue, green, etc.)
- Aliases must be names the org is actually known by (abbreviations, street names, alternative spellings)
- Founded year should be the year the org was established, not when it joined a larger alliance.
- Membership estimates should reflect peak or current membership; use null if unknown.

When you have gathered enough information, respond with ONLY valid JSON matching this schema:
{
  "description": "2-3 sentence factual description or null if you cannot improve on existing",
  "founded_year": 1972 or null,
  "founded_year_precision": "exact|circa|decade|estimate" or null,
  "colors": ["red", "black"] or null,
  "aliases": ["Alias 1", "Alias 2"] or null,
  "membership_estimate": 5000 or null
}

Return null for any field you cannot confidently fill. Better to leave a gap than provide wrong data."""


def load_orgs() -> dict[str, dict]:
    """Load all org JSON files."""
    orgs = {}
    for f in sorted(DATA_ORGS.glob("*.json")):
        org = json.loads(f.read_text())
        org["_file"] = str(f)
        orgs[org["id"]] = org
    return orgs


def load_edge_counts() -> Counter:
    """Count edges per org."""
    edges = json.loads(DATA_EDGES.read_text())
    counts = Counter()
    for e in edges:
        counts[e["source"]] += 1
        counts[e["target"]] += 1
    return counts


def gather_raw_context(org: dict) -> str:
    """Search data/raw/ for mentions of this org and return relevant snippets.

    Uses ripgrep for speed across 682MB of raw content. Falls back to a simple
    grep if rg isn't available. Returns up to MAX_CONTEXT_CHARS of context.
    """
    name = org.get("name", "")
    aliases = org.get("aliases") or []

    # Build search terms: org name + aliases + slug variations
    search_terms = [name]
    search_terms.extend(aliases)
    # Add slug-based variations (e.g. "rollin-60s" from org ID)
    org_id = org.get("id", "")
    slug = org_id.replace("org:", "")
    slug_words = slug.replace("-", " ")
    if slug_words != name.lower():
        search_terms.append(slug_words)

    # Deduplicate and filter short terms
    search_terms = list({t for t in search_terms if t and len(t) > 3})

    if not search_terms:
        return ""

    # Build grep pattern (case-insensitive, any term)
    pattern = "|".join(re.escape(t) for t in search_terms[:5])  # limit to 5 terms

    snippets = []
    total_chars = 0

    try:
        # Use ripgrep for speed
        result = subprocess.run(
            ["rg", "-il", "--max-count=1", pattern, str(DATA_RAW)],
            capture_output=True, text=True, timeout=10,
        )
        matching_files = result.stdout.strip().split("\n") if result.stdout.strip() else []
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # Fallback: use grep
        try:
            result = subprocess.run(
                ["grep", "-ril", "--include=*.txt", "--include=*.html", pattern, str(DATA_RAW)],
                capture_output=True, text=True, timeout=15,
            )
            matching_files = result.stdout.strip().split("\n") if result.stdout.strip() else []
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ""

    # Read snippets from matching files
    for filepath in matching_files[:10]:  # limit to 10 files
        if not filepath or not Path(filepath).exists():
            continue
        try:
            content = Path(filepath).read_text(errors="ignore")
            # Strip script/style blocks from HTML
            content = re.sub(r"<script[^>]*>.*?</script>", " ", content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r"<style[^>]*>.*?</style>", " ", content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r"/\*.*?\*/", " ", content, flags=re.DOTALL)  # CSS comments
            # Extract paragraphs mentioning the org
            for para in re.split(r"\n{2,}|\<p\>|\<\/p\>|\<br\s*/?\>", content):
                para_lower = para.lower()
                if any(t.lower() in para_lower for t in search_terms[:3]):
                    # Clean HTML tags
                    clean = re.sub(r"<[^>]+>", " ", para).strip()
                    clean = re.sub(r"\s+", " ", clean)
                    # Skip if it looks like code/CSS/JS
                    if any(junk in clean for junk in ["{", "}", "function(", "var ", "const ", "sourceURL=", "font-", "margin:", "padding:"]):
                        continue
                    if len(clean) > 50 and len(clean) < 2000:
                        snippets.append(clean)
                        total_chars += len(clean)
                        if total_chars >= MAX_CONTEXT_CHARS:
                            break
        except (OSError, UnicodeDecodeError):
            continue

        if total_chars >= MAX_CONTEXT_CHARS:
            break

    if not snippets:
        return ""

    # Deduplicate similar snippets
    seen = set()
    unique = []
    for s in snippets:
        key = s[:80].lower()
        if key not in seen:
            seen.add(key)
            unique.append(s)

    return "\n\n".join(unique[:15])  # max 15 snippets


def score_org(org: dict, edge_count: int) -> tuple[float, list[str]]:
    """Score an org's weakness. Higher = more in need of enrichment.

    Returns (priority_score, list_of_issues).
    Priority = issue_count * connectivity_weight.
    """
    issues = []
    desc = org.get("description", "")

    # Description quality
    if len(desc) < 50:
        issues.append("stub_desc")
    elif len(desc) < 100 or "is a street gang based in" in desc:
        issues.append("short_desc")

    # Missing fields
    if not org.get("founded_year"):
        issues.append("no_year")
    if not (org.get("colors") or []):
        issues.append("no_colors")
    if not (org.get("aliases") or []):
        issues.append("no_aliases")
    if not org.get("membership_estimate"):
        issues.append("no_membership")

    if not issues:
        return 0.0, []

    # Weight by connectivity — stubs with many edges matter more
    connectivity_weight = max(1, edge_count)
    priority = len(issues) * connectivity_weight

    return priority, issues


def build_prompt(org: dict, issues: list[str], edge_count: int, raw_context: str = "") -> str:
    """Build the user prompt for enriching a specific org."""
    existing = []
    if org.get("description"):
        existing.append(f"Current description: {org['description']}")
    if org.get("founded_year"):
        existing.append(f"Founded: {org['founded_year']} ({org.get('founded_year_precision', 'unknown')} precision)")
    if org.get("colors"):
        existing.append(f"Colors: {', '.join(org['colors'])}")
    if org.get("aliases"):
        existing.append(f"Aliases: {', '.join(org['aliases'])}")
    if org.get("membership_estimate"):
        existing.append(f"Membership estimate: {org['membership_estimate']}")
    if org.get("nation_affiliation"):
        existing.append(f"Nation affiliation: {org['nation_affiliation']}")

    sources = org.get("sources") or []
    if sources:
        existing.append(f"Sources: {', '.join(s.get('title', s.get('url', '')) for s in sources)}")

    missing = []
    if "stub_desc" in issues or "short_desc" in issues:
        missing.append("description (2-3 factual sentences)")
    if "no_year" in issues:
        missing.append("founded_year + precision")
    if "no_colors" in issues:
        missing.append("colors")
    if "no_aliases" in issues:
        missing.append("aliases (alternative names, abbreviations)")
    if "no_membership" in issues:
        missing.append("membership_estimate")

    prompt = f"""Enrich this organization's profile:

Name: {org.get('name', '')}
Metro: {org.get('metro', 'Unknown')}
Lane: {org.get('lane', 'Unknown')}
Type: {org.get('type', 'street_gang')}
Edge count: {edge_count} connections in our graph

{chr(10).join(existing) if existing else 'No existing data.'}

Fields needed: {', '.join(missing)}
"""

    if raw_context:
        prompt += f"""
--- SOURCE MATERIAL (from our scraped archives) ---
The following passages mention this organization. Use them as your PRIMARY source of information.
Only use your own knowledge to fill gaps the source material doesn't cover.

{raw_context}
--- END SOURCE MATERIAL ---
"""

    prompt += "\nFill in what you can confidently determine from the source material above. Use null for anything not supported by the text."

    return prompt


# --- Tool definitions for the agentic loop ---

TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web for information about a gang/organization. Use this to find founding dates, membership estimates, colors, aliases, and history.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g. 'Latin Kings gang founded year membership')",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_url",
        "description": "Fetch and read the text content of a specific URL. Use this to read source pages that might have information about the org.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to fetch (e.g. 'https://en.wikipedia.org/wiki/Latin_Kings')",
                }
            },
            "required": ["url"],
        },
    },
]


def execute_web_search(query: str) -> str:
    """Execute a web search via DuckDuckGo HTML (no API key needed)."""
    try:
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (compatible; gang-guide-research/1.0)"},
            timeout=10.0,
            follow_redirects=True,
        )
        resp.raise_for_status()
        # Extract result snippets from HTML
        results = []
        for match in re.finditer(
            r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?'
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
            resp.text,
            re.DOTALL,
        ):
            url = match.group(1)
            title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            snippet = re.sub(r"<[^>]+>", "", match.group(3)).strip()
            if title and snippet:
                results.append(f"[{title}]({url})\n{snippet}")
            if len(results) >= 8:
                break

        if not results:
            # Fallback: try simpler extraction
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
            for s in snippets[:8]:
                clean = re.sub(r"<[^>]+>", "", s).strip()
                if clean:
                    results.append(clean)

        return "\n\n".join(results) if results else "No results found."
    except Exception as e:
        return f"Search failed: {e}"


def execute_fetch_url(url: str) -> str:
    """Fetch a URL and extract readable text content."""
    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; gang-guide-research/1.0)"},
            timeout=15.0,
            follow_redirects=True,
        )
        resp.raise_for_status()
        content = resp.text

        # Strip script/style
        content = re.sub(r"<script[^>]*>.*?</script>", " ", content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r"<style[^>]*>.*?</style>", " ", content, flags=re.DOTALL | re.IGNORECASE)
        # Strip HTML tags
        content = re.sub(r"<[^>]+>", " ", content)
        # Normalize whitespace
        content = re.sub(r"\s+", " ", content).strip()
        # Truncate to reasonable size
        return content[:6000] if len(content) > 6000 else content
    except Exception as e:
        return f"Fetch failed: {e}"


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool call and return the result."""
    if tool_name == "web_search":
        return execute_web_search(tool_input.get("query", ""))
    elif tool_name == "fetch_url":
        return execute_fetch_url(tool_input.get("url", ""))
    else:
        return f"Unknown tool: {tool_name}"


def call_llm(prompt: str, use_tools: bool = True, timeout: float = 90.0) -> dict | None:
    """Call the Kiro gateway with agentic tool-use loop.

    The LLM can request web searches and URL fetches to gather information.
    We execute the tools and feed results back until the LLM produces its final JSON answer.
    """
    messages = [{"role": "user", "content": prompt}]
    headers = {
        "x-api-key": KIRO_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    max_turns = 6  # safety cap on tool-use turns

    for turn in range(max_turns):
        payload = {
            "model": MODEL,
            "max_tokens": 2048,
            "temperature": 0.1,
            "thinking": {"type": "disabled"},
            "messages": messages,
            "system": SYSTEM_PROMPT,
        }
        if use_tools and turn < max_turns - 1:
            payload["tools"] = TOOLS

        try:
            resp = httpx.post(
                f"{KIRO_URL}/v1/messages",
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            resp.raise_for_status()
            body = resp.json()
        except (httpx.HTTPStatusError, httpx.TimeoutException) as e:
            print(f"    ✗ API error on turn {turn + 1}: {e}")
            return None

        stop_reason = body.get("stop_reason", "")
        content_blocks = body.get("content", [])

        # Check if the model wants to use a tool
        if stop_reason == "tool_use":
            # Add assistant message with all content blocks
            messages.append({"role": "assistant", "content": content_blocks})

            # Execute each tool call
            tool_results = []
            for block in content_blocks:
                if block.get("type") == "tool_use":
                    tool_name = block["name"]
                    tool_input = block.get("input", {})
                    tool_id = block["id"]
                    print(f"    🔧 {tool_name}({json.dumps(tool_input)[:80]})")
                    result = execute_tool(tool_name, tool_input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result[:4000],  # cap result size
                    })

            messages.append({"role": "user", "content": tool_results})
            continue

        # Model produced a final text response
        text_out = "".join(
            p.get("text", "") for p in content_blocks if p.get("type") == "text"
        )
        return _parse_json_response(text_out)

    print(f"    ✗ Exceeded max tool-use turns ({max_turns})")
    return None


def _parse_json_response(text_out: str) -> dict | None:
    """Parse a JSON response from LLM output, handling markdown fences etc."""
    text_out = text_out.strip()
    if not text_out:
        return None

    # Strip markdown fences if present
    if "```" in text_out:
        parts = text_out.split("```")
        for part in parts[1:]:
            candidate = part.lstrip("json\n").strip()
            if candidate.startswith("{"):
                text_out = candidate
                break

    if not text_out.startswith("{"):
        start_idx = text_out.find("{")
        if start_idx != -1:
            text_out = text_out[start_idx:]
        else:
            return None

    # Find closing brace
    depth = 0
    for i, ch in enumerate(text_out):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                text_out = text_out[: i + 1]
                break

    try:
        return json.loads(text_out)
    except json.JSONDecodeError:
        return None


def apply_enrichment(org: dict, enrichment: dict, issues: list[str]) -> dict:
    """Apply LLM enrichment to org, only upgrading weak fields."""
    changes = {}

    # Description: only upgrade if it was a stub/short
    if ("stub_desc" in issues or "short_desc" in issues) and enrichment.get("description"):
        new_desc = enrichment["description"]
        old_desc = org.get("description", "")
        if len(new_desc) > len(old_desc) + 20:  # meaningful improvement
            changes["description"] = new_desc

    # Founded year: only fill if missing
    if "no_year" in issues and enrichment.get("founded_year"):
        changes["founded_year"] = enrichment["founded_year"]
        if enrichment.get("founded_year_precision"):
            changes["founded_year_precision"] = enrichment["founded_year_precision"]

    # Colors: only fill if empty
    if "no_colors" in issues and enrichment.get("colors"):
        colors = [c.lower().strip() for c in enrichment["colors"] if c]
        if colors:
            changes["colors"] = colors

    # Aliases: only fill if empty
    if "no_aliases" in issues and enrichment.get("aliases"):
        aliases = [a.strip() for a in enrichment["aliases"] if a and len(a) < 60]
        if aliases:
            changes["aliases"] = aliases

    # Membership: only fill if missing
    if "no_membership" in issues and enrichment.get("membership_estimate"):
        est = enrichment["membership_estimate"]
        if isinstance(est, (int, float)) and est > 0:
            changes["membership_estimate"] = int(est)

    return changes


def save_org(org: dict, changes: dict) -> None:
    """Apply changes to org and write back to file."""
    filepath = org["_file"]
    # Reload fresh (without _file key)
    data = json.loads(Path(filepath).read_text())
    data.update(changes)
    Path(filepath).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Enrich weak org profiles via LLM")
    parser.add_argument("--limit", type=int, default=20, help="Max orgs to enrich (default: 20)")
    parser.add_argument("--dry-run", action="store_true", help="Score and rank only, don't call LLM")
    parser.add_argument("--org", type=str, default=None, help="Enrich a specific org by ID")
    parser.add_argument("--min-edges", type=int, default=0, help="Only enrich orgs with >= N edges")
    parser.add_argument("--model", type=str, default=None, help="Override model")
    parser.add_argument("--no-tools", action="store_true", help="Disable agentic tool use (no web search)")
    args = parser.parse_args()

    global MODEL
    if args.model:
        MODEL = args.model

    if not args.dry_run and not KIRO_KEY:
        print("ERROR: Set KIRO_GATEWAY_API_KEY or PROXY_API_KEY")
        raise SystemExit(1)

    orgs = load_orgs()
    edge_counts = load_edge_counts()

    # Score and rank
    scored = []
    for org_id, org in orgs.items():
        if args.org and org_id != args.org:
            continue
        ec = edge_counts.get(org_id, 0)
        if ec < args.min_edges:
            continue
        priority, issues = score_org(org, ec)
        if priority > 0:
            scored.append((priority, org, issues, ec))

    scored.sort(key=lambda x: -x[0])

    if args.dry_run:
        print(f"Top {min(args.limit, len(scored))} orgs needing enrichment:\n")
        print(f"{'Priority':>8}  {'Edges':>5}  {'Issues':>6}  Name")
        print(f"{'--------':>8}  {'-----':>5}  {'------':>6}  ----")
        for priority, org, issues, ec in scored[: args.limit]:
            print(f"{priority:8.0f}  {ec:5d}  {len(issues):6d}  {org['name']} ({', '.join(issues)})")
        print(f"\nTotal enrichable: {len(scored)}")
        return

    # Enrich
    batch = scored[: args.limit]
    print(f"Enriching {len(batch)} orgs...\n")

    enriched = 0
    skipped = 0
    for i, (priority, org, issues, ec) in enumerate(batch):
        print(f"  [{i+1}/{len(batch)}] {org['name']} ({ec} edges, {len(issues)} issues)")

        # Gather context from raw scraped data
        raw_context = gather_raw_context(org)
        if raw_context:
            print(f"    → found {len(raw_context)} chars of source context")
        else:
            print(f"    → no raw context found (using LLM knowledge only)")

        prompt = build_prompt(org, issues, ec, raw_context)
        result = call_llm(prompt, use_tools=not args.no_tools)

        if not result:
            skipped += 1
            continue

        changes = apply_enrichment(org, result, issues)
        if not changes:
            print(f"    → no improvements (LLM returned nulls)")
            skipped += 1
            continue

        save_org(org, changes)
        enriched += 1
        fields = ", ".join(changes.keys())
        print(f"    ✓ enriched: {fields}")

        # Small delay between calls
        if i < len(batch) - 1:
            time.sleep(0.5)

    print(f"\nDone: {enriched} enriched, {skipped} skipped")


if __name__ == "__main__":
    main()
