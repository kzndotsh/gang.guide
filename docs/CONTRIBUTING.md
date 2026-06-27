# Contributing

## Setup

```bash
git clone https://github.com/kzndotsh/gang.guide.git
cd gang.guide
just setup
```

Requires Node 22+, Python 3.12+. Use `nix develop` for a reproducible environment with all dependencies.

## Development

```bash
just dev          # start dev server
just test-all     # run all tests
just fmt          # format + lint fix
just ci           # run full CI locally
```

## Commits

This project uses [conventional commits](https://www.conventionalcommits.org/) enforced by lefthook + commitlint.

```
feat(web): add timeline scrubber
fix(data): correct disbanded_year for BMF
docs: update README
chore(infra): update CI workflow
```

Valid scopes: `web`, `data`, `pipeline`, `infra`, `deps`, `ci`, `release`

## Adding an Org

1. Create `data/orgs/my-new-org.json`:

```json
{
  "id": "org:my-new-org",
  "name": "My New Org",
  "aliases": [],
  "type": "street_gang",
  "lane": "california-latino-other",
  "metro": "Los Angeles",
  "founded_year": 1985,
  "founded_year_precision": "circa",
  "description": "Factual 1-3 sentence description with founding context.",
  "colors": ["blue"],
  "nation_affiliation": null,
  "status": "active",
  "sources": [{"url": "https://...", "title": "Source Name"}]
}
```

2. Add edges to `data/edges.json` if relationships are known
3. Run `just build-data` and verify with `just lint`

## Data Quality Rules

- Every org needs at least one source with `url` and `title`
- Descriptions must be factual, 1-3 sentences, no scrape junk
- `founded_year_precision`: `exact`, `circa`, `decade`, `estimate`
- Never fabricate data — every entry must be a real organization
- Run `just lint` before committing data changes

## Tests

```bash
pytest                              # unit tests only (fast, no API)
pytest -m "slow"                    # e2e tests (needs API key)
pytest -m ""                        # everything
cd apps/web && npx vitest run       # web tests
```

## Pipeline

The LLM extraction pipeline requires `nix develop` and API keys (see `.env.example`).

```bash
just extract chicago_history        # extract from raw pages
just adjudicate chicago_history     # resolve conflicts (opus)
just merge chicago_history          # consensus filtering
just apply-preview chicago_history  # preview changes
just apply chicago_history          # commit changes
```

## Code Style

- Python: ruff (config in `apps/pipeline/pyproject.toml`)
- TypeScript/Svelte: handled by editor (svelte-check in CI)
- 2-space indent everywhere except Python (4-space)
- LF line endings
