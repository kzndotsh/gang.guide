<script lang="ts">
  import {
    Crosshair,
    ExternalLink,
    GitBranch,
    Handshake,
    Info,
    Layers,
    MousePointerClick,
    Network,
    Palette,
    Quote,
    ScanSearch,
    Swords,
    X,
  } from '@lucide/svelte';
  import type { Component } from 'svelte';
  import type { Graph, GraphNode } from '$lib/types';
  import {
    colorSwatch,
    confidencePct,
    orgTypeLabel,
    relTypeLabelDirectional,
    statusLabel,
    formatMembershipEstimate,
  } from '$lib/inspector/inspectorFormat';
  import { formatYearSpan, resolveDissolvedYearSpan, resolveNodeYearSpan } from '$lib/yearFormat';
  import { orgDisplayDescription, orgDisplayTitle } from '$lib/inspector/inspectorDisplay';
  import { dropConflictingSoftTies, groupConnections, mergeConnections } from '$lib/inspector/inspectorConnections';
  import { orgSourceLinks, groupedClaimSources, nonClaimSources, predicateLabel } from '$lib/orgSources';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
  import * as Tabs from '$lib/components/ui/tabs/index.js';
  import * as Accordion from '$lib/components/ui/accordion/index.js';
  import * as Empty from '$lib/components/ui/empty/index.js';
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
  const laneLabel = $derived(node?.data?.layout?.lane_label ?? null);
  const membershipText = $derived(formatMembershipEstimate(node?.data?.membership_estimate));
  const militaryService = $derived(node?.data?.military_service?.trim() || null);
  const typeLabel = $derived(
    orgType.replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
  );
  const metro = $derived(node?.data?.metro?.trim() || null);
  const showMetro = $derived(Boolean(metro && !(laneLabel && metro && laneLabel.toLowerCase().includes(metro.toLowerCase()))));

  const hasFacts = $derived(
    Boolean(
      typeLabel ||
        statusText ||
        foundedSpan ||
        dissolvedSpan ||
        showMetro ||
        laneLabel ||
        nationLabel ||
        membershipText ||
        militaryService,
    ),
  );

  const hasOverview = $derived(
    Boolean(
      displayDescription ||
        node?.data?.aliases?.length ||
        hasFacts,
    ),
  );

  const identityCount = $derived(
    (node?.data?.colors?.length ?? 0) +
      (node?.data?.symbols?.length ?? 0) +
      (node?.data?.original_text_names?.length ?? 0),
  );

  // Source links — org sources + edge citations merged and grouped
  const sourceLinks = $derived(orgSourceLinks(graph, node, []));
  const claimGroups = $derived(groupedClaimSources(sourceLinks));
  const refSources = $derived(nonClaimSources(sourceLinks));
  const totalSourceCount = $derived(sourceLinks.length);
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
          <span class="inline-flex min-w-0 max-w-full items-baseline gap-1">
            <span class="truncate">Network</span>
            <span class="text-[0.6rem] tabular-nums text-muted-foreground">({connectionCount})</span>
          </span>
        </Tabs.Trigger>
        <Tabs.Trigger value="identity" class="!flex-none min-w-0 gap-1 px-2 py-1.5 text-[0.68rem] data-[state=active]:text-foreground data-[state=active]:border-b data-[state=active]:border-foreground data-[state=active]:shadow-none data-[state=active]:ring-0 focus-visible:ring-0 focus-visible:outline-none ">
          <Palette class="size-3 shrink-0" />
          <span class="inline-flex min-w-0 max-w-full items-baseline gap-1">
            <span class="truncate">Identity</span>
            {#if identityCount}
              <span class="text-[0.6rem] tabular-nums text-muted-foreground">({identityCount})</span>
            {/if}
          </span>
        </Tabs.Trigger>
        <Tabs.Trigger value="sources" class="!flex-none min-w-0 gap-1 px-2 py-1.5 text-[0.68rem] data-[state=active]:text-foreground data-[state=active]:border-b data-[state=active]:border-foreground data-[state=active]:shadow-none data-[state=active]:ring-0 focus-visible:ring-0 focus-visible:outline-none ">
          <ExternalLink class="size-3 shrink-0" />
          <span class="inline-flex min-w-0 max-w-full items-baseline gap-1">
            <span class="truncate">Sources</span>
            {#if totalSourceCount}
              <span class="text-[0.6rem] tabular-nums text-muted-foreground">({totalSourceCount})</span>
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

            {#if hasFacts}
              <section>
                <h3 class="mb-1.5 text-[0.65rem] font-medium uppercase tracking-wider text-muted-foreground">Profile</h3>
                <dl class="flex flex-col gap-1">
                  {#if typeLabel}
                    <div class="flex items-baseline gap-3 rounded-md border border-border/50 bg-background/40 px-3 py-1.5">
                      <dt class="w-[5.5rem] shrink-0 text-[0.65rem] uppercase tracking-wide text-muted-foreground">Type</dt>
                      <dd class="min-w-0 text-sm">{typeLabel}</dd>
                    </div>
                  {/if}
                  {#if statusText}
                    <div class="flex items-baseline gap-3 rounded-md border border-border/50 bg-background/40 px-3 py-1.5">
                      <dt class="w-[5.5rem] shrink-0 text-[0.65rem] uppercase tracking-wide text-muted-foreground">Status</dt>
                      <dd class="min-w-0 text-sm">{statusText}</dd>
                    </div>
                  {/if}
                  {#if foundedSpan}
                    <div class="flex items-baseline gap-3 rounded-md border border-border/50 bg-background/40 px-3 py-1.5">
                      <dt class="w-[5.5rem] shrink-0 text-[0.65rem] uppercase tracking-wide text-muted-foreground">Founded</dt>
                      <dd class="min-w-0 text-sm tabular-nums">{formatYearSpan(foundedSpan)}</dd>
                    </div>
                  {/if}
                  {#if dissolvedSpan}
                    <div class="flex items-baseline gap-3 rounded-md border border-border/50 bg-background/40 px-3 py-1.5">
                      <dt class="w-[5.5rem] shrink-0 text-[0.65rem] uppercase tracking-wide text-muted-foreground">Disbanded</dt>
                      <dd class="min-w-0 text-sm tabular-nums">{formatYearSpan(dissolvedSpan)}</dd>
                    </div>
                  {/if}
                  {#if showMetro && metro}
                    <div class="flex items-baseline gap-3 rounded-md border border-border/50 bg-background/40 px-3 py-1.5">
                      <dt class="w-[5.5rem] shrink-0 text-[0.65rem] uppercase tracking-wide text-muted-foreground">Metro</dt>
                      <dd class="min-w-0 text-sm">{metro}</dd>
                    </div>
                  {/if}
                  {#if laneLabel}
                    <div class="flex items-baseline gap-3 rounded-md border border-border/50 bg-background/40 px-3 py-1.5">
                      <dt class="w-[5.5rem] shrink-0 text-[0.65rem] uppercase tracking-wide text-muted-foreground">Lane</dt>
                      <dd class="min-w-0 text-sm">{laneLabel}</dd>
                    </div>
                  {/if}
                  {#if nationId && nationLabel}
                    <div class="flex items-baseline gap-3 rounded-md border border-border/50 bg-background/40 px-3 py-1.5">
                      <dt class="w-[5.5rem] shrink-0 text-[0.65rem] uppercase tracking-wide text-muted-foreground">Nation</dt>
                      <dd class="min-w-0 text-sm">
                        <button type="button" class="text-left text-primary hover:underline" onclick={() => pickNode(nationId)}>
                          {nationLabel}
                        </button>
                      </dd>
                    </div>
                  {/if}
                  {#if membershipText}
                    <div class="flex items-baseline gap-3 rounded-md border border-border/50 bg-background/40 px-3 py-1.5">
                      <dt class="w-[5.5rem] shrink-0 text-[0.65rem] uppercase tracking-wide text-muted-foreground">Members</dt>
                      <dd class="min-w-0 text-sm tabular-nums">{membershipText}</dd>
                    </div>
                  {/if}
                  {#if militaryService}
                    <div class="flex items-baseline gap-3 rounded-md border border-border/50 bg-background/40 px-3 py-1.5">
                      <dt class="w-[5.5rem] shrink-0 text-[0.65rem] uppercase tracking-wide text-muted-foreground">Military</dt>
                      <dd class="min-w-0 text-sm">{militaryService}</dd>
                    </div>
                  {/if}
                </dl>
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
                        {@const edgeEvidence = (node?.data as any)?.edgeEvidence as Array<{ target?: string; source?: string; type?: string; citations?: Array<{ url?: string; title?: string; evidence?: string }> }> | undefined}
                        {@const edgeDetail = edgeEvidence?.find((e) => (e.target === conn.peerId || e.source === conn.peerId) && e.type === conn.type)}
                        {@const citations = edgeDetail?.citations ?? conn.citations ?? []}
                        <li class="flex flex-col gap-1">
                          <div class="flex items-center gap-1">
                            <button
                              type="button"
                              class={cn(
                                'flex flex-1 items-center justify-between gap-2 rounded-md border border-border/50 border-l-2 bg-background/40 px-3 py-2 text-left transition-colors hover:bg-accent/30',
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
                                      {relTypeLabelDirectional(conn.type, conn.isOutgoing)}
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
                          {#if citations.length > 0}
                            <button
                              type="button"
                              class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border/50 bg-background/40 text-muted-foreground transition-colors hover:bg-accent/30 hover:text-foreground"
                              aria-label="Show source evidence"
                              onclick={(e) => { e.stopPropagation(); const el = (e.currentTarget as HTMLElement).closest('li')?.querySelector('[data-evidence]'); if (el) el.classList.toggle('hidden'); }}
                            >
                              <Quote class="size-3" />
                            </button>
                          {/if}
                          </div>
                          {#if citations.length > 0}
                            <div data-evidence class="hidden ml-1 flex flex-col gap-1.5">
                              {#each citations as cit, ci (ci)}
                                {#if cit.evidence || cit.url}
                                  <div class="rounded-md border border-border/30 bg-background/60 px-3 py-2">
                                    <p class="text-[0.68rem] leading-relaxed text-muted-foreground">
                                      {#if cit.evidence}
                                        <span class="italic">"{cit.evidence}"</span>
                                      {/if}
                                      {#if cit.url}
                                        {#if cit.evidence}<span class="not-italic ml-1 mr-1">—</span>{/if}<a href={cit.url} target="_blank" rel="noopener" class="not-italic text-primary/70 hover:text-primary hover:underline">{cit.title || cit.url.replace(/^https?:\/\/(www\.)?/, '').split('/')[0]}</a>
                                      {/if}
                                    </p>
                                  </div>
                                {/if}
                              {/each}
                            </div>
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
            {#if totalSourceCount}
              <!-- Claim sources grouped by predicate (e.g. "Founded year", "Description") -->
              {#if claimGroups.length}
                <Accordion.Root type="multiple" value={claimGroups.map(g => g.predicate)} class="gap-2">
                  {#each claimGroups as group (group.predicate)}
                    <Accordion.Item value={group.predicate} class="rounded-lg border border-border/60 px-1">
                      <Accordion.Trigger class="items-center px-3 py-2 text-xs hover:no-underline">
                        <div class="flex items-center gap-1.5">
                          <span class="font-medium">{predicateLabel(group.predicate)}</span>
                          <span class="text-[0.6rem] tabular-nums text-muted-foreground">({group.items.length})</span>
                        </div>
                      </Accordion.Trigger>
                      <Accordion.Content class="px-2 pb-2">
                        <div class="flex flex-col gap-1.5">
                          {#each group.items as src}
                            <div class="rounded-md border border-border/40 bg-background/40 px-3 py-2">
                              {#if src.snippets[0]?.quote}
                                <p class="mb-1.5 text-[0.68rem] italic leading-relaxed text-muted-foreground">
                                  "{src.snippets[0].quote.length > 160 ? src.snippets[0].quote.slice(0, 157) + '…' : src.snippets[0].quote}"
                                </p>
                              {/if}
                              {#if src.url}
                                <a href={src.url} target="_blank" rel="noopener noreferrer"
                                  class="inline-flex items-center gap-1 text-[0.65rem] text-primary/80 hover:text-primary hover:underline">
                                  <ExternalLink class="size-2.5 shrink-0" />
                                  {src.label}
                                </a>
                              {:else}
                                <span class="text-[0.65rem] text-muted-foreground">{src.label}</span>
                              {/if}
                            </div>
                          {/each}
                        </div>
                      </Accordion.Content>
                    </Accordion.Item>
                  {/each}
                </Accordion.Root>
              {/if}

              <!-- Reference sources (org-level sources[]) -->
              {#if refSources.length}
                {#if claimGroups.length}
                  <div class="pt-1 text-[0.62rem] font-medium uppercase tracking-wider text-muted-foreground">References</div>
                {/if}
                <div class="flex flex-col gap-1">
                  {#each refSources as src}
                    {#if src.url}
                      <a href={src.url} target="_blank" rel="noopener noreferrer"
                        class="flex items-start gap-2 rounded-md border border-border/60 px-3 py-2 text-xs transition-colors hover:bg-accent/40">
                        <ExternalLink class="mt-0.5 size-3 shrink-0 text-muted-foreground" />
                        <span class="min-w-0">
                          <span class="block font-medium text-primary">{src.label}</span>
                          <span class="block truncate text-[0.6rem] text-muted-foreground">{src.url}</span>
                        </span>
                      </a>
                    {/if}
                  {/each}
                </div>
              {/if}
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
        <p class="max-w-48 text-[0.7rem] text-muted-foreground md:hidden">
          Tap a node on the map or use search
        </p>
        <p class="hidden max-w-48 text-[0.7rem] text-muted-foreground md:block">
          Click a node on the map or press <Kbd>⌘K</Kbd> to search
        </p>
      </div>
      <div class="hidden flex-wrap items-center justify-center gap-x-4 gap-y-2 text-[0.65rem] text-muted-foreground md:flex">
        <span class="inline-flex items-center gap-1"><Kbd>⌘K</Kbd> search</span>
        <span class="inline-flex items-center gap-1"><Kbd>Esc</Kbd> deselect</span>
        <span class="inline-flex items-center gap-1"><Kbd>F</Kbd> fit</span>
        <span class="inline-flex items-center gap-1"><Kbd>+</Kbd><Kbd>−</Kbd> zoom</span>
      </div>
    </div>
  {/if}
</div>
