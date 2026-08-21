# apps/web: SvelteKit canvas map

Konva.js timeline map. **Architecture:** [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md). **UX:** [`docs/USER.md`](../../docs/USER.md).

## Commands

- `npm run dev` / `just dev`
- `npm run check`: svelte-check
- `npm run build` / `npm run deploy`

Deployed to Cloudflare Workers (`adapter-cloudflare`, `alchemy.run.ts`).

## Layout

```
src/lib/
├── map/           # KonvaMap, layout, panZoom, timelineScale, mapFilters, visibility
├── inspector/     # InspectorPanel, inspectorDisplay, inspectorConnections, inspectorFormat
├── overlays/      # search, year slider, zoom, edge mode, lane filter, legend, coverage
├── components/ui/ # shadcn: don't edit unless overriding
├── AppHeader.svelte
├── types.ts
└── utils.ts
```

## Rendering

Four layers: bg, edges, nodes, labels. Rebuild nodes on filter/data change; redraw edges/labels on hover, selection, and edge mode (`hover` | `all`). Do not hardcode node/edge counts.

## Conventions

Svelte 5 runes. Tailwind. shadcn-svelte. `graph.json` on load; `details.json` on first org click.

Dense, monospace, borders-only, semantic color (alliances green, rivalries red, nation/member_of purple, spin-off/parent amber). No load animations, no UI emojis, `active:scale-[0.97]`, GPU-safe `transform`/`opacity` only. ⌘K / Ctrl+K search, Esc deselect.

Components: PascalCase, `Props` + `$props()`. Types in `types.ts` as `GraphNode` / `GraphEdge`.
