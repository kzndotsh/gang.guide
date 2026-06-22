99;6u# apps/web — SvelteKit Canvas Map Viewer

Interactive timeline map of 968 gang organizations rendered on HTML5 Canvas via Konva.js.

## Commands

- `npm run dev` — start dev server
- `npx svelte-check --threshold error` — type-check
- `npx vite build` — production build

## Key Files

```
src/lib/
├── map/               ← Canvas rendering (KonvaMap, tooltip, scale, zoom, visibility)
├── inspector/         ← Org detail sidebar (InspectorPanel + logic files)
├── overlays/          ← Floating UI (search, zoom, year slider, lane filter, coverage)
├── components/ui/     ← shadcn primitives
├── AppHeader.svelte   ← Top bar (branding + stats + coverage + changelog)
├── types.ts           ← Graph/Node/Edge type definitions
└── utils.ts           ← Shared utilities
```

## Architecture

- **Konva.js** — imperative Canvas API, 4 layers: bg (grid/lanes), edges (bezier curves), nodes (circles), labels (text)
- `buildScene()` destroys and recreates all Konva objects on filter/selection changes
- Pan/zoom via Konva's built-in stage dragging + wheel events (no rebuild needed)
- Labels: bounding-box collision detection hides overlapping, selected/hovered always on top
- `zoomCommand` prop with incrementing `seq` for parent→child communication
- Floating overlays: MapOverlay component positions controls at map corners

## Conventions

- Svelte 5 runes: `$state`, `$derived`, `$effect`, `$props`
- shadcn-svelte component library (all components installed)
- Tailwind CSS for styling
- Static adapter (Cloudflare Workers via Alchemy planned)
- graph.json loaded at page mount; details.json lazy-loaded on first org click

## UI Design Rules

- **Dense & functional** — this is a data tool, not a marketing site. Prioritize information density.
- **Monospace font** globally (JetBrains Mono / SF Mono / Fira Code)
- **No heavy shadows** — `shadow-sm` max. Never `shadow-md` or higher.
- **Borders**: solid `border-border`, never thick or colorful. 1px only.
- **Border radius**: `rounded-lg` (8px) for overlays/cards. Never `rounded-xl` or `rounded-2xl`.
- **Solid backgrounds** on overlays — `bg-card`, no transparency/blur on map controls.
- **Text colors**: off-tones only (oklch 0.94 not pure white, muted-foreground for secondary).
- **Color is semantic** — used for data meaning (Crips=blue, Bloods=red, alliances=green, rivalries=red), not decoration.
- **Active states**: `active:scale-[0.97]` on all interactive buttons for tactile feel.
- **No animations on load** — no scroll-entry, no stagger reveals. The map IS the content.
- **GPU-safe only** — animate exclusively via `transform` and `opacity`. Never `top/left/width/height`.
- **No emojis** in UI — use icons or symbols (⌘ is fine, 🎉 is not).
- **Consistent overlay sizing**: all floating map controls use `h-6` content + `p-0.5` wrapper + same border/bg.
- **shadcn first** — use shadcn primitives (Slider, Command, Kbd, Dialog, Badge) before building custom.
- **Components**: single responsibility, typed Props interface, PascalCase filenames.
- **No dead code** — remove unused imports, files, and features immediately.

## UX & Interaction Rules

- `timing-under-300ms` — all user-initiated transitions complete within 300ms
- `timing-consistent` — similar elements use identical timing values
- `easing-no-linear-motion` — never use `linear` easing except progress bars
- `physics-active-state` — interactive elements need `:active` scale transform
- `none-high-frequency` — no animation for rapid repeated actions (typing, scrolling)
- `none-keyboard-navigation` — keyboard nav is instant, no transition
- `ux-fitts-target-size` — min 24px touch targets (our h-6 standard)
- `ux-fitts-hit-area` — expand hit areas with padding, not visible size
- `ux-doherty-under-400ms` — respond within 400ms to feel instant
- `ux-hicks-minimize-choices` — minimize choices per interaction (lane filter groups, not 41 individual lanes)
- `ux-millers-chunking` — chunk data into scannable groups (coverage panel sections)
- `ux-proximity-grouping` — group related elements spatially
- `ux-jakobs-familiar-patterns` — ⌘K for search, Esc to deselect, scroll to zoom

## Typography Rules

- `type-tabular-nums-for-data` — all numbers in stats/counts use `tabular-nums`
- `type-antialiased-on-retina` — `antialiased` font smoothing enabled globally
- `type-font-display-swap` — prevent invisible text during font load
- `type-letter-spacing-uppercase` — add tracking to uppercase text (lane group labels)

## Interface Design Intent

**User:** Researcher/journalist exploring gang history and connections. Laptop, cross-referencing sources.
**Task:** Find org → see connections → understand history → discover related orgs.
**Feel:** Cold like a terminal. Dense like a trading floor. Precise like an intelligence briefing.
**Signature:** Timeline lane structure — horizontal taxonomy bands with time flowing left-to-right.

## Depth Strategy

- **Borders-only** — clean, technical. No shadows for hierarchy.
- Surfaces: same hue, shift only lightness for elevation (sidebar = same bg as canvas, border separates)
- Inputs: slightly darker than surroundings (inset feel)
- Dropdowns: one level above parent surface

