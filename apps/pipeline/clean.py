"""clean.py — verify and clean org profiles via LLM spot-checking.

Unlike enrich.py (which fills missing fields), clean.py spot-checks existing
data for accuracy. It flags potential fabrications, outdated info, description
quality issues, and incorrect field values — then either removes or corrects them.

Scoring priority:
  - Orgs with only LLM-generated or single-source data (high risk of hallucination)
  - Orgs with descriptions that look boilerplate or scraped
  - Orgs with precise dates but no supporting evidence
  - Orgs with membership estimates that seem implausible
  - Randomly sampled orgs for general spot-checking

Usage:
    python3 -m apps.pipeline.clean --dry-run --limit 20
    python3 -m apps.pipeline.clean --limit 10
    python3 -m apps.pipeline.clean --org org:rollin-60s-neighborhood-crips
    python3 -m apps.pipeline.clean --issues bad_desc
    python3 -m apps.pipeline.clean --lane chicago-folk --limit 20
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

from apps.pipeline.ignore import load_ignore_rules
from apps.pipeline.log import PipelineLogger

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_ORGS = ROOT / "data" / "orgs"
DATA_EDGES = ROOT / "data" / "edges.json"
DATA_RAW = ROOT / "data" / "raw"

KIRO_URL = os.environ.get("KIRO_GATEWAY_URL", "http://127.0.0.1:9000")
KIRO_KEY = os.environ.get("KIRO_GATEWAY_API_KEY", os.environ.get("PROXY_API_KEY", ""))
MODEL = os.environ.get("CLEAN_MODEL", "claude-sonnet-4.6")

MAX_CONTEXT_CHARS = 8000

SYSTEM_PROMPT = """You are a fact-checker and data quality auditor for a knowledge base of US criminal organizations.
Your job is NOT to add new information — it is to verify and correct what's already there.

You have access to tools:
- web_search: Search the web to verify a claim about this organization
- fetch_url: Read a specific URL to check if it supports the current data

WORKFLOW:
1. Check the source material provided in the prompt (from our scraped archives) first.
2. Use web_search to verify any suspicious or unverified fields.
3. Use fetch_url to read specific pages that may confirm or deny the data.
4. Respond with a JSON verdict on each field that looks problematic.

WHAT TO LOOK FOR:
- Descriptions that are factually wrong, contain HTML entities, slurs, or scraped junk
- Descriptions that are generic boilerplate ("is a street gang based in X")
- Founded years that seem wrong (e.g. a Crip set founded before 1969)
- Membership estimates that are implausibly large or small given the org's profile
- Colors that are wrong for this org type or affiliation
- Symbols that are wrong or don't match known identifiers
- Aliases that are wrong, too long, or are actually the org's full name
- Sources with URLs that 404, are irrelevant, or don't mention this org

RESPONSE FORMAT:
Respond with ONLY valid JSON:
{
  "verdict": "clean" | "issues_found",
  "description": "corrected description or null to keep existing or 'REMOVE' to clear",
  "founded_year": corrected year as integer or null to keep existing,
  "founded_year_precision": "exact|circa|decade|estimate" or null to keep existing,
  "colors": ["corrected", "colors"] or null to keep or [] to clear,
  "aliases": ["corrected", "aliases"] or null to keep or [] to clear,
  "membership_estimate": corrected integer or null to keep or 0 to clear,
  "symbols": ["corrected", "symbols"] or null to keep or [] to clear,
  "sources": [{"url": "...", "title": "..."}] or null to keep,
  "notes": "brief explanation of what was wrong and what you changed"
}

