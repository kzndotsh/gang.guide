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
  }

  let {
    min = 1930,
    max = 2025,
    defaultMin = min,
    defaultMax = max,
    yearMin = $bindable(),
    yearMax = $bindable(),
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
</script>

<div class="flex h-8 items-center gap-1.5 rounded-full bg-muted pl-3 pr-1 md:h-7">
  <span class="text-[0.65rem] font-medium tabular-nums text-muted-foreground">{yearMin}</span>
  <Slider
    type="multiple"
    {min}
    {max}
    step={1}
    bind:value
    {onValueChange}
    class="w-24 md:w-20 [&_[data-slot=slider-track]]:h-1 [&_[data-slot=slider-track]]:bg-transparent [&_[data-slot=slider-thumb]]:size-3.5 md:[&_[data-slot=slider-thumb]]:size-2 [&_[data-slot=slider-thumb]]:border-0 [&_[data-slot=slider-thumb]]:bg-muted-foreground/60 [&_[data-slot=slider-thumb]]:hover:bg-foreground [&_[data-slot=slider-range]]:h-full [&_[data-slot=slider-range]]:bg-muted-foreground/60"
  />
  <span class="text-[0.65rem] font-medium tabular-nums text-muted-foreground">{yearMax}</span>
  <button
    type="button"
    class="inline-flex size-6 shrink-0 items-center justify-center rounded-full text-muted-foreground hover:text-foreground active:scale-[0.97] disabled:pointer-events-none disabled:opacity-30 md:size-5"
    onclick={reset}
    disabled={atDefault}
    aria-label="Reset year range"
    title="Reset year range"
  >
    <RotateCcw class="size-3" strokeWidth={2} />
  </button>
</div>
