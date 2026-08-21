# src/lib

Map, inspector, overlays. Parent conventions: [`apps/web/AGENTS.md`](../AGENTS.md). Product docs: [`docs/ARCHITECTURE.md`](../../../docs/ARCHITECTURE.md).

- **KonvaMap.svelte**: bg / edge / node / label layers. Nodes rebuilt on filters; edges+labels on hover/select/edgeMode. LOD hides labels at low zoom.
- **InspectorPanel.svelte**: Overview, Network, Identity, Sources (`inspectorDisplay.ts`, `inspectorConnections.ts`, `inspectorFormat.ts`).
- **overlays/**: OrgSearch (⌘K), YearSlider, ZoomControls, EdgeModeToggle (`hover`/`all`), LaneFilter, EdgeLegend, CoverageDialog.

Runes only. `cn()` from `utils.ts`. Don't invent node/edge counts: read `graph.json` meta.
