import type { Graph } from '$lib/types';

/** Sorted unique metro labels from graph nodes. */
export function metroOptions(graph: Graph): string[] {
  const metros = new Set<string>();
  for (const node of graph.nodes) {
    const metro = node.data?.metro?.trim();
    if (metro) metros.add(metro);
  }
  return [...metros].sort((a, b) => a.localeCompare(b));
}

export function nodeMatchesMetro(
  node: Graph['nodes'][number],
  metroFilter: string | null,
): boolean {
  if (!metroFilter) return true;
  return (node.data?.metro?.trim() || '') === metroFilter;
}
