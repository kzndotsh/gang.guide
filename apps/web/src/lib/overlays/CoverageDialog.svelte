<script lang="ts">
  import { Info } from '@lucide/svelte';
  import type { EdgeMode } from '$lib/map/KonvaMap.svelte';
  import type { Graph } from '$lib/types';
  import { visibleEdgeCount } from '$lib/map/visibility';
  import { Button } from '$lib/components/ui/button/index.js';
  import * as Dialog from '$lib/components/ui/dialog/index.js';

  interface Props {
    graph: Graph;
    edgeMode: EdgeMode;
    selectedId: string | null;
  }

  let { graph, edgeMode, selectedId }: Props = $props();

  const vis = $derived(graph.meta?.visibility);

  function fmt(n: number | undefined): string {
    return n == null ? '—' : n.toLocaleString();
  }

  function pct(n: number | undefined, total: number | undefined): string {
    if (n == null || total == null || total === 0) return '—';
    return `${Math.round((n / total) * 100)}%`;
  }
</script>

<Dialog.Root>
  <Dialog.Trigger>
    {#snippet child({ props })}
      <Button
        {...props}
        variant="outline"
        size="icon-sm"
        class="size-6 shrink-0 text-muted-foreground hover:text-foreground"
        aria-label="Data coverage"
      >
        <Info class="size-3.5" />
      </Button>
    {/snippet}
  </Dialog.Trigger>

  <Dialog.Content class="sm:max-w-2xl">
    <Dialog.Header>
      <Dialog.Title>Data Coverage Report</Dialog.Title>
    </Dialog.Header>

    {#if vis}
      <!-- Top stats row -->
      <div class="grid grid-cols-4 gap-3 py-4">
        <div class="rounded-lg border border-border p-3 text-center">
          <div class="text-2xl font-bold tabular-nums">{fmt(vis.exported.nodes)}</div>
          <div class="text-[0.65rem] text-muted-foreground">Organizations</div>
        </div>
        <div class="rounded-lg border border-border p-3 text-center">
          <div class="text-2xl font-bold tabular-nums">{fmt(vis.exported.edges)}</div>
          <div class="text-[0.65rem] text-muted-foreground">Relationships</div>
        </div>
        <div class="rounded-lg border border-border p-3 text-center">
          <div class="text-2xl font-bold tabular-nums">{fmt(vis.exported.total_sources)}</div>
          <div class="text-[0.65rem] text-muted-foreground">Sources</div>
        </div>
        <div class="rounded-lg border border-border p-3 text-center">
          <div class="text-2xl font-bold tabular-nums">{Object.keys(vis.lane_counts ?? {}).length}</div>
          <div class="text-[0.65rem] text-muted-foreground">Lanes</div>
        </div>
      </div>

      <!-- Two column layout -->
      <div class="grid grid-cols-2 gap-6 text-xs">
        <!-- Left: Quality -->
        <div class="space-y-4">
          <div>
            <h4 class="mb-2 text-[0.65rem] font-semibold uppercase tracking-wider text-muted-foreground">Data Quality</h4>
            <div class="space-y-1.5">
              <div class="flex justify-between"><span>Descriptions</span><span class="font-medium text-green-500">{pct(vis.exported.nodes_with_description, vis.exported.nodes)}</span></div>
              <div class="flex justify-between"><span>Colors documented</span><span class="font-medium">{pct(vis.exported.nodes_with_colors, vis.exported.nodes)}</span></div>
              <div class="flex justify-between"><span>Multi-source (2+)</span><span class="font-medium">{pct(vis.exported.nodes_multi_source, vis.exported.nodes)}</span></div>
              <div class="flex justify-between"><span>Aliases present</span><span class="font-medium">{pct(vis.exported.nodes_with_aliases, vis.exported.nodes)}</span></div>
              <div class="flex justify-between"><span>Metro assigned</span><span class="font-medium">{pct(vis.exported.nodes_with_metro, vis.exported.nodes)}</span></div>
            </div>
          </div>

          <div>
            <h4 class="mb-2 text-[0.65rem] font-semibold uppercase tracking-wider text-muted-foreground">Year Precision</h4>
            <div class="space-y-1.5">
              <div class="flex justify-between"><span>Exact / circa</span><span class="font-medium text-green-500">{fmt(vis.exported.nodes_exact_circa)}</span></div>
              <div class="flex justify-between"><span>Decade-estimated</span><span class="font-medium text-yellow-500">{fmt(vis.exported.nodes_decade_estimated)}</span></div>
              <div class="flex justify-between"><span>Unresearched</span><span class="font-medium text-red-400">{fmt(vis.exported.nodes_estimate_only)}</span></div>
            </div>
          </div>
        </div>

        <!-- Right: Edges + Sources -->
        <div class="space-y-4">
          <div>
            <h4 class="mb-2 text-[0.65rem] font-semibold uppercase tracking-wider text-muted-foreground">Edge Breakdown</h4>
            <div class="space-y-1.5">
              {#each Object.entries(vis.edge_types ?? {}).sort((a, b) => (b[1] as number) - (a[1] as number)) as [type, count]}
                <div class="flex justify-between">
                  <span>{type}</span>
                  <span class="font-medium tabular-nums">{count}</span>
                </div>
              {/each}
            </div>
          </div>

          <div>
            <h4 class="mb-2 text-[0.65rem] font-semibold uppercase tracking-wider text-muted-foreground">Top Sources</h4>
            <div class="space-y-1.5">
              {#each (vis.top_source_domains ?? []).slice(0, 6) as [domain, count]}
                <div class="flex justify-between">
                  <span class="truncate">{domain}</span>
                  <span class="font-medium tabular-nums">{count}</span>
                </div>
              {/each}
            </div>
          </div>
        </div>
      </div>

      <!-- Status bar -->
      <div class="mt-4 flex items-center gap-4 border-t border-border pt-3 text-[0.65rem] text-muted-foreground">
        <span class="ml-auto">Built: {new Date(graph.exported_at ?? '').toLocaleString(undefined, {month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'})}</span>
      </div>
    {:else}
      <p class="py-8 text-center text-sm text-muted-foreground">Rebuild to populate coverage data.</p>
    {/if}
  </Dialog.Content>
</Dialog.Root>
