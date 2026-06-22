import type { Graph } from '$lib/types';

export async function load({ fetch }) {
  const res = await fetch('/graph.json');
  if (!res.ok) {
    throw new Error('Failed to load graph.json');
  }
  const graph: Graph = await res.json();
  return { graph };
}
