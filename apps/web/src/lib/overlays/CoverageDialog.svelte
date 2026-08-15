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
        class="size-8 shrink-0 text-muted-foreground hover:text-foreground md:size-6"
        aria-label="Data coverage"
      >
        <Info class="size-3.5" />
      </Button>
    {/snippet}
  </Dialog.Trigger>

  <Dialog.Content class="max-h-[85dvh] overflow-y-auto sm:max-w-2xl">
    <Dialog.Header>
      <Dialog.Title>Data Coverage Report</Dialog.Title>
    </Dialog.Header>

    {#if vis}
      <div class="grid grid-cols-2 gap-2 py-2 sm:grid-cols-4 sm:gap-3 sm:py-4">
        <div class="min-w-0 rounded-lg border border-border p-2.5 text-center sm:p-3">
          <div class="text-xl font-bold tabular-nums sm:text-2xl">{fmt(vis.exported.nodes)}</div>
          <div class="text-[0.65rem] leading-tight text-muted-foreground">Orgs</div>
        </div>
        <div class="min-w-0 rounded-lg border border-border p-2.5 text-center sm:p-3">
          <div class="text-xl font-bold tabular-nums sm:text-2xl">{fmt(vis.exported.edges)}</div>
          <div class="text-[0.65rem] leading-tight text-muted-foreground">Edges</div>
        </div>
        <div class="min-w-0 rounded-lg border border-border p-2.5 text-center sm:p-3">
          <div class="text-xl font-bold tabular-nums sm:text-2xl">{fmt(vis.exported.total_sources)}</div>
          <div class="text-[0.65rem] leading-tight text-muted-foreground">Sources</div>
        </div>
        <div class="min-w-0 rounded-lg border border-border p-2.5 text-center sm:p-3">
          <div class="text-xl font-bold tabular-nums sm:text-2xl">{Object.keys(vis.lane_counts ?? {}).length}</div>
          <div class="text-[0.65rem] leading-tight text-muted-foreground">Lanes</div>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-5 text-xs sm:grid-cols-2 sm:gap-6">
        <div class="flex min-w-0 flex-col gap-4">
          <div>
            <h4 class="mb-2 text-[0.65rem] font-semibold uppercase tracking-wider text-muted-foreground">Data Quality</h4>
            <div class="flex flex-col gap-1.5">
              <div class="flex min-w-0 justify-between gap-2"><span class="min-w-0 truncate">Descriptions</span><span class="shrink-0 font-medium tabular-nums text-green-500">{pct(vis.exported.nodes_with_description, vis.exported.nodes)}</span></div>
              <div class="flex min-w-0 justify-between gap-2"><span class="min-w-0 truncate">Colors documented</span><span class="shrink-0 font-medium tabular-nums">{pct(vis.exported.nodes_with_colors, vis.exported.nodes)}</span></div>
              <div class="flex min-w-0 justify-between gap-2"><span class="min-w-0 truncate">Multi-source (2+)</span><span class="shrink-0 font-medium tabular-nums">{pct(vis.exported.nodes_multi_source, vis.exported.nodes)}</span></div>
              <div class="flex min-w-0 justify-between gap-2"><span class="min-w-0 truncate">Aliases present</span><span class="shrink-0 font-medium tabular-nums">{pct(vis.exported.nodes_with_aliases, vis.exported.nodes)}</span></div>
              <div class="flex min-w-0 justify-between gap-2"><span class="min-w-0 truncate">Metro assigned</span><span class="shrink-0 font-medium tabular-nums">{pct(vis.exported.nodes_with_metro, vis.exported.nodes)}</span></div>
            </div>
          </div>

          <div>
            <h4 class="mb-2 text-[0.65rem] font-semibold uppercase tracking-wider text-muted-foreground">Year Precision</h4>
            <div class="flex flex-col gap-1.5">
              <div class="flex min-w-0 justify-between gap-2"><span class="min-w-0 truncate">Exact / circa</span><span class="shrink-0 font-medium tabular-nums text-green-500">{fmt(vis.exported.nodes_exact_circa)}</span></div>
              <div class="flex min-w-0 justify-between gap-2"><span class="min-w-0 truncate">Decade-estimated</span><span class="shrink-0 font-medium tabular-nums text-yellow-500">{fmt(vis.exported.nodes_decade_estimated)}</span></div>
              <div class="flex min-w-0 justify-between gap-2"><span class="min-w-0 truncate">Unresearched</span><span class="shrink-0 font-medium tabular-nums text-red-400">{fmt(vis.exported.nodes_estimate_only)}</span></div>
            </div>
          </div>
        </div>

        <div class="flex min-w-0 flex-col gap-4">
          <div>
            <h4 class="mb-2 text-[0.65rem] font-semibold uppercase tracking-wider text-muted-foreground">Edge Breakdown</h4>
            <div class="flex flex-col gap-1.5">
              {#each Object.entries(vis.edge_types ?? {}).sort((a, b) => (b[1] as number) - (a[1] as number)) as [type, count]}
                <div class="flex min-w-0 justify-between gap-2">
                  <span class="min-w-0 truncate">{type}</span>
                  <span class="shrink-0 font-medium tabular-nums">{count}</span>
                </div>
              {/each}
            </div>
          </div>

          <div>
            <h4 class="mb-2 text-[0.65rem] font-semibold uppercase tracking-wider text-muted-foreground">Top Sources</h4>
            <div class="flex flex-col gap-1.5">
              {#each (vis.top_source_domains ?? []).slice(0, 6) as [domain, count]}
                <div class="flex min-w-0 justify-between gap-2">
                  <span class="min-w-0 truncate">{domain}</span>
                  <span class="shrink-0 font-medium tabular-nums">{count}</span>
                </div>
              {/each}
            </div>
          </div>
        </div>
      </div>

      <div class="mt-4 flex items-center border-t border-border pt-3 text-[0.65rem] text-muted-foreground">
        <span class="ml-auto truncate">Built: {new Date(graph.exported_at ?? '').toLocaleString(undefined, {month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'})}</span>
      </div>
    {:else}
      <p class="py-8 text-center text-sm text-muted-foreground">Rebuild to populate coverage data.</p>
    {/if}
  </Dialog.Content>
</Dialog.Root>
