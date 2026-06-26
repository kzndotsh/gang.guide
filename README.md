<div align="center">
    <p>
        <a href="https://github.com/kzndotsh/gang.guide/actions/workflows/ci.yml">
            <img alt="CI" src="https://github.com/kzndotsh/gang.guide/actions/workflows/ci.yml/badge.svg"></a>
        <a href="https://codecov.io/gh/kzndotsh/gang.guide">
            <img alt="Coverage" src="https://codecov.io/gh/kzndotsh/gang.guide/graph/badge.svg"></a>
        <a href="https://github.com/kzndotsh/gang.guide/releases">
            <img alt="Release" src="https://img.shields.io/github/v/release/kzndotsh/gang.guide?logo=github&logoColor=white"></a>
        <a href="https://svelte.dev">
            <img alt="SvelteKit" src="https://img.shields.io/badge/SvelteKit-5-ff3e00?logo=svelte&logoColor=white"></a>
        <a href="https://workers.cloudflare.com">
            <img alt="Cloudflare Workers" src="https://img.shields.io/badge/Cloudflare_Workers-f38020?logo=cloudflare&logoColor=white"></a>
        <a href="https://konvajs.org">
            <img alt="Konva.js" src="https://img.shields.io/badge/Konva.js-Canvas-0d83cd"></a>
        <a href="https://python.org">
            <img alt="Python" src="https://img.shields.io/badge/Python-3.12+-3776ab?logo=python&logoColor=white"></a>
    </p>
</div>

<img src=".github/assets/readme-header.png" alt="gang.guide" width="100%">

<div align="center">
    <h1>gang.guide</h1>
    <p><strong>Evidence backed mapping of criminal organizations across the US — alliances, rivalries, history, and culture.</strong></p>
    <p>
        <a href="https://gang.guide">🌐 Live Site</a> •
        <a href="#quick-start">🚀 Quick Start</a> •
        <a href="#data-stats">📊 Stats</a> •
        <a href="TODO.md">🗺️ Roadmap</a>
    </p>
</div>

---

## Quick Start

```bash
# Clone and setup
git clone https://github.com/kzndotsh/gang.guide.git
cd gang.guide
just setup

# Or manually:
npm install
cd apps/web && npm install
python3 build.py

# Run the dev server
just dev
```

## How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                          DATA PIPELINE                              │
│  SOURCES e.g:                                                       │
│  Wikipedia ─┐                                                       │
│  StreetGangs ─┼─→ scrape → clean HTML → LLM extract ×3              │
│  DOJ/FBI ───┘                    │                                  │
│                                  ▼                                  │
│                         consensus filter (2/3 agree)                │
│                                  │                                  │
│                                  ▼                                  │
│                         conservative merge                          │
└──────────────────────────────────┼──────────────────────────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  data/orgs/*.json  →  build.py  →  graph.json  →  SvelteKit+Konva   │
│     (967 files)       (compile)    (static)       (interactive map) │
└─────────────────────────────────────────────────────────────────────┘
```

- **No database** — flat JSON files are the source of truth
- **No CMS** — edit org files directly, run `just build-data`
- **No API** — static JSON files served from Cloudflare Workers edge

## Project Structure

```
├── build.py                  # Builds graph.json + details.json from flat data
├── data/
│   ├── orgs/                 # One JSON per org (~980 files, source of truth)
│   ├── edges.json            # Edge list (alliances, rivalries, affiliations)
│   └── lanes.json            # Lane taxonomy + org anchors
├── apps/
│   ├── web/                  # SvelteKit + Konva.js Canvas map viewer
│   │   └── alchemy.run.ts   # Deployment config (Cloudflare Workers)
│   └── pipeline/             # Python scraping, parsing, LLM extraction
├── .ruler/                   # AI agent instructions (source of truth)
├── .github/workflows/        # CI + release workflows
├── .vscode/                  # Shared editor settings + recommended extensions
├── justfile                  # Task runner commands
├── lefthook.yml              # Git hook config (commitlint)
├── commitlint.config.js      # Conventional commit enforcement
└── TODO.md                   # Roadmap
```

## Data Stats

Stats are computed at build time by `build.py` and embedded in `graph.json`.

**Sources:** Wikipedia, StreetGangs.com, UnitedGangs.com, Chicago Gang History, DOJ/FBI

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Data** | Flat JSON files, Python build script |
| **Frontend** | SvelteKit 5, Konva.js, Tailwind CSS, shadcn-svelte |
| **Rendering** | Raw Konva Canvas API (4-layer architecture) |
| **Deployment** | Cloudflare Workers via Alchemy IaC |
| **Linting** | Ruff (Python), svelte-check (frontend) |
| **CI/CD** | GitHub Actions, conventional commits, lefthook |

## Commands

```bash
just              # list all tasks
just setup        # bootstrap after cloning
just dev          # start dev server
just build-data   # rebuild graph.json from org files
just lint         # lint data integrity
just check        # type-check frontend
just deploy       # deploy to production
just ruler        # regenerate AI agent configs
```

## Adding a New Org

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
2. Add relationships to `data/edges.json` if needed
3. Run `just build-data`

## Deployment

Deployed to Cloudflare Workers via [Alchemy](https://github.com/alchemy-run/alchemy).

```bash
just deploy           # production
just deploy-preview   # personal stage
```

Requires `apps/web/.env` with `ALCHEMY_PASSWORD`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`.

## AI Agent Setup

Instructions managed via [Ruler](https://github.com/intellectronica/ruler). After cloning:

```bash
just ruler
```

This generates config files for Claude, Copilot, Cursor, and Kiro from `.ruler/AGENTS.md`.

## License

TBD

---

Created by [@kzndotsh](https://github.com/kzndotsh)
