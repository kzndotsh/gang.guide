<script lang="ts">
  /**
   * YearSlider — dual-thumb range slider using shadcn Slider.
   */
  import { RotateCcw } from '@lucide/svelte';
  import { Slider } from '$lib/components/ui/slider/index.js';

  interface Props {
    min?: number;
    max?: number;
    defaultMin?: number;
    defaultMax?: number;
    yearMin: number;
    yearMax: number;
    variant?: 'pill' | 'panel';
  }

  let {
    min = 1930,
    max = 2025,
    defaultMin = min,
    defaultMax = max,
    yearMin = $bindable(),
    yearMax = $bindable(),
    variant = 'pill',
  }: Props = $props();

  let value = $state([yearMin, yearMax]);
  const atDefault = $derived(yearMin === defaultMin && yearMax === defaultMax);

  $effect(() => {
    value = [yearMin, yearMax];
  });

  function onValueChange(v: number[]) {
    yearMin = v[0];
    yearMax = v[1];
  }

  function reset() {
    yearMin = defaultMin;
    yearMax = defaultMax;
  }

  const sliderClass =
    ' [&_[data-slot=slider-track]]:h-1 [&_[data-slot=slider-track]]:bg-muted [&_[data-slot=slider-thumb]]:border-0 [&_[data-slot=slider-thumb]]:bg-muted-foreground/60 fine-hover:[&_[data-slot=slider-thumb]]:bg-foreground [&_[data-slot=slider-range]]:h-full [&_[data-slot=slider-range]]:bg-muted-foreground/60';
</script>

{#if variant === 'panel'}
  <div class="flex w-56 flex-col gap-2.5">
    <div class="flex items-center justify-between gap-2">
      <span class="text-[0.65rem] font-medium text-muted-foreground">Year range</span>
      <button
        type="button"
        class="inline-flex size-7 select-none items-center justify-center rounded-md text-muted-foreground active:scale-[0.97] disabled:pointer-events-none disabled:opacity-30 fine-hover:bg-accent fine-hover:text-foreground"
        onclick={reset}
        disabled={atDefault}
        aria-label="Reset year range"
        title="Reset year range"
      >
        <RotateCcw class="size-3" strokeWidth={2} />
      </button>
    </div>
    <div class="flex items-center gap-2">
      <span class="w-9 shrink-0 text-[0.65rem] font-medium tabular-nums text-muted-foreground">{yearMin}</span>
      <Slider
        type="multiple"
        {min}
        {max}
        step={1}
        bind:value
        {onValueChange}
        class="min-w-0 flex-1{sliderClass} [&_[data-slot=slider-thumb]]:size-4"
      />
      <span class="w-9 shrink-0 text-right text-[0.65rem] font-medium tabular-nums text-muted-foreground">{yearMax}</span>
    </div>
  </div>
{:else}
<div class="flex h-8 items-center gap-1 rounded-full bg-muted pl-2.5 pr-0.5 md:h-7 md:gap-1.5 md:pl-3 md:pr-1">
  <span class="text-[0.62rem] font-medium tabular-nums text-muted-foreground md:text-[0.65rem]">{yearMin}</span>
  <Slider
    type="multiple"
    {min}
    {max}
    step={1}
    bind:value
    {onValueChange}
    class="w-[4.5rem] md:w-20{sliderClass} [&_[data-slot=slider-track]]:bg-transparent [&_[data-slot=slider-thumb]]:size-4 md:[&_[data-slot=slider-thumb]]:size-2"
  />
  <span class="text-[0.62rem] font-medium tabular-nums text-muted-foreground md:text-[0.65rem]">{yearMax}</span>
  <button
    type="button"
    class="inline-flex size-8 shrink-0 select-none items-center justify-center rounded-full text-muted-foreground active:scale-[0.97] disabled:pointer-events-none disabled:opacity-30 fine-hover:text-foreground md:size-5"
    onclick={reset}
    disabled={atDefault}
    aria-label="Reset year range"
    title="Reset year range"
  >
    <RotateCcw class="size-3" strokeWidth={2} />
  </button>
</div>
{/if}
