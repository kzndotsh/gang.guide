# Pipeline

## Overview

The pipeline extracts structured data from raw HTML pages using LLMs, then merges it into the dataset.

```
data/raw/{source}/*.txt → extract → adjudicate → verify → merge → apply → data/orgs/ + edges.json
```

Run the full pipeline: `just pipeline chicago_history`

## Sources Processed

| Source Key | Scraper | Site |
|-----------|---------|------|
| `chicago_history` | `cgh.py` | Chicago Gang History |
| `detroit_dsg` | `dsg.py` | Detroit Street Gangs |
| `ngcrc` | `ngcrc.py` | National Gang Crime Research Center |
| `nyc_historical` | `nyc.py` | New York City Gangs |
| `stonegreasers` | `stonegreasers.py` | StoneGreasers |
| `unitedgangs` | `unitedgangs.py` | UnitedGangs.com |

Additional scraper: `wikipedia.py` (general-purpose Wikipedia scraping).

## Stages

### 1. Extract (`apps/pipeline/extract.py`)

Sends cleaned page text to **sonnet 4.5** at 3 temperatures (0.1, 0.3, 0.7). Uses v2 prompt.

- Input: `data/raw/{source}/{slug}.txt`
- Output: `data/extracted/{source}/{slug}/run_1.json`, `run_2.json`, `run_3.json`
- Skips pages already extracted (checks `meta.json` prompt hash)
- Resumes from existing runs on crash
- Thinking disabled on gateway for cleaner responses

Each run produces:
```json
{
  "subject_org": "Ambrose",
  "founded_year": 1958,
  "colors": ["black", "light blue"],
  "symbols": ["spear", "knight's helmet"],
  "edges": [{"target": "...", "type": "rivalry", "evidence": "...", "period": "1986-present"}],
  "orgs_mentioned": ["Folk Nation", "Rampants", ...]
}
```

### 2. Adjudicate (`apps/pipeline/adjudicate.py`)

Sends all 3 runs to **opus 4.6** which validates each edge's evidence quote. Uses v2 prompt.

- Checks: does the quote actually prove the claimed relationship type?
- Resolves: conflicting years, ambiguous names
- Filters: weak/vague evidence, hallucinated connections
- Assigns: `confidence: "high"` or `"medium"` per edge
- Output: `data/extracted/{source}/{slug}/adjudicated.json`

### 3. Verify (`apps/pipeline/verify.py`)

Post-adjudication web-search fact-checking using **haiku** for speed.

- Runs between adjudicate and merge — filters suspicious edges before consensus
- Identifies suspicious edges: weak evidence, spin_off claims, mafia membership, hearsay language
- Uses an agentic tool-use loop with `web_search` (DuckDuckGo) to verify claims
- Produces a verdict for each edge: `supported`, `unsupported`, or `uncertain`
- Removes high-confidence unsupported edges from the adjudicated result
- Output: `data/extracted/{source}/{slug}/verified.json`

### 4. Merge (`apps/pipeline/merge.py`)

Produces `consensus.json` — the final record that apply reads.

- If `adjudicated.json` exists: uses it directly (opus already filtered)
- If not: algorithmic consensus (keep data appearing in 2/3 runs)
- Output: `data/extracted/{source}/{slug}/consensus.json`

### 5. Apply (`apps/pipeline/apply.py`)

Conservative upgrade of the actual data files.

- Only upgrades weaker fields (empty colors, thin descriptions, imprecise years)
- Adds new edges that don't already exist
- `--create-orgs` flag creates stub org files for newly-mentioned orgs
- Guards against page titles (rejects names like "History of..." or "Groups in...")
- LA org metro inheritance (Piru, Compton, etc. → "Los Angeles")
- Slug collision check prevents overwriting existing files
- Skips contradictory edges unless temporal data disambiguates them
- Skips self-referencing edges
- Converts `period` strings ("1977-1992") to `start_year`/`end_year` integers
- Runs lint as final gate — rejects all changes if lint fails

