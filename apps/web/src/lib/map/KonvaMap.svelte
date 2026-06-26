<script lang="ts">
  // @ts-nocheck — Konva types don't export shape classes (Rect, Circle, etc.) properly
  import { onMount, onDestroy } from 'svelte';
  import type { Graph, GraphEdge, GraphNode } from '$lib/types';
  import Konva from 'konva/lib/Core';
  import { Rect } from 'konva/lib/shapes/Rect';
  import { Circle } from 'konva/lib/shapes/Circle';
  import { Line } from 'konva/lib/shapes/Line';
  import { Text } from 'konva/lib/shapes/Text';
  import { Shape } from 'konva/lib/Shape';
  import { deriveClientLayout, laneLabel, laneSortOrder, shortLabel } from './layout';
  import { orgDisplayTitle } from '$lib/inspector/inspectorDisplay';
  import { nodeMatchesMetro } from './mapFilters';
  import { formatYearSpan, resolveNodeYearSpan } from '$lib/yearFormat';
  import { clampZoom, fitContentInViewport, zoomAtPoint } from './panZoom';
  import {
    buildTimelineScale,
    computeYearDomain,
    labeledYearStep,
    labeledYears,
    plotYearForNode,
    yearTicks,
    LANE_ROW_COUNT,
  } from './timelineScale';
  import MapNodeTooltip from './MapNodeTooltip.svelte';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { cn } from '$lib/utils.js';

  export type EdgeMode = 'nation' | 'focus' | 'all';

  interface Props {
    graph: Graph;
    selectedId: string | null;
    edgeMode?: EdgeMode;
    metroFilter?: string | null;
    yearMin?: number;
    yearMax?: number;
    hiddenLanes?: Set<string>;
    layoutReady?: boolean;
    zoomCommand?: { action: 'in' | 'out' | 'fit' | 'focus'; target?: string; seq?: number } | null;
    onselect: (id: string) => void;
    ondeselect?: () => void;
    onzoom?: (level: number) => void;
    onready?: () => void;
  }

  let {
    graph,
    selectedId,
    edgeMode = 'all',
    metroFilter = null,
    yearMin = 1930,
    yearMax = 2025,
    hiddenLanes = new Set<string>(),
    layoutReady = true,
    zoomCommand = null,
    onselect,
    ondeselect,
    onzoom,
    onready,
  }: Props = $props();

  const LANE_HEIGHT = 140;
  const LANE_ROW_OFFSET = 18;
  const BASE_ROW_COUNT = 5;
  const CHART_PAD = 24;

  let containerEl = $state<HTMLDivElement | null>(null);
  let hoveredId = $state<string | null>(null);
  let hoveredNode = $state<GraphNode | null>(null);
  let tooltipPos = $state<{ x: number; y: number } | null>(null);
  let mapReady = $state(false);
  let didInitialFit = false;

  // Konva state (imperative)
  let stage: any = null;
  let bgLayer: any = null;
  let edgeLayer: any = null;
  let nodeLayer: any = null;
  let labelLayer: any = null;

  // Track current zoom for LOD
  let currentZoom = 1;
  let baseZoom = 1; // the zoom level that = "100%" (initial fit)

  // Node position cache
  let nodePositions = new Map<string, { x: number; y: number }>();
  let nodeShapes = new Map<string, any>();

  const visibleNodes = $derived(
    graph.nodes.filter((node) => {
      if (!nodeMatchesMetro(node, metroFilter)) return false;
      const lane = node.data?.layout?.lane ?? 'unplaced';
      if (hiddenLanes.has(lane)) return false;
      const year = node.data?.founded_year ?? node.data?.layout?.display_year ?? 1980;
      if (year < yearMin || year > yearMax) return false;
      return true;
    }),
  );

  const visibleIds = $derived(new Set(visibleNodes.map((n) => n.id)));

  const lanes = $derived(
    [...new Set(visibleNodes.map((n) => n.data?.layout?.lane ?? 'unplaced'))].sort(
      (a, b) => laneSortOrder(a, graph) - laneSortOrder(b, graph)
    )
  );

  const laneRowCount = $derived.by(() => {
    const counts = new Map<string, number>();
    for (const n of visibleNodes) {
      const lane = n.data?.layout?.lane ?? 'unplaced';
      counts.set(lane, (counts.get(lane) ?? 0) + 1);
    }
    const result = new Map<string, number>();
    for (const [lane, count] of counts) {
      result.set(lane, Math.min(12, Math.max(BASE_ROW_COUNT, Math.ceil(count / 10))));
    }
    return result;
  });

  const yearDomain = $derived(computeYearDomain(visibleNodes));
  const scale = $derived(buildTimelineScale(yearDomain.minYear, yearDomain.maxYear));
  const contentWidth = $derived(scale.svgWidth);
  const contentHeight = $derived(scale.pad * 2 + lanes.length * LANE_HEIGHT + 56);

  function laneY(lane: string): number {
    return scale.pad + lanes.indexOf(lane) * LANE_HEIGHT + 100;
  }

  function nodeMidX(node: GraphNode): number {
    const baseX = scale.xForYear(plotYearForNode(node));
    const slot = node.data?.layout?.slot ?? 0;
    const jitter = slot * 8;
    return baseX + jitter;
  }

  function nodeLaneY(node: GraphNode): number {
    const layout = node.data?.layout ?? deriveClientLayout(node);
    const base = laneY(layout.lane);
    const slot = layout.slot ?? 0;
    const rowCount = laneRowCount.get(layout.lane) ?? BASE_ROW_COUNT;
    const row = slot % rowCount;
    const center = (rowCount - 1) / 2;
    const y = base + (row - center) * LANE_ROW_OFFSET;
    return y;
  }

  function nodePos(node: GraphNode): { x: number; y: number } {
    return { x: nodeMidX(node), y: nodeLaneY(node) };
  }

  function nodeColor(node: GraphNode): string {
    if (node.data?.nation_affiliation === 'org:bloods' || node.data?.layout?.lane?.includes('blood')) return '#e05550';
    if (node.data?.nation_affiliation === 'org:crips' || node.data?.layout?.lane?.includes('crip')) return '#4a9eff';
    if (node.data?.nation_affiliation === 'org:folk-nation') return '#3b82c4';
    if (node.data?.nation_affiliation === 'org:people-nation') return '#c75050';
    if (node.data?.layout?.lane?.includes('chicago')) return '#3fb950';
    if (node.data?.layout?.lane?.includes('latino')) return '#d29922';
    if (node.data?.layout?.lane?.includes('asian')) return '#bc8ff3';
    if (node.data?.layout?.lane?.includes('new-york')) return '#da7756';
    return '#6e7681';
  }

  function bandColor(lane: string): string {
    if (lane.includes('blood') || lane === 'blood-nation') return 'rgba(248,81,73,0.04)';
    if (lane.includes('crip') || lane === 'crip-nation') return 'rgba(88,166,255,0.04)';
    if (lane.includes('latino')) return 'rgba(210,153,34,0.03)';
    if (lane.includes('chicago')) return 'rgba(63,185,80,0.04)';
    if (lane.includes('asian')) return 'rgba(188,143,243,0.04)';
    if (lane.includes('motorcycle')) return 'rgba(139,148,158,0.05)';
    if (lane.includes('white-supremacist') || lane.includes('prison')) return 'rgba(139,148,158,0.04)';
    return 'transparent';
  }

  function edgeStroke(edge: GraphEdge): string {
    switch (edge.type) {
      case 'nation_affiliation': return '#a371f7';
      case 'alliance': return '#4ade80';
      case 'rivalry': return '#dc2626';
      case 'parent_set': case 'spin_off': return '#d29922';
      default: return '#8b949e';
    }
  }

  function edgeVisible(edge: GraphEdge): boolean {
    if (!visibleIds.has(edge.source) || !visibleIds.has(edge.target)) return false;
    if (edgeMode === 'all') return true;
    if (edgeMode === 'focus' && selectedId) {
      return edge.source === selectedId || edge.target === selectedId;
    }
    return edge.type === 'nation_affiliation';
  }

  function edgeOpacity(edge: GraphEdge): number {
    const focusId = selectedId ?? hoveredId;
    if (focusId) {
      const focused = edge.source === focusId || edge.target === focusId;
      if (!focused) return edge.type === 'nation_affiliation' ? 0.08 : 0.14;
      return 1;
    }
    if (edgeMode === 'all' && edge.type === 'nation_affiliation') return 0.08;
    return 0.45;
  }

  // --- Konva rendering ---

  function buildScene() {
    if (!stage) return;

    bgLayer.destroyChildren();
    edgeLayer.destroyChildren();
    nodeLayer.destroyChildren();
    labelLayer.destroyChildren();
    nodePositions.clear();
    nodeShapes.clear();

    const labelStep = labeledYearStep(yearDomain.maxYear - yearDomain.minYear);
    const majorYears = labeledYears(yearDomain.minYear, yearDomain.maxYear, labelStep);
    const majorYearSet = new Set(majorYears);
    const minorYears = yearTicks(yearDomain.minYear, yearDomain.maxYear);

    // Background layer: chart backdrop, grid, lane bands
    const chartX = -CHART_PAD;
    const chartY = scale.pad - 24 - CHART_PAD;
    const chartW = contentWidth + CHART_PAD * 2;
    const chartH = contentHeight - (scale.pad - 24) + CHART_PAD * 2;
    const barH = 24;

    // Window chrome title bar
    bgLayer.add(new Konva.Rect({
      x: chartX, y: chartY - barH + 1,
      width: chartW, height: barH,
      fill: '#1c2128',
      cornerRadius: [6, 6, 0, 0],
      listening: false,
    }));
    // Traffic light dots
    [0, 1, 2].forEach((i) => {
      bgLayer.add(new Konva.Circle({
        x: chartX + 16 + i * 14, y: chartY - barH / 2,
        radius: 4, fill: '#30363d', listening: false,
      }));
    });

    // Main chart area
    bgLayer.add(new Konva.Rect({
      x: chartX, y: chartY,
      width: chartW, height: chartH,
      fill: '#161b22',
      
      
      cornerRadius: [0, 0, 6, 6],
      listening: false,
    }));

    // Grid lines
    for (const year of minorYears) {
      const x = scale.xForYear(year);
      const isMajor = majorYearSet.has(year);
      bgLayer.add(new Konva.Line({
        points: [x, scale.pad - 12, x, contentHeight - scale.pad],
        stroke: isMajor ? '#30363d' : '#21262d',
        
        dash: isMajor ? undefined : [2, 6],
        listening: false,
      }));
    }

    // Year labels
    for (const year of majorYears) {
      bgLayer.add(new Konva.Text({
        x: scale.xForYear(year),
        y: scale.pad - 34,
        text: String(year),
        fontSize: labelStep === 1 ? 9 : 11,
        fill: '#b1bac4',
        align: 'center',
        offsetX: 15,
        width: 30,
        listening: false,
      }));
    }

    // Lane bands + labels
    for (const lane of lanes) {
      const top = laneY(lane) - 20;
      const bc = bandColor(lane);
      if (bc !== 'transparent') {
        bgLayer.add(new Konva.Rect({
          x: 0, y: top - 10, width: contentWidth, height: LANE_HEIGHT,
          fill: bc, listening: false,
        }));
      }
      bgLayer.add(new Konva.Line({
        points: [scale.pad, top + 36, contentWidth - scale.pad, top + 36],
        stroke: '#21262d',  listening: false,
      }));
      bgLayer.add(new Konva.Text({
        x: 10, y: top + 2,
        text: laneLabel(lane, graph),
        fontSize: 11, fill: '#b1bac4', listening: false,
      }));
    }

    // Compute all node positions first
    for (const node of visibleNodes) {
      nodePositions.set(node.id, nodePos(node));
    }

    // Edges
    for (const edge of graph.edges) {
      if (!edgeVisible(edge)) continue;
      const srcPos = nodePositions.get(edge.source);
      const tgtPos = nodePositions.get(edge.target);
      if (!srcPos || !tgtPos) continue;

      const midX = (srcPos.x + tgtPos.x) / 2;
      const midY = (srcPos.y + tgtPos.y) / 2;
      const dx = tgtPos.x - srcPos.x;
      const dy = tgtPos.y - srcPos.y;
      const cx = midX - dy * 0.08;
      const cy = midY + dx * 0.08;

      const focusId = selectedId ?? hoveredId;
      const isFocused = focusId ? (edge.source === focusId || edge.target === focusId) : false;

      edgeLayer.add(new Konva.Shape({
        sceneFunc: (ctx: any, shape: any) => {
          ctx.beginPath();
          ctx.moveTo(srcPos.x, srcPos.y);
          ctx.quadraticCurveTo(cx, cy, tgtPos.x, tgtPos.y);
          ctx.fillStrokeShape(shape);
        },
        stroke: edgeStroke(edge),
        strokeWidth: isFocused ? 2 : (edge.type === 'nation_affiliation' ? 1.5 : 1),
        opacity: edgeOpacity(edge),
        dash: edge.type === 'rivalry' ? [4, 3] : undefined,
        listening: false,
      }));
    }

    // Nodes
    for (const node of visibleNodes) {
      const pos = nodePositions.get(node.id)!;
      const isSelected = selectedId === node.id;
      const isHovered = hoveredId === node.id;
      const r = isSelected ? 10 : isHovered ? 9 : 6;

      const circle = new Konva.Circle({
        x: pos.x, y: pos.y, radius: r,
        fill: isSelected ? '#f78166' : nodeColor(node),
        stroke: isSelected ? '#fff' : isHovered ? '#58a6ff' : undefined,
        strokeWidth: (isSelected || isHovered) ? 2 : 0,
        id: node.id,
        hitStrokeWidth: 12, perfectDrawEnabled: false,
      });

      circle.on('click tap', () => onselect(node.id));
      circle.on('mouseenter', () => handleNodeHover(node));
      circle.on('mouseleave', () => handleNodeLeave());

      nodeLayer.add(circle);
      nodeShapes.set(node.id, circle);
    }

    // Labels (only at sufficient zoom)
    if (currentZoom > 0.45) {
      const placed: Array<{ x1: number; y1: number; x2: number; y2: number }> = [];

      for (const node of visibleNodes) {
        const pos = nodePositions.get(node.id)!;
        const isActive = selectedId === node.id || hoveredId === node.id;
        if (isActive) continue; // render active labels last
        const text = shortLabel(orgDisplayTitle(node), 22);
        const w = text.length * 5.6;
        const h = 12;
        const x1 = pos.x - w / 2;
        const y1 = pos.y + 12;
        const x2 = x1 + w;
        const y2 = y1 + h;

        // Skip if overlaps any already-placed label
        const overlaps = placed.some(r => x1 < r.x2 && x2 > r.x1 && y1 < r.y2 && y2 > r.y1);
        if (overlaps) continue;
        placed.push({ x1, y1, x2, y2 });

        labelLayer.add(new Konva.Text({
          x: pos.x, y: pos.y + 12,
          text,
          fontSize: 10,
          fill: resolveNodeYearSpan(node.data) ? '#c9d1d9' : '#e3b341',
          stroke: '#0d1117',
          strokeWidth: 3,
          fillAfterStrokeEnabled: true,
          align: 'center',
          offsetX: w / 2,
          listening: false,
        }));
      }
      // Active (selected/hovered) label always on top
      for (const node of visibleNodes) {
        const pos = nodePositions.get(node.id)!;
        if (selectedId !== node.id && hoveredId !== node.id) continue;
        const text = orgDisplayTitle(node);
        const w = text.length * 7;

        labelLayer.add(new Konva.Text({
          x: pos.x, y: pos.y + 12,
          text,
          fontSize: 12,
          fontStyle: 'bold',
          fill: '#ffffff',
          stroke: '#0d1117',
          strokeWidth: 4,
          fillAfterStrokeEnabled: true,
          align: 'center',
          offsetX: w / 2,
          listening: false,
        }));
      }
    }

    bgLayer.draw();
    edgeLayer.draw();
    nodeLayer.draw();
    labelLayer.draw();
  }

  function buildSceneAsync() {
    buildScene();
    fitToView();
    didInitialFit = true;
    mapReady = true;
    onready?.();
  }

  function getNodePosById(id: string): { x: number; y: number } | null {
    const node = graph.nodes.find(n => n.id === id);
    if (!node) return null;
    const pos = nodePos(node);
    nodePositions.set(id, pos);
    return pos;
  }

  function handleNodeHover(node: GraphNode) {
    hoveredId = node.id;
    hoveredNode = node;
    const pos = nodePositions.get(node.id);
    if (pos && stage) {
      const stagePos = stage.getAbsoluteTransform().point(pos);
      tooltipPos = { x: stagePos.x, y: stagePos.y };
    }
  }

  function handleNodeLeave() {
    hoveredId = null;
    hoveredNode = null;
    tooltipPos = null;
  }

  function handleStageClick(e: any) {
    if (e.target === stage) {
      ondeselect?.();
    }
  }

  // --- Public API (matches GraphMap) ---

  export function zoomIn() {
    if (!containerEl || !stage) return;
    const center = { x: containerEl.clientWidth / 2, y: containerEl.clientHeight / 2 };
    applyZoom(1.25, center.x, center.y);
  }

  export function zoomOut() {
    if (!containerEl || !stage) return;
    const center = { x: containerEl.clientWidth / 2, y: containerEl.clientHeight / 2 };
    applyZoom(0.8, center.x, center.y);
  }

  export function fitToView() {
    if (!containerEl || !stage) return;
    const vw = containerEl.clientWidth;
    const vh = containerEl.clientHeight;
    const fit = fitContentInViewport(vw, vh, contentWidth, contentHeight);
    stage.scale({ x: fit.zoom, y: fit.zoom });
    stage.position({ x: fit.panX, y: fit.panY });
    currentZoom = fit.zoom;
    baseZoom = fit.zoom;
    stage.batchDraw();
    onzoom?.(currentZoom / baseZoom);
    updateLOD();
  }

  export function focusOnNode(id: string) {
    if (!containerEl || !stage) return;
    const pos = nodePositions.get(id);
    if (!pos) return;
    const targetZoom = clampZoom(Math.max(currentZoom, 1.15));
    const vw = containerEl.clientWidth;
    const vh = containerEl.clientHeight;
    stage.scale({ x: targetZoom, y: targetZoom });
    stage.position({
      x: vw / 2 - pos.x * targetZoom,
      y: vh / 2 - pos.y * targetZoom,
    });
    currentZoom = targetZoom;
    stage.batchDraw();
    onzoom?.(currentZoom / baseZoom);
    updateLOD();
  }

  function applyZoom(factor: number, focalX: number, focalY: number) {
    const oldScale = stage.scaleX();
    const newScale = clampZoom(oldScale * factor);
    const mousePointTo = {
      x: (focalX - stage.x()) / oldScale,
      y: (focalY - stage.y()) / oldScale,
    };
    stage.scale({ x: newScale, y: newScale });
    stage.position({
      x: focalX - mousePointTo.x * newScale,
      y: focalY - mousePointTo.y * newScale,
    });
    currentZoom = newScale;
    stage.batchDraw();
    onzoom?.(currentZoom / baseZoom);
    updateLOD();
  }

  function updateLOD() {
    if (!labelLayer) return;
    const showLabels = currentZoom > 0.45;
    if (labelLayer.visible() !== showLabels) {
      labelLayer.visible(showLabels);
      labelLayer.batchDraw();
    }
  }

  // Only rebuild scene when data/filters actually change (not on hover/zoom)
  let rebuildTimer: ReturnType<typeof setTimeout> | null = null;
  let prevVisibleCount = 0;
  let prevSelectedId: string | null = null;
  let prevEdgeMode: EdgeMode = 'all';

  $effect(() => {
    // Track only structural changes
    const count = visibleNodes.length;
    const sel = selectedId;
    const mode = edgeMode;
    if (stage && (count !== prevVisibleCount || sel !== prevSelectedId || mode !== prevEdgeMode)) {
      prevVisibleCount = count;
      prevSelectedId = sel;
      prevEdgeMode = mode;
      if (rebuildTimer) clearTimeout(rebuildTimer);
      rebuildTimer = setTimeout(() => buildScene(), 16);
    }
  });

  // React to zoom commands from parent
  $effect(() => {
    if (!zoomCommand || !stage) return;
    if (zoomCommand.action === 'in') zoomIn();
    else if (zoomCommand.action === 'out') zoomOut();
    else if (zoomCommand.action === 'fit') fitToView();
    else if (zoomCommand.action === 'focus' && zoomCommand.target) focusOnNode(zoomCommand.target);
  });

  let resizeObserver: ResizeObserver | null = null;

  onMount(() => {
    if (!containerEl) return;

    Konva.pixelRatio = 1;

    stage = new Konva.Stage({
      container: containerEl,
      width: containerEl.clientWidth,
      height: containerEl.clientHeight,
      draggable: true,
    });

    bgLayer = new Konva.Layer({ listening: false });
    edgeLayer = new Konva.Layer({ listening: false });
    nodeLayer = new Konva.Layer();
    labelLayer = new Konva.Layer({ listening: false });

    stage.add(bgLayer);
    stage.add(edgeLayer);
    stage.add(nodeLayer);
    stage.add(labelLayer);

    // Wheel zoom
    stage.on('wheel', (e: any) => {
      e.evt.preventDefault();
      const factor = e.evt.deltaY > 0 ? 0.9 : 1.1;
      const pointer = stage.getPointerPosition();
      if (pointer) applyZoom(factor, pointer.x, pointer.y);
    });

    // Hide expensive layers during drag for smooth panning
    stage.on('dragstart', () => {
      edgeLayer.opacity(0.3);
    });
    stage.on('dragend', () => {
      edgeLayer.opacity(1);
      stage.batchDraw();
    });

    // Click on empty space = deselect
    stage.on('click tap', (e: any) => {
      if (e.target === stage) ondeselect?.();
    });

    // Resize observer
    resizeObserver = new ResizeObserver(() => {
      if (!containerEl || !stage) return;
      stage.width(containerEl.clientWidth);
      stage.height(containerEl.clientHeight);
      if (!didInitialFit) {
        fitToView();
        didInitialFit = true;
        mapReady = true; onready?.();
      }
    });
    resizeObserver.observe(containerEl);

    // Initial render
    buildSceneAsync();

    return () => {
      resizeObserver?.disconnect();
      stage?.destroy();
    };
  });

  onDestroy(() => {
    if (rebuildTimer) clearTimeout(rebuildTimer);
  });