## Avoid

- Harsh borders (if borders are first thing you see, too strong)
- Dramatic surface jumps (elevation whisper-quiet)
- Inconsistent spacing (clearest sign of no system)
- Gradients and decorative color (color = meaning only)
- Multiple accent colors (dilutes focus)
- Different hues for different surfaces (same hue, shift lightness)
- Pure white cards on colored backgrounds
- Missing interaction states (hover, focus, disabled, loading, error)
- Spring/bounce animations in this professional context
- First-idea implementations without considering alternatives (design it twice)

## Component Naming & Structure

### Layout zones
```
┌──────────────────────────────────────────────┬──────────────────────┐
│              WORKSPACE                       │      INSPECTOR       │
│                                              │                      │
│  ┌────────────────────────────────────────┐  │  Org Name            │
│  │ HEADER (stats · coverage · changelog)  │  │  ───────────         │
│  └────────────────────────────────────────┘  │  type · metro · yr   │
│                                              │                      │
│  ┌────────────VIEWPORT────────────────────┐  │  [Overview][Network] │
│  │ Search…  ⌘K              1930━━━━2025  │  │  [Identity][Sources] │
│  │                                        │  │                      │
│  │   ┌───────CANVAS────────────────────┐  │  │  About               │
│  │    ┄lane┄  ● ● ●   ●                   │  │  Description text... │
│  │    ┄lane┄    ● ●     ●                 │  │                      │
│  │    ┄lane┄  ●   ●   ● ●                 │  │  Also known as       │
│  │   └─────────────────────────────────┘  │  │  Alias One           │
│  │                                        │  │  Alias Two           │
│  │ nation·focus·all           − 100% + ⛶  │  │  Alias Three         │
│  │ All·Bloods·Crips·Chicago…              │  │                      │
│  └────────────────────────────────────────┘  │                      │
│                                              │                      │
└──────────────────────────────────────────────┴──────────────────────┘
```

- **Workspace** — left pane (header + viewport)
- **Viewport** — the clipping container (`<main>`) that holds the canvas + overlays
- **Canvas** — the Konva drawing (`KonvaMap.svelte`) with lanes, nodes, edges
- **Overlays** — floating controls positioned over the canvas within the viewport
- **Header** — top bar with stats/icons
- **Inspector** — right pane with org details (tabs: Overview, Network, Identity, Sources)

### File organization

```
src/lib/
├── map/              ← Canvas rendering (Konva, layout, pan/zoom, scale)
│   ├── KonvaMap.svelte        ← Main canvas component (lanes, nodes, edges, pan/zoom)
│   ├── MapNodeTooltip.svelte  ← Hover tooltip
│   ├── layout.ts              ← Lane/node layout helpers (slot assignment, labels)
│   ├── panZoom.ts             ← Pan/zoom math (clamp, fit, zoom-at-point)
│   ├── timelineScale.ts       ← Year → x-position mapping, tick generation
│   ├── mapFilters.ts          ← Node visibility filtering (metro, year, lane)
│   ├── mapState.ts            ← Shared map state
│   ├── mapViewOptions.ts      ← Edge mode options config
│   └── visibility.ts          ← Edge count helpers
├── inspector/        ← Right panel (org detail)
│   ├── InspectorPanel.svelte  ← Main inspector component
│   ├── inspectorDisplay.ts    ← Display helpers (title, type labels)
│   └── connections.ts         ← Edge grouping for Network tab
├── overlays/         ← Floating map controls
│   ├── MapOverlay.svelte      ← Position wrapper (top-left, bottom-right, etc.)
│   ├── OrgSearch.svelte       ← ⌘K search dialog
│   ├── YearSlider.svelte      ← Dual-thumb year range
│   ├── ZoomControls.svelte    ← +/−/fit buttons
│   ├── EdgeModeToggle.svelte  ← Nation/Focus/All toggle
│   ├── LaneFilter.svelte      ← Lane group visibility
│   └── CoverageDialog.svelte  ← Data quality modal
├── components/ui/    ← shadcn-svelte primitives (don't edit unless overriding)
├── AppHeader.svelte  ← Top bar (branding, stats, icons)
├── types.ts          ← Graph/Node/Edge interfaces
├── utils.ts          ← cn() + general helpers
├── yearFormat.ts     ← Year span formatting
├── orgSources.ts     ← Source URL helpers
└── searchNodes.ts    ← Fuzzy search logic
```

### Naming conventions

- **Components**: PascalCase, descriptive (`YearSlider` not `Slider`, `EdgeModeToggle` not `Toggle`)
- **Utilities**: camelCase files, named exports (`yearFormat.ts` exports `formatYearSpan()`)
- **Types**: in `types.ts`, prefixed with domain (`GraphNode`, `GraphEdge`, not `Node`, `Edge`)
- **CSS**: Tailwind only, no custom CSS classes except global overrides in `app.css`
- **State**: Svelte 5 runes (`$state`, `$derived`, `$effect`), no stores
- **Props interface**: always named `Props`, destructured with `$props()`