If the data looks correct, return {"verdict": "clean", "notes": "all fields verified"} with everything else null.
Never fabricate corrections — only fix what you can verify is actually wrong.
Use 0 for membership_estimate to signal it should be removed (null means keep existing).
Use [] for arrays to signal they should be cleared."""


# ── Issue detection ────────────────────────────────────────────────────────────


def detect_issues(org: dict, edge_count: int) -> list[str]:
    """Detect data quality issues that warrant a clean pass.

    Returns list of issue codes sorted by severity.
    """
    issues = []
    desc = org.get("description", "") or ""
    name = org.get("name", "")
    lane = org.get("lane", "") or ""
    org_type = org.get("type", "") or ""

    # --- Description issues ---
    boilerplate_patterns = [
        r"^[A-Z].* is a (street gang|criminal gang|gang) (based in|located in|from|operating in)",
        r"^[A-Z].* is an? (African-American|Latino|Hispanic|White|Asian) (street )?gang",
    ]
    if any(re.match(p, desc) for p in boilerplate_patterns) and len(desc) < 150:
        issues.append("boilerplate_desc")

    if re.search(r"&amp;|&lt;|&gt;|&#\d+;|<[a-z]+>", desc):
        issues.append("html_in_desc")

    # Descriptions that are implausibly long or contain metadata junk
    if len(desc) > 800:
        issues.append("desc_too_long")

    # --- Founded year issues ---
    year = org.get("founded_year")
    precision = org.get("founded_year_precision", "") or ""
    if year:
        # Crip/Blood/Piru sets can't predate the movements
        name_lower = name.lower()
        if ("crip" in name_lower or "crip" in lane) and year < 1969:
            issues.append("impossible_year")
        if ("piru" in name_lower or "blood" in name_lower) and "blood" in lane and year < 1969:
            issues.append("impossible_year")
        # Decade precision with a very specific year (e.g. founded_year=1974, precision=decade)
        if precision == "decade" and year % 10 != 0:
            issues.append("precision_mismatch")
        # Exact precision with a round year is suspicious without evidence
        if precision == "exact" and year % 5 == 0:
            issues.append("suspicious_exact_year")

    # --- Membership estimate plausibility ---
    est = org.get("membership_estimate")
    if est:
        # Tiny obscure sets with huge membership claims
        if est > 5000 and edge_count < 10:
            issues.append("implausible_membership")
        # Street gang claiming more than 50k
        if est > 50000 and org_type == "street_gang":
            issues.append("implausible_membership")

    # --- Source quality ---
    sources = org.get("sources") or []
    bare_domain_pattern = re.compile(r"^(https?://)?(www\.)?[\w.-]+\.[a-z]{2,}/?$")
    for s in sources:
        title = s.get("title", "") or ""
        if bare_domain_pattern.match(title):
            issues.append("bare_source_title")
            break
        if len(title) < 5:
            issues.append("bare_source_title")
            break

    # --- Single source with precise data (high fabrication risk) ---
    if len(sources) <= 1 and precision == "exact" and est and est > 100:
        issues.append("single_source_precise")

    # --- General spot-check (low priority, random sampling for coverage) ---
    # Flag ~1 in 20 orgs for general verification even if no specific issue
    import hashlib

    h = int(hashlib.md5(org.get("id", "").encode()).hexdigest(), 16)
    if h % 20 == 0 and not issues:
        issues.append("spot_check")

    return issues


def score_org(org: dict, edge_count: int) -> tuple[float, list[str]]:
    """Score an org's clean priority. Higher = more urgently needs verification."""
    issues = detect_issues(org, edge_count)
    if not issues:
        return 0.0, []

    # Weight severity
    severity = {
        "impossible_year": 100,
        "html_in_desc": 80,
        "precision_mismatch": 60,
        "implausible_membership": 50,
        "suspicious_exact_year": 30,
        "single_source_precise": 25,
        "boilerplate_desc": 20,
        "bare_source_title": 15,
        "desc_too_long": 10,
        "spot_check": 5,
    }
    base_score = sum(severity.get(i, 10) for i in issues)
    # Weight by connectivity — errors on high-connectivity orgs matter more
    connectivity_weight = max(1, edge_count) / 10
    priority = base_score * max(1.0, connectivity_weight)

    return priority, issues


# ── Raw context (shared with enrich.py) ───────────────────────────────────────


