# TODO.md — gang.guide roadmap

## Current state (June 2026)

- 967 orgs, 1,147 edges, 2,020 sources, 82/82 inactive orgs have `disbanded_year`
- 100% descriptions, 100% founding years, 87% colors
- SvelteKit + Konva.js canvas map, **live on Cloudflare Workers** (gang.guide)
- Full LLM pipeline: extract (sonnet 4.5) → adjudicate (opus 4.6) → merge → apply
- 129 unit tests with coverage (40%), codecov integration
- CI: ruff lint, pytest + coverage, svelte-check, vite build, codecov upload

---

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
- [ ] GangsterReport.com timelines

### Data
- [ ] ID doesn't match name slug pattern (currently info-level, not error)
- [ ] Asymmetric nation edges (org field vs edges.json mismatch)
- [ ] Edges between orgs with non-overlapping time periods
- [ ] Lanes with suspiciously few or many orgs
- [ ] Completeness score per org
- [ ] Existing edges stay sparse until organically enriched
- [ ] Add `membership_estimate` and `membership_year` for orgs where known
- [ ] Structured colors: `[{color, context}]` for gangs with subset-specific colors
- [ ] Keep `symbols` field — expand coverage from 29 orgs via LLM extraction pipeline (CGH pages have symbols for all 97 gangs)
- [ ] Merge `nation_affiliation` + `nation` edge types → single `nation` type
- [ ] Identify thin descriptions (<100 chars or just "X is a Y gang founded in Z")
- [ ] For orgs with raw pages in `data/raw/`, generate richer 2-3 sentence summaries via LLM
- [ ] Priority: the ~75 CGH bulk-imports that got auto-generated one-liners
- [ ] Target: every description should contain founding context, notable incidents, or distinguishing characteristics
- [ ] IDE autocomplete for org editing (VSCode validates on save)
- [ ] `lint.py` validates every org against schema before structural checks
- [ ] Document all fields with descriptions and examples in the schema
- [ ] `build.py` emits a `changelog.json` diff on each run: new orgs, removed orgs, changed fields
- [ ] Cumulative changelog viewable in the coverage panel or a `/changelog` page
- [ ] Extract: founding dates, territory claims, membership estimates from court filings
- [ ] These are the most authoritative sources for verified data (sworn testimony, judicial findings)
- [ ] Parsers are re-runnable without re-scraping (raw data is cached)
- [ ] `parse_index.py` builds `data/raw/index.json` mapping pages → org IDs:
- [ ] `lib/resolve.py` — entity resolution for LLM-extracted names → org IDs:
- [ ] Strip HTML entities (`&amp;`, `&#8217;`, `&nbsp;`) → proper unicode
- [ ] Remove navigation/footer/sidebar junk (CSS selectors for known source layouts)
- [ ] Collapse whitespace (multiple newlines, tabs, trailing spaces)
- [ ] Remove cookie banners, ad blocks, "related articles" sections
- [ ] Detect and strip encoding errors (mojibake: `Ã©` → `é`)
- [ ] Remove inline citations/reference markers (`[1]`, `[citation needed]`)
- [ ] Detect pages that are mostly junk (>50% non-prose: tables, lists of links, nav) — flag as low-quality
- [ ] Output quality score per page: word count, prose ratio, detected language
- [ ] Runs as first step: `raw.html` → `content.txt` — all downstream scripts read `content.txt` only
- [ ] Reads raw pages from `data/raw/`, sends each to LLM 3 times (different seeds)
- [ ] Single prompt per page extracts everything: edges, colors, years, symbols, membership, description, orgs mentioned
- [ ] Each run outputs structured JSON with evidence quotes for every edge
- [ ] Prompt requires verbatim quote from source text — no quote means no edge
- [ ] **Chunking**: pages >3,000 words split into chunks; infobox/header prepended to every chunk
- [ ] **Prompt versioning**: prompt hash stored in output; `--force-version` re-extracts stale pages
- [ ] **Idempotency**: skips pages with existing 3-run output unless `--force`
- [ ] **Error handling**: retry with backoff (3 retries), partial results saved, resume on restart
- [ ] **LLM backend**: Kiro gateway (Anthropic-compatible proxy at `KIRO_GATEWAY_URL`, default `http://127.0.0.1:9000`)
- [ ] Cost estimate: ~$0.01/page × 1,500 pages × 3 runs = ~$45 total
- [ ] Takes 3 extraction outputs per page, keeps only consistent data:
- [ ] Dedupes edges across chunks from same page before cross-run consensus
- [ ] Hallucinated edges get filtered automatically (rarely repeat across runs)
- [ ] Output: `data/extracted/{page}.json` — one consensus result per page
- [ ] Only overwrites fields that are currently weaker:
- [ ] Resolves extracted org names → org IDs via entity resolution
- [ ] Unresolved orgs mentioned in 2+ pages: auto-create with extracted fields
- [ ] Idempotent: running twice produces same result
- [ ] Writes changes to `data/orgs/` and `data/edges.json`
- [ ] Runs automatically after apply — if lint fails, changes are rejected
- [ ] Catches: impossible years (Crip before 1969), broken edge refs, junk descriptions, bad colors
- [ ] Nothing reaches graph.json unless it passes all lint error-level checks
- [ ] The LLM pipeline can propose anything — lint is the safety net
- [ ] Blocklist: edges/data to always reject (known false positives)
- [ ] Forcelist: data to always keep (manually verified facts the LLM might miss)
- [ ] Split `chicago-sets` lane when too dense
- [ ] `schema.json` enables contributors to validate their additions locally

