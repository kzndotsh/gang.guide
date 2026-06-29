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

  export type EdgeMode = 'hover' | 'all';

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
    edgeMode = 'hover',
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

  // Viewport culling bounds (in content coordinates)
  function getViewportBounds(): { x1: number; y1: number; x2: number; y2: number } {
    if (!stage || !containerEl) return { x1: -Infinity, y1: -Infinity, x2: Infinity, y2: Infinity };
    const scale = stage.scaleX();
    const pos = stage.position();
    const w = containerEl.clientWidth;
    const h = containerEl.clientHeight;
    const buffer = 200; // px buffer outside viewport
    return {
      x1: (-pos.x - buffer) / scale,
      y1: (-pos.y - buffer) / scale,
      x2: (w - pos.x + buffer) / scale,
      y2: (h - pos.y + buffer) / scale,
    };
  }

  function isInViewport(x: number, y: number, bounds: ReturnType<typeof getViewportBounds>): boolean {
    return x >= bounds.x1 && x <= bounds.x2 && y >= bounds.y1 && y <= bounds.y2;
  }

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
      case 'nation': case 'member_of': return '#b87fff';
      case 'alliance': return '#3fff8a';
      case 'rivalry': return '#ff4444';
      case 'parent': case 'spin_off': return '#ffb938';
      default: return '#8b949e';
    }
  }

  // --- Konva rendering ---

  let bgBuilt = false;
  let prevLaneCount = 0;
  let nodesBuilt = false;

  // Edge index for fast lookup by node id
  let edgeIndex = new Map<string, GraphEdge[]>();

  function rebuildEdgeIndex() {
    edgeIndex.clear();
    for (const edge of graph.edges) {
      if (!visibleIds.has(edge.source) || !visibleIds.has(edge.target)) continue;
      if (!edgeIndex.has(edge.source)) edgeIndex.set(edge.source, []);
      if (!edgeIndex.has(edge.target)) edgeIndex.set(edge.target, []);
      edgeIndex.get(edge.source)!.push(edge);
      edgeIndex.get(edge.target)!.push(edge);
    }
  }

  function buildBackground() {
    if (!stage) return;
    bgLayer.destroyChildren();

    const labelStep = labeledYearStep(yearDomain.maxYear - yearDomain.minYear);
    const majorYears = labeledYears(yearDomain.minYear, yearDomain.maxYear, labelStep);
    const majorYearSet = new Set(majorYears);
    const minorYears = yearTicks(yearDomain.minYear, yearDomain.maxYear);

    const chartX = -CHART_PAD;
    const chartY = scale.pad - 24 - CHART_PAD;
    const chartW = contentWidth + CHART_PAD * 2;
    const chartH = contentHeight - (scale.pad - 24) + CHART_PAD * 2;
    const barH = 24;

    bgLayer.add(new Konva.Rect({
      x: chartX, y: chartY - barH + 1,
      width: chartW, height: barH,
      fill: '#1c2128', cornerRadius: [6, 6, 0, 0], listening: false,
    }));
    [0, 1, 2].forEach((i) => {
      bgLayer.add(new Konva.Circle({
        x: chartX + 16 + i * 14, y: chartY - barH / 2,
        radius: 4, fill: '#30363d', listening: false,
      }));
    });
    bgLayer.add(new Konva.Rect({
      x: chartX, y: chartY,
      width: chartW, height: chartH,
      fill: '#161b22', cornerRadius: [0, 0, 6, 6], listening: false,
    }));

    for (const year of minorYears) {
      const x = scale.xForYear(year);
      const isMajor = majorYearSet.has(year);
      bgLayer.add(new Konva.Line({
        points: [x, scale.pad - 12, x, contentHeight - scale.pad],
        stroke: isMajor ? '#30363d' : '#21262d',
        dash: isMajor ? undefined : [2, 6], listening: false,
      }));
    }

    for (const year of majorYears) {
      bgLayer.add(new Konva.Text({
        x: scale.xForYear(year), y: scale.pad - 34,
        text: String(year),
        fontSize: labelStep === 1 ? 9 : 11,
        fill: '#b1bac4', align: 'center', offsetX: 15, width: 30, listening: false,
      }));
    }

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
        stroke: '#21262d', listening: false,
      }));
      bgLayer.add(new Konva.Text({
        x: 10, y: top + 2,
        text: laneLabel(lane, graph),
        fontSize: 11, fill: '#b1bac4', listening: false,
      }));
    }

    bgLayer.draw();
    bgBuilt = true;
    prevLaneCount = lanes.length;
  }

  /** Build nodes once. Never destroy unless filters change. */
  function buildNodes() {
    nodeLayer.destroyChildren();
    nodePositions.clear();
    nodeShapes.clear();

    for (const node of visibleNodes) {
      const pos = nodePos(node);
      nodePositions.set(node.id, pos);

      const circle = new Konva.Circle({
        x: pos.x, y: pos.y, radius: 6,
        fill: nodeColor(node),
        id: node.id,
        hitStrokeWidth: 12, perfectDrawEnabled: false,
      });

      circle.on('click tap', () => onselect(node.id));
      circle.on('mouseenter', () => handleNodeHover(node));
      circle.on('mouseleave', () => handleNodeLeave());

      nodeLayer.add(circle);
      nodeShapes.set(node.id, circle);
    }

    nodeLayer.draw();
    nodesBuilt = true;
    rebuildEdgeIndex();
  }

  /** Update node appearance for selection/hover without recreating */
  function updateNodeAppearance() {
    for (const [id, circle] of nodeShapes) {
      const isSelected = selectedId === id;
      const isHovered = hoveredId === id;
      const node = graph.nodes.find(n => n.id === id);
      circle.radius(isSelected ? 10 : isHovered ? 9 : 6);
      circle.fill(isSelected ? '#f78166' : nodeColor(node!));
      circle.stroke(isSelected ? '#fff' : isHovered ? '#58a6ff' : null);
      circle.strokeWidth((isSelected || isHovered) ? 2 : 0);
    }
    nodeLayer.batchDraw();
  }

  /** Draw edges based on current mode */
  function drawEdges(focusNodeId: string | null) {
    edgeLayer.destroyChildren();

    let edgesToDraw: GraphEdge[] = [];

    if (edgeMode === 'all') {
      // Draw all edges
      for (const edge of graph.edges) {
        if (!visibleIds.has(edge.source) || !visibleIds.has(edge.target)) continue;
        if (!nodePositions.has(edge.source) || !nodePositions.has(edge.target)) continue;
        edgesToDraw.push(edge);
      }
    } else {
      // 'hover' mode: only show focused node's edges
      if (focusNodeId) {
        edgesToDraw.push(...(edgeIndex.get(focusNodeId) ?? []));
      }
    }

    if (edgesToDraw.length === 0) {
      edgeLayer.draw();
      return;
    }

    // Filter to edges with valid positions
    edgesToDraw = edgesToDraw.filter(e => nodePositions.has(e.source) && nodePositions.has(e.target));

    // Filter out directional edges from batches — they'll be drawn separately with arrows
    const directionalTypes = new Set(['spin_off', 'parent', 'member_of', 'nation']);
    const batchEdges: GraphEdge[] = [];
    const arrowEdges: GraphEdge[] = [];
    for (const edge of edgesToDraw) {
      if (directionalTypes.has(edge.type)) {
        arrowEdges.push(edge);
      } else {
        batchEdges.push(edge);
      }
    }

    // Batch non-directional edges by type
    const buckets = new Map<string, GraphEdge[]>();
    for (const edge of batchEdges) {
      const t = edge.type;
      if (!buckets.has(t)) buckets.set(t, []);
      buckets.get(t)!.push(edge);
    }

    for (const [type, batch] of buckets) {
      const isFocusBatch = edgeMode !== 'all';
      const hasFocus = !!selectedId;
      const bgOpacity = isFocusBatch ? 1 : hasFocus ? 0.12 : 0.35;
      edgeLayer.add(new Konva.Shape({
        sceneFunc: (ctx: any, shape: any) => {
          ctx.beginPath();
          for (const edge of batch) {
            const srcPos = nodePositions.get(edge.source)!;
            const tgtPos = nodePositions.get(edge.target)!;
            const midX = (srcPos.x + tgtPos.x) / 2;
            const midY = (srcPos.y + tgtPos.y) / 2;
            const dx = tgtPos.x - srcPos.x;
            const dy = tgtPos.y - srcPos.y;
            ctx.moveTo(srcPos.x, srcPos.y);
            ctx.quadraticCurveTo(midX - dy * 0.08, midY + dx * 0.08, tgtPos.x, tgtPos.y);
          }
          ctx.fillStrokeShape(shape);
        },
        stroke: edgeStroke(batch[0]),
        strokeWidth: isFocusBatch ? 2 : 1,
        opacity: bgOpacity,
        dash: type === 'rivalry' ? [6, 3] : type === 'alliance' ? [0.5, 4] : undefined,
        lineCap: type === 'alliance' ? 'round' : undefined,
        listening: false,
        perfectDrawEnabled: false,
      }));
    }

    // Draw directional edges with shortened line + arrowhead
    const directionalBuckets = new Map<string, GraphEdge[]>();
    for (const edge of arrowEdges) {
      const t = edge.type;
      if (!directionalBuckets.has(t)) directionalBuckets.set(t, []);
      directionalBuckets.get(t)!.push(edge);
    }

    // Draw directional edges with line stopping at arrow
    for (const [type, batch] of directionalBuckets) {
      const isFocusBatch = edgeMode !== 'all';

      // Track edges per target to offset parallel arrows
      const targetCount = new Map<string, number>();

      for (const edge of batch) {
        let srcPos = nodePositions.get(edge.source)!;
        let tgtPos = nodePositions.get(edge.target)!;
        // For member_of/nation: flip so arrow goes from nation → org
        if (edge.type === 'member_of' || edge.type === 'nation') {
          [srcPos, tgtPos] = [tgtPos, srcPos];
        }
        const dx = tgtPos.x - srcPos.x;
        const dy = tgtPos.y - srcPos.y;
        const len = Math.sqrt(dx * dx + dy * dy);
        if (len < 20) continue;

        // Offset curve to spread parallel edges
        const tgtKey = `${tgtPos.x},${tgtPos.y}`;
        const idx = targetCount.get(tgtKey) ?? 0;
        targetCount.set(tgtKey, idx + 1);
        const spread = (idx - 0.5) * 0.12;

        const midX = (srcPos.x + tgtPos.x) / 2;
        const midY = (srcPos.y + tgtPos.y) / 2;
        const ctrlX = midX - dy * (0.08 + spread);
        const ctrlY = midY + dx * (0.08 + spread);

        // Tangent direction at target
        const tx = tgtPos.x - ctrlX;
        const ty = tgtPos.y - ctrlY;
        const tlen = Math.sqrt(tx * tx + ty * ty);
        const nx = tx / tlen;
        const ny = ty / tlen;

        // Arrow at end, gap before node. Line stops at arrow base.
        const tanX = tgtPos.x - ctrlX;
        const tanY = tgtPos.y - ctrlY;
        const tanLen = Math.sqrt(tanX * tanX + tanY * tanY);
        const mnx = tanX / tanLen;
        const mny = tanY / tanLen;

        // Arrow tip is 10px from node, base is 20px from node
        const tipX = tgtPos.x - mnx * 10;
        const tipY = tgtPos.y - mny * 10;
        const baseX = tgtPos.x - mnx * 20;
        const baseY = tgtPos.y - mny * 20;

        // Draw curve stopping at arrow base
        edgeLayer.add(new Konva.Shape({
          sceneFunc: (ctx: any, shape: any) => {
            ctx.beginPath();
            ctx.moveTo(srcPos.x, srcPos.y);
            ctx.quadraticCurveTo(ctrlX, ctrlY, baseX, baseY);
            ctx.fillStrokeShape(shape);
          },
          stroke: edgeStroke(edge),
          strokeWidth: isFocusBatch ? 2 : 1,
          opacity: isFocusBatch ? 1 : (selectedId ? 0.12 : 0.35),
          listening: false,
          perfectDrawEnabled: false,
        }));

        // Arrow triangle pointing at node
        const sz = 6;
        edgeLayer.add(new Konva.Shape({
          sceneFunc: (ctx: any, shape: any) => {
            ctx.beginPath();
            ctx.moveTo(tipX, tipY);
            ctx.lineTo(baseX - mny * sz, baseY + mnx * sz);
            ctx.lineTo(baseX + mny * sz, baseY - mnx * sz);
            ctx.closePath();
            ctx.fillStrokeShape(shape);
          },
          fill: edgeStroke(edge),
          opacity: isFocusBatch ? 1 : (selectedId ? 0.12 : 0.35),
          listening: false,
          perfectDrawEnabled: false,
        }));
      }
    }

    // In 'all' mode, draw focused node's edges on top at full opacity
    if (edgeMode === 'all') {
      const focusId = selectedId;
      if (focusId) {
        const focusEdges = (edgeIndex.get(focusId) ?? []).filter(
          e => nodePositions.has(e.source) && nodePositions.has(e.target)
        );
        const fBuckets = new Map<string, GraphEdge[]>();
        for (const e of focusEdges) {
          if (!fBuckets.has(e.type)) fBuckets.set(e.type, []);
          fBuckets.get(e.type)!.push(e);
        }
        for (const [ftype, fbatch] of fBuckets) {
          edgeLayer.add(new Konva.Shape({
            sceneFunc: (ctx: any, shape: any) => {
              ctx.beginPath();
              for (const edge of fbatch) {
                const s = nodePositions.get(edge.source)!;
                const t = nodePositions.get(edge.target)!;
                const mx = (s.x + t.x) / 2;
                const my = (s.y + t.y) / 2;
                const ddx = t.x - s.x;
                const ddy = t.y - s.y;
                ctx.moveTo(s.x, s.y);
                ctx.quadraticCurveTo(mx - ddy * 0.08, my + ddx * 0.08, t.x, t.y);
              }
              ctx.fillStrokeShape(shape);
            },
            stroke: edgeStroke(fbatch[0]),
            strokeWidth: 2.5,
            opacity: 1,
            dash: ftype === 'rivalry' ? [6, 3] : ftype === 'alliance' ? [0.5, 4] : undefined,
            lineCap: ftype === 'alliance' ? 'round' : undefined,
            listening: false,
            perfectDrawEnabled: false,
          }));
        }
      }
    }

    edgeLayer.draw();
  }

  /** Lightweight label update */
  function drawLabels() {
    labelLayer.destroyChildren();

    if (currentZoom <= 0.25) {
      labelLayer.draw();
      return;
    }

    const placed: Array<{ x1: number; y1: number; x2: number; y2: number }> = [];

    // Get viewport bounds for label culling
    const vb = getViewportBounds();

    for (const node of visibleNodes) {
      const pos = nodePositions.get(node.id);
      if (!pos) continue;
      if (!isInViewport(pos.x, pos.y, vb)) continue;

      const isActive = selectedId === node.id || hoveredId === node.id;
      if (isActive) continue;

      const text = shortLabel(orgDisplayTitle(node), 22);
      const w = text.length * 5.6;
      const h = 12;
      const x1 = pos.x - w / 2;
      const y1 = pos.y + 12;
      const x2 = x1 + w;
      const y2 = y1 + h;

      const overlaps = placed.some(r => x1 < r.x2 && x2 > r.x1 && y1 < r.y2 && y2 > r.y1);
      if (overlaps) continue;
      placed.push({ x1, y1, x2, y2 });

      labelLayer.add(new Konva.Text({
        x: pos.x, y: pos.y + 12, text,
        fontSize: 10,
        fill: resolveNodeYearSpan(node.data) ? '#c9d1d9' : '#e3b341',
        stroke: '#0d1117', strokeWidth: 3,
        fillAfterStrokeEnabled: true,
        align: 'center', offsetX: w / 2, listening: false,
      }));
    }

    // Active labels on top (both selected and hovered)
    for (const activeId of [selectedId, hoveredId]) {
      if (!activeId) continue;
      const node = graph.nodes.find(n => n.id === activeId);
      const pos = nodePositions.get(activeId);
      if (node && pos) {
        const text = orgDisplayTitle(node);
        labelLayer.add(new Konva.Text({
          x: pos.x, y: pos.y + 12, text,
          fontSize: 12, fontStyle: 'bold',
          fill: '#ffffff', stroke: '#0d1117', strokeWidth: 4,
          fillAfterStrokeEnabled: true,
          align: 'center', offsetX: text.length * 7 / 2, listening: false,
        }));
      }
    }

    labelLayer.draw();
  }

  /** Full rebuild — only on filter/data changes */
  function buildScene() {
    if (!stage) return;
    if (!bgBuilt || lanes.length !== prevLaneCount) buildBackground();
    buildNodes();
    drawEdges(selectedId ?? hoveredId);
    drawLabels();
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
    const showLabels = currentZoom > 0.25;
    if (labelLayer.visible() !== showLabels) {
      labelLayer.visible(showLabels);
      labelLayer.batchDraw();
    }
  }

  // Only rebuild scene when data/filters actually change (not on hover/zoom)
  let rebuildTimer: ReturnType<typeof setTimeout> | null = null;
  let prevVisibleCount = 0;
  let prevSelectedId: string | null = null;
  let prevEdgeMode: EdgeMode = 'hover';
  let prevHoveredId: string | null = null;

  $effect(() => {
    const count = visibleNodes.length;
    const sel = selectedId;
    const mode = edgeMode;
    // Full rebuild only when filters change node set
    if (stage && count !== prevVisibleCount) {
      prevVisibleCount = count;
      prevSelectedId = sel;
      prevEdgeMode = mode;
      if (rebuildTimer) clearTimeout(rebuildTimer);
      rebuildTimer = setTimeout(() => buildScene(), 16);
    }
    // Selection or mode change: update appearance + edges (no node rebuild)
    else if (stage && nodesBuilt && (sel !== prevSelectedId || mode !== prevEdgeMode)) {
      prevSelectedId = sel;
      prevEdgeMode = mode;
      updateNodeAppearance();
      drawEdges(sel ?? hoveredId);
      drawLabels();
    }
  });

  // Hover: just update edges + node appearance (very cheap)
  $effect(() => {
    const hov = hoveredId;
    if (!stage || !nodesBuilt) return;
    if (hov !== prevHoveredId) {
      prevHoveredId = hov;
      updateNodeAppearance();
      drawEdges(selectedId ?? hov);
      drawLabels();
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

    // Rebuild labels on pan end (viewport-dependent)
    stage.on('dragend', () => {
      if (rebuildTimer) clearTimeout(rebuildTimer);
      rebuildTimer = setTimeout(() => drawLabels(), 150);
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

