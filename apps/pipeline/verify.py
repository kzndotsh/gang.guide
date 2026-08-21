"""verify.py — post-adjudication web verification of suspicious claims.

Runs between adjudicate and merge. Identifies edges with weak evidence
or suspicious data, uses web search to fact-check, and marks or removes
unverifiable claims.

Writes results back into adjudicated.json in-place:
  - "unsupported" edges with high confidence are removed
  - "uncertain" edges are flagged with verify_uncertain=True (apply.py will skip them)
  - Org-level field issues (metro/lane mismatch, impossible years) are flagged as warnings

Usage:
    python3 -m apps.pipeline.verify --source unitedgangs --dry-run
    python3 -m apps.pipeline.verify --source unitedgangs --limit 50
"""

import argparse
import json
import os
import re
import time
from pathlib import Path

import httpx

from apps.pipeline.ignore import load_ignore_rules
from apps.pipeline.log import PipelineLogger

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_EXTRACTED = ROOT / "data" / "extracted"
DATA_ORGS = ROOT / "data" / "orgs"

KIRO_URL = os.environ.get("KIRO_GATEWAY_URL", "http://127.0.0.1:9000")
KIRO_KEY = os.environ.get("KIRO_GATEWAY_API_KEY", os.environ.get("PROXY_API_KEY", ""))
MODEL = os.environ.get("VERIFY_MODEL", "claude-sonnet-4.6")

MAX_TOOL_TURNS = 8  # raised from 4 — gives LLM enough turns to actually find evidence

SYSTEM_PROMPT = """You are a fact-checker for a criminal organization knowledge graph. You verify claims about gang relationships using web search results.

You have access to:
- web_search: Search the web for information to verify a claim
- fetch_url: Fetch a specific URL to read its content

Your job is to determine if a claimed relationship between organizations is SUPPORTED or UNSUPPORTED by available evidence.

IMPORTANT: Use multiple searches. Do not give up after one inconclusive result. Try:
1. Searching for both org names together
2. Searching for the relationship type specifically
3. Fetching any relevant Wikipedia or news pages

Respond with ONLY valid JSON:
{
  "verdict": "supported" | "unsupported" | "uncertain",
  "confidence": 0.0-1.0,
  "reason": "Brief explanation of why"
}

Use "uncertain" only when you genuinely cannot find relevant evidence after thorough searching.
Use "unsupported" when evidence actively contradicts the claim, or when the claim is implausible
and no supporting evidence exists after thorough searching.
"""

TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web to verify a claim about gang relationships, founding dates, or affiliations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to verify the claim",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_url",
        "description": "Fetch and read a specific URL to check its content for verification.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to fetch and read",
                }
            },
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


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool call."""
    if tool_name == "web_search":
        return execute_web_search(tool_input.get("query", ""))
    elif tool_name == "fetch_url":
        return execute_fetch_url(tool_input.get("url", ""))
    return f"Unknown tool: {tool_name}"


def load_org_metro(org_id: str) -> str | None:
    """Look up an org's metro from data/orgs/ by ID."""
    slug = org_id.replace("org:", "")
    f = DATA_ORGS / f"{slug}.json"
    if f.exists():
        try:
            d = json.loads(f.read_text())
            return d.get("metro") or None
        except (json.JSONDecodeError, OSError):
            return None
    return None


