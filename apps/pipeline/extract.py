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
MODEL = os.environ.get("EXTRACT_MODEL", "claude-haiku-4.5")
RUNS_PER_PAGE = 3
MAX_CHUNK_WORDS = 2500

PROMPT_VERSION = "v1"

SYSTEM_PROMPT = """You are an expert on US street gangs. Extract structured data from the provided text about a criminal organization.

Return ONLY valid JSON with this exact schema:
{
  "subject_org": "Name of the main org this page is about",
  "founded_year": 1972 or null,
  "colors": ["blue", "black"] or [],
  "symbols": ["pitchfork", "six-point star"] or [],
  "membership_estimate": 5000 or null,
  "description": "2-3 sentence factual summary of the org",
  "edges": [
    {
      "target": "Name of related org",
      "type": "alliance|rivalry|parent|member_of|spin_off",
      "evidence": "Verbatim quote from text proving this relationship",
      "period": "1977-1992" or null
    }
  ],
  "orgs_mentioned": ["Other Org 1", "Other Org 2"]
}

RULES:
- founded_year: only if explicitly stated in text. Never guess.
- colors: only if explicitly stated. Not from context.
- edges: ONLY real direct relationships between two orgs. NOT co-mentions.
- evidence: MUST be a verbatim quote from the text. If you can't quote it, don't emit the edge.
- edges.type: alliance (work together), rivalry (fight each other), parent (umbrella org), member_of (belongs to nation), spin_off (formed from another)
- orgs_mentioned: every named criminal organization in the text, even without a relationship
- description: factual, no speculation, based only on what the text says
- If the text is too short or uninformative, return empty arrays and null fields."""


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


def call_kiro(text: str, timeout: float = 90.0) -> dict | None:
    """Call kiro gateway and parse JSON response."""
    payload = {
        "model": MODEL,
        "max_tokens": 4096,
        "temperature": 0.3,
        "messages": [
            {"role": "user", "content": f"Extract gang data from this text:\n\n{text}"}
        ],
        "system": SYSTEM_PROMPT,
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
            call_elapsed = time.time() - call_start
            body = resp.json()
            text_out = "".join(
                p.get("text", "") for p in body.get("content", []) if p.get("type") == "text"
            )
            # Parse JSON from response (handle markdown code blocks)
            text_out = text_out.strip()
            if text_out.startswith("```"):
                text_out = text_out.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text_out)
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

    # Run extraction N times
    runs = []
    for run_idx in range(RUNS_PER_PAGE):
        run_results = []
        for chunk in chunks:
            result = call_kiro(chunk)
            if result:
                run_results.append(result)
            time.sleep(random.uniform(0.5, 1.5))

        # Merge chunks within a single run
        merged_run = merge_chunks(run_results)
        runs.append(merged_run)
        (out_dir / f"run_{run_idx}.json").write_text(json.dumps(merged_run, indent=2), encoding="utf-8")

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
    parser = argparse.ArgumentParser(description="LLM extraction from raw pages")
    parser.add_argument("--source", required=True, help="Source directory in data/raw/")
    parser.add_argument("--limit", type=int, default=0, help="Max pages to process")
    parser.add_argument("--force", action="store_true", help="Re-extract even if done")
    parser.add_argument("--dry-run", action="store_true", help="Count pages without calling API")
    args = parser.parse_args()

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
