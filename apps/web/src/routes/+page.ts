import type { Graph } from '$lib/types';

export async function load({ fetch }) {
  // Do not pass a custom AbortSignal. SvelteKit hydrates prerendered fetch
  // results from a script tag; a timeout/retry can miss that cache and hang
  // on a competing <link rel=preload> of the same URL.
  const res = await fetch('/graph.json');
  if (!res.ok) {
    throw new Error(`Failed to load graph.json (${res.status})`);
  }
  const graph: Graph = await res.json();
  return { graph };
}
