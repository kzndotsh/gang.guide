<script lang="ts">
  /**
   * EdgeModeToggle — minimal text toggles for edge display.
   */
  import { Link2 } from '@lucide/svelte';
  import { type EdgeMode } from '$lib/map/KonvaMap.svelte';
  import { EDGE_OPTIONS } from '$lib/map/mapViewOptions';

  interface Props {
    edgeMode: EdgeMode;
    selectedId: string | null;
    compact?: boolean;
  }

  let { edgeMode = $bindable(), selectedId, compact = false }: Props = $props();
</script>

<div
  role="group"
  aria-label="Edge display mode"
  class="flex items-center overflow-visible rounded-full bg-muted p-0.5 {compact ? 'h-10 shrink-0 gap-0.5' : 'h-8 w-full gap-1.5 md:h-7 md:w-auto md:gap-2'}"
>
  <span
    class="flex shrink-0 items-center justify-center text-muted-foreground {compact ? 'pl-2.5 pr-0.5' : 'pl-2 pr-0.5 md:pl-2.5'}"
    aria-hidden="true"
  >
    <Link2 class={compact ? 'size-3.5' : 'size-3'} strokeWidth={2} />
  </span>
  <div class="flex shrink-0 items-center gap-0.5 overflow-visible {compact ? 'pr-1.5' : 'min-w-0 flex-1 pr-0.5'}">
  {#each EDGE_OPTIONS as opt}
    {@const disabled = opt.needsSelection && !selectedId}
    {@const active = edgeMode === opt.value}
    <button
      type="button"
      class="shrink-0 select-none whitespace-nowrap rounded-full leading-none font-medium transition-[color,background-color,box-shadow] {compact ? 'px-3 py-1.5 text-[0.65rem]' : 'min-w-0 flex-1 px-1.5 py-0.5 text-[0.62rem] md:flex-none md:px-3 md:py-0.5 md:text-[0.65rem]'} {active ? 'bg-accent text-foreground shadow-sm' : 'text-muted-foreground fine-hover:text-foreground'} {disabled ? 'pointer-events-none opacity-30' : ''}"
      onclick={() => { edgeMode = opt.value; }}
      aria-pressed={active}
      aria-label={opt.mobileLabel}
      {disabled}
      title={opt.hint}
    >
      <span class="md:hidden">{opt.mobileLabel}</span>
      <span class="hidden md:inline">{opt.label}</span>
    </button>
  {/each}
  </div>
</div>