def gather_raw_context(org: dict) -> str:
    """Search data/raw/ for mentions of this org and return relevant snippets."""
    name = org.get("name", "")
    aliases = org.get("aliases") or []
    search_terms = [name, *list(aliases)]
    search_terms = list({t for t in search_terms if t and len(t) > 3})
    if not search_terms:
        return ""

    pattern = "|".join(re.escape(t) for t in search_terms[:5])
    snippets = []
    total_chars = 0

    try:
        result = subprocess.run(
            ["rg", "-il", "-i", "--max-count=1", pattern, str(DATA_RAW)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        matching_files = result.stdout.strip().split("\n") if result.stdout.strip() else []
    except (FileNotFoundError, subprocess.TimeoutExpired):
        try:
            result = subprocess.run(
                ["grep", "-ril", "--include=*.txt", "--include=*.html", pattern, str(DATA_RAW)],
                capture_output=True,
                text=True,
                timeout=15,
            )
            matching_files = result.stdout.strip().split("\n") if result.stdout.strip() else []
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ""

    for filepath in matching_files[:10]:
        if not filepath or not Path(filepath).exists():
            continue
        try:
            content = Path(filepath).read_text(errors="ignore")
            content = re.sub(r"<script[^>]*>.*?</script>", " ", content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r"<style[^>]*>.*?</style>", " ", content, flags=re.DOTALL | re.IGNORECASE)
            for para in re.split(r"\n{2,}|<p>|</p>|<br\s*/?>", content):
                para_lower = para.lower()
                if any(t.lower() in para_lower for t in search_terms[:3]):
                    clean = re.sub(r"<[^>]+>", " ", para).strip()
                    clean = re.sub(r"\s+", " ", clean)
                    if any(junk in clean for junk in ["{", "}", "function(", "var ", "const ", "sourceURL="]):
                        continue
                    if 50 < len(clean) < 2000:
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
    seen: set[str] = set()
    unique = []
    for s in snippets:
        key = s[:80].lower()
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return "\n\n".join(unique[:15])


# ── Prompt building ───────────────────────────────────────────────────────────


def build_clean_prompt(org: dict, issues: list[str], edge_count: int, raw_context: str = "") -> str:
    """Build the verification prompt for a specific org."""
    fields_summary = []
    if org.get("description"):
        fields_summary.append(f"Description: {org['description']}")
    if org.get("founded_year"):
        fields_summary.append(
            f"Founded: {org['founded_year']} (precision: {org.get('founded_year_precision', 'unknown')})"
        )
    if org.get("colors"):
        fields_summary.append(f"Colors: {', '.join(org['colors'])}")
    if org.get("aliases"):
        fields_summary.append(f"Aliases: {', '.join(org['aliases'])}")
    if org.get("membership_estimate"):
        fields_summary.append(f"Membership estimate: {org['membership_estimate']}")
    if org.get("symbols"):
        fields_summary.append(f"Symbols: {', '.join(org['symbols'])}")
    sources = org.get("sources") or []
    if sources:
        source_list = "\n".join(f"  - {s.get('title','?')} ({s.get('url','?')})" for s in sources[:5])
        fields_summary.append(f"Sources:\n{source_list}")

    issue_notes = []
    if "impossible_year" in issues:
        issue_notes.append(
            f"⚠ SUSPICIOUS: founded_year={org.get('founded_year')} seems too early for this type of org — verify."
        )
    if "precision_mismatch" in issues:
        issue_notes.append(
            f"⚠ SUSPICIOUS: precision='{org.get('founded_year_precision')}' but year={org.get('founded_year')} doesn't match (decade precision should be a round decade year)."
        )
    if "suspicious_exact_year" in issues:
        issue_notes.append(
            f"⚠ SUSPICIOUS: founded_year={org.get('founded_year')} marked 'exact' but is a round number — verify exactness."
        )
    if "implausible_membership" in issues:
        issue_notes.append(
            f"⚠ SUSPICIOUS: membership_estimate={org.get('membership_estimate')} seems implausible for this org's profile ({edge_count} connections)."
        )
    if "boilerplate_desc" in issues:
        issue_notes.append("⚠ QUALITY: Description looks like generic boilerplate — improve with specific facts if possible.")
    if "html_in_desc" in issues:
        issue_notes.append("⚠ QUALITY: Description contains HTML entities or tags — clean up.")
    if "bare_source_title" in issues:
        issue_notes.append("⚠ QUALITY: One or more sources have bare domain names as titles — fix with proper titles.")
    if "single_source_precise" in issues:
        issue_notes.append(
            "⚠ RISK: High-precision data (exact year, membership) with only one source — verify it's real, not fabricated."
        )
    if "desc_too_long" in issues:
        issue_notes.append("⚠ QUALITY: Description is too long — trim to 2-4 factual sentences.")
    if "spot_check" in issues:
        issue_notes.append("ℹ General spot-check — verify the overall profile looks accurate.")

    prompt = f"""Verify and clean this organization's profile:

Name: {org.get("name", "")}
Metro: {org.get("metro", "Unknown")}
Lane: {org.get("lane", "Unknown")}
Type: {org.get("type", "street_gang")}
Graph connections: {edge_count}

--- CURRENT DATA ---
{chr(10).join(fields_summary) if fields_summary else "No data fields."}

--- FLAGS ---
{chr(10).join(issue_notes)}
"""

    if raw_context:
        prompt += f"""
--- SOURCE MATERIAL (from our scraped archives) ---
Use this as ground truth. If the current data contradicts this, correct it.

{raw_context}
--- END SOURCE MATERIAL ---
"""

    prompt += """
Your task: verify the flagged fields above. Use web_search and fetch_url to check claims.
Only change what you can confirm is wrong. Return your verdict as JSON."""

    return prompt


# ── LLM + tools (identical to enrich.py) ──────────────────────────────────────

TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web to verify a claim about a gang/organization.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        },
    },
    {
        "name": "fetch_url",
        "description": "Fetch a URL to read its content for fact-checking.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "URL to fetch"}},
            "required": ["url"],
        },
    },
]