def identify_suspicious_edges(adjudicated: dict) -> list[dict]:
    """Find edges that should be fact-checked.

    Returns list of dicts sorted by priority (highest first).
    Each item: {edge, subject, reasons, priority}
    """
    suspicious = []
    edges = adjudicated.get("edges", [])
    subject = adjudicated.get("subject_org", "Unknown")
    subject_metro = adjudicated.get("metro", "") or ""

    for edge in edges:
        # Skip edges already flagged as verified uncertain (re-runs shouldn't re-check)
        if edge.get("verify_uncertain"):
            continue

        evidence = edge.get("evidence") or (edge.get("citations") or [{}])[0].get("evidence", "")
        target = edge.get("target", "")
        edge_type = edge.get("type", "")
        reasons = []

        # --- Evidence quality issues ---
        if len(evidence) < 30:
            reasons.append("very_short_evidence")
        elif re.match(r"^(Allies|Rivals|Allies include|Rivals include)", evidence, re.I) and len(evidence) < 80:
            reasons.append("list_only_evidence")

        # Hearsay language
        if re.search(r"\b(said|claims|reportedly|allegedly|rumored)\b", evidence, re.I):
            reasons.append("hearsay_language")

        # --- Edge type checks ---
        # Only flag spin_off if evidence is weak (long detailed evidence = probably fine)
        if edge_type == "spin_off" and len(evidence) < 100:
            reasons.append("weak_spin_off")

        # Member_of mafia claims are prone to hallucination
        if edge_type == "member_of" and "mafia" in target.lower():
            reasons.append("mafia_membership_claim")

        # --- Cross-metro heuristic (new) ---
        # Alliance/rivalry between orgs in different cities is suspicious.
        # National umbrella orgs (Crips, Folk Nation, etc.) are exempt.
        if edge_type in ("alliance", "rivalry") and subject_metro:
            NATIONAL_ORGS = {
                "org:crips", "org:bloods", "org:folk-nation", "org:people-nation",
                "org:surenos", "org:nortenos", "org:united-blood-nation",
                "org:mexican-mafia", "org:aryan-brotherhood",
            }
            # Resolve target to org_id if possible (simple slug guess)
            target_slug = re.sub(r"[^a-z0-9]+", "-", target.lower()).strip("-")
            target_org_id = f"org:{target_slug}"

            if target_org_id not in NATIONAL_ORGS and subject not in NATIONAL_ORGS:
                target_metro = load_org_metro(target_org_id)
                if (
                    target_metro
                    and target_metro != subject_metro
                    and target_metro not in ("United States", "National")
                    and subject_metro not in ("United States", "National")
                ):
                    reasons.append(f"cross_metro:{subject_metro}↔{target_metro}")

        if reasons:
            suspicious.append(
                {
                    "edge": edge,
                    "subject": subject,
                    "reasons": reasons,
                    "priority": len(reasons),
                }
            )

    suspicious.sort(key=lambda x: -x["priority"])
    return suspicious


def check_org_fields(adjudicated: dict) -> list[str]:
    """Check extracted org-level fields for obvious problems.

    Returns list of warning strings. These are printed but don't block the pipeline.
    """
    warnings = []
    subject = adjudicated.get("subject_org", "Unknown")
    metro = adjudicated.get("metro", "") or ""
    lane = adjudicated.get("org_lane", "") or ""
    year = adjudicated.get("founded_year")

    # Metro/lane consistency
    LANE_METRO = {
        "california-": ["Los Angeles", "San Francisco", "California", "San Diego",
                         "Sacramento", "Compton", "Long Beach", "Pomona", "Inglewood",
                         "Orange County", "Inland Empire"],
        "chicago-": ["Chicago"],
        "detroit": ["Detroit"],
        "new-york": ["New York"],
        "historical-east": ["New York", "Boston", "Philadelphia", "Baltimore",
                             "Washington", "Newark", "Hartford"],
    }
    for prefix, valid_metros in LANE_METRO.items():
        if lane.startswith(prefix) and metro and metro not in valid_metros:
            warnings.append(f"  ⚠ org-field: '{subject}' has lane='{lane}' but metro='{metro}' — likely wrong metro")
            break

    # Impossible founding years for specific movements
    name_lower = subject.lower()
    if year:
        if ("crip" in name_lower or "crip" in lane) and year < 1969:
            warnings.append(f"  ⚠ org-field: '{subject}' founded_year={year} predates Crips movement (1969)")
        if ("piru" in name_lower or "blood" in name_lower) and "blood" in lane and year < 1969:
            warnings.append(f"  ⚠ org-field: '{subject}' founded_year={year} predates Bloods movement (1969)")
        if year < 1800 or year > 2030:
            warnings.append(f"  ⚠ org-field: '{subject}' has implausible founded_year={year}")

    return warnings


