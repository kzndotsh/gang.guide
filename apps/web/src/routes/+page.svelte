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
  import type { Graph } from '$lib/types';
  import { visibleEdgeCount } from '$lib/map/visibility';
  import { PaneGroup, Pane, Handle } from '$lib/components/ui/resizable/index.js';

    const INSPECTOR_LAYOUT_KEY = 'gang-guide-inspector';
  const INSPECTOR_MIN_SIZE = 16;
  const INSPECTOR_MAX_SIZE = 50;
  const INSPECTOR_DEFAULT_SIZE = 30;

  let { data } = $props();

  let selectedId = $state<string | null>(null);
  let edgeMode = $state<EdgeMode>('all');
  let zoomCmd = $state<{ action: 'in' | 'out' | 'fit' | 'focus'; target?: string; seq: number } | null>(null);
  let zoomSeq = 0;
  function sendZoom(action: 'in' | 'out' | 'fit' | 'focus', target?: string) {
    zoomCmd = { action, target, seq: ++zoomSeq };
  }
  let zoomPct = $state(100);
  let searchRef = $state<OrgSearch | null>(null);
  let yearMin = $state(1930);
  let yearMax = $state(2025);
  let hiddenLanes = $state<Set<string>>(new Set());

  // Restore filters from localStorage
  if (browser) {
    const saved = localStorage.getItem('gang-guide-filters');
    if (saved) {
      try {
        const f = JSON.parse(saved);
        if (f.yearMin) yearMin = f.yearMin;
        if (f.yearMax) yearMax = f.yearMax;
        if (f.hiddenLanes) hiddenLanes = new Set(f.hiddenLanes);
      } catch {}
    }
  }

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
  const metroOptions = $derived(
    [...new Set(graph.nodes.map((n) => n.data?.metro?.trim()).filter(Boolean))].sort() as string[],
  );

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
  let detailsCache = $state<Record<string, { description?: string; sources?: any[] }>>({});
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
      },
    };
  });

  const visibleEdgeCountDerived = $derived(
    visibleEdgeCount(graph, edgeMode, selectedId)
  );

  onMount(() => {
    if (!browser) return;
    const org = new URL(window.location.href).searchParams.get('org');
    if (org && graph.nodes.some((n) => n.id === org)) {
      selectFromSearch(org);
    }
  });

  $effect(() => {
    if (!browser) return;
    const url = new URL(window.location.href);
    if (selectedId) url.searchParams.set('org', selectedId);
    else url.searchParams.delete('org');
    history.replaceState({}, '', url);
  });

  function select(id: string) {
    if (selectedId === id) {
      deselect();
      return;
    }
    selectedId = id;
    if (edgeMode === 'all') {
      edgeMode = 'focus';
    }
  }

  function selectFromSearch(id: string) {
    if (selectedId === id) {
      sendZoom("focus", id);
      return;
    }
    selectedId = id;
    if (edgeMode === 'all') {
      edgeMode = 'focus';
    }
    sendZoom("focus", id);
  }

  function deselect() {
    selectedId = null;
    if (edgeMode === 'focus') {
      edgeMode = 'all';
    }
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
  <title>gang.guide — US street gang history map</title>
</svelte:head>

<svelte:window onkeydown={onKeydown} />

<div class="fixed inset-0 overflow-hidden bg-background">
  <!-- Desktop: full-height sidebar on right, everything else on left -->
  <PaneGroup autoSaveId={INSPECTOR_LAYOUT_KEY}
    direction="horizontal"
    class="hidden h-full md:flex "
  >
    <Pane defaultSize={100 - INSPECTOR_DEFAULT_SIZE} minSize={40} class="min-h-0 min-w-0">
      <div class="flex h-full flex-col">
        <AppHeader
          {graph}
          {selectedId}
          nodeCount={graph.nodes.length}
          edgeCount={visibleEdgeCountDerived}
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
          <MapOverlay position="bottom-left">
            <div class="flex flex-col gap-1">
              <EdgeModeToggle bind:edgeMode {selectedId} />
              <LaneFilter
                groups={laneGroups}
                {hiddenLanes}
                onToggleGroup={toggleLaneGroup}
                onShowAll={() => { if (hiddenLanes.size === 0) { hiddenLanes = new Set(Object.values(laneGroups).flat()); } else { hiddenLanes = new Set(); } }}
              />
            </div>
          </MapOverlay>
          <MapOverlay position="top-right">
            <YearSlider bind:yearMin bind:yearMax />
          </MapOverlay>
          <MapOverlay position="top-left">
            <button
              class="flex h-6 min-w-36 items-center gap-1.5 px-2 py-0.5 text-foreground/60 hover:text-foreground drop-shadow-[0_1px_1px_rgba(0,0,0,0.3)] active:scale-[0.97]"
              onclick={() => searchRef?.focusSearch()}
              title="Search (⌘K)"
            >
              <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
              <span class="text-[0.7rem]">Search…</span>
              <Kbd.Root class="ml-auto">⌘K</Kbd.Root>
            </button>
          </MapOverlay>
          <OrgSearch bind:this={searchRef} {graph} onselect={selectFromSearch} />
          <MapOverlay position="bottom-right">
            <ZoomControls
              {zoomPct}
              onZoomIn={() => sendZoom("in")}
              onZoomOut={() => sendZoom("out")}
              onFit={() => sendZoom("fit")}
            />
          </MapOverlay>
        </main>
      </div>
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

  <!-- Mobile: full-width map + slide-over inspector -->
  <div class="relative min-h-0 flex-1 md:hidden">
    <main class="h-full min-h-0 overflow-hidden bg-background">
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
    </main>

    {#if enrichedNode}
      <aside
        class="absolute inset-0 z-10 flex flex-col overflow-hidden bg-card"
        aria-label="Entity inspector"
      >
        <InspectorPanel
          {graph}
          node={enrichedNode}
          onclose={deselect}
          onselect={select}
        />
      </aside>
    {/if}
  </div>
</div>
