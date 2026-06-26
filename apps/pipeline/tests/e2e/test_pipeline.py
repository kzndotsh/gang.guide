"""End-to-end pipeline test on a single CGH page.

Runs: clean → extract (3 temps) → adjudicate → merge → apply (dry-run)
Prints detailed results at each stage for evaluation.

Usage:
    python -m apps.pipeline.tests.test_pipeline_e2e
    python -m apps.pipeline.tests.test_pipeline_e2e --page vice-lords
    python -m apps.pipeline.tests.test_pipeline_e2e --page almighty-ambrose --skip-extract
"""

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_EXTRACTED = ROOT / "data" / "extracted"

KIRO_URL = os.environ.get("KIRO_GATEWAY_URL", "http://127.0.0.1:9000")
KIRO_KEY = os.environ.get("KIRO_GATEWAY_API_KEY", os.environ.get("PROXY_API_KEY", ""))


def ts():
    return datetime.now().strftime("%H:%M:%S")


def section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")


def main():
    parser = argparse.ArgumentParser(description="End-to-end pipeline test")
    parser.add_argument("--page", default="almighty-ambrose", help="CGH page slug to test")
    parser.add_argument("--skip-extract", action="store_true", help="Use existing extractions")
    args = parser.parse_args()

    if not KIRO_KEY:
        print("ERROR: Set KIRO_GATEWAY_API_KEY or PROXY_API_KEY")
        return

    page = args.page
    source = "chicago_history"
    start_time = time.time()

    # === STAGE 1: CLEAN ===
    section(f"STAGE 1: CLEAN ({page})")
    from apps.pipeline.parse.clean import clean_html, quality_score

    raw_path = DATA_RAW / source / f"{page}.txt"
    if not raw_path.exists():
        print(f"ERROR: {raw_path} not found")
        return

    raw = raw_path.read_text(encoding="utf-8")
    text = clean_html(raw)
    score = quality_score(text)
    print(f"  [{ts()}] Raw: {len(raw):,} chars → Clean: {len(text):,} chars")
    print(f"  [{ts()}] Quality: {score['word_count']} words, {score['prose_ratio']:.0%} prose, low_quality={score['is_low_quality']}")

    if score["is_low_quality"]:
        print("  ❌ Page is low quality, would be skipped in production")
        return

    # === STAGE 2: EXTRACT ===
    section("STAGE 2: EXTRACT (3 temperatures)")
    from apps.pipeline.extract import TEMPERATURES, call_kiro, chunk_text, SYSTEM_PROMPT

    chunks = chunk_text(text)
    print(f"  [{ts()}] Chunks: {len(chunks)} (max 2500 words each)")

    out_dir = DATA_EXTRACTED / source / page
    out_dir.mkdir(parents=True, exist_ok=True)

    runs = []
    if args.skip_extract:
        for i in range(3):
            run_path = out_dir / f"run_{i}.json"
            if run_path.exists():
                runs.append(json.loads(run_path.read_text()))
        print(f"  [{ts()}] Loaded {len(runs)} existing runs")
    else:
        for run_idx, temp in enumerate(TEMPERATURES):
            run_start = time.time()
            run_results = []
            for chunk_idx, chunk in enumerate(chunks):
                result = call_kiro(chunk, temperature=temp)
                if result:
                    run_results.append(result)
                time.sleep(0.5)

            # Merge chunks
            from apps.pipeline.extract import merge_chunks
            merged = merge_chunks(run_results)
            runs.append(merged)

            elapsed = time.time() - run_start
            edges = len(merged.get("edges", []))
            print(f"  [{ts()}] Run {run_idx} (temp={temp}): {edges} edges, {len(run_results)}/{len(chunks)} chunks OK ({elapsed:.1f}s)")

            # Save
            (out_dir / f"run_{run_idx}.json").write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n")

    if len(runs) < 2:
        print("  ❌ Not enough runs to continue")
        return

    # Print run comparison
    print("\n  Run comparison:")
    print(f"  {'':20} {'Run 0':>8} {'Run 1':>8} {'Run 2':>8}")
    print(f"  {'Edges':20} {len(runs[0].get('edges',[])):>8} {len(runs[1].get('edges',[])):>8} {len(runs[2].get('edges',[])) if len(runs)>2 else '-':>8}")
    print(f"  {'Colors':20} {len(runs[0].get('colors',[])):>8} {len(runs[1].get('colors',[])):>8} {len(runs[2].get('colors',[])) if len(runs)>2 else '-':>8}")
    print(f"  {'Orgs mentioned':20} {len(runs[0].get('orgs_mentioned',[])):>8} {len(runs[1].get('orgs_mentioned',[])):>8} {len(runs[2].get('orgs_mentioned',[])) if len(runs)>2 else '-':>8}")
    print(f"  {'Year':20} {runs[0].get('founded_year','?'):>8} {runs[1].get('founded_year','?'):>8} {runs[2].get('founded_year','?') if len(runs)>2 else '-':>8}")

    # === STAGE 3: ADJUDICATE ===
    section("STAGE 3: ADJUDICATE (opus 4.6)")
    from apps.pipeline.adjudicate import call_adjudicator

    adj_start = time.time()
    adjudicated = call_adjudicator(runs)
    adj_elapsed = time.time() - adj_start

    if adjudicated:
        print(f"  [{ts()}] Adjudicated in {adj_elapsed:.1f}s")
        print(f"  Edges: {len(adjudicated.get('edges', []))}")
        print(f"  Colors: {adjudicated.get('colors', [])}")
        print(f"  Symbols: {adjudicated.get('symbols', [])}")
        print(f"  Year: {adjudicated.get('founded_year')} ({adjudicated.get('founded_year_precision', '?')})")
        print(f"  Membership: {adjudicated.get('membership_estimate')}")
        print(f"  Unresolved: {adjudicated.get('unresolved_names', [])}")
        print(f"\n  Description: {adjudicated.get('description', '')[:200]}")

        (out_dir / "adjudicated.json").write_text(json.dumps(adjudicated, indent=2, ensure_ascii=False) + "\n")
    else:
        print("  ❌ Adjudication failed, falling back to algorithmic merge")
        adjudicated = None

    # === STAGE 4: MERGE ===
    section("STAGE 4: MERGE (consensus)")
    from apps.pipeline.merge import merge_runs

    if adjudicated:
        consensus = adjudicated
        print(f"  [{ts()}] Using adjudicated result")
    else:
        consensus = merge_runs(runs)
        print(f"  [{ts()}] Algorithmic merge: {len(consensus.get('edges', []))} edges (2/3 consensus)")

    (out_dir / "consensus.json").write_text(json.dumps(consensus, indent=2, ensure_ascii=False) + "\n")

    # === STAGE 5: APPLY (dry-run) ===
    section("STAGE 5: APPLY (dry-run)")
    from apps.pipeline.lib.resolve import build_index, resolve

    org_index = build_index()
    subject = consensus.get("subject_org", "")
    org_id = resolve(subject, org_index)
    print(f"  [{ts()}] Subject: '{subject}' → resolved: {org_id}")

    if org_id:
        # Check what would change
        org_path = ROOT / "data" / "orgs"
        for f in org_path.glob("*.json"):
            org = json.loads(f.read_text())
            if org.get("id") == org_id:
                print(f"\n  Current state of {f.name}:")
                print(f"    Year: {org.get('founded_year')} ({org.get('founded_year_precision')})")
                print(f"    Colors: {org.get('colors', [])}")
                print(f"    Description: {org.get('description', '')[:100]}...")
                break

        # Show proposed edges
        print(f"\n  Proposed edges ({len(consensus.get('edges', []))}):")
        for e in consensus.get("edges", [])[:10]:
            target_id = resolve(e.get("target", ""), org_index)
            status = "✓" if target_id else "?"
            confidence = e.get("confidence", "")
            print(f"    {status} {e.get('type'):12} → {e.get('target'):30} [{confidence}]")
            if e.get("evidence"):
                print(f"      evidence: \"{e['evidence'][:80]}...\"")
        if len(consensus.get("edges", [])) > 10:
            print(f"    ... and {len(consensus['edges']) - 10} more")

    # === SUMMARY ===
    total_elapsed = time.time() - start_time
    section("SUMMARY")
    print(f"  Page: {page}")
    print(f"  Total time: {total_elapsed:.0f}s ({total_elapsed/60:.1f}m)")
    print(f"  Chunks: {len(chunks)}")
    print(f"  Edges extracted: {'/'.join(str(len(r.get('edges',[]))) for r in runs)}")
    print(f"  Edges after consensus: {len(consensus.get('edges', []))}")
    print(f"  Resolvable edges: {sum(1 for e in consensus.get('edges',[]) if resolve(e.get('target',''), org_index))}/{len(consensus.get('edges', []))}")
    print(f"  Org resolved: {org_id or 'FAILED'}")
    print()


if __name__ == "__main__":
    main()
