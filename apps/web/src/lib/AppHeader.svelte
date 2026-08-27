<script lang="ts">
  import type { Graph } from '$lib/types';
  import CoverageDialog from '$lib/overlays/CoverageDialog.svelte';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import * as Dialog from '$lib/components/ui/dialog/index.js';
  import { restoreBodyInteraction } from '$lib/restoreBodyInteraction';


  interface Props {
    graph: Graph;
    selectedId: string | null;
    nodeCount: number;
    edgeCount: number;
    onhome?: () => void;
  }

  let {
    graph,
    selectedId,
    nodeCount,
    edgeCount,
    onhome,
  }: Props = $props();
</script>

<header
  class="z-10 flex h-11 min-w-0 items-center gap-2 border-b border-border/80 bg-card px-2 sm:gap-3 sm:px-3"
  style="grid-area: toolbar"
>
  <!-- Brand -->
  <div class="flex min-w-0 shrink-0 items-center gap-2 pr-1 sm:pr-2">
    <button
      type="button"
      class="flex min-w-0 select-none items-center gap-2 rounded-md text-left active:scale-[0.97]"
      onclick={() => onhome?.()}
      aria-label="Home, reset map"
      title="Home"
    >
      <div
        class="relative flex size-7 shrink-0 items-center justify-center rounded-md bg-gradient-to-br from-green-500/20 to-primary/20 ring-1 ring-primary/25"
        aria-hidden="true"
      >
        <svg class="size-4 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>
        </svg>
      </div>
      <div class="min-w-0 leading-none">
        <h1 class="truncate text-sm font-semibold tracking-tight">gang.guide</h1>
        <p class="hidden truncate text-[0.62rem] text-muted-foreground sm:block">
          Mapping criminal organizations across the US
        </p>
      </div>
    </button>
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

  <div class="ml-auto flex items-center gap-1.5 lg:ml-0">
    <CoverageDialog {graph} />
    <Dialog.Root onOpenChange={(open) => { if (!open) restoreBodyInteraction(); }}>
    <Dialog.Trigger>
      {#snippet child({ props })}
        <button {...props} class="inline-flex size-11 select-none items-center justify-center rounded-md text-muted-foreground active:scale-[0.97] fine-hover:bg-muted fine-hover:text-foreground md:size-6" title="Build history" aria-label="Build history">
              <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 8v4l3 3"/><circle cx="12" cy="12" r="10"/></svg>
            </button>
      {/snippet}
    </Dialog.Trigger>
    <Dialog.Content class="sm:max-w-md">
      <Dialog.Header>
        <Dialog.Title>Build history</Dialog.Title>
      </Dialog.Header>
      {#await fetch('/changelog.json').then(r => r.json())}
        <p class="text-xs text-muted-foreground">Loading...</p>
      {:then entries}
        {@const last = entries[entries.length - 1]}
        <div class="max-h-80 overflow-y-auto pr-2 font-mono text-[0.65rem]">
          {#each [...entries].reverse() as entry, i}
            <div class="border-b border-border/30 py-2">
              <div class="text-muted-foreground">{new Date(entry.built_at).toLocaleString(undefined, {month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"})}</div>
              <div class="mt-0.5 flex gap-3 tabular-nums">
                <span class="text-foreground">{entry.nodes} nodes{#if entry.delta_nodes} <span class="{entry.delta_nodes > 0 ? 'text-green-500' : 'text-red-400'}">({entry.delta_nodes > 0 ? '+' : ''}{entry.delta_nodes})</span>{/if}</span>
                <span class="text-foreground">{entry.edges} edges{#if entry.delta_edges} <span class="{entry.delta_edges > 0 ? 'text-green-500' : 'text-red-400'}">({entry.delta_edges > 0 ? '+' : ''}{entry.delta_edges})</span>{/if}</span>
                <span class="text-foreground">{entry.sources} src{#if entry.delta_sources} <span class="{entry.delta_sources > 0 ? 'text-green-500' : 'text-red-400'}">({entry.delta_sources > 0 ? '+' : ''}{entry.delta_sources})</span>{/if}</span>
              </div>
            </div>
          {/each}
        </div>
      {/await}
    </Dialog.Content>
  </Dialog.Root>
    <a
      href="https://github.com/kzndotsh/gang.guide"
      target="_blank"
      rel="noopener"
      class="inline-flex size-11 select-none items-center justify-center rounded-md text-muted-foreground active:scale-[0.97] fine-hover:bg-muted fine-hover:text-foreground md:size-6"
      title="GitHub"
      aria-label="GitHub repository"
    >
      <svg class="size-3.5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/>
      </svg>
    </a>
  </div>
</header>
