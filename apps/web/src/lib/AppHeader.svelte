<script lang="ts">
  import type { Graph } from '$lib/types';
  import CoverageDialog from '$lib/overlays/CoverageDialog.svelte';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import * as Dialog from '$lib/components/ui/dialog/index.js';


  interface Props {
    graph: Graph;
    selectedId: string | null;
    nodeCount: number;
    edgeCount: number;
  }

  let {
    graph,
    selectedId,
    nodeCount,
    edgeCount,
  }: Props = $props();
</script>

<header
  class="z-10 flex h-11 min-w-0 items-center gap-2 border-b border-border/80 bg-card px-2 sm:gap-3 sm:px-3"
  style="grid-area: toolbar"
>
  <!-- Brand -->
  <div class="flex shrink-0 items-center gap-2 pr-1 sm:pr-2">
    <div
      class="relative flex size-7 shrink-0 items-center justify-center rounded-md bg-gradient-to-br from-green-500/20 to-primary/20 ring-1 ring-primary/25"
      aria-hidden="true"
    >
      <svg class="size-4 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>
      </svg>
    </div>
    <div class="min-w-0 leading-none">
      <h1 class="flex items-center gap-1.5 truncate text-sm font-semibold tracking-tight">gang.guide <span class="rounded bg-muted-foreground/10 px-1 py-0.5 text-[0.55rem] font-normal text-muted-foreground">v0.2</span></h1>
      <p class="hidden truncate text-[0.62rem] text-muted-foreground sm:block">
        Mapping criminal organizations across the US
      </p>
    </div>
  </div>

  <!-- Graph stats -->
  <div
    class="ml-auto hidden shrink-0 items-center gap-1 lg:flex"
    aria-label="Graph statistics"
  >
    <Badge variant="secondary" class="h-6 gap-1 px-2 text-[0.65rem] font-normal tabular-nums">
      {nodeCount}
      <span class="text-muted-foreground">nodes</span>
    </Badge>
    <Badge variant="secondary" class="h-6 gap-1 px-2 text-[0.65rem] font-normal tabular-nums">
      {edgeCount}
      <span class="text-muted-foreground">edges</span>
    </Badge>

  </div>

  <div class="flex items-center gap-1.5">
    <CoverageDialog {graph} edgeMode="all" {selectedId} />
    <Dialog.Root>
    <Dialog.Trigger>
      {#snippet child({ props })}
        <button {...props} class="inline-flex size-6 items-center justify-center rounded-md border border-border bg-card text-muted-foreground hover:bg-accent hover:text-foreground" title="Build history">
              <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 8v4l3 3"/><circle cx="12" cy="12" r="10"/></svg>
            </button>
      {/snippet}
    </Dialog.Trigger>
    <Dialog.Content class="sm:max-w-lg">
      <Dialog.Header>
        <Dialog.Title>Build history</Dialog.Title>
      </Dialog.Header>
      {#await fetch('/changelog.json').then(r => r.json())}
        <p class="text-xs text-muted-foreground">Loading...</p>
      {:then entries}
        {@const last = entries[entries.length - 1]}
        <div class="max-h-72 overflow-y-auto font-mono text-[0.65rem]">
          {#each [...entries].reverse() as entry, i}
            <div class="flex items-center gap-2 border-b border-border/30 py-1.5">
              <span class="shrink-0 mr-2 text-muted-foreground">{new Date(entry.built_at).toLocaleString(undefined, {month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"})}</span>
              {#if entry.delta_nodes || entry.delta_edges || entry.delta_sources}
                <span class="flex gap-1.5 tabular-nums">
                  {#if entry.delta_nodes}<span class="{entry.delta_nodes > 0 ? 'text-green-500' : 'text-red-400'}">{entry.delta_nodes > 0 ? '+' : ''}{entry.delta_nodes}n</span>{/if}
                  {#if entry.delta_edges}<span class="{entry.delta_edges > 0 ? 'text-green-500' : 'text-red-400'}">{entry.delta_edges > 0 ? '+' : ''}{entry.delta_edges}e</span>{/if}
                </span>
              {/if}
              <span class="ml-auto tabular-nums text-foreground">{entry.nodes} nodes · {entry.edges} edges · {entry.sources} sources</span>
            </div>
          {/each}
        </div>
      {/await}
    </Dialog.Content>
  </Dialog.Root>
  </div>
</header>
