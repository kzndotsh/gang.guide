# Architecture

gang.guide is a static site backed by flat JSON files. There is no database, API server, or accounts. Curation is the hard part; serving the site is not.

## System diagram

```
data/orgs/*.json ─┐
data/edges.json ──┼─→ build.py ─→ graph.json ──→ Cloudflare Workers ──→ Browser
data/lanes.json ──┘               details.json     (static assets)       (SvelteKit + Konva)
```

Docs: [INDEX.md](INDEX.md). Agents: [`.ruler/AGENTS.md`](../.ruler/AGENTS.md).

## Layers

### Data (`data/`)

Source of truth: one JSON file per org, one edge list, one lane taxonomy. Counts live in `graph.json` `meta` after `just build-data`.

### Pipeline (`apps/pipeline/`)

Manual / `just`: not in the web runtime.

- **Scrapers** (`scrape/`): `cgh.py`, `dsg.py`, `ngcrc.py`, `nyc.py`, `stonegreasers.py`, `unitedgangs.py`, `wikipedia.py`, `stophoustongangs.py`, `adl.py`, `fbi_ngta.py`, `insightcrime.py`, `splc.py`, plus `common.py`
- **Extract / adjudicate / verify / merge / apply**: see [PIPELINE.md](PIPELINE.md)
- **Enrich / clean**: profile fill and spot-check, not part of `just pipeline`
- **lint.py**: CI gate

### Build (`build.py`)

Reads orgs + edges → `apps/web/static/graph.json` (render) and `details.json` (lazy). Also:

- Nation edges from `nation_affiliation`
- Lane-aware `display_year` when `founded_year` is missing

### Frontend (`apps/web/`)

SvelteKit with `prerender = true`, Cloudflare Workers via Alchemy (`apps/web/alchemy.run.ts`), `@sveltejs/adapter-cloudflare`.

- **KonvaMap.svelte**: four layers (bg, edges, nodes, labels). Nodes rebuilt on filter/data change, not on hover. Edges/labels redraw on selection and edge-mode change.
- **Edge modes**: `hover` ("On hover") and `all` ("All links")
- **Arrows**: nation, member_of, spin_off, parent
- **Inspector**: Overview, Network, Identity, Sources
- **URL state**: `?org=`, `?year=min-max`, `?lane=` (comma-separated IDs)

### Deployment

`just deploy` runs `vite build` then Alchemy `--stage production`. Env: `ALCHEMY_PASSWORD`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` in `apps/web/.env`. `.alchemy/` is gitignored.

## Decisions

- **No database**: org files are small; deploy as static assets
- **No API**: client loads `graph.json` once
- **Prerendered SPA**: pages are static HTML
- **Edge IDs**: 12-char hash of source+target+type
- **Undirected edges**: alliance/rivalry stored with sorted endpoints
- **Nation field is canonical**: edges derived at build
- **Lane-aware year fallback**: null `founded_year` still plots in the right era