def execute_web_search(query: str) -> str:
    """Multi-source search: Brave + DuckDuckGo + Wikipedia REST + CourtListener."""
    from apps.pipeline.search import multi_search
    return multi_search(query)


def execute_fetch_url(url: str) -> str:
    """Fetch URL with Wikipedia REST API optimization for Wikipedia pages."""
    from apps.pipeline.search import fetch_url
    return fetch_url(url)


def call_llm(prompt: str, use_tools: bool = True, timeout: float = 120.0, logger: "PipelineLogger | None" = None) -> dict | None:
    """Call the LLM with agentic tool-use loop."""
    messages = [{"role": "user", "content": prompt}]
    headers = {
        "x-api-key": KIRO_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    max_turns = 10

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
            resp = httpx.post(f"{KIRO_URL}/v1/messages", headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
            body = resp.json()
        except (httpx.HTTPStatusError, httpx.TimeoutException) as e:
            print(f"    ✗ API error on turn {turn + 1}: {e}")
            return None

        stop_reason = body.get("stop_reason", "")
        content_blocks = body.get("content", [])

        if stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": content_blocks})
            tool_results = []
            for block in content_blocks:
                if block.get("type") == "tool_use":
                    tool_name = block["name"]
                    tool_input = block.get("input", {})
                    tool_id = block["id"]
                    print(f"    🔧 {tool_name}({json.dumps(tool_input)[:80]})")
                    if tool_name == "web_search":
                        result = execute_web_search(tool_input.get("query", ""))
                    elif tool_name == "fetch_url":
                        result = execute_fetch_url(tool_input.get("url", ""))
                    else:
                        result = f"Unknown tool: {tool_name}"
                    if logger:
                        logger.tool_call(tool_name, tool_input, len(result))
                    tool_results.append({"type": "tool_result", "tool_use_id": tool_id, "content": result[:4000]})
            messages.append({"role": "user", "content": tool_results})
            continue

        text_out = "".join(p.get("text", "") for p in content_blocks if p.get("type") == "text")
        return _parse_json_response(text_out)

    print(f"    ✗ Exceeded max tool-use turns ({max_turns})")
    return None


def _parse_json_response(text_out: str) -> dict | None:
    """Parse JSON from LLM output."""
    text_out = text_out.strip()
    if not text_out:
        return None
    if "```" in text_out:
        for part in text_out.split("```")[1:]:
            candidate = part.lstrip("json\n").strip()
            if candidate.startswith("{"):
                text_out = candidate
                break
    if not text_out.startswith("{"):
        start = text_out.find("{")
        if start == -1:
            return None
        text_out = text_out[start:]
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


# ── Apply corrections ─────────────────────────────────────────────────────────


def apply_corrections(org: dict, verdict: dict, issues: list[str]) -> dict:
    """Apply LLM-verified corrections to an org.

    More conservative than enrich — only applies changes the LLM
    explicitly verified as wrong. Never removes sourced data without a reason.
    """
    if verdict.get("verdict") == "clean":
        return {}

    changes = {}
    notes = verdict.get("notes", "")

    VALID_COLORS = {
        "red", "blue", "green", "black", "white", "yellow", "orange", "purple",
        "brown", "gold", "silver", "gray", "grey", "pink", "maroon", "burgundy",
        "tan", "beige", "khaki", "navy", "teal", "crimson",
    }

    # Description
    new_desc = verdict.get("description")
    if new_desc is not None:
        if new_desc == "REMOVE":
            # Only allow removal if the org has a replacement description coming from another field
            # Never clear without replacement — would create a lint error
            pass  # skip removal; log the intent but don't clear
        elif isinstance(new_desc, str) and len(new_desc) > 30 and "<" not in new_desc:
            changes["description"] = new_desc

    # Founded year
    new_year = verdict.get("founded_year")
    if new_year is not None and isinstance(new_year, (int, float)):
        year_int = int(new_year)
        if 1800 <= year_int <= 2025:
            changes["founded_year"] = year_int
    new_prec = verdict.get("founded_year_precision")
    if new_prec in ("exact", "circa", "decade", "estimate"):
        changes["founded_year_precision"] = new_prec

    # Colors
    new_colors = verdict.get("colors")
    if new_colors is not None:
        if new_colors == []:
            changes["colors"] = []
        elif isinstance(new_colors, list):
            valid = [c.lower().strip() for c in new_colors if isinstance(c, str) and c.lower().strip() in VALID_COLORS]
            if valid:
                changes["colors"] = valid

    # Aliases
    new_aliases = verdict.get("aliases")
    if new_aliases is not None:
        if new_aliases == []:
            changes["aliases"] = []
        elif isinstance(new_aliases, list):
            def _title_alias(a: str) -> str:
                """Title-case an alias, preserving ALL-CAPS abbreviations."""
                if a.isupper() and len(a) <= 6:
                    return a  # pure abbreviations like GTS, OHC
                words = a.strip().split()
                result = []
                for w in words:
                    if w.isupper() and len(w) <= 6:
                        result.append(w)
                    else:
                        result.append(w[0].upper() + w[1:] if w else w)
                return " ".join(result)

            cleaned = [_title_alias(a) for a in new_aliases if isinstance(a, str) and 2 < len(a.strip()) < 60]
            if cleaned:
                changes["aliases"] = cleaned

    # Membership estimate: 0 means remove, null means keep
    new_est = verdict.get("membership_estimate")
    if new_est is not None:
        if new_est == 0:
            changes["membership_estimate"] = None
        elif isinstance(new_est, (int, float)) and 5 <= new_est <= 100000:
            changes["membership_estimate"] = int(new_est)

    # Symbols
    new_symbols = verdict.get("symbols")
    if new_symbols is not None:
        if new_symbols == []:
            changes["symbols"] = []
        elif isinstance(new_symbols, list):
            def _title_word(w: str) -> str:
                if w.isupper() and len(w) <= 6:
                    return w
                return w[0].upper() + w[1:] if w else w

            cleaned = [
                " ".join(_title_word(w) for w in s.strip().split())
                for s in new_symbols
                if isinstance(s, str) and 2 < len(s.strip()) < 80
            ]
            if cleaned:
                changes["symbols"] = cleaned

    # Sources: only accept if all have valid https URLs and titles
    new_sources = verdict.get("sources")
    if new_sources is not None and isinstance(new_sources, list):
        valid_sources = []
        for s in new_sources:
            if not isinstance(s, dict):
                continue
            url = (s.get("url") or "").strip()
            title = (s.get("title") or "").strip()
            if url.startswith("https://") and 5 <= len(title) <= 200:
                valid_sources.append({"url": url, "title": title})
        if valid_sources:
            changes["sources"] = valid_sources

    return changes


def save_org(org: dict, changes: dict) -> None:
    """Apply changes and write back to file."""
    filepath = org["_file"]
    data = json.loads(Path(filepath).read_text())
    for k, v in changes.items():
        if v is None:
            data.pop(k, None)
        else:
            data[k] = v
    Path(filepath).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def load_orgs() -> dict[str, dict]:
    orgs = {}
    for f in sorted(DATA_ORGS.glob("*.json")):
        org = json.loads(f.read_text())
        org["_file"] = str(f)
        orgs[org["id"]] = org
    return orgs


def load_edge_counts() -> Counter:
    edges = json.loads(DATA_EDGES.read_text())
    counts: Counter = Counter()
    for e in edges:
        counts[e["source"]] += 1
        counts[e["target"]] += 1
    return counts


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify and clean org profiles via LLM spot-checking")
    parser.add_argument("--limit", type=int, default=20, help="Max orgs to clean (default: 20)")
    parser.add_argument("--dry-run", action="store_true", help="Show priority ranking without calling LLM")
    parser.add_argument("--org", type=str, default=None, help="Clean a specific org by ID")
    parser.add_argument("--min-edges", type=int, default=0, help="Only clean orgs with >= N edges")
    parser.add_argument("--lane", type=str, default=None, help="Only clean orgs in a specific lane")
    parser.add_argument(
        "--issues",
        type=str,
        default=None,
        help="Only clean orgs with a specific issue code (e.g. impossible_year, boilerplate_desc)",
    )
    parser.add_argument("--model", type=str, default=None, help="Override LLM model")
    parser.add_argument("--no-tools", action="store_true", help="Disable agentic web search tools")
    args = parser.parse_args()

    global MODEL
    if args.model:
        MODEL = args.model

    if not args.dry_run and not KIRO_KEY:
        print("ERROR: Set KIRO_GATEWAY_API_KEY or PROXY_API_KEY")
        raise SystemExit(1)

    orgs = load_orgs()
    edge_counts = load_edge_counts()
    ignore = load_ignore_rules()

    # Score and rank by cleaning priority
    scored = []
    for org_id, org in orgs.items():
        if args.org and org_id != args.org:
            continue
        if args.lane and org.get("lane") != args.lane:
            continue
        ec = edge_counts.get(org_id, 0)
        if ec < args.min_edges:
            continue
        if ignore.should_skip_clean(org_id) or ignore.should_skip_org(org_id):
            continue
        priority, issues = score_org(org, ec)
        if args.issues and args.issues not in issues:
            continue
        if priority > 0:
            scored.append((priority, org, issues, ec))

    scored.sort(key=lambda x: -x[0])

    if args.dry_run:
        print(f"Top {min(args.limit, len(scored))} orgs needing verification:\n")
        print(f"{'Priority':>8}  {'Edges':>5}  {'Issues':>6}  Name")
        print(f"{'--------':>8}  {'-----':>5}  {'------':>6}  ----")
        for priority, org, issues, ec in scored[: args.limit]:
            print(f"{priority:8.0f}  {ec:5d}  {len(issues):6d}  {org['name']} ({', '.join(issues)})")
        print(f"\nTotal needing clean: {len(scored)}")
        return

    batch = scored[: args.limit]
    print(f"Cleaning {len(batch)} orgs...\n")

    cleaned = 0
    clean_count = 0
    skipped = 0

    with PipelineLogger("clean", source=args.org or "batch", limit=args.limit, model=MODEL) as log:
        log.info("clean_started", batch_size=len(batch), total_flagged=len(scored))

        for i, (priority, org, issues, ec) in enumerate(batch):
            print(f"  [{i + 1}/{len(batch)}] {org['name']} ({ec} edges) [{', '.join(issues)}]")

            raw_context = gather_raw_context(org)
            if raw_context:
                print(f"    → found {len(raw_context)} chars of source context")
            else:
                print("    → no raw context found (LLM + web search only)")

            prompt = build_clean_prompt(org, issues, ec, raw_context)
            verdict = call_llm(prompt, use_tools=not args.no_tools, logger=log)

            if not verdict:
                skipped += 1
                log.warn("llm_no_result", org=org["id"])
                continue

            if verdict.get("verdict") == "clean":
                print(f"    ✓ clean: {verdict.get('notes', '')[:80]}")
                clean_count += 1
                log.decision("org_verified_clean", org=org["id"], notes=verdict.get("notes", ""))
                continue

            changes = apply_corrections(org, verdict, issues)
            notes = verdict.get("notes", "")

            if not changes:
                print(f"    ℹ issues found but no actionable changes: {notes[:80]}")
                skipped += 1
                log.decision("clean_no_changes", org=org["id"], notes=notes)
                continue

            save_org(org, changes)
            cleaned += 1
            fields = ", ".join(changes.keys())
            print(f"    ✓ corrected: {fields}")
            if notes:
                print(f"    ℹ {notes[:100]}")
            log.action(
                "org_cleaned",
                org=org["id"],
                issues=issues,
                fields=list(changes.keys()),
                changes=changes,
                notes=notes,
            )

            if i < len(batch) - 1:
                time.sleep(0.5)

        log.info("clean_completed", cleaned=cleaned, verified_clean=clean_count, skipped=skipped)

    print(f"\nDone: {cleaned} corrected, {clean_count} verified clean, {skipped} skipped")


if __name__ == "__main__":
    main()
