<script lang="ts">
  import {
    BookOpen,
    ChevronDown,
    ExternalLink,
    Library,
    Newspaper,
    Pin,
    PinOff,
  } from '@lucide/svelte';
  import type { Graph, GraphNode } from '$lib/types';
  import SourceContextCard from './SourceContextCard.svelte';
  import {
    orgEvents,
    orgSourceLinks,
    groupedClaimSources,
    nonClaimSources,
    eventArticleSources,
    predicateLabel,
  } from '$lib/orgSources';
  import { formatEventYear } from '$lib/yearFormat';
  import { truncate } from '$lib/inspector/inspectorFormat';
  import { orgDisplayTitle } from '$lib/inspector/inspectorDisplay';
  import { Button } from '$lib/components/ui/button/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
  import { Separator } from '$lib/components/ui/separator/index.js';
  import * as Tabs from '$lib/components/ui/tabs/index.js';
  import * as Accordion from '$lib/components/ui/accordion/index.js';
  import * as Empty from '$lib/components/ui/empty/index.js';
  import * as Item from '$lib/components/ui/item/index.js';
  import { cn } from '$lib/utils.js';

  export type SourcesPanelTab = 'events' | 'sources';

  interface Props {
    graph: Graph;
    node: GraphNode | null;
    activeTab?: SourcesPanelTab;
    expanded: boolean;
    pinned: boolean;
    onPinnedChange: (value: boolean) => void;
    onCollapse: () => void;
    onExpand: () => void;
  }

  let {
    graph,
    node,
    activeTab = $bindable('events'),
    expanded,
    pinned,
    onPinnedChange,
    onCollapse,
    onExpand,
  }: Props = $props();

  let sourceAccordionOpen = $state<string[]>([]);

  const events = $derived(orgEvents(graph, node?.id ?? null));
  const sources = $derived(orgSourceLinks(graph, node, events));
  const claimGroups = $derived(groupedClaimSources(sources));
  const otherSources = $derived(nonClaimSources(sources));
  const fieldSourceCount = $derived(
    claimGroups.reduce((total, group) => total + group.items.length, 0) + otherSources.length,
  );

  function primaryArticleUrl(
    ev: (typeof events)[number],
    articleSources: ReturnType<typeof eventArticleSources>,
  ): string | undefined {
    return (
      articleSources.find((source) => source.url)?.url ??
      ev.data?.evidence?.find((item) => item.source_url)?.source_url ??
      undefined
    );
  }

  function primaryArticleLabel(
    ev: (typeof events)[number],
    articleSources: ReturnType<typeof eventArticleSources>,
  ): string {
    return (
      articleSources.find((source) => source.url)?.label ??
      ev.data?.evidence?.find((item) => item.source_url)?.source_title?.trim() ??
      'Source'
    );
  }

  const sourceSectionIds = $derived([
    ...claimGroups.map((g) => g.predicate),
    ...(otherSources.length ? ['references'] : []),
  ]);

  $effect(() => {
    sourceAccordionOpen = sourceSectionIds;
  });

  let expandClickTimer: ReturnType<typeof setTimeout> | undefined;

  function toggleDrawer() {
    if (expanded) onCollapse();
    else onExpand();
  }

  function onDrawerChromeDblClick(e: MouseEvent) {
    if ((e.target as HTMLElement).closest('button, a')) return;
    clearTimeout(expandClickTimer);
    toggleDrawer();
  }

  function onCollapsedStripClick() {
    clearTimeout(expandClickTimer);
    expandClickTimer = setTimeout(() => {
      onExpand();
      expandClickTimer = undefined;
    }, 250);
  }

  function onCollapsedStripDblClick(e: MouseEvent) {
    e.preventDefault();
    clearTimeout(expandClickTimer);
    toggleDrawer();
  }
</script>

