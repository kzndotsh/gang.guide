# Pipeline

The pipeline extracts structured data from raw source text with LLMs, then merges it into `data/orgs/` and `data/edges.json`.

```
data/raw/{source}/  →  extract  →  adjudicate  →  merge  →  apply  →  orgs + edges.json
                         (optional: verify between adjudicate and merge)
```

```bash
just pipeline chicago_history
```

That recipe is: **extract → adjudicate → merge → apply (dry-run)**. It does **not** run `verify`. Review the dry-run, then `just apply chicago_history`. For web-search fact-checking, run `just verify chicago_history` after adjudicate (and re-merge / re-apply if you want those verdicts in the dataset).

`merge.py` currently prefers `adjudicated.json` over algorithmic 2/3 consensus. It does **not** read a separate `verified.json`. `verify.py` modifies `adjudicated.json` in-place, so running verify before merge is all that is needed — no manual copy step.

## Sources

| Source key | Scraper | Site |
|------------|---------|------|
| `chicago_history` | `cgh.py` | Chicago Gang History |
| `detroit_dsg` | `dsg.py` | Detroit Street Gangs |
| `ngcrc` | `ngcrc.py` | National Gang Crime Research Center |
| `nyc_historical` | `nyc.py` | New York City Gangs |
| `stonegreasers` | `stonegreasers.py` | StoneGreasers |
| `unitedgangs` | `unitedgangs.py` | UnitedGangs.com |
| `stophoustongangs` | `stophoustongangs.py` | StopHoustonGangs.org (FlareSolverr) |
| `adl` | `adl.py` | ADL WS prison gang PDFs + hate-symbol pages (Wayback) |
| `fbi_ngta` | `fbi_ngta.py` | FBI NGTA PDFs 2009/2011/2015 (`pypdf`) |
| `insightcrime` | `insightcrime.py` | InSight Crime |
| `splc` | `splc.py` | SPLC Extremist Files (FlareSolverr) |

Also: `wikipedia.py` (general Wikipedia). Shared helpers in `scrape/common.py`.

Scrapers write `data/raw/{source}/{slug}/content.txt` + `url.txt`. Extract also accepts a flat `data/raw/{source}/{slug}.txt`.

Cloudflare-protected sites need FlareSolverr (`docker run -p 8191:8191 ghcr.io/flaresolverr/flaresolverr`). PDFs need `pypdf` (flake.nix / pipeline deps). LLM steps need `KIRO_GATEWAY_URL` and `KIRO_GATEWAY_API_KEY` (see `.env.example`).

## Stages

### 1. Extract (`apps/pipeline/extract.py`)

Sends cleaned page text to **claude-sonnet-4.6** at temperatures 0.1, 0.3, 0.7 (v2 prompt). Thinking disabled on the gateway.

- Input: `data/raw/{source}/...`
- Output: `data/extracted/{source}/{slug}/run_1.json` ... `run_3.json`
- Skips pages already extracted (prompt hash in `meta.json`) unless `--force`
- Resumes existing runs on crash

Each run includes `subject_org`, `org_type`, `org_lane`, `founded_year`, `colors`, `symbols`, `edges` (with verbatim `evidence` quote and optional `period`), `orgs_mentioned`. Apply converts these to `citations[]` entries when writing to `edges.json`.

### 2. Adjudicate (`apps/pipeline/adjudicate.py`)

Sends all three runs to **claude-sonnet-4.6** (v2 prompt). Validates that evidence quotes prove the claimed relationship, resolves years/names, drops weak or hallucinated edges, assigns `confidence` `high` or `medium`.

Output: `data/extracted/{source}/{slug}/adjudicated.json`

### 3. Verify (`apps/pipeline/verify.py`): optional

Web-search fact-checking with **claude-sonnet-4.6** (up to 8 tool turns via `apps/pipeline/search.py` — Brave Search + DuckDuckGo + Wikipedia + CourtListener).

**Modifies `adjudicated.json` in-place** — merge reads the already-cleaned version. No separate verified.json data path.

Suspicious edge heuristics:
- Very short evidence (<30 chars) or list-only ("Allies include X")
- Hearsay language ("reportedly", "allegedly")
- `spin_off` with weak evidence (<100 chars) — long quotes exempt
- `member_of` + mafia target
- **Cross-metro alliance/rivalry** — orgs in different cities are suspicious without strong evidence

