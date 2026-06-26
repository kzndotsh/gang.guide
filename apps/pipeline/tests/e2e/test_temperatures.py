"""Test extraction at every temperature from 0.0 to 1.0 on a single CGH page."""

import json
import os
import time
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_RAW = ROOT / "data" / "raw"

KIRO_URL = os.environ.get("KIRO_GATEWAY_URL", "http://127.0.0.1:9000")
KIRO_KEY = os.environ.get("KIRO_GATEWAY_API_KEY", os.environ.get("PROXY_API_KEY", ""))
from apps.pipeline.parse.clean import clean_html
from apps.pipeline.extract import SYSTEM_PROMPT, chunk_text

MODEL = os.environ.get("EXTRACT_MODEL", "claude-sonnet-4.5")

PAGE = "almighty-ambrose"


def ts():
    return datetime.now().strftime("%H:%M:%S")


def call(text: str, temperature: float) -> tuple[dict | None, float]:
    from apps.pipeline.extract import SYSTEM_PROMPT as SYS
    payload = {
        "model": MODEL,
        "max_tokens": 4096,
        "temperature": temperature,
        "messages": [{"role": "user", "content": f"Extract gang data from this text. Respond with ONLY a JSON object, no markdown fences, no explanation:\n\n{text}"}],
        "system": SYS + "\n\nIMPORTANT: Output ONLY the JSON object. No markdown code fences. No preamble. Start with { and end with }.",
    }
    headers = {
        "x-api-key": KIRO_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    start = time.time()
    try:
        resp = httpx.post(f"{KIRO_URL}/v1/messages", headers=headers, json=payload, timeout=120.0)
        resp.raise_for_status()
        elapsed = time.time() - start
        body = resp.json()
        text_out = "".join(p.get("text", "") for p in body.get("content", []) if p.get("type") == "text")
        text_out = text_out.strip()
        if "```" in text_out:
            parts = text_out.split("```")
            for part in parts[1:]:
                candidate = part.lstrip("json\n").strip()
                if candidate.startswith("{"):
                    text_out = candidate
                    break
        if not text_out.startswith("{"):
            idx = text_out.find("{")
            if idx != -1:
                text_out = text_out[idx:]
        return json.loads(text_out), elapsed
    except Exception as e:
        return None, time.time() - start


def main():
    if not KIRO_KEY:
        print("ERROR: Set KIRO_GATEWAY_API_KEY or PROXY_API_KEY")
        return

    raw = (DATA_RAW / "chicago_history" / f"{PAGE}.txt").read_text()
    text = clean_html(raw)
    # Use first chunk only to keep it fast
    chunks = chunk_text(text)
    chunk = chunks[0]
    print(f"[{ts()}] Testing {PAGE} (chunk 1/{len(chunks)}, {len(chunk.split())} words)")
    print(f"[{ts()}] Model: {MODEL}")
    print(f"{'='*80}")
    print(f"{'Temp':<6} {'Time':<8} {'Edges':<7} {'Colors':<15} {'Year':<6} {'Parse':<6} Edge types")
    print(f"{'-'*80}")

    results = []
    for temp_int in range(0, 11):  # 0.0 to 1.0 in 0.1 steps
        temp = temp_int / 10.0
        result, elapsed = call(chunk, temp)
        if result:
            edges = result.get("edges", [])
            colors = result.get("colors", [])
            year = result.get("founded_year")
            edge_types = {}
            for e in edges:
                t = e.get("type", "?")
                edge_types[t] = edge_types.get(t, 0) + 1
            type_str = " ".join(f"{t}:{c}" for t, c in sorted(edge_types.items()))
            print(f"{temp:<6.1f} {elapsed:<8.1f} {len(edges):<7} {','.join(colors[:3]):<15} {year or '?':<6} {'OK':<6} {type_str}")
            results.append({"temp": temp, "edges": len(edges), "colors": colors, "year": year, "elapsed": elapsed})
        else:
            print(f"{temp:<6.1f} {elapsed:<8.1f} {'FAIL':<7}")
            results.append({"temp": temp, "edges": 0, "parse_fail": True, "elapsed": elapsed})

        time.sleep(0.5)

    print(f"{'='*80}")
    # Summary
    ok = [r for r in results if not r.get("parse_fail")]
    fails = [r for r in results if r.get("parse_fail")]
    edge_counts = [r["edges"] for r in ok]
    print(f"\n[{ts()}] Summary:")
    print(f"  Parse OK: {len(ok)}/11, Failures: {len(fails)}/11")
    if edge_counts:
        print(f"  Edges: min={min(edge_counts)}, max={max(edge_counts)}, avg={sum(edge_counts)/len(edge_counts):.1f}")
    print(f"  Avg time: {sum(r['elapsed'] for r in results)/len(results):.1f}s")
    if fails:
        print(f"  Failed at temps: {[r['temp'] for r in fails]}")


if __name__ == "__main__":
    main()
