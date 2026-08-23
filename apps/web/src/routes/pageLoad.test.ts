import { describe, expect, it, vi } from 'vitest';
import { load } from './+page';

describe('page graph load', () => {
  it('reads graph.json through kit fetch without a custom abort signal', async () => {
    const graph = { nodes: [], edges: [], meta: {} };
    const fetch = vi.fn(async (url: string, init?: RequestInit) => {
      expect(url).toBe('/graph.json');
      expect(init?.signal).toBeUndefined();
      return new Response(JSON.stringify(graph), { status: 200 });
    });

    const result = await load({ fetch } as never);

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(result.graph).toEqual(graph);
  });
});
