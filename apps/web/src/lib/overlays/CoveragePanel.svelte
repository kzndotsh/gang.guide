<script lang="ts">
  import type { EdgeMode } from '$lib/map/KonvaMap.svelte';
  import type { Graph } from '$lib/types';
  import { visibleEdgeCount } from '$lib/map/visibility';
  import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';

  interface Props {
    graph: Graph;
    edgeMode: EdgeMode;
    selectedId: string | null;
  }

  let { graph, edgeMode, selectedId }: Props = $props();

  const vis = $derived(graph.meta?.visibility);
  const drawnEdges = $derived(visibleEdgeCount(graph, edgeMode, selectedId));
  const hiddenEdges = $derived((graph.edges.length || 0) - drawnEdges);

  function fmt(n: number | undefined): string {
    return n == null ? '—' : n.toLocaleString();
  }

  function pct(n: number | undefined, total: number | undefined): string {
    if (n == null || total == null || total === 0) return '';
    return `${Math.round((n / total) * 100)}%`;
  }
</script>

<ScrollArea class="max-h-[min(70vh,32rem)] pr-3">
  <div class="space-y-3">
    <section>
      <h4 class="mb-1.5 text-[0.6rem] font-semibold uppercase tracking-wider text-muted-foreground/80">
        Visible on map
      </h4>
      <ul class="flex list-none flex-col gap-0.5 p-0">
        <li class="flex justify-between gap-3 text-xs text-muted-foreground">
          <span>Nodes</span>
          <strong class="font-semibold tabular-nums text-foreground">{graph.nodes.length}</strong>
        </li>
        <li class="flex justify-between gap-3 text-xs text-muted-foreground">
          <span>Edges drawn</span>
          <strong class="font-semibold tabular-nums text-foreground">{drawnEdges}</strong>
        </li>
        {#if hiddenEdges > 0}
          <li class="flex justify-between gap-3 text-xs">
            <span class="text-amber-400">Edges hidden by filter</span>
            <strong class="font-semibold tabular-nums text-foreground">{hiddenEdges}</strong>
          </li>
        {/if}
      </ul>
    </section>

    {#if vis}
      <section class="border-t border-border/60 pt-3">
        <h4 class="mb-1.5 text-[0.6rem] font-semibold uppercase tracking-wider text-muted-foreground/80">
          Data quality
        </h4>
        <ul class="flex list-none flex-col gap-0.5 p-0">
          <li class="flex justify-between gap-3 text-xs text-muted-foreground">
            <span>Description (50+ chars)</span>
            <strong class="font-semibold tabular-nums text-foreground">{fmt(vis.exported.nodes_with_description)} <span class="text-muted-foreground/60">{pct(vis.exported.nodes_with_description, vis.exported.nodes)}</span></strong>
          </li>
          <li class="flex justify-between gap-3 text-xs text-muted-foreground">
            <span>Colors documented</span>
            <strong class="font-semibold tabular-nums text-foreground">{fmt(vis.exported.nodes_with_colors)} <span class="text-muted-foreground/60">{pct(vis.exported.nodes_with_colors, vis.exported.nodes)}</span></strong>
          </li>
          <li class="flex justify-between gap-3 text-xs text-muted-foreground">
            <span>Aliases present</span>
            <strong class="font-semibold tabular-nums text-foreground">{fmt(vis.exported.nodes_with_aliases)} <span class="text-muted-foreground/60">{pct(vis.exported.nodes_with_aliases, vis.exported.nodes)}</span></strong>
          </li>
          <li class="flex justify-between gap-3 text-xs text-muted-foreground">
            <span>Metro assigned</span>
            <strong class="font-semibold tabular-nums text-foreground">{fmt(vis.exported.nodes_with_metro)} <span class="text-muted-foreground/60">{pct(vis.exported.nodes_with_metro, vis.exported.nodes)}</span></strong>
          </li>
          <li class="flex justify-between gap-3 text-xs text-muted-foreground">
            <span>Multi-source (2+)</span>
            <strong class="font-semibold tabular-nums text-foreground">{fmt(vis.exported.nodes_multi_source)} <span class="text-muted-foreground/60">{pct(vis.exported.nodes_multi_source, vis.exported.nodes)}</span></strong>
          </li>
        </ul>
      </section>

      <section class="border-t border-border/60 pt-3">
        <h4 class="mb-1.5 text-[0.6rem] font-semibold uppercase tracking-wider text-muted-foreground/80">
          Founded year precision
        </h4>
        <ul class="flex list-none flex-col gap-0.5 p-0">
          <li class="flex justify-between gap-3 text-xs text-muted-foreground">
            <span>Exact / circa</span>
            <strong class="font-semibold tabular-nums text-foreground">{fmt(vis.exported.nodes_exact_circa)} <span class="text-muted-foreground/60">{pct(vis.exported.nodes_exact_circa, vis.exported.nodes)}</span></strong>
          </li>
          <li class="flex justify-between gap-3 text-xs text-muted-foreground">
            <span>Decade-estimated</span>
            <strong class="font-semibold tabular-nums text-foreground">{fmt(vis.exported.nodes_decade_estimated)} <span class="text-muted-foreground/60">{pct(vis.exported.nodes_decade_estimated, vis.exported.nodes)}</span></strong>
          </li>
          <li class="flex justify-between gap-3 text-xs text-muted-foreground">
            <span>Unresearched estimate</span>
            <strong class="font-semibold tabular-nums text-foreground">{fmt(vis.exported.nodes_estimate_only)} <span class="text-muted-foreground/60">{pct(vis.exported.nodes_estimate_only, vis.exported.nodes)}</span></strong>
          </li>
          <li class="flex justify-between gap-3 text-xs text-muted-foreground">
            <span>Missing year entirely</span>
            <strong class="font-semibold tabular-nums text-foreground">{(vis.exported.nodes ?? 0) - (vis.exported.nodes_with_founded_year ?? 0)}</strong>
          </li>
        </ul>
      </section>

      <section class="border-t border-border/60 pt-3">
        <h4 class="mb-1.5 text-[0.6rem] font-semibold uppercase tracking-wider text-muted-foreground/80">
          Status
        </h4>
        <ul class="flex list-none flex-col gap-0.5 p-0">
          <li class="flex justify-between gap-3 text-xs text-muted-foreground">
            <span>Active</span>
            <strong class="font-semibold tabular-nums text-foreground">{fmt(vis.exported.nodes_active)}</strong>
          </li>
          <li class="flex justify-between gap-3 text-xs text-muted-foreground">
            <span>Inactive / defunct</span>
            <strong class="font-semibold tabular-nums text-foreground">{fmt(vis.exported.nodes_inactive)}</strong>
          </li>
        </ul>
      </section>

      <section class="border-t border-border/60 pt-3">
        <h4 class="mb-1.5 text-[0.6rem] font-semibold uppercase tracking-wider text-muted-foreground/80">
          Edge breakdown
        </h4>
        <ul class="flex list-none flex-col gap-0.5 p-0">
          {#each Object.entries(vis.edge_types ?? {}).sort((a, b) => (b[1] as number) - (a[1] as number)) as [type, count]}
            <li class="flex justify-between gap-3 text-xs text-muted-foreground">
              <span>{type}</span>
              <strong class="font-semibold tabular-nums text-foreground">{count}</strong>
            </li>
          {/each}
        </ul>
      </section>

      <section class="border-t border-border/60 pt-3">
        <h4 class="mb-1.5 text-[0.6rem] font-semibold uppercase tracking-wider text-muted-foreground/80">
          Sources ({fmt(vis.exported.total_sources)} total)
        </h4>
        <ul class="flex list-none flex-col gap-0.5 p-0">
          {#each vis.top_source_domains ?? [] as [domain, count]}
            <li class="flex justify-between gap-3 text-xs text-muted-foreground">
              <span class="truncate">{domain}</span>
              <strong class="font-semibold tabular-nums text-foreground">{count}</strong>
            </li>
          {/each}
        </ul>
      </section>
    {:else}
      <p class="m-0 text-xs text-muted-foreground/80">Re-export graph to populate coverage metadata.</p>
    {/if}
  </div>
</ScrollArea>