<section class="flex h-full min-h-0 flex-col" aria-label="Research panel">
  <!-- Panel chrome -->
  <div
    class="flex shrink-0 cursor-pointer select-none items-center gap-2 border-b border-border/70 bg-card px-3 py-2 sm:gap-3 sm:px-4"
    title="Double-click to expand or collapse"
    ondblclick={onDrawerChromeDblClick}
  >
    <div class="flex min-w-0 flex-1 items-center gap-2.5">
      <div
        class="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/20"
        aria-hidden="true"
      >
        <Library class="size-4" />
      </div>
      <div class="min-w-0">
        <p class="text-[0.62rem] font-semibold uppercase tracking-wider text-muted-foreground">
          Research
        </p>
        {#if node}
          <h2 class="truncate text-sm font-semibold leading-tight">{orgDisplayTitle(node)}</h2>
        {:else}
          <h2 class="text-sm font-medium text-muted-foreground">No org selected</h2>
        {/if}
      </div>
    </div>

    {#if node}
      <div class="hidden items-center gap-1.5 sm:flex">
        <Badge variant="secondary" class="h-6 gap-1 px-2 text-[0.65rem] font-normal tabular-nums">
          <Newspaper class="size-3" />
          {events.length}
        </Badge>
        <Badge variant="secondary" class="h-6 gap-1 px-2 text-[0.65rem] font-normal tabular-nums">
          <BookOpen class="size-3" />
          {fieldSourceCount}
        </Badge>
      </div>
    {/if}

    <div class="flex shrink-0 items-center gap-1">
      <Button
        variant={pinned ? 'secondary' : 'ghost'}
        size="icon-sm"
        aria-pressed={pinned}
        title={pinned ? 'Unpin panel height' : 'Pin panel height'}
        onclick={() => onPinnedChange(!pinned)}
        class={cn(pinned && 'text-primary')}
      >
        {#if pinned}
          <Pin class="size-3.5" />
        {:else}
          <PinOff class="size-3.5" />
        {/if}
      </Button>
      {#if expanded}
        <Button variant="ghost" size="icon-sm" title="Minimize panel" onclick={onCollapse}>
          <ChevronDown class="size-4" />
        </Button>
      {:else}
        <Button variant="ghost" size="icon-sm" title="Expand panel" onclick={onExpand}>
          <ChevronDown class="size-4 rotate-180" />
        </Button>
      {/if}
    </div>
  </div>

  <div class="flex min-h-0 flex-1 flex-col bg-background/95">
  {#if !expanded}
    <button
      type="button"
      class="flex flex-1 cursor-pointer items-center justify-center px-4 py-2 text-xs text-muted-foreground transition-colors hover:bg-secondary/40 hover:text-foreground"
      title="Click to expand · double-click to toggle"
      onclick={onCollapsedStripClick}
      ondblclick={onCollapsedStripDblClick}
    >
      {#if node}
        {events.length} article{events.length === 1 ? '' : 's'} · {fieldSourceCount} source{fieldSourceCount === 1 ? '' : 's'} — click to browse
      {:else}
        Select an org on the map to browse articles and sources
      {/if}
    </button>
  {:else if !node}
    <Empty.Root class="min-h-0 flex-1 border-none">
      <Empty.Header>
        <Empty.Media variant="icon">
          <Newspaper />
        </Empty.Media>
        <Empty.Title>No org selected</Empty.Title>
        <Empty.Description>
          Click a node on the map to browse linked articles and source citations.
        </Empty.Description>
      </Empty.Header>
    </Empty.Root>
  {:else}
    <!-- Wide: side-by-side columns -->
    <div class="hidden min-h-0 flex-1 xl:grid xl:grid-cols-2">
      <div class="flex min-h-0 flex-col border-r border-border/60">
        <div class="flex shrink-0 items-center gap-2 px-4 py-2">
          <Newspaper class="size-3.5 text-muted-foreground" />
          <span class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Articles
          </span>
          <Badge variant="outline" class="h-5 px-1.5 text-[0.62rem] tabular-nums">{events.length}</Badge>
        </div>
        <Separator />
        <ScrollArea class="min-h-0 flex-1">
          <div class="p-3">
            {@render articlesPane()}
          </div>
        </ScrollArea>
      </div>

      <div class="flex min-h-0 flex-col">
        <div class="flex shrink-0 items-center gap-2 px-4 py-2">
          <BookOpen class="size-3.5 text-muted-foreground" />
          <span class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Sources
          </span>
          <Badge variant="outline" class="h-5 px-1.5 text-[0.62rem] tabular-nums">{fieldSourceCount}</Badge>
        </div>
        <Separator />
        <ScrollArea class="min-h-0 flex-1">
          <div class="p-3">
            {@render sourcesPane()}
          </div>
        </ScrollArea>
      </div>
    </div>

    <!-- Narrow: tabs -->
    <Tabs.Root bind:value={activeTab} class="flex min-h-0 flex-1 flex-col xl:hidden">
      <Tabs.List variant="line" class="w-full shrink-0 justify-start px-3">
        <Tabs.Trigger value="events" class="gap-1.5 text-xs">
          <Newspaper class="size-3.5" />
          Articles
          <Badge variant="secondary" class="h-4 px-1.5 text-[0.62rem] tabular-nums">{events.length}</Badge>
        </Tabs.Trigger>
        <Tabs.Trigger value="sources" class="gap-1.5 text-xs">
          <BookOpen class="size-3.5" />
          Sources
          <Badge variant="secondary" class="h-4 px-1.5 text-[0.62rem] tabular-nums">{fieldSourceCount}</Badge>
        </Tabs.Trigger>
      </Tabs.List>

      <Tabs.Content value="events" class="mt-0 min-h-0 flex-1 overflow-hidden p-0">
        <ScrollArea class="h-full p-3">
          {@render articlesPane()}
        </ScrollArea>
      </Tabs.Content>

      <Tabs.Content value="sources" class="mt-0 min-h-0 flex-1 overflow-hidden p-0">
        <ScrollArea class="h-full p-3">
          {@render sourcesPane()}
        </ScrollArea>
      </Tabs.Content>
    </Tabs.Root>
  {/if}
  </div>
</section>

{#snippet articlesPane()}
  {#if events.length}
    <Item.Group class="gap-1">
      {#each events as ev (ev.id)}
        {@const articleSources = eventArticleSources(ev.id, sources)}
        {@const href = primaryArticleUrl(ev, articleSources)}
        {@const sourceLabel = primaryArticleLabel(ev, articleSources)}
        <Item.Root variant="outline" size="sm" class={cn(href && 'hover:bg-accent/40')}>
          {#snippet child({ props }: { props: Record<string, unknown> })}
            {#if href}
              <a
                {...props}
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                class={cn(props.class as string, 'group w-full text-left')}
              >
                <Item.Media variant="icon" class="size-8 rounded-md bg-secondary">
                  <Newspaper class="size-3.5" />
                </Item.Media>
                <Item.Content>
                  <Item.Title class="line-clamp-2">{ev.title}</Item.Title>
                  <Item.Description class="text-xs">
                    <span class="inline-flex min-w-0 items-center gap-1 text-primary group-hover:underline">
                      {sourceLabel}
                      <ExternalLink class="size-3 shrink-0 opacity-70" />
                    </span>
                  </Item.Description>
                </Item.Content>
                <Badge variant="outline" class="shrink-0 tabular-nums text-[0.65rem] font-normal">
                  {formatEventYear(ev)}
                </Badge>
              </a>
            {:else}
              <div {...props} class={cn(props.class as string, 'w-full text-left')}>
                <Item.Media variant="icon" class="size-8 rounded-md bg-secondary">
                  <Newspaper class="size-3.5" />
                </Item.Media>
                <Item.Content>
                  <Item.Title class="line-clamp-2">{ev.title}</Item.Title>
                  <Item.Description class="line-clamp-2 text-xs text-muted-foreground">
                    {#if ev.data?.description}
                      {truncate(ev.data.description, 120)}
                    {:else}
                      {formatEventYear(ev)}
                    {/if}
                  </Item.Description>
                </Item.Content>
                <Badge variant="outline" class="shrink-0 tabular-nums text-[0.65rem] font-normal">
                  {formatEventYear(ev)}
                </Badge>
              </div>
            {/if}
          {/snippet}
        </Item.Root>
      {/each}
    </Item.Group>
  {:else}
    <Empty.Root class="border-none py-8">
      <Empty.Header>
        <Empty.Media variant="icon">
          <Newspaper />
        </Empty.Media>
        <Empty.Title class="text-sm">No articles yet</Empty.Title>
        <Empty.Description class="text-xs">
          No linked articles for this org in the corpus.
        </Empty.Description>
      </Empty.Header>
    </Empty.Root>
  {/if}
{/snippet}

{#snippet sourcesPane()}
  {#if fieldSourceCount}
    <Accordion.Root type="multiple" bind:value={sourceAccordionOpen} class="gap-2">
      {#each claimGroups as group (group.predicate)}
        <Accordion.Item value={group.predicate} class="rounded-lg border border-border/60 px-1">
          <Accordion.Trigger class="items-center px-3 py-2 text-xs hover:no-underline">
            <div class="flex items-center gap-1.5">
              <span>{predicateLabel(group.predicate)}</span>
              <Badge variant="secondary" class="h-5 shrink-0 px-1.5 tabular-nums text-[0.62rem] font-normal">
                {group.items.length}
              </Badge>
            </div>
          </Accordion.Trigger>
          <Accordion.Content class="px-2 pb-2">
            <div class="flex flex-col gap-2">
              {#each group.items as src (src.url || src.label)}
                <SourceContextCard source={src} />
              {/each}
            </div>
          </Accordion.Content>
        </Accordion.Item>
      {/each}

      {#if otherSources.length}
        <Accordion.Item value="references" class="rounded-lg border border-border/60 px-1">
          <Accordion.Trigger class="items-center px-3 py-2 text-xs hover:no-underline">
            <div class="flex items-center gap-1.5">
              <span>References</span>
              <Badge variant="secondary" class="h-5 shrink-0 px-1.5 tabular-nums text-[0.62rem] font-normal">
                {otherSources.length}
              </Badge>
            </div>
          </Accordion.Trigger>
          <Accordion.Content class="px-2 pb-2">
            <div class="flex flex-col gap-2">
              {#each otherSources as src (src.url || src.label)}
                <SourceContextCard source={src} />
              {/each}
            </div>
          </Accordion.Content>
        </Accordion.Item>
      {/if}
    </Accordion.Root>
  {:else}
    <Empty.Root class="border-none py-8">
      <Empty.Header>
        <Empty.Media variant="icon">
          <BookOpen />
        </Empty.Media>
        <Empty.Title class="text-sm">No sources yet</Empty.Title>
        <Empty.Description class="text-xs">
          No source citations recorded for this org.
        </Empty.Description>
      </Empty.Header>
    </Empty.Root>
  {/if}
{/snippet}