def verify_edge(edge: dict, subject: str) -> dict | None:
    """Use LLM + web search to verify a single edge claim.

    Returns verdict dict: {verdict, confidence, reason} or None on API failure.
    """
    target = edge.get("target", "")
    edge_type = edge.get("type", "")
    evidence = edge.get("evidence") or (edge.get("citations") or [{}])[0].get("evidence", "")
    reasons = edge.get("_verify_reasons", [])

    # Build a focused prompt based on the specific concern
    concern_notes = ""
    if any("cross_metro" in r for r in reasons):
        metros = [r.split(":")[1] for r in reasons if "cross_metro" in r]
        concern_notes = f"\n⚠ CONCERN: These two orgs appear to be in different cities ({', '.join(metros)}). Verify this relationship is real and not a resolution error."
    if "weak_spin_off" in reasons:
        concern_notes += "\n⚠ CONCERN: spin_off claims are frequently fabricated. Verify this is a documented organizational split."
    if "hearsay_language" in reasons:
        concern_notes += "\n⚠ CONCERN: The evidence contains hearsay language. Check if this is a documented fact."

    prompt = f"""Verify this claimed relationship:

Subject org: {subject}
Target org: {target}
Relationship type: {edge_type}
Evidence given: "{evidence}"
{concern_notes}

Search for both organizations and their relationship. Try multiple searches — don't give up after one result.
Then give your verdict as JSON."""

    messages = [{"role": "user", "content": prompt}]
    headers = {
        "x-api-key": KIRO_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    for turn in range(MAX_TOOL_TURNS):
        payload = {
            "model": MODEL,
            "max_tokens": 1024,
            "temperature": 0.0,
            "thinking": {"type": "disabled"},
            "messages": messages,
            "system": SYSTEM_PROMPT,
        }
        if turn < MAX_TOOL_TURNS - 1:
            payload["tools"] = TOOLS

        try:
            resp = httpx.post(
                f"{KIRO_URL}/v1/messages",
                headers=headers,
                json=payload,
                timeout=60.0,  # raised from 30s
            )
            resp.raise_for_status()
            body = resp.json()
        except (httpx.HTTPStatusError, httpx.TimeoutException) as e:
            print(f"      ✗ API error: {e}")
            return None

        content_blocks = body.get("content", [])
        stop_reason = body.get("stop_reason", "")

        if stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": content_blocks})
            tool_results = []
            for block in content_blocks:
                if block.get("type") == "tool_use":
                    tool_name = block["name"]
                    tool_input = block.get("input", {})
                    print(f"      🔍 {tool_name}: {json.dumps(tool_input)[:70]}")
                    result = execute_tool(tool_name, tool_input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block["id"],
                            "content": result[:3000],
                        }
                    )
            messages.append({"role": "user", "content": tool_results})
            continue

        # Final text response — parse JSON verdict
        text_out = "".join(p.get("text", "") for p in content_blocks if p.get("type") == "text").strip()
        try:
            if not text_out.startswith("{"):
                idx = text_out.find("{")
                if idx != -1:
                    text_out = text_out[idx:]
            depth = 0
            for i, ch in enumerate(text_out):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        text_out = text_out[: i + 1]
                        break
            return json.loads(text_out)
        except (json.JSONDecodeError, ValueError):
            return None

    return None


