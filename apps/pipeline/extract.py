"""extract.py — LLM multi-run extraction from raw pages.

Reads cleaned text from data/raw/, sends to kiro gateway 3 times per page,
outputs structured JSON to data/extracted/.

Usage:
    python -m apps.pipeline.extract --source chicago_history --limit 5
    python -m apps.pipeline.extract --source chicago_history --force
    python -m apps.pipeline.extract --dry-run
"""

import argparse
import hashlib
import json
import os
import time
import random
from datetime import datetime
from pathlib import Path

import httpx

from .parse.clean import clean_html, quality_score
from .lib.resolve import build_index, resolve

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_EXTRACTED = ROOT / "data" / "extracted"
DATA_EXTRACTED.mkdir(exist_ok=True)

KIRO_URL = os.environ.get("KIRO_GATEWAY_URL", "http://127.0.0.1:9000")
KIRO_KEY = os.environ.get("KIRO_GATEWAY_API_KEY", os.environ.get("PROXY_API_KEY", ""))
MODEL = os.environ.get("EXTRACT_MODEL", "claude-sonnet-4.5")
TEMPERATURES = [0.1, 0.3, 0.7]  # conservative → balanced → creative
RUNS_PER_PAGE = len(TEMPERATURES)
MAX_CHUNK_WORDS = 50000  # sonnet 4.5 handles 1M context; only chunk truly massive docs

PROMPT_VERSION = "v2"

SYSTEM_PROMPT = """You extract structured relationship data from source text about US criminal organizations. Your output feeds a knowledge graph where accuracy matters more than completeness — a missed edge is fine, a wrong edge corrupts the dataset.

Return ONLY valid JSON matching this schema:
{
  "subject_org": "Full proper name of the main organization this page is about",
  "founded_year": 1972 or null,
  "colors": ["blue", "black"] or [],
  "symbols": ["pitchfork", "six-point star"] or [],
  "membership_estimate": 5000 or null,
  "description": "2-3 sentence factual summary of the org based only on what the text says",
  "edges": [
    {
      "target": "Full proper name of related org",
      "type": "alliance|rivalry|parent|member_of|spin_off",
      "evidence": "Exact verbatim quote from the source text proving this relationship",
      "period": "1977-1992" or null
    }
  ],
  "orgs_mentioned": ["Other Org 1", "Other Org 2"]
}

<rules>
EDGE QUALITY (most important):
- Only emit an edge when the text contains an explicit statement of relationship between two named organizations. The evidence quote must contain a clear relationship verb (allied, fought, split from, joined, warred with, formed from, etc.).
- A co-mention is NOT an edge. Two orgs appearing in the same sentence, list, or location does NOT prove a relationship.
- The evidence field must be a verbatim quote you can point to in the source text. If you cannot quote a specific sentence proving the relationship, do not emit the edge.

NAMING:
- subject_org: Use the full proper name as written in the text (e.g. "7 Mile Rollin 60s Crips" not just "Rollin 60s").
- edges.target: Always use the MOST SPECIFIC name from the text. If the source discusses local sets in Detroit and mentions "Rollin 60s", use the local set name that appears in the text (e.g. "7 Mile Rollin 60s Crips"), not the generic national org name. This prevents duplicates in the knowledge graph.

FIELDS:
- founded_year: Only if the text explicitly states a year. "Founded in the early 2000s" = null.
- colors: Only if explicitly stated as the org's colors. Not colors mentioned in other contexts.
- membership_estimate: Only if a number is given. Ranges like "200-300" → use the midpoint.
- description: Factual, based only on what the text says. No speculation or external knowledge.
- orgs_mentioned: Every named criminal organization in the text, even those without a relationship edge.

EDGE TYPES:
- alliance: explicitly work together, share territory peacefully, mutual aid
- rivalry: fight each other, documented conflict, war, beef
- parent: umbrella organization (e.g. Folk Nation is parent of Gangster Disciples)
- member_of: the subject belongs to a larger alliance/nation
- spin_off: the target org formed from/splintered off the subject org (A → spin_off → B means "B came from A")

If the text is too short or uninformative, return empty arrays and null fields. Returning nothing is better than guessing.
</rules>"""


def prompt_hash() -> str:
    return hashlib.md5(SYSTEM_PROMPT.encode()).hexdigest()[:8]


