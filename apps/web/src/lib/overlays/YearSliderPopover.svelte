<script lang="ts">
  import { CalendarRange } from '@lucide/svelte';
  import * as Popover from '$lib/components/ui/popover/index.js';
  import YearSlider from '$lib/overlays/YearSlider.svelte';

  interface Props {
    min?: number;
    max?: number;
    defaultMin?: number;
    defaultMax?: number;
    yearMin: number;
    yearMax: number;
    large?: boolean;
  }

  let {
    min = 1930,
    max = 2025,
    defaultMin = min,
    defaultMax = max,
    yearMin = $bindable(),
    yearMax = $bindable(),
    large = false,
  }: Props = $props();

  const atDefault = $derived(yearMin === defaultMin && yearMax === defaultMax);
</script>

<Popover.Root>
  <Popover.Trigger
    class="relative inline-flex shrink-0 select-none items-center justify-center rounded-full bg-muted text-muted-foreground active:scale-[0.97] fine-hover:text-foreground {large ? 'size-9' : 'size-8'}"
    aria-label={atDefault ? 'Year range' : `Year range, ${yearMin} to ${yearMax}`}
  >
    <CalendarRange class="size-3.5" strokeWidth={2} />
    {#if !atDefault}
      <span class="absolute -top-0.5 -right-0.5 size-2 rounded-full bg-primary" aria-hidden="true"></span>
    {/if}
  </Popover.Trigger>
  <Popover.Content side="top" align="start" sideOffset={8} class="w-auto p-3 shadow-sm">
    <YearSlider
      variant="panel"
      bind:yearMin
      bind:yearMax
      {min}
      {max}
      {defaultMin}
      {defaultMax}
    />
  </Popover.Content>
</Popover.Root>
