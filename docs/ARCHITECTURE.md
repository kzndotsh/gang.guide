# Architecture

## Overview

gang.guide is a static site backed by flat JSON files. There is no database, no API server, and no user accounts. The complexity lives in the data curation pipeline, not the runtime infrastructure.

## System Diagram

```
data/orgs/*.json ─┐
data/edges.json ──┼─→ build.py ─→ graph.json ──→ Cloudflare Workers ──→ Browser
data/lanes.json ──┘               details.json     (static assets)       (SvelteKit + Konva)
```

## Layers

### Data Layer (`data/`)

Flat JSON files are the source of truth. 967 org files, one edge list, one lane taxonomy.

- **Orgs** — one file per organization, human-editable
- **Edges** — single file, all relationships with IDs and optional temporal data
- **Lanes** — defines the Y-axis layout groupings on the canvas

### Pipeline Layer (`apps/pipeline/`)

Python scripts that enrich the data using LLMs. Not part of the runtime — runs manually or via `just pipeline`.

- **Extract** — sends source pages to sonnet 4.5 at 3 temperatures
- **Adjudicate** — opus 4.6 validates evidence quotes
- **Merge** — produces consensus from multiple runs
- **Apply** — conservative upgrade of org files + edges

### Build Layer (`build.py`)

Single Python script that reads all org files + edges and produces two static JSON files:

- `graph.json` — slim rendering payload (nodes + edges + layout metadata)
- `details.json` — descriptions + sources (lazy-loaded on click)

Also auto-generates nation edges from the `nation_affiliation` field.

### Frontend Layer (`apps/web/`)

SvelteKit prerendered to static HTML, deployed to Cloudflare Workers via Alchemy IaC.

- **KonvaMap.svelte** — 4-layer canvas (background, edges, nodes, labels)
- **Inspector panel** — details view when a node is selected
- **URL state** — `?org=`, `?year=`, `?lane=` sync bidirectionally

### Deployment

- Alchemy (`alchemy.run.ts`) manages Cloudflare Workers deployment
- `adapter-cloudflare` serves prerendered pages + static JSON from edge
- Zero cold starts, global CDN distribution

## Key Decisions

- **No database** — 967 files at ~2KB each = ~2MB total. Fits in memory, deploys as static assets.
- **No API** — client fetches `graph.json` once, everything is client-side after that
- **Prerendered** — no SSR needed, all pages are identical (single-page app)
- **Edge IDs** — 12-char hash of source+target+type for stable references
- **Normalized edges** — undirected types (alliance/rivalry) stored alphabetically to prevent duplicates
- **Nation edges generated at build time** — `nation_affiliation` field is canonical, edges derived
