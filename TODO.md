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
- [ ] Add `membership_estimate` for orgs where known (from pipeline output)
- [ ] Expand `symbols` coverage via pipeline (CGH pages have symbols for 97 gangs)
- [ ] Enrich thin descriptions (<100 chars) via LLM for ~75 CGH bulk-imports
- [ ] Merge `nation_affiliation` field + `nation` edge type into single approach
- [ ] `build.py` changelog: emit diff on each run (new orgs, changed fields)
- [ ] Lint: add completeness score per org
- [ ] Lint: detect edges between orgs with non-overlapping time periods
- [ ] Merge 4 duplicate org pairs (gangster-crips-47/96/97/98)
- [ ] Resolve ~30 contradictory edges (alliance + rivalry) with temporal data
- [ ] Apply CGH extraction results (run merge → apply on 73 extracted pages)
- [ ] Validate orgs against `schema.json` in lint.py

### Pipeline
- [ ] Run full pipeline on all 73 extracted CGH pages (merge → apply)
- [ ] Run extraction on remaining sources (streetgangs, wikipedia)
- [ ] Wire up Wikipedia scraper (MediaWiki API, category traversal)
- [ ] Wire up CourtListener scraper (gang-enhancement cases)
- [ ] Add `--dry-run` cost estimate to extract CLI
- [ ] Curated overrides file (blocklist/forcelist for known bad/good edges)
- [ ] Aggregate `unresolved_names` from adjudication into review queue
- [ ] Add async/concurrent extraction (run 3 temps in parallel for 3x speedup)

### Infrastructure
- [ ] `LICENSE` — MIT for code, CC-BY-4.0 for data
- [ ] Tag v1.1.0 release when pipeline enrichment is applied at scale
- [ ] Issue templates: "Add new org", "Fix org data", "Report bad edge"
- [ ] PR template with checklist (lint, build, map verification)
- [ ] Protect main branch when collaborators join
- [ ] Enable Dependabot + secret scanning (toggle when public)

### Scale (Phase 4)
- [ ] Gangland (History Channel) episode transcripts
- [ ] SPLC Intelligence Reports (white supremacist orgs)
- [ ] FBI Vault declassified files
- [ ] ATF/NDIC National Gang Threat Assessments
- [ ] LA Times gang archive series
- [ ] Texas (Tango Blast, Texas Syndicate, Barrio Azteca)
- [ ] East Coast (NYC Latin Kings, Trinitarios, DDP, more UBN sets)
- [ ] Southeast (Atlanta sets, Memphis, New Orleans)
- [ ] Pacific NW (Sureños/Norteños expansion)
- [ ] GangsterReport.com timelines

### New Sources (researched)
- [ ] **InSight Crime** (insightcrime.org) — MS-13, Tren de Aragua, cartel profiles. Structured pages, good for pipeline extraction. Fills our transnational/Latino gap.
- [ ] **SPLC/ADL profiles** — Prison gang + white supremacist detailed profiles (AB, Nazi Lowriders, PEN1). Clean HTML, low effort.
- [ ] **FBI National Gang Threat Assessment (2015)** — Single PDF, confirms memberships/territories/threat levels for top orgs. Validation source.
- [ ] **State AG press releases** (CA, IL, NY) — RICO cases explicitly name sets + relationships in legal filings. Gold for edges.
- [ ] **PACER/CourtListener RICO filings** — Legal factual basis for edges (already in plan but worth prioritizing)
- [ ] **National Gang Center (NGC/OJJDP)** — Gang surveys, risk factors, legislation database. More stats than entities but useful for validation.
- [ ] **Chronicling America (LOC)** — Historic newspapers for pre-1960 org founding dates
- [ ] **NYPL Digital Collections** — NYC gang history archives for East Coast expansion
- [ ] **DEA Cartels page** — If we expand scope to cartel-street gang connections
- [ ] **DetroitStreetGangs.com** — Detroit-specific sets
- [ ] **ADL white supremacist prison gang inventory** (2022 assessment) — State-by-state AB variants, Aryan Circle, etc.
- [ ] **START.umd Tracking Cartels** — Infographics + data on cartel operational zones (territorial edges)
- [ ] **OCVED** (ocved.mx) — Organized crime violence event data, Mexico 2000-2019+. Territorial presence dataset.
- [ ] **ACLED Mexico data** — Criminal group violence, downloadable CSV datasets
- [ ] **GI-TOC Global Organized Crime Index** (ocindex.net) — Country-level metrics, regional observatories
- [ ] **UNODC SHERLOC** — Transnational organized crime case law + legislation
- [ ] **Journal of Gang Research (NGCRC)** — Peer-reviewed, special reports on prison gangs, federal legislation
- [ ] **Europol criminal network reports** — 821+ groups analyzed, good for international expansion if scope widens

### Schema improvements
- [ ] Add `tier` field to sources: 1=legal/court, 2=academic, 3=news/wiki, 4=community. Lets adjudicate.py weigh conflicts.
- [ ] Add `evidence` field to edges (verbatim quote proving the relationship)
- [ ] Add `source_url` to edges (where the evidence came from)

---

## Done
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
- JSONL for edges — JSON array works fine at 1,147 edges, JSONL adds complexity for no benefit at this scale
- Dynamic lane assignment based on filter state — lanes are a fixed taxonomy, not user-configurable; URL params handle filtering
- Evaluate pixi.js / WebGL — Konva handles 967 nodes smoothly, no perf issues to solve yet
- Virtual rendering (only draw nodes in viewport) — all nodes render fine without virtualization at current scale
- Web Worker for layout computation — layout is instant (<50ms), no jank to offload

---
