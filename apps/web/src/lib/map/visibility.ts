import type { EdgeMode } from '$lib/map/KonvaMap.svelte';
import type { Graph } from '$lib/types';

function visibleNodeIds(graph: Graph): Set<string> {
  return new Set(graph.nodes.map((n) => n.id));
}

export function visibleEdgeCount(
  graph: Graph,
  edgeMode: EdgeMode,
  selectedId: string | null
): number {
  const nodeIds = visibleNodeIds(graph);
  const endpointsVisible = (e: Graph['edges'][number]) =>
    nodeIds.has(e.source) && nodeIds.has(e.target);

  switch (edgeMode) {
    case 'all':
      return graph.edges.filter(endpointsVisible).length;
    case 'hover':
      if (!selectedId) return 0;
      return graph.edges.filter(
        (e) => endpointsVisible(e) && (e.source === selectedId || e.target === selectedId)
      ).length;
    default: {
      const _exhaustive: never = edgeMode;
      return _exhaustive;
    }
  }
}