## CLI Reference

```bash
just extract chicago_history          # extract from raw pages
just adjudicate chicago_history       # resolve conflicts (opus)
just verify chicago_history           # web-search fact-checking (haiku)
just merge chicago_history            # consensus filtering
just apply-preview chicago_history    # preview changes (dry run)
just apply chicago_history            # commit changes
just pipeline chicago_history         # all of the above
just enrich                           # LLM enrichment of weak org profiles
just enrich-rank                      # show org weakness × connectivity ranking
```

## Models

| Stage | Model | Temperature | Purpose |
|-------|-------|-------------|---------|
| Extract | claude-sonnet-4.5 | 0.1, 0.3, 0.7 | Structured data extraction (v2 prompt) |
| Adjudicate | claude-opus-4.6 | 0.1 | Evidence validation (v2 prompt) |
| Verify | claude-haiku | 0.1 | Web-search fact-checking of suspicious edges |
| Enrich | configurable (--model) | — | Agentic enrichment of weak org profiles |

Override via env: `EXTRACT_MODEL`, `ADJUDICATE_MODEL`

## Idempotency

- Extract: skips pages with existing runs (unless `--force`)
- Adjudicate: skips pages with existing `adjudicated.json` (unless `--force`)
- Verify: skips pages with existing `verified.json` (unless `--force`)
- Merge: skips pages with existing `consensus.json` (unless `--force`)
- Apply: skips fields already strong, edges already existing

Safe to re-run at any time.

## Quality Gates

1. **Multi-temperature consensus** — hallucinations don't repeat across 3 temps
2. **Opus adjudication** — validates evidence quotes prove claimed relationships
3. **Web-search verification** — haiku fact-checks suspicious edges via DuckDuckGo, removes unsupported claims
4. **Contradiction check** — won't add alliance where rivalry exists (without dates)
5. **Self-reference check** — won't create org→itself edges
6. **Page title guard** — rejects generic/navigational names from becoming orgs
7. **Slug collision check** — prevents overwriting existing org files
8. **Lint gate** — rejects apply if lint errors increase

## Enrich (`apps/pipeline/enrich.py`)

Standalone LLM enrichment of weak org profiles — not part of the source pipeline flow.

### Logging

All pipeline steps emit structured JSONL logs to `data/logs/`.

- **Logger**: `apps/pipeline/log.py` — `PipelineLogger` class
- **Output**: `data/logs/{step}_{source}_{timestamp}.jsonl`
- **Schema** (per line): `ts`, `elapsed`, `level`, `event`, `run_id`, `step`, `source` + context fields
- **Levels**: `debug`, `info`, `warn`, `error`
- **Events**: past-tense verbs — `edge_rejected`, `file_written`, `run_started`, etc.

Query logs with jq:

```bash
jq 'select(.level=="error")' data/logs/*.jsonl
jq 'select(.event=="edge_rejected")' data/logs/adjudicate_*.jsonl
```

### How It Works

1. **Rank** orgs by weakness × connectivity (orgs with many edges but thin profiles are prioritized)
2. **Gather context** from `data/raw/` (3794 scraped files) via ripgrep search
3. **Agentic loop** — the LLM can call `web_search` (DuckDuckGo) and `fetch_url` tools to find additional information
4. **Conservative upgrade** — only fills gaps (empty colors, missing descriptions, imprecise years); never overwrites strong existing data

### CLI Options

```bash
just enrich                           # enrich top-ranked weak orgs
just enrich-rank                      # show weakness × connectivity ranking (no changes)
```

Flags:
- `--dry-run` — preview changes without writing
- `--limit N` — max orgs to enrich per run
- `--org ID` — enrich a specific org by ID
- `--min-edges N` — minimum edge count to consider
- `--no-tools` — disable web_search/fetch_url tools
- `--model` — override the LLM model used
