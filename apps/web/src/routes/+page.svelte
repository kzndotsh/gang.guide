<script lang="ts">
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import KonvaMap from '$lib/map/KonvaMap.svelte';
  import { type EdgeMode } from '$lib/map/KonvaMap.svelte';
  import InspectorPanel from '$lib/inspector/InspectorPanel.svelte';
  import AppHeader from '$lib/AppHeader.svelte';
  import OrgSearch from '$lib/overlays/OrgSearch.svelte';
  import MapOverlay from '$lib/overlays/MapOverlay.svelte';
  import ZoomControls from '$lib/overlays/ZoomControls.svelte';
  import YearSlider from '$lib/overlays/YearSlider.svelte';
  import * as Kbd from '$lib/components/ui/kbd/index.js';
  import LaneFilter from '$lib/overlays/LaneFilter.svelte';
  import EdgeModeToggle from '$lib/overlays/EdgeModeToggle.svelte';
  import EdgeLegend from '$lib/overlays/EdgeLegend.svelte';
  import type { Graph } from '$lib/types';
  import { visibleEdgeCount } from '$lib/map/visibility';
  import { PaneGroup, Pane, Handle } from '$lib/components/ui/resizable/index.js';
  import * as Drawer from '$lib/components/ui/drawer/index.js';
  import { IsMobile } from '$lib/hooks/is-mobile.svelte.js';
  import { DEFAULT_YEAR_MIN, replaceLocation, yearQueryValue } from '$lib/urlState';

    const INSPECTOR_LAYOUT_KEY = 'gang-guide-inspector';
  const INSPECTOR_MIN_SIZE = 16;
  const INSPECTOR_MAX_SIZE = 50;
  const INSPECTOR_DEFAULT_SIZE = 30;

  let { data } = $props();

  let selectedId = $state<string | null>(null);
  let edgeMode = $state<EdgeMode>('hover');
  let zoomCmd = $state<{ action: 'in' | 'out' | 'fit' | 'focus'; target?: string; seq: number } | null>(null);
  let zoomSeq = 0;
  function sendZoom(action: 'in' | 'out' | 'fit' | 'focus', target?: string) {
    zoomCmd = { action, target, seq: ++zoomSeq };
  }
  let zoomPct = $state(100);
  let searchRef = $state<OrgSearch | null>(null);
  let yearMin = $state(DEFAULT_YEAR_MIN);
  let yearMax = $state(new Date().getFullYear());
  let hiddenLanes = $state<Set<string>>(new Set());
  let yearPreferenceRestored = false;

  // Restore filters from localStorage
  if (browser) {
    const saved = localStorage.getItem('gang-guide-filters');
    if (saved) {
      try {
        const f = JSON.parse(saved);
        if (f.yearMin) { yearMin = f.yearMin; yearPreferenceRestored = true; }
        if (f.yearMax) { yearMax = f.yearMax; yearPreferenceRestored = true; }
        if (f.hiddenLanes) hiddenLanes = new Set(f.hiddenLanes);
      } catch {}
    }
  }

  // Align yearMax to the graph (not the calendar year) when the user has no saved range.
  // Otherwise first paint of `/` writes `?year=1930-{thisYear}` and aborts hydration.
  $effect(() => {
    if (!yearPreferenceRestored) {
      yearMax = yearDomain.max;
    }
  });

  // Save filters on change
  $effect(() => {
    if (!browser) return;
    localStorage.setItem('gang-guide-filters', JSON.stringify({
      yearMin,
      yearMax,
      hiddenLanes: [...hiddenLanes],
    }));
  });

  const graph = $derived(data.graph as Graph);

  // Year domain derived from actual graph data — not hardcoded
  const yearDomain = $derived.by(() => {
    const years = graph.nodes
      .map((n) => n.data?.layout?.display_year ?? n.data?.founded_year)
      .filter((y): y is number => typeof y === 'number' && y > 1000);
    if (!years.length) return { min: 1800, max: new Date().getFullYear() };
    return {
      min: Math.floor(Math.min(...years)),
      max: Math.ceil(Math.max(...years)),
    };
  });

  // Lane groups for the filter panel
  const laneGroups = $derived.by(() => {
    const groups: Record<string, string[]> = {};
    for (const lane of graph.meta?.lanes ?? []) {
      const group = (lane as any).group ?? 'Other';
      if (!groups[group]) groups[group] = [];
      groups[group].push(lane.id);
    }
    return groups;
  });

  function toggleLaneGroup(group: string) {
    const lanes = laneGroups[group] ?? [];
    const allHidden = lanes.every(l => hiddenLanes.has(l));
    const next = new Set(hiddenLanes);
    if (allHidden) {
      lanes.forEach(l => next.delete(l));
    } else {
      lanes.forEach(l => next.add(l));
    }
    hiddenLanes = next;
  }
  const selectedNode = $derived(
    selectedId ? (graph.nodes.find((n) => n.id === selectedId) ?? null) : null
  );

  // Lazy-load details (descriptions, sources) on demand
  let detailsCache = $state<Record<string, { description?: string; sources?: any[]; edges?: any[] }>>({});
  let detailsLoaded = $state(false);

  async function loadDetails() {
    if (detailsLoaded) return;
    const res = await fetch('/details.json');
    if (res.ok) {
      const data = await res.json();
      detailsCache = data.nodes ?? {};
      detailsLoaded = true;
    }
  }

  // Load details when first node is selected
  $effect(() => {
    if (selectedId && !detailsLoaded) {
      loadDetails();
    }
  });

  // Enrich selected node with details
  const enrichedNode = $derived.by(() => {
    if (!selectedNode) return null;
    const details = detailsCache[selectedNode.id];
    if (!details) return selectedNode;
    return {
      ...selectedNode,
      data: {
        ...selectedNode.data,
        description: details.description ?? selectedNode.data?.description,
        sources: details.sources ?? selectedNode.data?.sources,
        edgeEvidence: details.edges ?? [],
      },
    };
  });

  const visibleEdgeCountDerived = $derived(
    visibleEdgeCount(graph, edgeMode, selectedId)
  );

  const isMobile = new IsMobile();
  let urlSyncEnabled = $state(false);

  onMount(() => {
    if (!browser) return;
    const params = new URL(window.location.href).searchParams;

    // Restore org from URL
    const org = params.get('org');
    if (org && graph.nodes.some((n) => n.id === org)) {
      selectFromSearch(org);
    }

    // Restore year range from URL
    const y = params.get('year');
    if (y && y.includes('-')) {
      const [min, max] = y.split('-').map(Number);
      if (min >= 1800 && max <= 2030) {
        yearMin = min;
        yearMax = max;
        yearPreferenceRestored = true;
      }
    }

    // Restore hidden lanes from URL
    const lane = params.get('lane');
    if (lane) {
      const allLanes = graph.meta?.lanes?.map((l: any) => l.id) ?? [];
      const showLanes = new Set(lane.split(','));
      hiddenLanes = new Set(allLanes.filter((l: string) => !showLanes.has(l)));
    }

    // Wait until after layout/paint so a query rewrite cannot abort first load.
    let cancelled = false;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (!cancelled) urlSyncEnabled = true;
      });
    });
    return () => {
      cancelled = true;
    };
  });

  // Sync state → URL after restore. Native history only — Kit replaceState can abort `/`.
  $effect(() => {
    if (!browser || !urlSyncEnabled) return;
    const url = new URL(window.location.href);

    if (selectedId) url.searchParams.set('org', selectedId);
    else url.searchParams.delete('org');

    const year = yearQueryValue(yearMin, yearMax, yearDomain.max);
    if (year) url.searchParams.set('year', year);
    else url.searchParams.delete('year');

    // Only set lane param if something is hidden
    if (hiddenLanes.size > 0) {
      const allLanes = graph.meta?.lanes?.map((l: any) => l.id) ?? [];
      const visible = allLanes.filter((l: string) => !hiddenLanes.has(l));
      url.searchParams.set('lane', visible.join(','));
    } else {
      url.searchParams.delete('lane');
    }

    replaceLocation(`${url.pathname}${url.search}${url.hash}`);
  });

  function onInspectorOpenChange(open: boolean) {
    if (!open) deselect();
  }

  function select(id: string) {
    if (selectedId === id) {
      deselect();
      return;
    }
    selectedId = id;
  }

  function selectFromSearch(id: string) {
    if (selectedId === id) {
      sendZoom("focus", id);
      return;
    }
    selectedId = id;
    sendZoom("focus", id);
  }

  function deselect() {
    selectedId = null;
  }

  function resetHome() {
    selectedId = null;
    edgeMode = 'hover';
    hiddenLanes = new Set();
    yearMin = DEFAULT_YEAR_MIN;
    yearMax = yearDomain.max;
    yearPreferenceRestored = true;
    if (browser) localStorage.removeItem('gang-guide-filters');
    sendZoom('fit');
  }

  function onKeydown(e: KeyboardEvent) {
    const tag = (e.target as HTMLElement)?.tagName;
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      searchRef?.focusSearch();
      return;
    }
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'BUTTON') return;

    if (e.key === 'Escape') {
      deselect();
      return;
    }
    if (e.key === '+' || e.key === '=') {
      e.preventDefault();
      sendZoom("in");
      return;
    }
    if (e.key === '-') {
      e.preventDefault();
      sendZoom("out");
      return;
    }
    if (e.key === 'f' || e.key === 'F') {
      e.preventDefault();
      sendZoom("fit");
      return;
    }
  }
