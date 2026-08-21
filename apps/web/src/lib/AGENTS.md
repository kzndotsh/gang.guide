# src/lib

Map, inspector, overlays. Parent conventions: [`apps/web/AGENTS.md`](../AGENTS.md). Product docs: [`docs/ARCHITECTURE.md`](../../../docs/ARCHITECTURE.md).

- **KonvaMap.svelte**: bg / edge / node / label / axis layers. Nodes rebuilt on filters; edges+labels on hover/select/edgeMode. LOD hides labels at low zoom. Year ruler is sticky (screen-space).
- **laneColors.ts**: group → hex for node fill and band tint (4% alpha). Unplaced has no band. Hoover lane is orange.
- **InspectorPanel.svelte**: Overview (about + profile facts), Network, Identity, Sources (`inspectorDisplay.ts`, `inspectorConnections.ts`, `inspectorFormat.ts`).
- **overlays/**: OrgSearch (⌘K), YearSlider (top), EdgeModeToggle (`hover`/`all`, desktop bottom-center), LaneFilter, ZoomControls, EdgeLegend, CoverageDialog.

Runes only. `cn()` from `utils.ts`. Don't invent node/edge counts: read `graph.json` meta.
