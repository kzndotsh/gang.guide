import type { Graph } from '$lib/types';

export function nodeMatchesMetro(
  node: Graph['nodes'][number],
  metroFilter: string | null,
): boolean {
  if (!metroFilter) return true;
  return (node.data?.metro?.trim() || '') === metroFilter;
}
