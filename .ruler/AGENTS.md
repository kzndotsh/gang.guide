# gang.guide

Evidence-backed US criminal organization history data platform. Curated org profiles → LLM extraction pipeline → interactive timeline map.

## Core Commands

- `just dev` — start dev server
- `just build-data` — rebuild graph.json from org files
- `just lint` — lint data integrity
- `just test-all` — run all tests (pytest + vitest)
- `just fmt` — format + lint fix Python
- `just ci` — run full CI locally
- `just deploy` — deploy to production
- `just pipeline chicago_history` — run full LLM pipeline on a source
- `just enrich` — LLM enrichment of weak org profiles
- `just enrich-rank` — show org weakness × connectivity ranking
- `just verify <source>` — post-adjudication web-search fact-checking
- `just ruler` — regenerate AI agent configs

## Project Layout

```
├── build.py              # Generates graph.json + details.json from flat files
├── data/
│   ├── orgs/             # One JSON file per org (source of truth)
│   ├── edges.json        # Edge list (alliances, rivalries, affiliations)
│   ├── lanes.json        # Lane taxonomy + org anchors + metro defaults
│   ├── logs/             # Pipeline structured logs (JSONL, gitignored)
│   └── raw/              # 682MB scraped source material (gitignored)
├── apps/
│   ├── web/              # SvelteKit + Konva.js Canvas map viewer
│   └── pipeline/         # Python LLM extraction pipeline
│       ├── extract.py    # Multi-temp extraction (sonnet 4.5)
│       ├── adjudicate.py # Conflict resolution (opus 4.6)
│       ├── verify.py     # Post-adjudication web-search fact-checking (haiku)
│       ├── merge.py      # Consensus filtering
│       ├── apply.py      # Conservative data upgrade
│       ├── enrich.py     # LLM enrichment of weak org profiles
│       ├── log.py        # Centralized structured logging (PipelineLogger)
│       ├── lint.py       # Data validation
│       └── tests/        # Unit tests + e2e + fixtures
├── .ruler/               # AI agent instructions (source of truth)
├── justfile              # Task runner
├── pytest.ini            # Test config
└── flake.nix             # Nix dev shell
```

## Architecture

- `build.py` reads `data/orgs/*.json` + `edges.json` → outputs `apps/web/static/graph.json` (rendering) + `details.json` (lazy-loaded)
- The web app is a prerendered SvelteKit site deployed to Cloudflare Workers via Alchemy
- `+layout.ts` exports `prerender = true` — all pages are static HTML at build time
- No database — flat JSON files are the source of truth
- URL-driven state: `?org=`, `?year=`, `?lane=` params sync bidirectionally

## Pipeline

`just pipeline <source>` runs: extract → adjudicate → verify → merge → apply (dry-run)

- **Extract**: sonnet 4.5 at temps 0.1/0.3/0.7, structured JSON output with evidence quotes
- **Adjudicate**: opus 4.6 validates evidence, resolves conflicts (always runs)
- **Verify**: haiku web-search fact-checking of suspicious edges (weak evidence, spin_off claims, hearsay); removes unsupported claims
- **Merge**: algorithmic consensus (2/3 agreement) or adjudicated result
- **Apply**: conservative upgrade — only improves weaker fields, lint gates result
- **Enrich**: standalone LLM enrichment of weak org profiles (`just enrich`); scores orgs by weakness × connectivity, gathers context via ripgrep + agentic web search
- **Logging**: all steps emit structured JSONL to `data/logs/{step}_{source}_{timestamp}.jsonl` — queryable with `jq`
- **Thinking disabled** on gateway for faster/cleaner responses

## Deployment

- **IaC**: Alchemy (`alchemy.run.ts`) using `SvelteKit` resource from `alchemy/cloudflare`
- **Adapter**: `@sveltejs/adapter-cloudflare`
- **Domain**: `gang.guide` via Alchemy `domains` prop
- **Env vars**: `ALCHEMY_PASSWORD`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` in `apps/web/.env`
- **Deploy**: `just deploy` = `vite build && tsx alchemy.run.ts --stage production`
- **State**: `.alchemy/` is gitignored (contains API tokens)

## Data Conventions

- Org files: one per gang, schema includes `id`, `name`, `lane`, `metro`, `description`, `founded_year`, `founded_year_precision`, `colors`, `aliases`, `sources`, `nation_affiliation`, `status`, `disbanded_year`
- Edge schema: `source`, `target`, `type` (required) + optional `sources`, `start_year`, `end_year`
- `founded_year_precision`: `exact`, `circa`, `decade`, `estimate`
- `sources` array: objects with `url` (https) and `title`
- `lane` must match an ID in `data/lanes.json`
- All descriptions must be factual, no scrape junk, no slurs, no HTML entities
- Node IDs use format `org:slug-name`

## Code Style

**Python** (pipeline):
- Ruff enforced (config in `apps/pipeline/pyproject.toml`)
- 4-space indent, 120 char line limit
- Type hints on function signatures
- Docstrings on modules and public functions
- No bare `except:` — always specify exception type

**TypeScript/Svelte** (web):
- Svelte 5 runes: `$state`, `$derived`, `$effect`, `$props`
- Tailwind for styling, shadcn-svelte for UI components
- No `any` — use proper types or `unknown`
- Prefer `const` over `let`

**Git workflow**:
- Conventional commits: `type(scope): description` (lowercase, imperative)
- Never push directly to main without CI passing
- Run `just ci` before pushing if unsure
- Keep commits atomic — one logical change per commit

## Constraints

- Never commit `data/raw/` (682MB, gitignored)
- Never fabricate gang data — every entry must be a real organization
- Descriptions should be factual 1-3 sentences, not scraped comments
- When editing org files, always run `just build-data` after to regenerate outputs
- The web app uses Svelte 5 runes mode (`$state`, `$derived`, `$effect`, `$props`)
- `.env` is gitignored — never commit secrets
- Agent config files (`AGENTS.md`, `CLAUDE.md`, `.kiro/steering/`) are generated by Ruler from `.ruler/AGENTS.md` — edit the source, not the outputs
- Conventional commits enforced (lefthook + commitlint). Scopes: `web`, `data`, `pipeline`, `infra`, `deps`, `ci`, `release`

## Testing

- `pytest` — unit tests (no API calls, runs in CI)
- `pytest -m slow` — e2e tests (needs API key)
- `cd apps/web && npx vitest run` — web tests
- Coverage tracked via codecov, badge in README
- Golden fixtures in `apps/pipeline/tests/fixtures/` for regression detection

## Current Stats

Stats are computed at build time and embedded in `graph.json` meta. Run `just build-data` to see current counts.

- Edge types: nation, rivalry, alliance, member_of, spin-off, parent
- Top sources: Wikipedia, StreetGangs, UnitedGangs, Chicago Gang History, DOJ
