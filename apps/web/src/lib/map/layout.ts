import type { Graph, GraphNode } from '$lib/types';

export type LaneMeta = {
  id: string;
  label: string;
  sort_order?: number;
  order?: number;
  cluster?: string;
};

const FALLBACK_LABELS: Record<string, string> = {
  prison: 'Prison gangs',
  'chicago-folk-people': 'Chicago · Folk / People',
  'chicago-sets': 'Chicago · sets',
  'blood-nation': 'Bloods (alliance)',
  'california-bloods': 'California · Bloods sets',
  'crip-nation': 'Crips (alliance)',
  'california-hispanic': 'California · Latino gangs',
  'new-york': 'New York',
  southwest: 'Southwest',
  unplaced: 'Unplaced',
};

const FALLBACK_ORDER: Record<string, number> = {
  prison: 10,
  'chicago-folk-people': 20,
  'chicago-sets': 30,
  'blood-nation': 39,
  'california-bloods': 40,
  'crip-nation': 45,
  'california-hispanic': 55,
  'new-york': 60,
  southwest: 70,
  unplaced: 100,
};

export function laneCatalog(graph?: Graph): LaneMeta[] {
  if (graph?.meta?.lanes?.length) {
    return [...graph.meta.lanes].sort(
      (a, b) => (a.sort_order ?? a.order ?? 999) - (b.sort_order ?? b.order ?? 999)
    );
  }
  return Object.entries(FALLBACK_LABELS).map(([id, label]) => ({
    id,
    label,
    sort_order: FALLBACK_ORDER[id],
  }));
}

export function laneLabel(laneId: string, graph?: Graph, node?: GraphNode): string {
  if (node?.data?.layout?.lane_label && node.data.layout.lane === laneId) {
    return node.data.layout.lane_label;
  }
  const row = laneCatalog(graph).find((l) => l.id === laneId);
  return row?.label ?? FALLBACK_LABELS[laneId] ?? laneId;
}

export function laneSortOrder(laneId: string, graph?: Graph, node?: GraphNode): number {
  if (node?.data?.layout?.lane_index != null && node.data.layout.lane === laneId) {
    return node.data.layout.lane_index;
  }
  const row = laneCatalog(graph).find((l) => l.id === laneId);
  return row?.sort_order ?? row?.order ?? FALLBACK_ORDER[laneId] ?? 999;
}

export function shortLabel(label: string, max = 18): string {
  return label.length <= max ? label : `${label.slice(0, max - 1)}…`;
}

/** Client fallback when exported layout is missing (static dev edge cases). */
export function deriveClientLayout(node: GraphNode, slot = 0) {
  const existing = node.data?.layout;
  if (existing) return existing;

  return {
    lane: 'unplaced',
    lane_label: 'Unplaced',
    lane_index: 100,
    display_year: 1970 + (slot % 24),
    slot,
    overview: false,
  };
}
