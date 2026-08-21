import type { Graph } from '$lib/types';

const GRAPH_ATTEMPTS = 3;
const GRAPH_TIMEOUT_MS = 12_000;

export async function load({ fetch }) {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt < GRAPH_ATTEMPTS; attempt++) {
    try {
      const res = await fetch('/graph.json', { signal: abortAfter(GRAPH_TIMEOUT_MS) });
      if (!res.ok) {
        lastError = new Error(`Failed to load graph.json (${res.status})`);
        continue;
      }
      const graph: Graph = await res.json();
      return { graph };
    } catch (err) {
      lastError = err instanceof Error ? err : new Error('Failed to load graph.json');
    }
  }

  throw lastError ?? new Error('Failed to load graph.json');
}

function abortAfter(ms: number): AbortSignal | undefined {
  try {
    return AbortSignal.timeout(ms);
  } catch {
    return undefined;
  }
}