</script>

<svelte:head>
  <title>gang.guide</title>
</svelte:head>

<svelte:window onkeydown={onKeydown} />

<div class="fixed inset-0 h-dvh overflow-hidden bg-background pb-[env(safe-area-inset-bottom)]" style="background-color:#0d1117">
  {#snippet mapWorkspace()}
      <div class="flex h-full flex-col">
        <AppHeader
          {graph}
          {selectedId}
          nodeCount={graph.nodes.length}
          edgeCount={visibleEdgeCountDerived}
          onhome={resetHome}
        />
        <main class="relative min-h-0 flex-1 overflow-hidden bg-background">
          <KonvaMap
            zoomCommand={zoomCmd}
            {graph}
            {selectedId}
            {edgeMode}
            {yearMin}
            {yearMax}
            {hiddenLanes}
            onselect={select}
            ondeselect={deselect}
            onzoom={(z) => (zoomPct = Math.round(z * 100))}
          />
          <div class="absolute top-12 right-3 left-3 z-[2] flex items-center gap-2 md:top-3 md:justify-between">
            <button
              class="flex h-8 min-w-0 flex-1 items-center gap-1.5 rounded-full bg-muted px-3 text-muted-foreground hover:text-foreground active:scale-[0.97] md:h-7 md:min-w-36 md:flex-none"
              onclick={() => searchRef?.focusSearch()}
              title="Search (⌘K)"
            >
              <svg class="size-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
              <span class="text-[0.65rem]">Search…</span>
              <Kbd.Root class="ml-auto hidden md:inline-flex">⌘K</Kbd.Root>
            </button>
            <YearSlider
              bind:yearMin
              bind:yearMax
              min={yearDomain.min}
              max={yearDomain.max}
              defaultMin={1930}
              defaultMax={yearDomain.max}
            />
          </div>
          <MapOverlay position="middle-left" class="hidden md:block">
            <EdgeLegend />
          </MapOverlay>
          <MapOverlay position="bottom-left" class="hidden md:block">
            <LaneFilter
              groups={laneGroups}
              {hiddenLanes}
              onToggleGroup={toggleLaneGroup}
              onShowAll={() => { if (hiddenLanes.size === 0) { hiddenLanes = new Set(Object.values(laneGroups).flat()); } else { hiddenLanes = new Set(); } }}
            />
          </MapOverlay>
          <MapOverlay position="bottom-center" class="hidden md:block">
            <EdgeModeToggle bind:edgeMode {selectedId} />
          </MapOverlay>
          <OrgSearch bind:this={searchRef} {graph} onselect={selectFromSearch} />
          <MapOverlay position="bottom-right" class="hidden md:block">
            <ZoomControls
              {zoomPct}
              onZoomIn={() => sendZoom("in")}
              onZoomOut={() => sendZoom("out")}
              onFit={() => sendZoom("fit")}
            />
          </MapOverlay>
          <div class="absolute inset-x-3 bottom-3 z-[2] flex items-center gap-1 md:hidden">
            <LaneFilter
              groups={laneGroups}
              {hiddenLanes}
              onToggleGroup={toggleLaneGroup}
              onShowAll={() => { if (hiddenLanes.size === 0) { hiddenLanes = new Set(Object.values(laneGroups).flat()); } else { hiddenLanes = new Set(); } }}
            />
            <div class="min-w-0 flex-1">
              <EdgeModeToggle bind:edgeMode {selectedId} />
            </div>
            <ZoomControls
              {zoomPct}
              onZoomIn={() => sendZoom("in")}
              onZoomOut={() => sendZoom("out")}
              onFit={() => sendZoom("fit")}
            />
          </div>
        </main>
      </div>
    {/snippet}

  {#if isMobile.current}
      {@render mapWorkspace()}
      <Drawer.Root
        open={Boolean(selectedId)}
        onOpenChange={onInspectorOpenChange}
        shouldScaleBackground={false}
      >
        <Drawer.Content class="h-[80dvh] max-h-[80dvh] min-h-0 gap-0 overflow-hidden rounded-t-lg bg-card p-0">
          <InspectorPanel
            {graph}
            node={enrichedNode}
            onclose={deselect}
            onselect={select}
          />
        </Drawer.Content>
      </Drawer.Root>
    {:else}
      <PaneGroup autoSaveId={INSPECTOR_LAYOUT_KEY} direction="horizontal" class="flex h-full">
        <Pane defaultSize={100 - INSPECTOR_DEFAULT_SIZE} minSize={40} class="min-h-0 min-w-0">
          {@render mapWorkspace()}
        </Pane>
        <Handle withHandle class="shrink-0 bg-border/80" />
        <Pane
          defaultSize={INSPECTOR_DEFAULT_SIZE}
          minSize={INSPECTOR_MIN_SIZE}
          maxSize={INSPECTOR_MAX_SIZE}
          class="min-h-0 min-w-0"
        >
          <aside
            class="flex h-full min-h-0 min-w-0 flex-col overflow-hidden border-l border-border/80 bg-card"
            aria-label="Entity inspector"
          >
            <InspectorPanel
              {graph}
              node={enrichedNode}
              onclose={deselect}
              onselect={select}
            />
          </aside>
        </Pane>
      </PaneGroup>
    {/if}
</div>