Also runs org-level field checks (printed as warnings, not blocking):
- `metro` contradicts `lane` (e.g. Chicago org in `historical-east` lane)
- `founded_year` predates the movement (Crips before 1969, etc.)

Verdicts:
- `supported` → no change
- `unsupported` (≥0.7 confidence) → edge **removed** from `adjudicated.json`
- `uncertain` or low-confidence unsupported → edge **flagged** `verify_uncertain: true` in `adjudicated.json`; `apply.py` skips these rather than silently accepting them

Not part of `just pipeline` by default. Run explicitly: `just verify <source>`

### 4. Merge (`apps/pipeline/merge.py`)

Writes `consensus.json` for apply.

- If `adjudicated.json` exists: copy it
- Else: keep fields/edges that appear in at least 2 of 3 extract runs

### 5. Apply (`apps/pipeline/apply.py`)

Conservative upgrade of live data files.

- Only fills weaker fields (empty colors, thin descriptions, imprecise years)
- Adds edges that do not already exist; for edges that already exist, appends a new citation if the source URL is not already recorded
- New citations are written as `citations[]` entries (`url`, `title`, `evidence`)
- `--create-orgs` writes stubs; type/lane from extract `org_type` / `org_lane`, else `street_gang` / unset
- Rejects page-title names, self-edges, slug collisions, contradictions without dates
- LA metro inheritance for Piru, Compton, etc.
- Converts `period` strings (`1977-1992`) to `start_year` / `end_year`
- Lint is the final gate: all changes rejected if lint errors increase

## CLI

```bash
just extract chicago_history
just adjudicate chicago_history
just verify chicago_history          # optional web check
just merge chicago_history
just apply-preview chicago_history   # dry-run
just apply chicago_history
just pipeline chicago_history        # extract → adjudicate → merge → apply dry-run

just enrich                          # weak org profiles (not in just pipeline)
just enrich-rank
just clean                           # spot-check existing fields
just clean-rank
just ignore-show
just ignore-validate
just index                           # page → org index from raw
```

## Models

| Stage | Default model | Temperature | Env override |
|-------|---------------|-------------|--------------|
| Extract | claude-sonnet-4.6 | 0.1, 0.3, 0.7 | `EXTRACT_MODEL` |
| Adjudicate | claude-sonnet-4.6 | 0.1 | `ADJUDICATE_MODEL` |
| Verify | claude-sonnet-4.6 | 0.1 |: |
| Enrich / clean | configurable `--model` |: |: |

## Idempotency

Extract, adjudicate, verify, and merge skip work that already exists unless `--force`. Apply skips strong fields and existing edges. Safe to re-run.

## Quality gates

1. Multi-temperature extract: one-off hallucinations usually fail 2/3
2. Adjudication: quote must prove the relationship (rejects co-mentions)
3. Optional web verify: unsupported suspicious edges can be removed
4. Apply contradiction / self-ref / page-title / slug-collision guards
5. Lint gate on apply

## Logging

All steps write JSONL to `data/logs/{step}_{source}_{timestamp}.jsonl` via `PipelineLogger` (`apps/pipeline/log.py`). Fields: `ts`, `elapsed`, `level`, `event`, `run_id`, `step`, `source`, plus context.

```bash
jq 'select(.level=="error")' data/logs/*.jsonl
jq 'select(.event=="edge_rejected")' data/logs/adjudicate_*.jsonl
```

## `.gangguideignore`

Parsed by `apps/pipeline/ignore.py`.

| Section | Tool | Purpose |
|---------|------|---------|
| `[enrich:skip]` | `enrich.py` | Skip org entirely |
| `[enrich:skip-field]` | `enrich.py` | Suppress one issue (`org-id  field`) |
| `[apply:skip-org]` | `apply.py` | Never overwrite these orgs |
| `[apply:skip-edge]` | `apply.py` | Never add matching edges (`source target type`, `*` = wildcard) |
| `[verify:skip]` | `verify.py` | Treat matching edges as already supported |
| `[lint:suppress]` | `lint.py` | Suppress a check (`org-id check-name`, `*` = global org) |
| `[clean:skip]` | `clean.py` | Skip org in clean |

**Enrich field names:** `no_membership`, `imprecise_year`, `no_year`, `no_symbols`, `no_aliases`, `no_colors`, `stub_desc`, `short_desc`, `single_source`