def process_source(source: str, limit: int = 50, dry_run: bool = False, min_confidence: float = 0.7):
    """Verify suspicious edges in adjudicated results for a source."""
    source_dir = DATA_EXTRACTED / source
    if not source_dir.exists():
        print(f"No extractions for {source}")
        return

    ignore = load_ignore_rules()

    total_checked = 0
    total_verified = 0
    total_rejected = 0
    total_uncertain = 0
    total_flagged = 0

    with PipelineLogger("verify", source=source, limit=limit, min_confidence=min_confidence, model=MODEL) as log:
        log.info("verification_started", source=source, limit=limit)

        for page_dir in sorted(source_dir.iterdir()):
            if not page_dir.is_dir():
                continue

            adj_path = page_dir / "adjudicated.json"
            if not adj_path.exists():
                continue

            adjudicated = json.loads(adj_path.read_text(encoding="utf-8"))
            subject = adjudicated.get("subject_org", page_dir.name)

            # Org-level field checks (always run, just prints warnings)
            field_warnings = check_org_fields(adjudicated)
            for w in field_warnings:
                print(w)
                log.warn("org_field_issue", subject=subject, warning=w)

            suspicious = identify_suspicious_edges(adjudicated)

            if not suspicious:
                continue

            if dry_run:
                for s in suspicious[:3]:
                    edge = s["edge"]
                    print(
                        f"  [{subject}] {edge.get('type', '?')} → {edge.get('target', '?')} "
                        f"({', '.join(s['reasons'])})"
                    )
                total_checked += len(suspicious)
                continue

            modified = False

            for s in suspicious:
                if total_checked >= limit:
                    break

                edge = s["edge"]
                edge_type = edge.get("type", "")
                edge_target = edge.get("target", "")

                # Skip edges in [verify:skip] — treat as supported
                if ignore.should_skip_verify_edge(subject, edge_target, edge_type):
                    total_verified += 1
                    total_checked += 1
                    print(f"  [{subject}] skipped (ignored): {edge_type} → {edge_target}")
                    continue

                print(f"  [{subject}] verifying: {edge_type} → {edge_target} ({', '.join(s['reasons'])})")

                # Pass reasons to verify_edge for focused prompting
                edge["_verify_reasons"] = s["reasons"]
                verdict = verify_edge(edge, subject)
                # Clean up internal field
                edge.pop("_verify_reasons", None)

                if not verdict:
                    total_checked += 1
                    log.warn("verdict_missing", subject=subject, target=edge_target)
                    continue

                v = verdict.get("verdict", "uncertain")
                conf = verdict.get("confidence", 0.5)
                reason = verdict.get("reason", "")

                log_entry = {
                    "subject": subject,
                    "target": edge_target,
                    "type": edge_type,
                    "evidence": edge.get("evidence", "")[:100],
                    "verdict": v,
                    "confidence": conf,
                    "reason": reason,
                    "reasons": s["reasons"],
                }

                if v == "supported":
                    total_verified += 1
                    log.decision("edge_supported", **log_entry)
                    print(f"    ✓ supported ({conf:.0%}): {reason[:70]}")

                elif v == "unsupported" and conf >= min_confidence:
                    # Remove the edge entirely
                    total_rejected += 1
                    adjudicated["edges"] = [
                        e
                        for e in adjudicated["edges"]
                        if not (e.get("target") == edge_target and e.get("type") == edge_type)
                    ]
                    modified = True
                    log_entry["action"] = "removed"
                    log.action("edge_rejected", **log_entry)
                    print(f"    ✗ rejected ({conf:.0%}): {reason[:70]}")

                else:
                    # uncertain OR unsupported with low confidence:
                    # Flag in the edge so apply.py can skip it rather than silently accepting
                    total_uncertain += 1
                    total_flagged += 1
                    for e in adjudicated["edges"]:
                        if e.get("target") == edge_target and e.get("type") == edge_type:
                            e["verify_uncertain"] = True
                            e["verify_reason"] = reason[:200]
                            break
                    modified = True
                    log.decision("edge_uncertain", **log_entry)
                    label = "uncertain" if v == "uncertain" else f"unsupported (low conf {conf:.0%})"
                    print(f"    ? {label}: {reason[:70]} [flagged]")

                total_checked += 1
                time.sleep(0.5)

            if modified and not dry_run:
                adj_path.write_text(json.dumps(adjudicated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                log.action("file_written", path=str(adj_path))

            if total_checked >= limit:
                break

        log.info(
            "verification_completed",
            checked=total_checked,
            supported=total_verified,
            rejected=total_rejected,
            uncertain=total_uncertain,
            flagged=total_flagged,
        )

    print(
        f"\nDone: {total_checked} checked, {total_verified} supported, "
        f"{total_rejected} rejected, {total_uncertain} uncertain ({total_flagged} flagged in adjudicated.json)"
    )


def main():
    parser = argparse.ArgumentParser(description="Post-adjudication web verification of suspicious claims")
    parser.add_argument("--source", required=True, help="Source to verify (e.g. unitedgangs)")
    parser.add_argument("--limit", type=int, default=50, help="Max edges to verify (default: 50)")
    parser.add_argument("--dry-run", action="store_true", help="Identify suspicious edges without verifying")
    parser.add_argument("--confidence", type=float, default=0.7, help="Min confidence to reject (default: 0.7)")
    parser.add_argument("--model", type=str, default=None, help="Override model")
    args = parser.parse_args()

    global MODEL
    if args.model:
        MODEL = args.model

    if not args.dry_run and not KIRO_KEY:
        print("ERROR: Set KIRO_GATEWAY_API_KEY or PROXY_API_KEY")
        raise SystemExit(1)

    process_source(args.source, limit=args.limit, dry_run=args.dry_run, min_confidence=args.confidence)


if __name__ == "__main__":
    main()


import argparse
import json
import os
import re
import time
from pathlib import Path

import httpx

from apps.pipeline.ignore import load_ignore_rules
from apps.pipeline.log import PipelineLogger

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_EXTRACTED = ROOT / "data" / "extracted"

KIRO_URL = os.environ.get("KIRO_GATEWAY_URL", "http://127.0.0.1:9000")
KIRO_KEY = os.environ.get("KIRO_GATEWAY_API_KEY", os.environ.get("PROXY_API_KEY", ""))
MODEL = os.environ.get("VERIFY_MODEL", "claude-sonnet-4.6")  # sonnet for better reasoning on ambiguous claims

SYSTEM_PROMPT = """You are a fact-checker for a criminal organization knowledge graph. You verify claims about gang relationships using web search results.

You have access to:
- web_search: Search the web for information to verify a claim

Your job is to determine if a claimed relationship between organizations is SUPPORTED or UNSUPPORTED by available evidence.

Respond with ONLY valid JSON:
{
  "verdict": "supported" | "unsupported" | "uncertain",
  "confidence": 0.0-1.0,
  "reason": "Brief explanation of why"
}
"""

TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web to verify a claim about gang relationships, founding dates, or affiliations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to verify the claim",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_url",
        "description": "Fetch and read a specific URL to check its content for verification.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to fetch and read",
                }
            },
            "required": ["url"],
        },
    },
]



