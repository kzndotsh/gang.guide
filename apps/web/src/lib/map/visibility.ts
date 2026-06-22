import type { EdgeMode } from '$lib/map/KonvaMap.svelte';
import type { Graph, GraphEvent } from '$lib/types';
import { eventYearMidpoint } from '$lib/yearFormat';

export function visibleNodeIds(graph: Graph): Set<string> {
  return new Set(graph.nodes.map((n) => n.id));
}

export function visibleEdgeCount(
  graph: Graph,
  edgeMode: EdgeMode,
  selectedId: string | null
): number {
  const nodeIds = visibleNodeIds(graph);
  return graph.edges.filter((e) => {
    if (!nodeIds.has(e.source) || !nodeIds.has(e.target)) return false;
    if (edgeMode === 'all') return true;
    if (edgeMode === 'focus' && selectedId) {
      return e.source === selectedId || e.target === selectedId;
    }
    return e.type === 'nation_affiliation';
  }).length;
}

export function isStripEvent(ev: GraphEvent): boolean {
  if (ev.title?.includes('NYGS estimated active gangs')) return false;
  return eventYearMidpoint(ev) != null;
}

export function isEventLinkedToGraph(graph: Graph, ev: GraphEvent): boolean {
  const nodeIds = new Set(graph.nodes.map((n) => n.id));
  return (ev.data?.org_ids ?? []).some((id) => nodeIds.has(id));
}
