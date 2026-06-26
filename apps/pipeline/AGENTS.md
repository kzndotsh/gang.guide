# apps/pipeline/ — Data Pipeline

Scraping, parsing, LLM extraction, and validation for gang.guide data.

## Pipeline Flow

```
scrape/  →  parse/clean.py  →  extract.py  →  merge.py  →  apply.py  →  lint.py
(fetch)      (HTML→text)       (LLM×3)       (consensus)   (upgrade)    (gate)
```

## Scripts

| Script | Purpose | Run with |
|--------|---------|----------|
| `lint.py` | Validate all org files + edges (errors fail CI) | `just lint` |
| `extract.py` | Send raw pages to LLM 3 times, output structured JSON | `python -m apps.pipeline.extract` |
| `merge.py` | Keep only data that appears in 2+ of 3 runs | `python -m apps.pipeline.merge` |
| `apply.py` | Conservatively upgrade org files from extractions | `python -m apps.pipeline.apply` |

## Scrapers (`scrape/`)

| Scraper | Source | Status |
|---------|--------|--------|
| `cgh.py` | Chicago Gang History | 97 pages scraped |
| `wikipedia.py` | MediaWiki API | Categories + URL list |
| `common.py` | Shared: rate limiting, retry, user-agent | — |

All scrapers output to `data/raw/{source}/{slug}/` with `content.txt` + `url.txt`.

## Parsers (`parse/`)

| Parser | Purpose |
|--------|---------|
| `clean.py` | HTML → clean plaintext (first step, always runs before LLM) |
| `parse_index.py` | Build raw page → org ID mapping via fuzzy match |
| `parse_cgh_infobox.py` | Extract structured fields from CGH info tables |

## Entity Resolution (`lib/resolve.py`)

Maps extracted gang names → org IDs. Checks primary name, aliases, abbreviations. Unresolved names collected as new-org candidates. Cache at `data/name_map.json`.

## Conventions

- Raw pages go in `data/raw/` (gitignored, 682MB)
- Extractions go in `data/extracted/` (gitignored)
- Only `lint.py` runs in CI — everything else is manual/local
- LLM backend: Kiro gateway (`KIRO_GATEWAY_URL`, Anthropic-compatible)
- Politeness: random jitter 1-4s between requests, custom User-Agent
- Consensus: extract 3×, keep what repeats. Hallucinations don't survive.

## Adding a New Scraper

1. Create `scrape/newsource.py`
2. Output to `data/raw/newsource/{slug}/content.txt`
3. Add to `parse_index.py` mapping
4. Run `extract.py --source newsource`
