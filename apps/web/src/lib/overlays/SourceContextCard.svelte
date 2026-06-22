<script lang="ts">
  import type { OrgSourceLink } from '$lib/orgSources';
  import { predicateLabel } from '$lib/orgSources';
  import { truncate } from '$lib/inspector/inspectorFormat';
  import * as Card from '$lib/components/ui/card/index.js';
  import { Badge } from '$lib/components/ui/badge/index.js';
  import { Button } from '$lib/components/ui/button/index.js';
  import { cn } from '$lib/utils.js';

  interface Props {
    source: OrgSourceLink;
    onclickEvent?: (eventId: string) => void;
  }

  let { source, onclickEvent }: Props = $props();

  const fieldLabel = $derived(source.predicate ? predicateLabel(source.predicate) : null);

  function snippetDisplay(
    snippet: (typeof source.snippets)[number],
  ): { heading?: string; quote?: string } {
    const eventTitle = snippet.eventTitle?.trim();
    let quote = snippet.quote?.trim();

    if (source.kind === 'claim') {
      return { heading: quote ? truncate(quote, 140) : undefined };
    }

    if (!eventTitle) {
      return { heading: quote ? truncate(quote, 100) : undefined };
    }

    if (quote) {
      if (quote === eventTitle) {
        quote = undefined;
      } else if (quote.startsWith(eventTitle)) {
        const rest = quote.slice(eventTitle.length).replace(/^[\s:—–-]+/, '').trim();
        quote = rest.length >= 24 ? rest : undefined;
      }
    }

    return {
      heading: truncate(eventTitle, 100),
      quote: quote ? truncate(quote, 360) : undefined,
    };
  }

  const displaySnippets = $derived(
    source.snippets.length
      ? source.snippets
      : [{ quote: undefined, eventTitle: undefined }],
  );

  const kindBadgeClass = $derived(
    source.kind === 'news'
      ? 'border-green-500/30 bg-green-500/10 text-green-400'
      : source.kind === 'profile'
        ? 'border-blue-400/30 bg-blue-400/10 text-blue-300'
        : source.kind === 'claim'
          ? 'border-purple-400/30 bg-purple-400/10 text-purple-300'
          : ''
  );
</script>

<Card.Root size="sm" class="gap-2 rounded-lg border border-border/60 bg-background py-2.5 ring-0">
  <Card.Header class="gap-1 px-3 pb-0">
    <div class="flex items-start justify-between gap-2.5">
      <div class="flex min-w-0 flex-wrap items-center gap-1.5">
        <Badge variant="outline" class={cn('text-[0.58rem] uppercase tracking-wide', kindBadgeClass)}>
          {source.kind === 'claim' && fieldLabel ? fieldLabel : source.kind}
        </Badge>
        {#if source.primary}
          <Badge class="border-green-500/30 bg-green-500/10 text-[0.58rem] uppercase tracking-wide text-green-400">
            Primary
          </Badge>
        {/if}
      </div>
      {#if source.reviewStatus}
        <span class="shrink-0 text-[0.62rem] text-muted-foreground/80">
          {source.reviewStatus.replace(/_/g, ' ')}
        </span>
      {:else if source.eventIds.length}
        <span class="shrink-0 text-[0.62rem] text-muted-foreground/80">
          {source.eventIds.length} linked event{source.eventIds.length === 1 ? '' : 's'}
        </span>
      {/if}
    </div>
  </Card.Header>

  <Card.Content class="flex flex-col gap-2 px-3 pt-0">
    <ul class="flex list-none flex-col gap-2 p-0">
      {#each displaySnippets as snippet, i (i)}
        {@const body = snippetDisplay(snippet)}
        {#if body.heading || source.label}
          <li class="flex min-w-0 flex-col gap-1">
            <div class="flex min-w-0 flex-wrap items-baseline gap-x-1.5 gap-y-0.5 text-[0.72rem] leading-snug">
              {#if body.heading}
                <span class="font-semibold text-foreground/90">{body.heading}</span>
                <span class="text-muted-foreground/45" aria-hidden="true">·</span>
              {/if}
              {#if source.url}
                <a
                  class="min-w-0 truncate text-primary hover:underline"
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {source.label}
                </a>
              {:else}
                <span class="min-w-0 truncate text-muted-foreground">{source.label}</span>
              {/if}
            </div>
            {#if body.quote}
              <p class="m-0 text-[0.68rem] leading-snug text-muted-foreground">{body.quote}</p>
            {/if}
          </li>
        {/if}
      {/each}
    </ul>

    {#if source.eventIds.length === 1 && onclickEvent}
      <Button
        variant="link"
        size="sm"
        class="h-auto self-start p-0 text-[0.68rem]"
        onclick={() => onclickEvent?.(source.eventIds[0])}
      >
        Open event detail
      </Button>
    {/if}
  </Card.Content>
</Card.Root>