### Pipeline
- [ ] All scrapers output to `data/raw/{source}/{slug}/` with `content.txt` + `url.txt` + `metadata.json`
- [ ] **Politeness**:
- [ ] **Error resilience**:
- [ ] **Cache/dedup**:
- [ ] Input: list of Wikipedia article URLs (from gang category pages + manual additions)
- [ ] Uses MediaWiki API (not raw HTML scraping) for stable versioned content
- [ ] Stores versioned URL (`oldid=`) so extractions are reproducible
- [ ] Extracts: body text, infobox fields, categories, inter-article links
- [ ] Auto-discovers new gang articles via Wikipedia category traversal (`Category:Street gangs`, `Category:Crips sets`, etc.)
- [ ] Incremental mode: check for new pages since last scrape
- [ ] Parse gang profile pages for structured data (name, colors, territory, allies/rivals from sidebars)
- [ ] Search CourtListener for gang-enhancement cases mentioning orgs in our dataset
- [ ] Every scraper stores raw HTML; `clean.py` produces `content.txt`; parsers extract structure from that
- [ ] **Cost controls**: `--dry-run` for token estimate, `--limit N`, `--source streetgangs`, progress bar with running cost
- [ ] Name map overrides: force specific name → org ID resolutions
- [ ] Applied after merge, before lint — overrides always win
- [ ] Court records (CourtListener) for verified dates/territories
- [ ] DetroitStreetGangs.com

### Infrastructure
- [ ] Tag git releases after major enrichment batches (v0.1 = 900 nodes, v0.2 = 980 nodes, etc.)
- [ ] Enables future server routes if needed (SSR org pages, `/api/search`, edge caching)
- [ ] `LICENSE` — MIT for code, CC-BY-4.0 for data (decide when open-sourcing)
- [ ] Enable Dependabot alerts + security updates (auto for public repos)
- [ ] Enable secret scanning + push protection (auto for public repos)
- [ ] Protect main branch (require PR for collaborators, allow maintainer direct push)
- [ ] Enable Discussions (for questions/community, lighter than issues)
- [ ] Tag git releases after major milestones (v1.1=1200 nodes, v2.0=2000+)
- [ ] Issue templates: "Add new org", "Fix org data", "Report bad edge"
- [ ] PR template with checklist: ran lint, ran build, verified on map

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
