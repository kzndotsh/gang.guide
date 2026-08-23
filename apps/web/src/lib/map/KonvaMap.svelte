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
  import { bandColor, nodeColor } from './laneColors';
  import { orgDisplayTitle } from '$lib/inspector/inspectorDisplay';
  import { nodeMatchesMetro } from './mapFilters';
  import { formatYearSpan, resolveNodeYearSpan } from '$lib/yearFormat';
  import { clampZoom, fitContentInViewport, isUsableStageSize } from './panZoom';
  import {
    buildTimelineScale,
    computeYearDomain,
    labeledYearStep,
    labeledYears,
    plotYearForNode,
    yearTicks,
  } from './timelineScale';
  import MapNodeTooltip from './MapNodeTooltip.svelte';
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

  const LANE_HEIGHT = 160;
  const LANE_ROW_OFFSET = 22;
  const BASE_ROW_COUNT = 5;
  const CHART_PAD = 24;
  const AXIS_HEIGHT = 36;

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
  let axisLayer: any = null;
  let axisBar: any = null;
  let axisMarks: Array<{ year: number; line: any; label: any | null }> = [];
  let axisBuilt = false;

  // Track current zoom for LOD
  let currentZoom = 1;
  let baseZoom = 1; // the zoom level that = "100%" (initial fit)

  // Node position cache
  let nodePositions = new Map<string, { x: number; y: number }>();
  let nodeShapes = new Map<string, any>();
  let nodeById = new Map<string, GraphNode>();

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
      result.set(lane, Math.min(16, Math.max(BASE_ROW_COUNT, Math.ceil(count / 10))));
    }
    return result;
  });

  const yearDomain = $derived(computeYearDomain(visibleNodes));
  const scale = $derived(buildTimelineScale(yearDomain.minYear, yearDomain.maxYear));
  const contentWidth = $derived(scale.svgWidth);
  const contentHeight = $derived(scale.pad * 2 + lanes.length * LANE_HEIGHT + 56);

  function laneY(lane: string): number {
    // Guard against null/unrecognized lanes (indexOf returns -1 → renders at top)
    const idx = lanes.indexOf(lane);
    const safeIdx = idx >= 0 ? idx : lanes.indexOf('unplaced');
    return scale.pad + Math.max(0, safeIdx) * LANE_HEIGHT + 100;
  }

  function nodeMidX(node: GraphNode): number {
    const baseX = scale.xForYear(plotYearForNode(node));
    const slot = node.data?.layout?.slot ?? 0;
    const layout = node.data?.layout ?? deriveClientLayout(node);
    const rowCount = laneRowCount.get(layout.lane) ?? BASE_ROW_COUNT;
    // Jitter wraps per row so nodes in the same row share the same X offset.
    // This prevents unbounded rightward drift in dense lanes (e.g. 74 nodes → slot 73 * 8 = 584px off-canvas).
    const col = Math.floor(slot / rowCount);
    const jitter = col * 4;
    return baseX + jitter;
  }

  function nodeLaneY(node: GraphNode): number {
    const layout = node.data?.layout ?? deriveClientLayout(node);
    const base = laneY(layout.lane);
    const slot = layout.slot ?? 0;
    const rowCount = laneRowCount.get(layout.lane) ?? BASE_ROW_COUNT;
    const row = slot % rowCount;
    const center = (rowCount - 1) / 2;
    // Clamp row offset so nodes stay within lane bounds even for dense lanes
    const maxSpread = LANE_HEIGHT - 32;
    const rowOffset = rowCount > 1 ? Math.min(LANE_ROW_OFFSET, maxSpread / (rowCount - 1)) : LANE_ROW_OFFSET;
    const y = base + (row - center) * rowOffset;
    return y;
  }

  function nodePos(node: GraphNode): { x: number; y: number } {
    return { x: nodeMidX(node), y: nodeLaneY(node) };
  }

  function nodeColorFor(node: GraphNode): string {
    return nodeColor(node, graph);
  }

  function bandColorFor(lane: string): string {
    return bandColor(lane, graph);
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
  let prevYearMin = 0;
  let prevYearMax = 0;
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

    bgLayer.add(new Konva.Rect({
      x: chartX, y: chartY,
      width: chartW, height: chartH,
      fill: '#161b22', cornerRadius: 6, listening: false,
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

    const bandRuns: { fill: string; y: number; height: number }[] = [];
    for (const lane of lanes) {
      const bandTop = laneY(lane) - 30;
      const fill = bandColorFor(lane);
      if (fill === 'transparent') continue;
      const last = bandRuns.at(-1);
      if (last && last.fill === fill) {
        last.height = bandTop + LANE_HEIGHT - last.y;
      } else {
        bandRuns.push({ fill, y: bandTop, height: LANE_HEIGHT });
      }
    }
    for (const run of bandRuns) {
      bgLayer.add(new Konva.Rect({
        x: 0,
        y: Math.round(run.y),
        width: contentWidth,
        height: Math.round(run.height),
        fill: run.fill,
        listening: false,
        strokeEnabled: false,
        perfectDrawEnabled: false,
      }));
    }

    for (const lane of lanes) {
      const bandTop = laneY(lane) - 30;
      const label = new Konva.Text({
        x: 10, y: bandTop,
        text: laneLabel(lane, graph),
        fontSize: 11, fill: '#b1bac4', listening: false,
      });
      label.offsetY(Math.round(label.height() / 2));
      bgLayer.add(new Konva.Line({
        points: [10 + label.getTextWidth() + 8, bandTop, contentWidth - scale.pad, bandTop],
        stroke: '#21262d', listening: false,
      }));
      bgLayer.add(label);
    }

    bgLayer.draw();
    bgBuilt = true;
    prevLaneCount = lanes.length;
    prevYearMin = yearDomain.minYear;
    prevYearMax = yearDomain.maxYear;
  }

  function buildAxis() {
    if (!stage || !axisLayer || !containerEl) return;
    axisLayer.destroyChildren();
    axisMarks = [];

    const labelStep = labeledYearStep(yearDomain.maxYear - yearDomain.minYear);
    const majorYears = labeledYears(yearDomain.minYear, yearDomain.maxYear, labelStep);
    const majorYearSet = new Set(majorYears);
    const minorYears = yearTicks(yearDomain.minYear, yearDomain.maxYear);

    axisBar = new Konva.Rect({
      x: 0, y: 0,
      width: containerEl.clientWidth, height: AXIS_HEIGHT,
      fill: '#1c2128', listening: false,
    });
    axisLayer.add(axisBar);

    for (const year of minorYears) {
      const isMajor = majorYearSet.has(year);
      const line = new Konva.Line({
        points: [0, isMajor ? 22 : 28, 0, AXIS_HEIGHT],
        stroke: isMajor ? '#8b949e' : '#30363d',
        strokeWidth: 1, listening: false,
      });
      axisLayer.add(line);
      let label: any = null;
      if (isMajor) {
        label = new Konva.Text({
          x: 0, y: 6,
          text: String(year),
          fontSize: labelStep === 1 ? 9 : 11,
          fill: '#b1bac4', align: 'center', offsetX: 16, width: 32, listening: false,
        });
        axisLayer.add(label);
      }
      axisMarks.push({ year, line, label });
    }

    axisBuilt = true;
    syncAxisLayer();
  }

  function syncAxisLayer() {
    if (!stage || !axisLayer || !containerEl) return;
    const S = stage.scaleX() || 1;
    const panX = stage.x();
    const panY = stage.y();
    axisLayer.position({ x: -panX / S, y: -panY / S });
    axisLayer.scale({ x: 1 / S, y: 1 / S });

    const vw = containerEl.clientWidth;
    if (axisBar) axisBar.width(vw);

    const margin = 24;
    for (const mark of axisMarks) {
      const sx = scale.xForYear(mark.year) * S + panX;
      const inView = sx >= -margin && sx <= vw + margin;
      mark.line.x(sx);
      mark.line.visible(inView);
      if (mark.label) {
        mark.label.x(sx);
        mark.label.visible(inView);
      }
    }
    axisLayer.batchDraw();
  }

  /** Build nodes once. Never destroy unless filters change. */
  function buildNodes() {
    nodeLayer.destroyChildren();
    nodePositions.clear();
    nodeShapes.clear();
    nodeById.clear();

    for (const node of visibleNodes) {
      const pos = nodePos(node);
      nodePositions.set(node.id, pos);
      nodeById.set(node.id, node);

      const circle = new Konva.Circle({
        x: pos.x, y: pos.y, radius: 6,
        fill: nodeColorFor(node),
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

  function segmentInView(
    ax: number, ay: number, bx: number, by: number,
    b: { x1: number; y1: number; x2: number; y2: number },
  ): boolean {
    return !(Math.max(ax, bx) < b.x1 || Math.min(ax, bx) > b.x2 || Math.max(ay, by) < b.y1 || Math.min(ay, by) > b.y2);
  }

  /** Update node appearance for selection/hover without recreating */
  function updateNodeAppearance() {
    for (const [id, circle] of nodeShapes) {
      const isSelected = selectedId === id;
      const isHovered = hoveredId === id;
      const node = nodeById.get(id);
      if (!node) continue;
      circle.radius(isSelected ? 10 : isHovered ? 9 : 6);
      circle.fill(isSelected ? '#f78166' : nodeColorFor(node));
      circle.stroke(isSelected ? '#fff' : isHovered ? '#58a6ff' : null);
      circle.strokeWidth((isSelected || isHovered) ? 2 : 0);
    }
    nodeLayer.batchDraw();
  }

  function bucketByType(edges: GraphEdge[]): Map<string, GraphEdge[]> {
    const buckets = new Map<string, GraphEdge[]>();
    for (const edge of edges) {
      const list = buckets.get(edge.type);
      if (list) list.push(edge);
      else buckets.set(edge.type, [edge]);
    }
    return buckets;
  }

  function addLineBatch(
    batch: GraphEdge[],
    opts: { curved: boolean; opacity: number; width: number; dash?: number[]; lineCap?: string; cull: boolean },
  ) {
    edgeLayer.add(new Konva.Shape({
      sceneFunc: (ctx: any, shape: any) => {
        const bounds = opts.cull ? getViewportBounds() : null;
        ctx.beginPath();
        for (const edge of batch) {
          const s = nodePositions.get(edge.source);
          const t = nodePositions.get(edge.target);
          if (!s || !t) continue;
          if (bounds && !segmentInView(s.x, s.y, t.x, t.y, bounds)) continue;
          ctx.moveTo(s.x, s.y);
          if (opts.curved) {
            const dx = t.x - s.x;
            const dy = t.y - s.y;
            ctx.quadraticCurveTo((s.x + t.x) / 2 - dy * 0.08, (s.y + t.y) / 2 + dx * 0.08, t.x, t.y);
          } else {
            ctx.lineTo(t.x, t.y);
          }
        }
        ctx.strokeShape(shape);
      },
      stroke: edgeStroke(batch[0]),
      strokeWidth: opts.width,
      opacity: opts.opacity,
      dash: opts.dash,
      lineCap: opts.lineCap,
      listening: false,
      perfectDrawEnabled: false,
      shadowForStrokeEnabled: false,
    }));
  }

  type ArrowGeom = {
    sx: number; sy: number; ctrlX: number; ctrlY: number;
    baseX: number; baseY: number; tipX: number; tipY: number;
    mnx: number; mny: number;
  };

  function arrowGeom(edge: GraphEdge, idx: number): ArrowGeom | null {
    let srcPos = nodePositions.get(edge.source);
    let tgtPos = nodePositions.get(edge.target);
    if (!srcPos || !tgtPos) return null;
    if (edge.type === 'member_of' || edge.type === 'nation') {
      [srcPos, tgtPos] = [tgtPos, srcPos];
    }
    const dx = tgtPos.x - srcPos.x;
    const dy = tgtPos.y - srcPos.y;
    const len = Math.sqrt(dx * dx + dy * dy);
    if (len < 20) return null;
    const spread = (idx - 0.5) * 0.12;
    const ctrlX = (srcPos.x + tgtPos.x) / 2 - dy * (0.08 + spread);
    const ctrlY = (srcPos.y + tgtPos.y) / 2 + dx * (0.08 + spread);
    const tanX = tgtPos.x - ctrlX;
    const tanY = tgtPos.y - ctrlY;
    const tanLen = Math.sqrt(tanX * tanX + tanY * tanY) || 1;
    const mnx = tanX / tanLen;
    const mny = tanY / tanLen;
    return {
      sx: srcPos.x, sy: srcPos.y, ctrlX, ctrlY, mnx, mny,
      tipX: tgtPos.x - mnx * 10, tipY: tgtPos.y - mny * 10,
      baseX: tgtPos.x - mnx * 20, baseY: tgtPos.y - mny * 20,
    };
  }

  function addArrowBatch(batch: GraphEdge[], opacity: number, width: number) {
    const targetCount = new Map<string, number>();
    const geoms: ArrowGeom[] = [];
    for (const edge of batch) {
      const tgt = nodePositions.get(edge.type === 'member_of' || edge.type === 'nation' ? edge.source : edge.target);
      const key = tgt ? `${tgt.x},${tgt.y}` : '';
      const idx = targetCount.get(key) ?? 0;
      targetCount.set(key, idx + 1);
      const geom = arrowGeom(edge, idx);
      if (geom) geoms.push(geom);
    }
    if (geoms.length === 0) return;
    const stroke = edgeStroke(batch[0]);
    edgeLayer.add(new Konva.Shape({
      sceneFunc: (ctx: any, shape: any) => {
        ctx.beginPath();
        for (const g of geoms) {
          ctx.moveTo(g.sx, g.sy);
          ctx.quadraticCurveTo(g.ctrlX, g.ctrlY, g.baseX, g.baseY);
        }
        ctx.strokeShape(shape);
      },
      stroke,
      strokeWidth: width,
      opacity,
      listening: false,
      perfectDrawEnabled: false,
      shadowForStrokeEnabled: false,
    }));
    edgeLayer.add(new Konva.Shape({
      sceneFunc: (ctx: any, shape: any) => {
        const sz = 6;
        for (const g of geoms) {
          ctx.beginPath();
          ctx.moveTo(g.tipX, g.tipY);
          ctx.lineTo(g.baseX - g.mny * sz, g.baseY + g.mnx * sz);
          ctx.lineTo(g.baseX + g.mny * sz, g.baseY - g.mnx * sz);
          ctx.closePath();
        }
        ctx.fillShape(shape);
      },
      fill: stroke,
      opacity,
      listening: false,
      perfectDrawEnabled: false,
    }));
  }

  /** Draw edges based on current mode */
  function drawEdges(focusNodeId: string | null) {
    edgeLayer.destroyChildren();

    const overview = edgeMode === 'all';
    let edgesToDraw: GraphEdge[] = [];

    if (overview) {
      for (const edge of graph.edges) {
        if (!visibleIds.has(edge.source) || !visibleIds.has(edge.target)) continue;
        if (!nodePositions.has(edge.source) || !nodePositions.has(edge.target)) continue;
        edgesToDraw.push(edge);
      }
    } else if (focusNodeId) {
      edgesToDraw.push(...(edgeIndex.get(focusNodeId) ?? []));
    }

    edgesToDraw = edgesToDraw.filter((e) => nodePositions.has(e.source) && nodePositions.has(e.target));
    if (edgesToDraw.length === 0) {
      edgeLayer.draw();
      return;
    }

    const directionalTypes = new Set(['spin_off', 'parent', 'member_of', 'nation']);
    const lineEdges: GraphEdge[] = [];
    const arrowEdges: GraphEdge[] = [];
    for (const edge of edgesToDraw) {
      if (!overview && directionalTypes.has(edge.type)) arrowEdges.push(edge);
      else lineEdges.push(edge);
    }

    const opacity = overview ? (selectedId ? 0.12 : 0.35) : 1;
    const width = overview ? 1 : 2;

    for (const [, batch] of bucketByType(lineEdges)) {
      addLineBatch(batch, {
        curved: !overview,
        opacity,
        width,
        dash: overview ? undefined : (batch[0].type === 'rivalry' ? [6, 3] : batch[0].type === 'alliance' ? [0.5, 4] : undefined),
        lineCap: batch[0].type === 'alliance' ? 'round' : undefined,
        cull: overview,
      });
    }

    for (const [, batch] of bucketByType(arrowEdges)) {
      addArrowBatch(batch, 1, 2);
    }

    if (overview && selectedId) {
      const focusEdges = (edgeIndex.get(selectedId) ?? []).filter(
        (e) => nodePositions.has(e.source) && nodePositions.has(e.target),
      );
      for (const [, fbatch] of bucketByType(focusEdges)) {
        addLineBatch(fbatch, {
          curved: true,
          opacity: 1,
          width: 2.5,
          dash: fbatch[0].type === 'rivalry' ? [6, 3] : fbatch[0].type === 'alliance' ? [0.5, 4] : undefined,
          lineCap: fbatch[0].type === 'alliance' ? 'round' : undefined,
          cull: false,
        });
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
    const yearDomainChanged = yearDomain.minYear !== prevYearMin || yearDomain.maxYear !== prevYearMax;
    if (!bgBuilt || lanes.length !== prevLaneCount || yearDomainChanged) buildBackground();
    if (!axisBuilt || yearDomainChanged) buildAxis();
    else syncAxisLayer();
    buildNodes();
    drawEdges(selectedId ?? hoveredId);
    drawLabels();
  }

  function buildSceneAsync() {
    buildScene();
    tryRevealMap();
  }

  function tryRevealMap(): boolean {
    if (!containerEl || !stage) return false;
    const width = containerEl.clientWidth;
    const height = containerEl.clientHeight;
    if (!isUsableStageSize(width, height)) return false;
    stage.width(width);
    stage.height(height);
    fitToView();
    didInitialFit = true;
    mapReady = true;
    onready?.();
    return true;
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
    syncAxisLayer();
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
    syncAxisLayer();
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
    syncAxisLayer();
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
      if (edgeMode !== 'all') drawEdges(selectedId ?? hov);
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
    let cancelled = false;
    let bootRaf = 0;
    const syncStageBox = () => {
      if (!containerEl || !stage) return;
      const width = containerEl.clientWidth;
      const height = containerEl.clientHeight;
      if (!isUsableStageSize(width, height)) return;
      stage.width(width);
      stage.height(height);
      syncAxisLayer();
      if (!didInitialFit) tryRevealMap();
    };

    const boot = () => {
      if (cancelled) return;
      if (!containerEl) {
        bootRaf = requestAnimationFrame(boot);
        return;
      }

    Konva.pixelRatio = 1;

    stage = new Konva.Stage({
      container: containerEl,
      width: Math.max(containerEl.clientWidth, 1),
      height: Math.max(containerEl.clientHeight, 1),
      draggable: true,
    });

    bgLayer = new Konva.Layer({ listening: false });
    edgeLayer = new Konva.Layer({ listening: false });
    nodeLayer = new Konva.Layer();
    labelLayer = new Konva.Layer({ listening: false });
    axisLayer = new Konva.Layer({ listening: false });

    stage.add(bgLayer);
    stage.add(edgeLayer);
    stage.add(nodeLayer);
    stage.add(labelLayer);
    stage.add(axisLayer);

    // Wheel zoom
    stage.on('wheel', (e: any) => {
      e.evt.preventDefault();
      const factor = e.evt.deltaY > 0 ? 0.9 : 1.1;
      const pointer = stage.getPointerPosition();
      if (pointer) applyZoom(factor, pointer.x, pointer.y);
    });

    let pinchDist = 0;
    let pinchCenter: { x: number; y: number } | null = null;

    function pinchPoint(touches: TouchList, i: number): { x: number; y: number } {
      const rect = containerEl!.getBoundingClientRect();
      return { x: touches[i].clientX - rect.left, y: touches[i].clientY - rect.top };
    }

    stage.on('touchmove', (e: any) => {
      const touches: TouchList | undefined = e.evt?.touches;
      if (!touches || touches.length < 2) return;
      e.evt.preventDefault();
      stage.draggable(false);
      const a = pinchPoint(touches, 0);
      const b = pinchPoint(touches, 1);
      const dist = Math.hypot(b.x - a.x, b.y - a.y);
      const center = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
      if (pinchDist > 0 && pinchCenter) {
        stage.position({
          x: stage.x() + (center.x - pinchCenter.x),
          y: stage.y() + (center.y - pinchCenter.y),
        });
        applyZoom(dist / pinchDist, center.x, center.y);
      }
      pinchDist = dist;
      pinchCenter = center;
    });

    const endPinch = () => {
      pinchDist = 0;
      pinchCenter = null;
      stage.draggable(true);
    };
    stage.on('touchend', endPinch);
    stage.on('touchcancel', endPinch);

    // Rebuild labels on pan end (viewport-dependent)
    // Also re-enable hit detection after drag (was disabled for perf during drag)
    stage.on('dragstart', () => {
      nodeLayer.listening(false);
    });
    stage.on('dragmove', () => {
      syncAxisLayer();
    });
    stage.on('dragend', () => {
      nodeLayer.listening(true);
      syncAxisLayer();
      if (rebuildTimer) clearTimeout(rebuildTimer);
      rebuildTimer = setTimeout(() => drawLabels(), 150);
    });

    // Click on empty space = deselect
    stage.on('click tap', (e: any) => {
      if (e.target === stage) ondeselect?.();
    });

    resizeObserver = new ResizeObserver(syncStageBox);
    resizeObserver.observe(containerEl);
    window.addEventListener('resize', syncStageBox);
    window.visualViewport?.addEventListener('resize', syncStageBox);

    buildSceneAsync();

    // PaneGroup can report 0×0 on the first frame; keep polling until layout exists.
    const pollReveal = () => {
      if (cancelled || didInitialFit) return;
      if (!tryRevealMap()) {
        bootRaf = requestAnimationFrame(pollReveal);
      }
    };
    pollReveal();
    };

    boot();

    return () => {
      cancelled = true;
      if (bootRaf) cancelAnimationFrame(bootRaf);
      resizeObserver?.disconnect();
      window.removeEventListener('resize', syncStageBox);
      window.visualViewport?.removeEventListener('resize', syncStageBox);
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