def chunk_text(text: str) -> list[str]:
    """Split text into chunks of ~MAX_CHUNK_WORDS."""
    words = text.split()
    if len(words) <= MAX_CHUNK_WORDS:
        return [text]
    chunks = []
    for i in range(0, len(words), MAX_CHUNK_WORDS):
        chunks.append(" ".join(words[i:i + MAX_CHUNK_WORDS]))
    return chunks


EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "subject_org": {"type": "string"},
        "founded_year": {"type": ["integer", "null"]},
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
                    "period": {"type": ["string", "null"]},
                },
                "required": ["target", "type", "evidence"],
                "additionalProperties": False,
            },
        },
        "orgs_mentioned": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["subject_org", "founded_year", "colors", "symbols", "membership_estimate", "description", "edges", "orgs_mentioned"],
    "additionalProperties": False,
}


def call_kiro(text: str, temperature: float = 0.0, timeout: float = 120.0) -> dict | None:
    """Call kiro gateway and parse JSON response."""
    payload = {
        "model": MODEL,
        "max_tokens": 4096,
        "temperature": temperature,
        "thinking": {"type": "disabled"},
        "messages": [
            {"role": "user", "content": f"Extract gang data from this text. Respond with ONLY a JSON object, no markdown fences, no explanation:\n\n{text}"}
        ],
        "system": SYSTEM_PROMPT + "\n\nIMPORTANT: Output ONLY the JSON object. No markdown code fences. No preamble. Start with { and end with }.",
    }
    headers = {
        "x-api-key": KIRO_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    for attempt in range(3):
        try:
            call_start = time.time()
            resp = httpx.post(
                f"{KIRO_URL}/v1/messages",
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            resp.raise_for_status()
            body = resp.json()
            text_out = "".join(
                p.get("text", "") for p in body.get("content", []) if p.get("type") == "text"
            )
            # Strip any wrapping (markdown fences, preamble text)
            text_out = text_out.strip()
            if "```" in text_out:
                # Extract content between first ``` and last ```
                parts = text_out.split("```")
                for part in parts[1:]:
                    candidate = part.lstrip("json\n").strip()
                    if candidate.startswith("{"):
                        text_out = candidate
                        break
            # Find the JSON object even if there's preamble
            if not text_out.startswith("{"):
                start_idx = text_out.find("{")
                if start_idx != -1:
                    text_out = text_out[start_idx:]
            # Trim trailing junk after the JSON
            if text_out.startswith("{"):
                depth = 0
                end_idx = 0
                for i, c in enumerate(text_out):
                    if c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                    if depth == 0:
                        end_idx = i + 1
                        break
                if end_idx:
                    text_out = text_out[:end_idx]
            parsed = json.loads(text_out)
            if not isinstance(parsed, dict) or "edges" not in parsed:
                if attempt >= 2:
                    return None
                continue
            return parsed
        except (httpx.HTTPStatusError, json.JSONDecodeError, httpx.TimeoutException) as e:
            if attempt >= 2:
                print(f"    [{ts()}] FAIL after {attempt+1} attempts: {type(e).__name__}: {e}")
                return None
            wait = min(2 ** attempt, 8)
            print(f"    [{ts()}] retry {attempt+1} ({type(e).__name__}), waiting {wait}s")
            time.sleep(wait)
    return None


def extract_page(source: str, slug: str, force: bool = False) -> dict | None:
    """Run extraction 3 times on a page, save raw outputs."""
    out_dir = DATA_EXTRACTED / source / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    # Check if already done with current prompt version
    meta_path = out_dir / "meta.json"
    if not force and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta.get("prompt_hash") == prompt_hash() and meta.get("runs", 0) >= RUNS_PER_PAGE:
            return None  # already done

    # Load and clean the raw page
    raw_path = DATA_RAW / source / f"{slug}.txt"
    if not raw_path.exists():
        raw_path = DATA_RAW / source / slug / "content.txt"
    if not raw_path.exists():
        return None

    raw = raw_path.read_text(encoding="utf-8")
    text = clean_html(raw) if "<" in raw[:100] else raw
    score = quality_score(text)

    if score["is_low_quality"]:
        return None

    # Chunk if needed
    chunks = chunk_text(text)

    # Run extraction N times (resume from existing runs)
    runs = []
    for run_idx, temp in enumerate(TEMPERATURES):
        existing_run = out_dir / f"run_{run_idx + 1}.json"
        if not force and existing_run.exists():
            runs.append(json.loads(existing_run.read_text(encoding="utf-8")))
            continue

        run_results = []
        for chunk in chunks:
            result = call_kiro(chunk, temperature=temp)
            if result:
                run_results.append(result)
            time.sleep(random.uniform(0.5, 1.5))

        # Merge chunks within a single run
        merged_run = merge_chunks(run_results)
        runs.append(merged_run)
        (out_dir / f"run_{run_idx + 1}.json").write_text(json.dumps(merged_run, indent=2), encoding="utf-8")

    # Save metadata
    meta = {
        "source": source,
        "slug": slug,
        "prompt_hash": prompt_hash(),
        "prompt_version": PROMPT_VERSION,
        "runs": len(runs),
        "model": MODEL,
        "quality_score": score,
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def merge_chunks(chunk_results: list[dict]) -> dict:
    """Merge extraction results from multiple chunks of the same page."""
    if not chunk_results:
        return {"subject_org": None, "edges": [], "orgs_mentioned": [], "colors": [], "symbols": []}
    if len(chunk_results) == 1:
        return chunk_results[0]

    # Take subject_org from first chunk
    merged = {
        "subject_org": chunk_results[0].get("subject_org"),
        "founded_year": None,
        "colors": [],
        "symbols": [],
        "membership_estimate": None,
        "description": "",
        "edges": [],
        "orgs_mentioned": [],
    }

    all_colors = set()
    all_symbols = set()
    all_orgs = set()
    all_edges = []
    descriptions = []

    for r in chunk_results:
        if r.get("founded_year") and not merged["founded_year"]:
            merged["founded_year"] = r["founded_year"]
        for c in (r.get("colors") or []):
            all_colors.add(c.lower())
        for s in (r.get("symbols") or []):
            all_symbols.add(s)
        if r.get("membership_estimate"):
            merged["membership_estimate"] = r["membership_estimate"]
        if r.get("description"):
            descriptions.append(r["description"])
        all_edges.extend(r.get("edges") or [])
        for o in (r.get("orgs_mentioned") or []):
            all_orgs.add(o)

    merged["colors"] = sorted(all_colors)
    merged["symbols"] = sorted(all_symbols)
    merged["orgs_mentioned"] = sorted(all_orgs)
    merged["edges"] = all_edges
    merged["description"] = max(descriptions, key=len) if descriptions else ""

    return merged


def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def main():
    global MODEL
    parser = argparse.ArgumentParser(description="LLM extraction from raw pages")
    parser.add_argument("--source", required=True, help="Source directory in data/raw/")
    parser.add_argument("--limit", type=int, default=0, help="Max pages to process")
    parser.add_argument("--model", default=None, help="Override model (default: claude-haiku-4.5 or EXTRACT_MODEL env)")
    parser.add_argument("--force", action="store_true", help="Re-extract even if done")
    parser.add_argument("--dry-run", action="store_true", help="Count pages without calling API")
    args = parser.parse_args()

    if args.model:
        MODEL = args.model

    if not KIRO_KEY and not args.dry_run:
        print("ERROR: Set KIRO_GATEWAY_API_KEY or PROXY_API_KEY")
        return

    source_dir = DATA_RAW / args.source
    if not source_dir.exists():
        print(f"ERROR: {source_dir} not found")
        return

    # Collect pages
    pages = []
    for f in sorted(source_dir.iterdir()):
        if f.suffix == ".txt" and not f.name.startswith("_"):
            pages.append(f.stem)
        elif f.is_dir() and (f / "content.txt").exists():
            pages.append(f.name)

    if args.limit:
        pages = pages[:args.limit]

    if args.dry_run:
        print(f"Would process {len(pages)} pages from {args.source}")
        print(f"Estimated API calls: {len(pages) * RUNS_PER_PAGE}")
        print(f"Estimated cost: ~${len(pages) * 0.01 * RUNS_PER_PAGE:.2f}")
        return

    start_time = time.time()
    print(f"[{ts()}] Extracting {len(pages)} pages from {args.source} ({RUNS_PER_PAGE} runs each)")
    processed = 0
    skipped = 0
    for i, slug in enumerate(pages):
        page_start = time.time()
        result = extract_page(args.source, slug, force=args.force)
        elapsed = time.time() - page_start
        if result:
            processed += 1
            print(f"  [{ts()}] [{processed}/{len(pages)}] {slug} ({elapsed:.1f}s)")
        else:
            skipped += 1
            print(f"  [{ts()}] [skip] {slug}")

    total_elapsed = time.time() - start_time
    print(f"\n[{ts()}] Done: {processed} extracted, {skipped} skipped in {total_elapsed:.0f}s ({total_elapsed/60:.1f}m)")


if __name__ == "__main__":
    main()
