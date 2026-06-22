# gang.guide

Evidence-backed US criminal organization history data platform. Interactive timeline map visualization of 967 organizations, their relationships, and historical context.

**Live:** [gang.guide](https://gang.guide) (Cloudflare Workers)

## Quick start

```bash
# Build graph.json from org files
python3 build.py

# Run the web viewer
cd apps/web && npm install && npm run dev
```

## How it works

1. Each gang is a single JSON file in `data/orgs/` — edit directly
2. `python3 build.py` assembles them into `graph.json` + `details.json`
3. The SvelteKit app renders an interactive Canvas timeline map

No database, no pipeline, no dependencies beyond Python 3 and Node.js.

## Project structure

```
├── build.py                  ← Builds graph.json + details.json from flat data
├── data/
│   ├── orgs/                 ← One JSON per org (source of truth, ~980 files)
│   ├── edges.json            ← Edge list (alliances, rivalries, affiliations)
│   ├── config/lanes.json     ← Lane taxonomy + org anchors
│   └── raw/                  ← Scraped source material (gitignored, 682MB+)
├── apps/web/                 ← SvelteKit + Konva.js Canvas map viewer
│   ├── alchemy.run.ts        ← Deployment config (Cloudflare Workers via Alchemy)
│   └── svelte.config.js      ← adapter-cloudflare
└── AGENTS.md                 ← AI agent instructions
```

## Data stats

- **967 nodes** — gangs, alliances, organizations
- **1,147 edges** — alliances, rivalries, nation affiliations, spin-offs
- **2,020 sources** — across Wikipedia, StreetGangs, UnitedGangs, Chicago Gang History, DOJ/FBI
- **41 lanes** — organized by affiliation/region (Crips, Bloods, Latino, Asian, Chicago, etc.)

Field coverage:
- Description: 100%
- Founded year: 100%
- Colors: 87%
- Sources: 100%

Year precision:
- Exact/circa: 32%
- Decade-estimated: 41%
- Unresearched estimate: 27%

## Org file format

```json
{
  "id": "org:18th-street-gang",
  "name": "18th Street gang",
  "aliases": ["Barrio 18", "Calle 18", "M-18"],
  "type": "alliance",
  "lane": "california-latino-other",
  "metro": "Los Angeles",
  "founded_year": 1965,
  "founded_year_precision": "circa",
  "description": "Multi-ethnic street gang from Los Angeles, founded in the 1960s...",
  "colors": ["blue", "black"],
  "nation_affiliation": null,
  "status": "active",
  "sources": [
    {"url": "https://...", "title": "Source Name"}
  ]
}
```

## Adding a new org

1. Create `data/orgs/my-new-org.json` with the fields above
2. Add relationships to `data/edges.json` if needed
3. Run `python3 build.py`

## Data sources

| Source | References | Notes |
|--------|-----------|-------|
| Wikipedia | 855 | Manual enrichment from articles |
| StreetGangs.com | 754 | Bulk scraped (1,436 pages in raw/) |
| UnitedGangs.com | 252 | Lane taxonomy + colors |
| Chicago Gang History | 112 | 97 pages scraped + parsed |
| DOJ/FBI/DEA | 39 | Federal indictments, gang profiles |

## Lanes

Lanes are horizontal bands on the timeline map, grouped by affiliation and region:

| Group | Lanes |
|-------|-------|
| National | prison, white-supremacist, motorcycle-clubs, organized-crime |
| Chicago | folk-people, sets |
| Bloods | compton, carson, la-south-bay, other |
| Crips | gangster, hoover, neighborhood, east-coast, hustler, rollin, inglewood, long-beach, south-la, other |
| Latino (CA) | east-la, south-la, sfv, sgv, westside, harbor, inland, other |
| Asian | asian-gangs |
| Regional | new-york, midwest, southeast-southwest, historical-east, other-national |

## Web viewer

SvelteKit app with Konva.js Canvas renderer. Run with:

```bash
cd apps/web && npm install && npm run dev
```

Features:
- Interactive pan/zoom Canvas map (Konva.js, handles 980 nodes smoothly)
- Lane-based filtering with group toggles
- Year range slider (1930–2025)
- Node coloring by affiliation (Crips=blue, Bloods=red, Hoovers=orange, etc.)
- Label collision detection (overlapping labels hidden, selected always visible)
- Org inspector sidebar (description, network, identity, sources)
- Data coverage panel with quality metrics
- Search with fuzzy matching
- Lazy-loaded detail data (descriptions + sources loaded on first click)
- URL-based org linking (`?org=org:18th-street-gang`)

## Deployment

Deployed to Cloudflare Workers via [Alchemy](https://github.com/alchemy-run/alchemy) (TypeScript IaC).

```bash
# Deploy to production
cd apps/web && npm run deploy

# Preview deploy (personal stage)
cd apps/web && npm run deploy:preview

# Tear down
cd apps/web && npm run destroy
```

Requires `.env` in `apps/web/` with:
- `ALCHEMY_PASSWORD`
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

## Tech stack

- **Data**: Flat JSON files, Python build script
- **Frontend**: SvelteKit 5, Konva.js, Tailwind CSS, shadcn-svelte
- **Rendering**: Raw Konva Canvas API (imperative, 4-layer architecture)
- **Deployment**: Cloudflare Workers via Alchemy (`adapter-cloudflare`, prerendered)
