# apps/pipeline/

Scraping, LLM extract/adjudicate/verify, merge, apply, enrich, clean, lint.

**Full docs:** [`docs/PIPELINE.md`](../../docs/PIPELINE.md). **Schema:** [`docs/SCHEMA.md`](../../docs/SCHEMA.md).

```
scrape/ → data/raw/{source}/{slug}/content.txt
extract (×3 temps) → adjudicate → [verify] → merge → apply → lint
```

`just pipeline` does **not** run verify. Merge prefers `adjudicated.json`, not `verified.json`.

| Script | Command |
|--------|---------|
| lint | `just lint` |
| extract / adjudicate / merge / apply | `just extract\|adjudicate\|merge\|apply <source>` |
| verify | `just verify <source>` |
| enrich / clean | `just enrich`, `just clean` |

New scraper: `scrape/foo.py` → `data/raw/foo/{slug}/content.txt` + `url.txt`, then `extract.py --source foo`. Entity names: `lib/resolve.py`. Ignore file: `.gangguideignore` via `ignore.py`.

Raw and `data/extracted/` are gitignored. Only lint runs in CI. LLM: Kiro gateway (`KIRO_GATEWAY_URL`).