**Lint check names** (must match substrings in lint messages; aliases in `lint.py`): `cross_metro`, `metro_lane_consistency`, `description_starts_with_name`, `status_description_consistency`, `fuzzy_dupe`, `spinoff_direction`, `temporal_logic`, `page_title_org`, `stub_quality`, `nation_consistency`, `isolated`, `symbol_title_case`, `founded_year_precision`, `single_source`

```
[enrich:skip]
org:denver-lane-bloods

[apply:skip-edge]
*  *  spin_off

[lint:suppress]
org:bloods  cross_metro
```

## Enrich (`apps/pipeline/enrich.py`)

Standalone. Not in `just pipeline`.

Ranks orgs by weakness × connectivity, greps `data/raw/`, then an agentic loop (`web_search`, `fetch_url`, `court_search`) fills gaps only. Never overwrites strong fields. All search calls route through `apps/pipeline/search.py` (multi-source — see below).

```bash
just enrich
just enrich-rank
python3 -m apps.pipeline.enrich --org org:trinitarios --dry-run
```

Flags: `--dry-run`, `--limit N`, `--org ID`, `--min-edges N`, `--no-tools`, `--model`.

## Clean (`apps/pipeline/clean.py`)

Post-enrichment verification. Scores issues × connectivity, then confirms with the same tool loop. Only changes fields it can show are wrong; never clears a description without a replacement.

| Issue | Meaning |
|-------|---------|
| `impossible_year` | Founded before the movement existed |
| `precision_mismatch` | `decade` with a non-round year, or `exact` on a round year |
| `suspicious_exact_year` | Exact year ending 0 or 5 without strong sourcing |
| `implausible_membership` | Estimate too large for connectivity |
| `boilerplate_desc` | Generic "is a street gang based in X" |
| `html_in_desc` | HTML entities/tags |
| `bare_source_title` | Title is a bare domain |
| `single_source_precise` | High precision, one source |
| `desc_too_long` | Over 800 characters |
| `spot_check` | Random sample |

```bash
just clean
just clean-rank
python3 -m apps.pipeline.clean --org org:trinitarios
python3 -m apps.pipeline.clean --issues suspicious_exact_year --lane chicago-folk
```

Flags: `--dry-run`, `--limit N`, `--org ID`, `--issues CODE`, `--lane ID`, `--no-tools`, `--model`.

## Search (`apps/pipeline/search.py`)

Shared multi-source search module used by `enrich.py`, `clean.py`, and `verify.py`. All three tools import `multi_search`, `fetch_url`, and `court_search` from here rather than implementing their own HTTP logic.

### Backends (run in parallel per query, results merged and deduplicated)

| Backend | Key required | What it finds |
|---------|-------------|---------------|
| **Brave Search API** | `BRAVE_API_KEY` in `.env` | Structured web + news results, independent index |
| **DuckDuckGo HTML** | None | Free fallback, always available |
| **Wikipedia REST** | None | Clean article summaries via CirrusSearch fulltext |
| **CourtListener** | `COURTLISTENER_API_KEY` in `.env` | Federal court opinions + PACER dockets |

### Deduplication

Results are deduplicated by normalized URL (query params stripped, lowercased) and by snippet fingerprint (first 60 chars). This removes near-duplicates when multiple backends return the same article.

### LLM tools exposed

| Tool | Description |
|------|-------------|
| `web_search(query)` | Runs all backends, returns merged results |
| `fetch_url(url)` | Fetches page content; Wikipedia URLs use REST API for cleaner extraction |
| `court_search(query)` | Searches CourtListener specifically — useful for founding dates and membership estimates cited in federal indictments |

### Key behaviors

- **CourtListener fires automatically** when the query contains legal/criminal keywords: `gang`, `rico`, `indictment`, `founded`, `membership`, `federal`, `convicted`, etc.
- **Wikipedia fires automatically** for entity-like queries (mostly title-cased words)
- **DDG redirect URLs are decoded** to direct destination URLs so `fetch_url` works on DDG results
- **Rate limits**: CourtListener is 5 req/min (Access Level 5, 125/hour) — natural LLM turn delays prevent hitting this in normal use

### API keys

Add to root `.env`:
```
BRAVE_API_KEY=your_key_here
COURTLISTENER_API_KEY=your_key_here
```

Get keys at: `brave.com/search/api` (2,000 free queries/month) and `courtlistener.com` (free with account registration).
