"""adjudicate.py — LLM-powered conflict resolution for extraction results.

Only invoked when algorithmic merge finds conflicts:
- Edges that appear in only 1/3 runs (uncertain)
- Contradictory data across runs (year disagreements, etc)
- Unresolved org names that need judgment

Uses a smarter model (sonnet) for a single adjudication pass per org.

Usage:
    python -m apps.pipeline.adjudicate --source chicago_history
    python -m apps.pipeline.adjudicate --source chicago_history --dry-run
"""

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_EXTRACTED = ROOT / "data" / "extracted"

KIRO_URL = os.environ.get("KIRO_GATEWAY_URL", "http://127.0.0.1:9000")
KIRO_KEY = os.environ.get("KIRO_GATEWAY_API_KEY", os.environ.get("PROXY_API_KEY", ""))
MODEL = os.environ.get("ADJUDICATE_MODEL", "claude-opus-4.6")

SYSTEM_PROMPT = """You consolidate multiple extraction runs about the same criminal organization into one authoritative record. Each run may contain errors — your job is to produce the highest-quality output by resolving conflicts and filtering noise.

<rules>
EDGE VALIDATION (most critical):
- An edge is VALID only when its evidence quote contains an explicit relationship verb linking two named organizations. Look for: "allied with", "at war with", "split from", "joined", "formed from", "became enemies of", "merged with".
- REJECT any edge where the evidence is a co-mention — orgs appearing in the same list, location, sentence, or context without an explicit relationship statement.

Examples of INVALID evidence (reject these):
- "Menard Prison 1990s Spanish Cobras, YLO Cobras and Insane Deuces" → just a list, no relationship stated
- "Both gangs operated in the Humboldt Park area" → shared location ≠ alliance
- "Members of X and Y were arrested together" → co-arrest ≠ alliance
- "The neighborhood had Bloods and Crips" → co-existence ≠ any relationship
- "X stands to benefit from Y's disarray" → opportunism ≠ rivalry

Examples of VALID evidence (keep these):
- "X and Y formed an alliance in 1977" → explicit alliance
- "X declared war on Y after the shooting" → explicit rivalry
- "X splintered off from Y in 1978" → explicit spin_off
- "X became enemies of Y" → explicit rivalry

NAMING:
- Use the most specific LOCAL set name from the source text. If the text is about Detroit gangs and mentions "Rollin 60s", the target should be the local Detroit set name (e.g. "7 Mile Rollin 60s Crips"), not the generic national parent ("Rollin 60s Neighborhood Crips"). This prevents cross-city false matches in the knowledge graph.

CONFLICT RESOLUTION:
- For years: prefer the most specific source. "Founded in 1958" beats "Founded in the 1950s".
- For colors: only include colors explicitly stated as the org's colors, not mentioned in passing.
- For descriptions: synthesize the best factual summary (2-3 sentences) from all inputs.
- For edges: if multiple runs agree on an edge with similar evidence, keep it. If only one run has it and evidence is weak, reject it.
- For orgs_mentioned: only include real criminal organizations, not neighborhoods, events, or people.

CONFIDENCE:
- "high": evidence is a direct quote explicitly naming both orgs with a clear relationship verb
- "medium": relationship is implied or evidence is indirect but reasonable
</rules>"""


def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def needs_adjudication(runs: list[dict]) -> bool:
    """Determine if runs have conflicts requiring LLM adjudication."""
    if len(runs) < 2:
        return False

    # Check year disagreement
    years = [r.get("founded_year") for r in runs if r.get("founded_year")]
    if len(set(years)) > 1:
        return True

    # Check for edges that only appear in 1 run (uncertain)
    from collections import Counter
    edge_keys = Counter()
    for r in runs:
        for e in (r.get("edges") or []):
            edge_keys[((e.get("target") or "").lower(), (e.get("type") or ""))] += 1
    # If any edges only in 1 run, there's uncertainty
    uncertain_edges = sum(1 for count in edge_keys.values() if count == 1)
    total_edges = sum(edge_keys.values())
    if uncertain_edges >= 3 and uncertain_edges / max(total_edges, 1) > 0.3:
        return True

    # Check color disagreement
    color_sets = [set(c.lower() for c in (r.get("colors") or [])) for r in runs]
    return len(color_sets) >= 2 and color_sets[0] != color_sets[1]


ADJUDICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "subject_org": {"type": "string"},
        "founded_year": {"type": ["integer", "null"]},
        "founded_year_precision": {"type": "string"},
        "colors": {"type": "array", "items": {"type": "string"}},
        "symbols": {"type": "array", "items": {"type": "string"}},
        "membership_estimate": {"type": ["integer", "null"]},
        "description": {"type": "string"},
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "target": {"type": "string"},
                    "type": {"type": "string"},
                    "evidence": {"type": "string"},
                    "start_year": {"type": ["integer", "null"]},
                    "end_year": {"type": ["integer", "null"]},
                    "confidence": {"type": "string"},
                },
                "required": ["target", "type", "evidence", "confidence"],
                "additionalProperties": False,
            },
        },
        "unresolved_names": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["subject_org", "founded_year", "founded_year_precision", "colors", "symbols", "membership_estimate", "description", "edges", "unresolved_names"],
    "additionalProperties": False,
}


def call_adjudicator(runs: list[dict], timeout: float = 120.0) -> dict | None:
    """Send runs to adjudicator model with structured output."""
    # Truncate to avoid token limits (keep edges + key fields, drop long descriptions)
    trimmed_runs = []
    for r in runs:
        trimmed = {k: v for k, v in r.items() if k != "description"}
        trimmed["description"] = (r.get("description") or "")[:200]
        trimmed_runs.append(trimmed)
    runs_json = json.dumps(trimmed_runs, indent=2)
    if len(runs_json) > 30000:
        runs_json = runs_json[:30000] + "\n... (truncated)"

    user_content = f"""Here are {len(runs)} extraction runs for the same org page. Resolve conflicts and produce the final record.
Respond with ONLY a JSON object matching the expected schema. No markdown. No explanation. Start with {{ and end with }}.

Extraction runs:
{runs_json}"""

    payload = {
        "model": MODEL,
        "max_tokens": 4096,
        "temperature": 0.1,
        "thinking": {"type": "disabled"},
        "messages": [{"role": "user", "content": user_content}],
        "system": SYSTEM_PROMPT + "\n\nIMPORTANT: Output ONLY the JSON object. No markdown code fences. No preamble. Start with { and end with }.",
    }
    headers = {
        "x-api-key": KIRO_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    for attempt in range(3):
        try:
            start = time.time()
            resp = httpx.post(f"{KIRO_URL}/v1/messages", headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
            elapsed = time.time() - start
            body = resp.json()
            text_out = "".join(p.get("text", "") for p in body.get("content", []) if p.get("type") == "text")
            text_out = text_out.strip()
            # Extract JSON from markdown fences or preamble
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
            result = json.loads(text_out)
            print(f"    [{ts()}] adjudicated in {elapsed:.1f}s")
            return result
        except (httpx.HTTPStatusError, json.JSONDecodeError, httpx.TimeoutException) as e:
            if attempt >= 2:
                print(f"    [{ts()}] FAIL: {type(e).__name__}: {e}")
                return None
            time.sleep(min(2 ** attempt, 8))
    return None


def process_source(source: str, dry_run: bool = False, force: bool = False):
    """Adjudicate conflicting extractions for a source."""
    source_dir = DATA_EXTRACTED / source
    if not source_dir.exists():
        print(f"No extractions for {source}")
        return

    adjudicated = 0
    skipped = 0
    auto_merged = 0

    for page_dir in sorted(source_dir.iterdir()):
        if not page_dir.is_dir():
            continue

        # Skip if already adjudicated
        adj_path = page_dir / "adjudicated.json"
        if not force and not dry_run and adj_path.exists():
            skipped += 1
            continue

        # Load runs
        runs = []
        for i in range(1, 4):
            run_path = page_dir / f"run_{i}.json"
            if run_path.exists():
                runs.append(json.loads(run_path.read_text(encoding="utf-8")))

        if len(runs) < 2:
            continue

        if not needs_adjudication(runs):
            # Still adjudicate everything — tokens are unlimited, quality wins
            pass

        slug = page_dir.name
        if dry_run:
            print(f"  [needs adjudication] {slug}")
            adjudicated += 1
            continue

        print(f"  [{ts()}] adjudicating {slug}...")
        result = call_adjudicator(runs)
        if result:
            adj_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            edges = len(result.get("edges", []))
            unresolved = len(result.get("unresolved_names", []))
            print(f"    → {edges} edges, {unresolved} unresolved names")
            adjudicated += 1
        time.sleep(1.0)

    print(f"\n[{ts()}] Done: {adjudicated} adjudicated, {auto_merged} auto-merged (no conflicts), {skipped} already done")


def main():
    parser = argparse.ArgumentParser(description="LLM-powered conflict resolution for extractions")
    parser.add_argument("--source", required=True, help="Source to adjudicate")
    parser.add_argument("--dry-run", action="store_true", help="Show which pages need adjudication without calling API")
    parser.add_argument("--force", action="store_true", help="Re-adjudicate even if already done")
    args = parser.parse_args()

    if not KIRO_KEY and not args.dry_run:
        print("ERROR: Set KIRO_GATEWAY_API_KEY or PROXY_API_KEY")
        return

    process_source(args.source, dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