def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool call."""
    if tool_name == "web_search":
        return execute_web_search(tool_input.get("query", ""))
    elif tool_name == "fetch_url":
        return execute_fetch_url(tool_input.get("url", ""))
    return f"Unknown tool: {tool_name}"


def identify_suspicious_edges(adjudicated: dict) -> list[dict]:
    """Find edges that should be fact-checked."""
    suspicious = []
    edges = adjudicated.get("edges", [])
    subject = adjudicated.get("subject_org", "Unknown")

    for edge in edges:
        evidence = edge.get("evidence") or (edge.get("citations") or [{}])[0].get("evidence", "")
        target = edge.get("target", "")
        edge_type = edge.get("type", "")
        reasons = []

        # Weak evidence: too short or just a list
        if len(evidence) < 30:
            reasons.append("very_short_evidence")
        elif re.match(r"^(Allies|Rivals|Allies include|Rivals include)", evidence, re.I) and len(evidence) < 80:
            reasons.append("list_only_evidence")

        # Suspicious types that need verification
        if edge_type == "spin_off":
            reasons.append("spin_off_claim")
        if edge_type == "member_of" and "mafia" in target.lower():
            reasons.append("mafia_membership_claim")

        # Evidence mentions "said" or "claims" (hearsay)
        if re.search(r"\b(said|claims|reportedly|allegedly|rumored)\b", evidence, re.I):
            reasons.append("hearsay_language")

        if reasons:
            suspicious.append(
                {
                    "edge": edge,
                    "subject": subject,
                    "reasons": reasons,
                    "priority": len(reasons),
                }
            )

    suspicious.sort(key=lambda x: -x["priority"])
    return suspicious


def verify_edge(edge: dict, subject: str) -> dict | None:
    """Use LLM + web search to verify a single edge claim."""
    target = edge.get("target", "")
    edge_type = edge.get("type", "")
    evidence = edge.get("evidence") or (edge.get("citations") or [{}])[0].get("evidence", "")

    prompt = f"""Verify this claimed relationship:

Subject org: {subject}
Target org: {target}
Relationship type: {edge_type}
Evidence given: "{evidence}"

Use web_search to check if this relationship is real. Search for both organizations and their relationship to each other.
Then give your verdict."""

    messages = [{"role": "user", "content": prompt}]
    headers = {
        "x-api-key": KIRO_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    max_turns = 4
    for turn in range(max_turns):
        payload = {
            "model": MODEL,
            "max_tokens": 1024,
            "temperature": 0.0,
            "thinking": {"type": "disabled"},
            "messages": messages,
            "system": SYSTEM_PROMPT,
        }
        if turn < max_turns - 1:
            payload["tools"] = TOOLS

        try:
            resp = httpx.post(
                f"{KIRO_URL}/v1/messages",
                headers=headers,
                json=payload,
                timeout=30.0,
            )
            resp.raise_for_status()
            body = resp.json()
        except (httpx.HTTPStatusError, httpx.TimeoutException) as e:
            print(f"      ✗ API error: {e}")
            return None

        content_blocks = body.get("content", [])
        stop_reason = body.get("stop_reason", "")

        if stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": content_blocks})
            tool_results = []
            for block in content_blocks:
                if block.get("type") == "tool_use":
                    tool_name = block["name"]
                    tool_input = block.get("input", {})
                    print(f"      🔍 {tool_name}: {json.dumps(tool_input)[:60]}")
                    result = execute_tool(tool_name, tool_input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block["id"],
                            "content": result[:3000],
                        }
                    )
            messages.append({"role": "user", "content": tool_results})
            continue

        # Final text response
        text_out = "".join(p.get("text", "") for p in content_blocks if p.get("type") == "text").strip()

        # Parse JSON verdict
        try:
            if not text_out.startswith("{"):
                idx = text_out.find("{")
                if idx != -1:
                    text_out = text_out[idx:]
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
            return json.loads(text_out)
        except (json.JSONDecodeError, ValueError):
            return None

    return None


def process_source(source: str, limit: int = 50, dry_run: bool = False, min_confidence: float = 0.7):
    """Verify suspicious edges in adjudicated results for a source."""
    source_dir = DATA_EXTRACTED / source
    if not source_dir.exists():
        print(f"No extractions for {source}")
        return

    ignore = load_ignore_rules()

    total_checked = 0
    total_verified = 0
    total_rejected = 0
    total_uncertain = 0
    verification_log = []

    with PipelineLogger("verify", source=source, limit=limit, min_confidence=min_confidence, model=MODEL) as log:
        log.info("verification_started", source=source, limit=limit)

        for page_dir in sorted(source_dir.iterdir()):
            if not page_dir.is_dir():
                continue

            adj_path = page_dir / "adjudicated.json"
            if not adj_path.exists():
                continue

            adjudicated = json.loads(adj_path.read_text(encoding="utf-8"))
            suspicious = identify_suspicious_edges(adjudicated)

            if not suspicious:
                continue

            if dry_run:
                subject = adjudicated.get("subject_org", page_dir.name)
                for s in suspicious[:3]:
                    edge = s["edge"]
                    print(
                        f"  [{subject}] {edge.get('type', '?')} → {edge.get('target', '?')} ({', '.join(s['reasons'])})"
                    )
                total_checked += len(suspicious)
                continue

            subject = adjudicated.get("subject_org", page_dir.name)
            modified = False

            for s in suspicious:
                if total_checked >= limit:
                    break

                edge = s["edge"]
                edge_type = edge.get("type", "")
                edge_target = edge.get("target", "")

                # Skip edges in [verify:skip] — treat as supported without LLM call
                if ignore.should_skip_verify_edge(subject, edge_target, edge_type):
                    total_verified += 1
                    total_checked += 1
                    print(f"  [{subject}] skipped (ignored): {edge_type} → {edge_target}")
                    continue

                print(f"  [{subject}] verifying: {edge_type} → {edge_target}")

                verdict = verify_edge(edge, subject)
                if not verdict:
                    total_checked += 1
                    log.warn("verdict_missing", subject=subject, target=edge.get("target", ""))
                    continue

                v = verdict.get("verdict", "uncertain")
                conf = verdict.get("confidence", 0.5)
                reason = verdict.get("reason", "")

                log_entry = {
                    "subject": subject,
                    "target": edge.get("target", ""),
                    "type": edge.get("type", ""),
                    "evidence": edge.get("evidence", "")[:100],
                    "verdict": v,
                    "confidence": conf,
                    "reason": reason,
                }

                if v == "supported":
                    total_verified += 1
                    log.decision("edge_supported", **log_entry)
                    print(f"    ✓ supported ({conf:.0%}): {reason[:60]}")
                elif v == "unsupported" and conf >= min_confidence:
                    total_rejected += 1
                    adjudicated["edges"] = [
                        e
                        for e in adjudicated["edges"]
                        if not (e.get("target") == edge.get("target") and e.get("type") == edge.get("type"))
                    ]
                    modified = True
                    log_entry["action"] = "removed"
                    log.action("edge_rejected", **log_entry)
                    print(f"    ✗ rejected ({conf:.0%}): {reason[:60]}")
                else:
                    total_uncertain += 1
                    log.decision("edge_uncertain", **log_entry)
                    print(f"    ? uncertain ({conf:.0%}): {reason[:60]}")

                verification_log.append(log_entry)
                total_checked += 1
                time.sleep(1.0)

            if modified:
                adj_path.write_text(json.dumps(adjudicated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                log.action("file_written", path=str(adj_path))

            if total_checked >= limit:
                break

        log.info(
            "verification_completed",
            checked=total_checked,
            supported=total_verified,
            rejected=total_rejected,
            uncertain=total_uncertain,
        )

    print(
        f"\nDone: {total_checked} checked, {total_verified} supported, {total_rejected} rejected, {total_uncertain} uncertain"
    )


def main():
    parser = argparse.ArgumentParser(description="Post-adjudication web verification of suspicious claims")
    parser.add_argument("--source", required=True, help="Source to verify (e.g. unitedgangs)")
    parser.add_argument("--limit", type=int, default=50, help="Max edges to verify (default: 50)")
    parser.add_argument("--dry-run", action="store_true", help="Identify suspicious edges without verifying")
    parser.add_argument("--confidence", type=float, default=0.7, help="Min confidence to reject (default: 0.7)")
    parser.add_argument("--model", type=str, default=None, help="Override model")
    args = parser.parse_args()

    global MODEL
    if args.model:
        MODEL = args.model

    if not args.dry_run and not KIRO_KEY:
        print("ERROR: Set KIRO_GATEWAY_API_KEY or PROXY_API_KEY")
        raise SystemExit(1)

    process_source(args.source, limit=args.limit, dry_run=args.dry_run, min_confidence=args.confidence)


if __name__ == "__main__":
    main()
