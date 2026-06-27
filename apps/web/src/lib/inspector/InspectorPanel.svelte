<script lang="ts">
  import {
    Clock,
    Crosshair,
    Database,
    ExternalLink,
    GitBranch,
    Handshake,
    Info,
    Layers,
    MapPin,
    MousePointerClick,
    Network,
    Palette,
    Quote,
    ScanSearch,
    Swords,
    Tag,
    Users,
    X,
  } from '@lucide/svelte';
  import type { Component } from 'svelte';
  import type { Graph, GraphNode } from '$lib/types';
  import {
    colorSwatch,
    confidencePct,
    orgTypeLabel,
    relTypeLabel,
    reviewLabel,
    statusLabel,
  } from '$lib/inspector/inspectorFormat';
  import { formatYearSpan, resolveDissolvedYearSpan, resolveNodeYearSpan } from '$lib/yearFormat';
  import { orgDisplayDescription, orgDisplayTitle } from '$lib/inspector/inspectorDisplay';
  import { dropConflictingSoftTies, groupConnections, mergeConnections } from '$lib/inspector/inspectorConnections';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
  import { Separator } from '$lib/components/ui/separator/index.js';
  import * as Card from '$lib/components/ui/card/index.js';
  import * as Tabs from '$lib/components/ui/tabs/index.js';
  import * as Accordion from '$lib/components/ui/accordion/index.js';
  import * as Empty from '$lib/components/ui/empty/index.js';
  import * as Item from '$lib/components/ui/item/index.js';
  import { Kbd } from '$lib/components/ui/kbd/index.js';
  import { cn } from '$lib/utils.js';

  type InspectorTab = 'overview' | 'network' | 'identity' | 'sources';

  const GROUP_ICONS: Record<string, Component> = {
    affiliation: Network,
    alliance: Handshake,
    rivalry: Swords,
    structure: GitBranch,
    other: Layers,
  };

  const GROUP_ACCENT: Record<string, string> = {
    affiliation: 'border-l-blue-400',
    alliance: 'border-l-green-400',
    rivalry: 'border-l-red-400',
    structure: 'border-l-purple-400',
    other: 'border-l-border',
  };

  const GROUP_TEXT: Record<string, string> = {
    affiliation: 'text-blue-300',
    alliance: 'text-green-400',
    rivalry: 'text-red-300',
    structure: 'text-purple-300',
    other: 'text-muted-foreground',
  };

  interface Props {
    graph: Graph;
    node: GraphNode | null;
    onclose: () => void;
    onselect?: (id: string) => void;
  }

  let { graph, node, onclose, onselect }: Props = $props();

  let activeTab = $state<InspectorTab>('overview');
  let networkOpen = $state<string[]>([]);

  const nodeById = $derived(new Map(graph.nodes.map((n) => [n.id, n])));

  function labelFor(id: string): string {
    const n = nodeById.get(id);
    return n ? orgDisplayTitle(n) : id;
  }

  function pickNode(id: string) {
    onselect?.(id);
  }

  const foundedSpan = $derived(node ? resolveNodeYearSpan(node.data) : null);
  const dissolvedSpan = $derived(node ? resolveDissolvedYearSpan(node.data) : null);
  const nationId = $derived(node?.data?.nation_affiliation ?? null);
  const nationLabel = $derived(nationId ? labelFor(nationId) : null);

  const connectionGroups = $derived.by(() => {
    if (!node) return [];
    const edges = graph.edges.filter((e) => e.source === node.id || e.target === node.id);
    const nation = node.data?.nation_affiliation ?? null;
    const merged = dropConflictingSoftTies(mergeConnections(node.id, edges)).filter(
      (c) => !(c.type === 'nation_affiliation' && c.peerId === nation),
    );
    return groupConnections(merged, labelFor);
  });

  const connectionCount = $derived(
    connectionGroups.reduce((sum, g) => sum + g.items.length, 0),
  );

  $effect(() => {
    if (node?.id) activeTab = 'overview';
  });

  $effect(() => {
    networkOpen = connectionGroups.map((g) => g.id);
  });

  const orgType = $derived(orgTypeLabel(node?.data?.type));
  const statusText = $derived(statusLabel(node?.data?.status));
  const displayTitle = $derived(orgDisplayTitle(node));
  const displayDescription = $derived(orgDisplayDescription(node));

  const lifeSummary = $derived.by(() => {
    const parts: string[] = [];
    if (foundedSpan) parts.push(`Founded ${formatYearSpan(foundedSpan)}`);
    if (dissolvedSpan) parts.push(`Dissolved ${formatYearSpan(dissolvedSpan)}`);
    return parts.join(' · ');
  });

  const identityCount = $derived(
    (node?.data?.colors?.length ?? 0) +
      (node?.data?.symbols?.length ?? 0) +
      (node?.data?.original_text_names?.length ?? 0),
  );

  const provenance = $derived.by(() => {
    if (!node) return [] as Array<{ predicate: string; claimIds: string[] }>;
    const prov = graph.provenance?.[node.id];
    if (!prov) return [];
    return Object.entries(prov)
      .map(([predicate, claimIds]) => ({ predicate, claimIds }))
      .sort((a, b) => b.claimIds.length - a.claimIds.length);
  });

  const hasOverview = $derived(
    Boolean(
      displayDescription ||
        node?.data?.aliases?.length ||
        lifeSummary ||
        node?.data?.metro ||
        nationId ||
        node?.data?.ethnicity ||
        node?.data?.era,
    ),
  );
