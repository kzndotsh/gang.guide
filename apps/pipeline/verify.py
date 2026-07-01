"""verify.py — post-adjudication web verification of suspicious claims.

Runs between adjudicate and merge. Identifies edges with weak evidence
or suspicious data, uses web search to fact-check, and marks or removes
unverifiable claims.

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

from apps.pipeline.log import PipelineLogger

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_EXTRACTED = ROOT / "data" / "extracted"

KIRO_URL = os.environ.get("KIRO_GATEWAY_URL", "http://127.0.0.1:9000")
KIRO_KEY = os.environ.get("KIRO_GATEWAY_API_KEY", os.environ.get("PROXY_API_KEY", ""))
MODEL = os.environ.get("VERIFY_MODEL", "claude-sonnet-4.5")  # sonnet for better reasoning on ambiguous claims

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


def execute_web_search(query: str) -> str:
    """Execute a web search via DuckDuckGo HTML."""
    try:
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (compatible; gang-guide-verify/1.0)"},
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
            title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            snippet = re.sub(r"<[^>]+>", "", match.group(3)).strip()
            if title and snippet:
                results.append(f"{title}: {snippet}")
            if len(results) >= 5:
                break
        return "\n".join(results) if results else "No results found."
    except Exception as e:
        return f"Search failed: {e}"


def execute_fetch_url(url: str) -> str:
    """Fetch a URL and extract readable text content."""
    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; gang-guide-verify/1.0)"},
            timeout=15.0,
            follow_redirects=True,
        )
        resp.raise_for_status()
        content = resp.text
        content = re.sub(r"<script[^>]*>.*?</script>", " ", content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r"<style[^>]*>.*?</style>", " ", content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r"<[^>]+>", " ", content)
        content = re.sub(r"\s+", " ", content).strip()
        return content[:5000]
    except Exception as e:
        return f"Fetch failed: {e}"


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
        evidence = edge.get("evidence", "")
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
            suspicious.append({
                "edge": edge,
                "subject": subject,
                "reasons": reasons,
                "priority": len(reasons),
            })

    suspicious.sort(key=lambda x: -x["priority"])
    return suspicious


def verify_edge(edge: dict, subject: str) -> dict | None:
    """Use LLM + web search to verify a single edge claim."""
    target = edge.get("target", "")
    edge_type = edge.get("type", "")
    evidence = edge.get("evidence", "")

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
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block["id"],
                        "content": result[:3000],
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        # Final text response
        text_out = "".join(
            p.get("text", "") for p in content_blocks if p.get("type") == "text"
        ).strip()

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
                    print(f"  [{subject}] {edge.get('type', '?')} → {edge.get('target', '?')} ({', '.join(s['reasons'])})")
                total_checked += len(suspicious)
                continue

            subject = adjudicated.get("subject_org", page_dir.name)
            modified = False

            for s in suspicious:
                if total_checked >= limit:
                    break

                edge = s["edge"]
                print(f"  [{subject}] verifying: {edge.get('type', '')} → {edge.get('target', '')}")

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
                        e for e in adjudicated["edges"]
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

        log.info("verification_completed", checked=total_checked, supported=total_verified, rejected=total_rejected, uncertain=total_uncertain)

    print(f"\nDone: {total_checked} checked, {total_verified} supported, {total_rejected} rejected, {total_uncertain} uncertain")


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
