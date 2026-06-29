# TODO.md — gang.guide roadmap

## Pending

### Frontend
- [ ] Timeline uses inferred dates (org founded/disbanded) as fallback when edge has no explicit period
- [ ] Compare mode — select two orgs, highlight shared connections
- [ ] Timeline scrubber — animate through decades using edge `period` data
- [ ] Identity-colored node dots (use org's first color as circle fill)
- [ ] Color swatches in inspector panel
- [ ] Edge labels on hover (show relationship type + period)
- [ ] Sources tab: group by domain (Wikipedia, StreetGangs, DOJ, etc.) for scannability
- [ ] Static org pages at `/org/crips` rendered at build time
- [ ] OpenGraph meta tags per org
- [ ] Sitemap generation in build.py

### Data
- [ ] Enrich thin descriptions (<100 chars) via LLM for stub orgs (~200 remaining)
- [ ] `build.py` changelog: emit diff on each run (new orgs, changed fields)
- [ ] Lint: detect edges between orgs with non-overlapping time periods
- [ ] Merge 4 duplicate org pairs (gangster-crips-47/96/97/98)
- [ ] Resolve ~30 contradictory edges (alliance + rivalry) with temporal data
- [ ] Audit 101 cross-metro rivalry edges (from lint check_cross_metro)
- [ ] Backfill founded_year on remaining 29 historical-east stubs

### Pipeline
- [ ] Run extraction on remaining sources (streetgangs, prisongang, SPLC/ADL)
- [ ] Wire up Wikipedia scraper (MediaWiki API, category traversal)
- [ ] Wire up CourtListener scraper (gang-enhancement cases)
- [ ] Add `--dry-run` cost estimate to extract CLI
- [ ] Curated overrides file (blocklist/forcelist for known bad/good edges)
- [ ] Aggregate `unresolved_names` from adjudication into review queue
- [ ] Add async/concurrent extraction (run 3 temps in parallel for 3x speedup)
- [ ] Metro-aware resolve() — prefer same-city match for ambiguous names
- [ ] Enrichment pass: backfill thin descriptions on stub orgs via LLM

### Infrastructure
- [ ] `LICENSE` — MIT for code, CC-BY-4.0 for data
- [ ] Issue templates: "Add new org", "Fix org data", "Report bad edge"
- [ ] PR template with checklist (lint, build, map verification)
- [ ] Protect main branch when collaborators join
- [ ] Enable Dependabot + secret scanning (toggle when public)

---

## Done
- [x] Run full pipeline on UnitedGangs (1400+ edges, largest single-source extraction)
- [x] Run full pipeline on Detroit (25 pages, +78 orgs, +127 edges)
- [x] Run full pipeline on NGCRC (6 academic profiles, +9 edges)
- [x] Run full pipeline on NYC Historical (115 pages, +156 orgs, +178 edges)
- [x] Run full pipeline on StoneGreasers (42 pages, +17 orgs, +42 edges)
- [x] Auto-create org files from pipeline (`apply.py --create-orgs`)
- [x] Backfill source_url on 788 CGH edges
- [x] Backfill founded_year on 110 historical NYC/Chicago orgs (manual research)
- [x] Lane-aware display_year fallback in build.py (historical orgs placed in correct era)
- [x] Detroit lane created, 65 orgs assigned
- [x] Scrapers: dsg.py, ngcrc.py, nyc.py, stonegreasers.py
- [x] Prompt v2: extraction + adjudication rewritten with Anthropic best practices
- [x] Lint: check_cross_metro, check_page_title_orgs, check_stub_quality, check_nation_consistency, check_spinoff_direction
- [x] Pipeline guards: reject page titles, LA identifier detection, slug collision check, nation contradiction gate
- [x] Evidence UI: toggle button with "quote — source" format, spacing fix
- [x] Inspector tabs: consistent (#) count format
- [x] Changelog modal: redesigned with inline diffs
- [x] Persistent nodes architecture (never destroyed on hover/select)
- [x] Edge-index based rendering for O(1) edge lookup
- [x] Edge modes: 'on hover' and 'all links' toggle
- [x] Edge legend overlay (color-coded by type)
- [x] Directional arrows on nation/spin-off/member_of/parent edges
- [x] Unified top bar layout with pill-styled controls (zoom, search, year slider)
- [x] Spelling variant duplicate detection in lint (Gangster/Gangsta, etc.)
- [x] Network tab: connection count in header
- [x] README: sources table, architecture in tech stack, stats SVG
- [x] Merge nation_affiliation + nation edge type (field is source of truth, build.py generates)
- [x] Add evidence field to edges (from pipeline adjudication)
- [x] Expand symbols coverage via CGH pipeline (110 field upgrades)
- [x] Run full pipeline on 93 CGH pages (extract → adjudicate → merge → apply)
- [x] Normalize edge schema: add IDs, deduplicate, fix direction
- [x] Remove nation edges from file (field is source of truth, build.py generates)
- [x] Add contradiction gate to apply.py (skip without temporal data)
- [x] Lower quality threshold to 10% (extracted 20 more pages)
- [x] Write docs: USER.md, ARCHITECTURE.md, TERMINOLOGY.md, PIPELINE.md, SCHEMA.md
- [x] Duplicate org IDs
- [x] Edges pointing to non-existent org IDs
- [x] Self-referencing edges (org allied with itself)
- [x] Duplicate edges (same source+target+type)
- [x] Missing required fields (id, name, lane, description, founded_year, sources)
- [x] Lane IDs not in lanes.json
- [x] Sources without both url and title
- [x] `disbanded_year` before `founded_year`
- [x] Descriptions containing HTML entities/scrape junk
- [x] Aliases that are absurdly long (>50 chars)
- [x] Colors that aren't real colors
- [x] Founded years impossible for org type (Crip before 1969, Piru before 1972)
- [x] Contradictory edges (alliance AND rivalry between same pair)
- [x] Fuzzy duplicate detection (Levenshtein + Dice, 90% threshold, numbered-set filter)
- [x] Over-cited source URLs (same URL in 15+ orgs)
- [x] Orgs with only 1 source (under-sourced)
- [x] Orgs with zero edges (isolated nodes)
- [x] Orgs with `estimate`/`decade` precision years
- [x] Temporal logic (orgs older than affiliated nation)
- [x] Boilerplate descriptions
- [x] ID-filename mismatches
- [x] Add optional `sources`, `start_year`, `end_year` fields to edge schema
- [x] `build.py` passes through new fields to graph.json
- [x] `lint.py` validates temporal consistency (end < start, start before org founded)
- [x] LLM pipeline populates these fields as it extracts new edges
- [x] Add `disbanded_year` for inactive orgs (82/82 done)
- [x] Tighten `type` enum: `street_gang` (was set/faction), `organized_crime` (was crime_family/organization), `motorcycle_club`, `prison_gang`, `white_supremacist` (was hate_group), `alliance`, `nation`
- [x] Empty `founded_year_precision` (205 orgs) → set to `"estimate"`
- [x] Empty `status` (840 orgs) → set to `"active"`
- [x] Collapse `"defunct"` → `"inactive"`
- [x] Missing `aliases` (322 orgs) → set to `[]`
- [x] Missing `colors` (122 orgs) → set to `[]`
- [x] Missing `metro` (2 orgs) → filled in
- [x] Remove `confidence` field from all edges
- [x] Remove `nation_affiliation` edges from edges.json (auto-generated by build.py)
- [x] 14 descriptions under 100 chars → enriched
- [x] Merged 12 duplicate orgs
- [x] Deduplicate source URLs across orgs (normalize trailing slashes, http→https, www prefix)
- [x] Flag sources with slightly different titles pointing to same URL
- [x] Remove dead domains (checked — none found, all sources are legitimate) — replace with archive.org where possible
- [x] Write formal JSON Schema for org files
- [x] Idempotent: skip existing pages unless `--force`
- [x] Resumable: resume from existing run_*.json files on crash
- [x] No scraper depends on another — each source is independent
- [x] Already have 1,436 pages in `data/raw/streetgangs/` from prior bulk scrape
- [x] URL-driven state: `?lane=chicago&year=1970-1990&q=disciples`
- [x] Deploy via [Alchemy](https://github.com/alchemy-run/alchemy) (TypeScript IaC) to Cloudflare Workers
- [x] `alchemy.run.ts` config using `SvelteKit` resource from `alchemy/cloudflare`
- [x] Swap `adapter-static` → `@sveltejs/adapter-cloudflare` in `svelte.config.js`
- [x] Custom domain: `gang.guide` via `domains` prop
- [x] `.env` with `ALCHEMY_PASSWORD`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`
- [x] Package scripts: `npm run deploy`, `deploy:preview`, `destroy`
- [x] Add domain to Cloudflare account (nameservers)
- [x] First deploy to production (live at gang.guide)
- [x] Add `export const prerender = true` to `src/routes/+layout.ts` (static asset serving)
- [x] `prerender.handleHttpError: 'warn'` for missing favicon during build
- [x] `.nvmrc` — pin Node version (22)
- [x] `.editorconfig` — consistent formatting across editors
- [x] `.gitattributes` — line ending normalization, linguist hints
- [x] `.vscode/settings.json` — Svelte, Tailwind, Ruff, performance exclusions
- [x] `.vscode/extensions.json` — recommended extensions
- [x] `justfile` — task runner (`just dev`, `just deploy`, `just lint`, etc.)
- [x] Root `package.json` — commitlint, lefthook, ruler as global devDeps
- [x] Proper `.gitignore` — `.alchemy/`, `.wrangler/`, `.cursor/`, `.env`, `data/raw/`, `apps/web/build/`
- [x] `.env.example` — document required env vars for deployment
- [x] Social media preview image (screenshot of the map)
- [x] Repository description + topics on GitHub
- [x] Commitlint (`commitlint.config.js`) — enforces conventional commits
- [x] Lefthook (`lefthook.yml`) — runs commitlint on commit-msg hook
- [x] Scopes: `web`, `data`, `pipeline`, `infra`, `deps`, `ci`, `release`
- [x] Ruler (`.ruler/`) — single source of truth for AI agent instructions
- [x] Generated agent configs (`AGENTS.md`, `CLAUDE.md`, `.kiro/steering/`) are gitignored
- [x] CI workflow (`.github/workflows/ci.yml`) on push/PR to main:
- [x] Release workflow (`.github/workflows/release.yml`) on `v*` tags:
- [x] Secrets in GitHub: `ALCHEMY_PASSWORD`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`
- [x] `ALCHEMY_CI_STATE_STORE_CHECK=false` for CI deploys (no remote state store)
- [x] v1.0.0 tagged and released
- [x] Git IS the backup — force-push protection on main branch — force-push protection on main branch
- [x] `data/raw/` stays gitignored (682MB) — backed up separately or re-scrapeable — backed up separately or re-scrapeable
- [x] CONTRIBUTING.md with org file format, quality standards, source requirements

---

## Discarded
- JSONL for edges — JSON array works fine at 3,152 edges, JSONL adds complexity for no benefit at this scale
- Dynamic lane assignment based on filter state — lanes are a fixed taxonomy, not user-configurable; URL params handle filtering
- Evaluate pixi.js / WebGL — Konva handles 1,201 nodes smoothly, no perf issues to solve yet
- Virtual rendering (only draw nodes in viewport) — all nodes render fine without virtualization at current scale
- Web Worker for layout computation — layout is instant (<50ms), no jank to offload

---