</script>

<div class="flex h-full min-h-0 flex-1 flex-col overflow-hidden bg-card" aria-label="Entity inspector">
  <!-- Chrome -->
  <div class="flex h-11 shrink-0 items-center justify-between border-b border-border/80 px-3">
    <div class="flex items-center gap-2">
      <div
        class="flex size-7 items-center justify-center rounded-md bg-secondary text-muted-foreground ring-1 ring-border/60"
        aria-hidden="true"
      >
        <ScanSearch class="size-3.5" />
      </div>
      <span class="text-sm font-semibold tracking-tight">Inspector</span>
    </div>
    {#if node}
      <Button variant="ghost" size="icon-sm" onclick={onclose} aria-label="Close inspector">
        <X class="size-4" />
      </Button>
    {/if}
  </div>

  {#if node}
    <!-- Profile hero -->
    <div class="shrink-0 border-b border-border/60 px-3 py-3">
      <h2 class="text-base font-semibold leading-snug tracking-tight">{displayTitle}</h2>
      <hr class="my-2 border-border/40"/>
      <p class="text-xs text-muted-foreground">
        {orgType.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}{node.data?.status === 'inactive' ? ' · inactive' : ''}{node.data?.metro ? ` · ${node.data.metro}` : ''}{node.data?.founded_year ? ` · ${node.data.founded_year}` : ''}
      </p>
    </div>

    <!-- Tabbed detail -->
    <Tabs.Root bind:value={activeTab} class="flex min-h-0 flex-1 flex-col">
      <Tabs.List
        variant="line"
        class="flex min-w-0 shrink-0 gap-0 px-1"
      >
        <Tabs.Trigger value="overview" class="!flex-none min-w-0 gap-1 px-2 py-1.5 text-[0.68rem] data-[state=active]:text-foreground data-[state=active]:border-b data-[state=active]:border-foreground data-[state=active]:shadow-none data-[state=active]:ring-0 focus-visible:ring-0 focus-visible:outline-none ">
          <Info class="size-3 shrink-0" />
          <span class="truncate">Overview</span>
        </Tabs.Trigger>
        <Tabs.Trigger value="network" class="!flex-none min-w-0 gap-1 px-2 py-1.5 text-[0.68rem] data-[state=active]:text-foreground data-[state=active]:border-b data-[state=active]:border-foreground data-[state=active]:shadow-none data-[state=active]:ring-0 focus-visible:ring-0 focus-visible:outline-none ">
          <Crosshair class="size-3 shrink-0" />
          <span class="inline-flex min-w-0 max-w-full items-baseline">
            <span class="truncate">Network</span>
          </span>
        </Tabs.Trigger>
        <Tabs.Trigger value="identity" class="!flex-none min-w-0 gap-1 px-2 py-1.5 text-[0.68rem] data-[state=active]:text-foreground data-[state=active]:border-b data-[state=active]:border-foreground data-[state=active]:shadow-none data-[state=active]:ring-0 focus-visible:ring-0 focus-visible:outline-none ">
          <Palette class="size-3 shrink-0" />
          <span class="inline-flex min-w-0 max-w-full items-baseline">
            <span class="truncate">Identity</span>
            {#if identityCount}
              <span class="mx-1 shrink-0 text-[0.55rem] text-muted-foreground/50">·</span>
              <span class="shrink-0 tabular-nums text-[0.6rem] text-muted-foreground">{identityCount}</span>
            {/if}
          </span>
        </Tabs.Trigger>
        <Tabs.Trigger value="sources" class="!flex-none min-w-0 gap-1 px-2 py-1.5 text-[0.68rem] data-[state=active]:text-foreground data-[state=active]:border-b data-[state=active]:border-foreground data-[state=active]:shadow-none data-[state=active]:ring-0 focus-visible:ring-0 focus-visible:outline-none ">
          <ExternalLink class="size-3 shrink-0" />
          <span class="inline-flex min-w-0 max-w-full items-baseline">
            <span class="truncate">Sources</span>
            {#if node?.data?.sources?.length}
              <span class="mx-1 shrink-0 text-[0.55rem] text-muted-foreground/50">·</span>
              <span class="shrink-0 tabular-nums text-[0.6rem] text-muted-foreground">{node.data.sources.length}</span>
            {/if}
          </span>
        </Tabs.Trigger>
      </Tabs.List>

      <Tabs.Content value="overview" class="mt-0 min-h-0 flex-1 overflow-hidden p-0">
        <ScrollArea class="h-full">
          <div class="space-y-4 p-3">
            {#if displayDescription}
              <section>
                <h3 class="mb-1.5 text-[0.65rem] font-medium uppercase tracking-wider text-muted-foreground">About</h3>
                <p class="whitespace-pre-wrap text-sm leading-relaxed text-foreground/90">
                  {displayDescription}
                </p>
              </section>
            {/if}

            {#if node.data?.aliases?.length}
              <section>
                <h3 class="mb-1.5 text-[0.65rem] font-medium uppercase tracking-wider text-muted-foreground">Also known as</h3>
                <div class="flex flex-col gap-1">
                  {#each node.data.aliases as alias}
                    <div class="rounded-md border border-border/50 bg-background/40 px-3 py-1.5 text-sm">{alias}</div>
                  {/each}
                </div>
              </section>
            {/if}

            {#if !hasOverview}
              <p class="py-6 text-center text-xs text-muted-foreground">No description or aliases on file.</p>
            {/if}
          </div>
        </ScrollArea>
      </Tabs.Content>

      <Tabs.Content value="network" class="mt-0 min-h-0 flex-1 overflow-hidden p-0">
        <ScrollArea class="h-full p-3">
          {#if connectionGroups.length}
            <Accordion.Root type="multiple" bind:value={networkOpen} class="gap-2">
              {#each connectionGroups as group (group.id)}
                {@const GroupIcon = GROUP_ICONS[group.id] ?? Layers}
                <Accordion.Item value={group.id} class="overflow-hidden rounded-lg border border-border/60">
                  <Accordion.Trigger
                    class="items-center gap-2 px-3 py-2.5 hover:no-underline [&_[data-slot=accordion-trigger-icon]]:text-muted-foreground"
                  >
                    <div class="flex min-w-0 flex-1 items-center gap-2">
                      <GroupIcon class={cn('size-3.5 shrink-0', GROUP_TEXT[group.id])} />
                      <span
                        class={cn(
                          'truncate text-xs font-medium uppercase tracking-wide',
                          GROUP_TEXT[group.id],
                        )}
                      >
                        {group.label}
                      </span>
                      <Badge
                        variant="secondary"
                        class="h-5 shrink-0 px-1.5 tabular-nums text-[0.62rem] font-normal"
                      >
                        {group.items.length}
                      </Badge>
                    </div>
                  </Accordion.Trigger>
                  <Accordion.Content class="px-2 pb-2 pt-0">
                    <ul class="flex list-none flex-col gap-1 p-0">
                      {#each group.items as conn (conn.peerId + conn.type)}
                        {@const evidence = (node?.data as any)?.edgeEvidence?.find((e: any) => e.target === conn.peerId && e.type === conn.type)}
                        <li>
                          <button
                            type="button"
                            class={cn(
                              'flex w-full items-center justify-between gap-2 rounded-md border border-border/50 border-l-2 bg-background/40 px-3 py-2 text-left transition-colors hover:bg-accent/30',
                              GROUP_ACCENT[group.id],
                            )}
                            onclick={() => pickNode(conn.peerId)}
                          >
                            <span class="min-w-0 truncate text-sm font-normal leading-snug">
                              {labelFor(conn.peerId)}
                            </span>
                            {#if (group.id === 'structure' || group.id === 'other') || conn.confidenceScore != null}
                              <span class="inline-flex shrink-0 items-center gap-1.5">
                                {#if group.id === 'structure' || group.id === 'other'}
                                  <Badge variant="outline" class="text-[0.58rem] font-normal uppercase">
                                    {relTypeLabel(conn.type)}
                                  </Badge>
                                {/if}
                                {#if conn.confidenceScore != null}
                                  <span class="text-[0.62rem] tabular-nums text-muted-foreground">
                                    {confidencePct(conn.confidenceScore)}
                                  </span>
                                {/if}
                              </span>
                            {/if}
                          </button>
                          {#if evidence?.evidence}
                            <p class="mt-1 px-3 text-[0.68rem] italic leading-tight text-muted-foreground/80">
                              "{evidence.evidence}"
                              {#if evidence.source_url}
                                <a href={evidence.source_url} target="_blank" rel="noopener" class="ml-1 not-italic text-primary/60 hover:text-primary">↗</a>
                              {/if}
                            </p>
                          {/if}
                        </li>
                      {/each}
                    </ul>
                  </Accordion.Content>
                </Accordion.Item>
              {/each}
            </Accordion.Root>
          {:else}
            <Empty.Root class="border-none py-8">
              <Empty.Header>
                <Empty.Media variant="icon">
                  <Crosshair />
                </Empty.Media>
                <Empty.Title class="text-sm">No connections</Empty.Title>
                <Empty.Description class="text-xs">
                  This org has no visible links under the current filter.
                </Empty.Description>
              </Empty.Header>
            </Empty.Root>
          {/if}
        </ScrollArea>
      </Tabs.Content>

      <Tabs.Content value="identity" class="mt-0 min-h-0 flex-1 overflow-hidden p-0">
        <ScrollArea class="h-full">
          <div class="space-y-4 p-3">
            {#if node.data?.colors?.length}
              <section>
                <h3 class="mb-1.5 text-[0.65rem] font-medium uppercase tracking-wider text-muted-foreground">Colors</h3>
                <div class="flex flex-col gap-1">
                  {#each node.data.colors as color}
                    <div class="flex items-center gap-2 rounded-md border border-border/50 bg-background/40 px-3 py-1.5">
                      <span class="size-3 rounded-full border border-white/20" style:background={colorSwatch(color)}></span>
                      <span class="text-sm capitalize">{color}</span>
                    </div>
                  {/each}
                </div>
              </section>
            {/if}

            {#if node.data?.symbols?.length}
              <section>
                <h3 class="mb-1.5 text-[0.65rem] font-medium uppercase tracking-wider text-muted-foreground">Symbols</h3>
                <div class="flex flex-col gap-1">
                  {#each node.data.symbols as symbol}
                    <div class="rounded-md border border-border/50 bg-background/40 px-3 py-1.5 text-sm">{symbol}</div>
                  {/each}
                </div>
              </section>
            {/if}

            {#if node.data?.original_text_names?.length}
              <section>
                <h3 class="mb-1.5 text-[0.65rem] font-medium uppercase tracking-wider text-muted-foreground">Source names</h3>
                <div class="flex flex-col gap-1">
                  {#each node.data.original_text_names as name}
                    <div class="rounded-md border border-border/50 bg-background/40 px-3 py-1.5 text-sm">{name}</div>
                  {/each}
                </div>
              </section>
            {/if}

            {#if !identityCount}
              <p class="py-6 text-center text-xs text-muted-foreground">No identity markers on file.</p>
            {/if}
          </div>
        </ScrollArea>
      </Tabs.Content>

      

      <Tabs.Content value="sources" class="mt-0 min-h-0 flex-1 overflow-hidden p-0">
        <ScrollArea class="h-full">
          <div class="space-y-2 p-3">
            {#if node?.data?.sources?.length}
              {#each node.data.sources as src}
                {#if typeof src === 'object' && src.url}
                  <a
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="flex items-start gap-2 rounded-md border border-border/60 px-3 py-2 text-xs transition-colors hover:bg-accent/40"
                  >
                    <ExternalLink class="mt-0.5 size-3 shrink-0 text-muted-foreground" />
                    <span class="min-w-0">
                      <span class="block font-medium text-primary">{src.title || 'Source'}</span>
                      <span class="block truncate text-[0.6rem] text-muted-foreground">{src.url}</span>
                    </span>
                  </a>
                {/if}
              {/each}
            {:else}
              <p class="py-4 text-center text-xs text-muted-foreground">No sources linked</p>
            {/if}
          </div>
        </ScrollArea>
      </Tabs.Content>
    </Tabs.Root>
  {:else}
    <div class="flex min-h-0 flex-1 flex-col items-center justify-center gap-6 px-6">
      <div class="flex flex-col items-center gap-2 text-center">
        <MousePointerClick class="size-8 text-muted-foreground/40" />
        <h3 class="text-sm font-medium text-foreground">No selection</h3>
        <p class="max-w-48 text-[0.7rem] text-muted-foreground">
          Click a node on the map or press <Kbd>⌘K</Kbd> to search
        </p>
      </div>
      <div class="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-[0.65rem] text-muted-foreground">
        <span class="inline-flex items-center gap-1"><Kbd>⌘K</Kbd> search</span>
        <span class="inline-flex items-center gap-1"><Kbd>Esc</Kbd> deselect</span>
        <span class="inline-flex items-center gap-1"><Kbd>F</Kbd> fit</span>
        <span class="inline-flex items-center gap-1"><Kbd>+</Kbd><Kbd>−</Kbd> zoom</span>
      </div>
    </div>
  {/if}
</div>
