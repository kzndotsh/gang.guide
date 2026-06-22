<script lang="ts">
  import type { GraphNode } from '$lib/types';
  import { orgDisplayTitle } from '$lib/inspector/inspectorDisplay';
  import { orgTypeLabel } from '$lib/inspector/inspectorFormat';
  import { formatYearSpan, resolveNodeYearSpan } from '$lib/yearFormat';

  interface Props {
    node: GraphNode;
    x: number;
    y: number;
  }

  let { node, x, y }: Props = $props();

  const span = $derived(resolveNodeYearSpan(node.data));
  const typeLabel = $derived(orgTypeLabel(node.data?.type));
  const displayTitle = $derived(orgDisplayTitle(node));
</script>

<div
  class="pointer-events-none absolute z-[3] max-w-56 -translate-x-1/2 -translate-y-[calc(100%+14px)] rounded-md border border-border bg-popover px-2 py-1.5 shadow-sm"
  style:left="{x}px"
  style:top="{y}px"
>
  <strong class="block text-xs font-semibold leading-snug">{displayTitle}</strong>
  <span class="mt-0.5 block text-[0.65rem] leading-snug text-muted-foreground">
    {#if node.data?.metro}
      {node.data.metro}
    {/if}
    {#if node.data?.metro && span}
      ·
    {/if}
    {#if span}
      {formatYearSpan(span)}
    {/if}
    {#if !node.data?.metro && !span}
      {typeLabel}
    {/if}
  </span>
</div>
