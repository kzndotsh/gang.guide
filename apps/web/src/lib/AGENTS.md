# src/lib — Shared Components & Utilities

## Map Rendering (KonvaMap.svelte)

The map uses raw Konva.js API imperatively for performance (942 nodes + 1200 edges). Key design:
- 4 layers: `bgLayer` (grid/lanes), `edgeLayer` (bezier curves), `nodeLayer` (circles), `labelLayer` (text)
- `buildScene()` destroys and recreates all Konva objects — only called on filter/selection changes
- Pan/zoom is handled by Konva's built-in stage dragging + wheel events (no rebuild needed)
- Labels have collision detection — overlapping labels are hidden, selected label always shows on top
- LOD: labels hidden below zoom 0.45 (layer visibility toggle, not rebuild)
- Parent sends zoom commands via `zoomCommand` prop with incrementing `seq` for reactivity

## Inspector (InspectorPanel.svelte)

4-tab panel: Overview (description, year, metro), Network (edges to other orgs), Identity (colors, aliases, type), Sources (citations with links).

## Layout Helpers

- `timelineScale.ts` — converts years to pixel X positions, computes year domain
- `panZoom.ts` — clampZoom, zoomAtPoint, fitContentInViewport
- `layout.ts` — lane catalog, sort order, label truncation
- `types.ts` — GraphNode, GraphEdge, Graph, GraphEvent types
- `visibility.ts` — edge counting for display
- `orgSources.ts` — source link formatting

## Conventions

- All components use Svelte 5 runes (`$state`, `$derived`, `$effect`, `$props`)
- Export functions for component methods (though KonvaMap uses prop-based commands instead)
- `cn()` from `utils.ts` for Tailwind class merging
- UI primitives in `components/ui/` (shadcn-svelte)
