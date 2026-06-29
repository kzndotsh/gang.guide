<script lang="ts">
  /**
   * YearSlider — dual-thumb range slider using shadcn Slider.
   */
  import { Slider } from '$lib/components/ui/slider/index.js';

  interface Props {
    min?: number;
    max?: number;
    yearMin: number;
    yearMax: number;
  }

  let { min = 1930, max = 2025, yearMin = $bindable(), yearMax = $bindable() }: Props = $props();

  let value = $state([yearMin, yearMax]);

  $effect(() => {
    value = [yearMin, yearMax];
  });

  function onValueChange(v: number[]) {
    yearMin = v[0];
    yearMax = v[1];
  }
</script>

<div class="flex h-7 items-center gap-1.5 rounded-full bg-muted px-3">
  <span class="text-[0.65rem] font-medium text-muted-foreground">{yearMin}</span>
  <Slider
    type="multiple"
    {min}
    {max}
    step={1}
    {value}
    {onValueChange}
    class="w-20 [&_[data-slot=slider-track]]:h-0.5 [&_[data-slot=slider-thumb]]:size-2 [&_[data-slot=slider-thumb]]:border-0 [&_[data-slot=slider-thumb]]:bg-muted-foreground/60 [&_[data-slot=slider-thumb]]:hover:bg-foreground [&_[data-slot=slider-range]]:bg-muted-foreground/40"
  />
  <span class="text-[0.65rem] font-medium text-muted-foreground">{yearMax}</span>
</div>