</script>

<div
  class="absolute inset-0 overflow-hidden touch-none bg-background cursor-grab [background-image:radial-gradient(circle_at_center,var(--map-grid-dot)_0.65px,transparent_0.65px)] [background-size:18px_18px]"
>
  <div
    class={cn(
      'h-full w-full', !mapReady && 'invisible',
    )}
    bind:this={containerEl}
    role="application"
    aria-label="Pannable timeline map"
  ></div>
</div>
{#if !mapReady}
  <div class="absolute inset-0 z-[10000] flex items-center justify-center">
    <svg class="size-20 animate-[spin_6s_linear_infinite] will-change-transform text-muted-foreground/20" viewBox="0 0 100 100" fill="none" stroke="currentColor" stroke-width="0.4">
      <circle cx="50" cy="50" r="45"/>
      <ellipse cx="50" cy="50" rx="45" ry="12"/>
      <ellipse cx="50" cy="50" rx="20" ry="45"/>
      <ellipse cx="50" cy="50" rx="35" ry="45"/>
      <circle cx="95" cy="50" r="2" fill="currentColor" stroke="none" class="text-muted-foreground/40"/>
    </svg>
  </div>
{/if}


{#if hoveredNode && tooltipPos}
  <MapNodeTooltip node={hoveredNode} x={tooltipPos.x} y={tooltipPos.y} />
{/if}

