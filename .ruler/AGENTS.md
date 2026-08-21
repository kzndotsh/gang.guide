# gang.guide

US criminal organization history as JSON profiles, an LLM extract pipeline, and a timeline map.

Docs: `docs/INDEX.md`, `docs/SCHEMA.md`, `docs/STANDARDS.md`, `docs/PIPELINE.md`. Edit `.ruler/AGENTS.md`, then `just ruler`. Do not edit generated `AGENTS.md` / `CLAUDE.md`.

## Core commands

- `just dev`: start dev server
- `just build-data`: rebuild graph.json from org files
- `just lint`: lint data integrity
- `just test-all`: pytest + vitest
- `just fmt`: format + lint fix Python
- `just ci`: full CI locally
- `just deploy`: production
- `just pipeline chicago_history`: extract → adjudicate → merge → apply dry-run (**not** verify)
- `just verify <source>`: optional web-search fact-checking (modifies adjudicated.json in-place; merge reads the cleaned version)
- `just enrich` / `just enrich-rank`: weak org profiles
- `just clean` / `just clean-rank`: spot-check existing fields
- `just ruler`: regenerate AI agent configs

## Project layout

```
├── build.py
├── data/orgs/ edges.json lanes.json   # source of truth
├── data/raw/                          # scraped text (gitignored)
├── apps/web/                          # SvelteKit + Konva map
├── apps/pipeline/                     # extract, adjudicate, verify, merge, apply, enrich, clean, lint, search
├── .ruler/AGENTS.md                   # this file
├── docs/                              # human documentation
└── justfile
```

## Architecture

- `build.py` → `apps/web/static/graph.json` + `details.json`
- Prerendered SvelteKit on Cloudflare Workers (Alchemy, `apps/web/alchemy.run.ts`)
- No database. URL state: `?org=`, `?year=`, `?lane=`

## Pipeline

`just pipeline <source>` = extract → adjudicate → merge → apply (dry-run). Verify, enrich, and clean are separate.

`apps/pipeline/search.py` — shared multi-source search (Brave + DuckDuckGo + Wikipedia REST + CourtListener). Used by enrich, clean, and verify. API keys: `BRAVE_API_KEY`, `COURTLISTENER_API_KEY` in root `.env`.

Extract: sonnet 4.6 at 0.1/0.3/0.7. Adjudicate: sonnet 4.6. Merge copies `adjudicated.json` if present, else 2/3 consensus. Apply only upgrades weaker fields; lint gates. Logs: `data/logs/*.jsonl`. Ignore rules: `.gangguideignore`.

## Deployment

Env in `apps/web/.env`: `ALCHEMY_PASSWORD`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`. `just deploy` = vite build + Alchemy production. Never commit `.env` or `.alchemy/`.

## Data conventions

- Org files: see `docs/SCHEMA.md`. Lint required: `id`, `name`, `description`, `sources`. Precision: `exact` | `circa` | `decade` | `estimate`. Status: `active` | `inactive` | `unknown`. Types: `street_gang`, `prison_gang`, `motorcycle_club`, `organized_crime`, `white_supremacist`, `cybercrime_group`, `alliance`, `nation`.
- Edges: `source`, `target`, `type` required. Edge evidence is stored in `citations[]` — each entry has `url`, `title`, `evidence` (verbatim quote). Types in `edges.json`: alliance, rivalry, member_of, spin_off, parent. Nation edges come from `nation_affiliation` at build.
- `spin_off`: source is origin, target split off. `member_of`: source belongs to target (not a gang nation). Use `nation_affiliation` for Crips, Bloods, and similar.
- IDs are `org:slug` (lowercase, hyphens; filename equals slug). Never invent orgs. After org edits, run `just lint` and `just build-data`.

## Code style

Python: Ruff, 4-space, 120 cols, typed signatures, no bare `except`. TS/Svelte: runes (`$state`, `$derived`, `$effect`, `$props`), Tailwind, shadcn-svelte, no `any`. Commits: `type(scope): description`. Scopes: `web`, `data`, `pipeline`, `infra`, `deps`, `ci`, `release`.

## Constraints

- Never commit `data/raw/`
- Nested `AGENTS.md` files are local agent context: keep them thin; do not duplicate schema/pipeline here
- Conventional commits via lefthook + commitlint

## Testing

- `pytest`: unit (CI)
- `pytest -m slow`: e2e (API key)
- `cd apps/web && npx vitest run`
- Fixtures: `apps/pipeline/tests/fixtures/`

Stats: `just build-data` / `graph.json` meta. Do not hardcode org/edge counts in this file.
