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
  }

  let { edgeMode = $bindable(), selectedId }: Props = $props();
</script>

<div
  role="group"
  aria-label="Edge display mode"
  class="flex h-8 w-full items-center gap-1.5 rounded-full bg-muted p-0.5 md:h-7 md:w-auto md:gap-2"
>
  <span
    class="flex shrink-0 items-center justify-center pl-2 pr-0.5 text-muted-foreground md:pl-2.5"
    aria-hidden="true"
  >
    <Link2 class="size-3" strokeWidth={2} />
  </span>
  <div class="flex min-w-0 flex-1 items-stretch gap-0.5 pr-0.5">
  {#each EDGE_OPTIONS as opt}
    {@const disabled = opt.needsSelection && !selectedId}
    {@const active = edgeMode === opt.value}
    <button
      type="button"
      class="min-w-0 flex-1 select-none rounded-full px-1.5 py-0.5 text-[0.62rem] font-medium transition-[color,background-color,box-shadow] md:flex-none md:px-3 md:text-[0.65rem] {active ? 'bg-accent text-foreground shadow-sm' : 'text-muted-foreground fine-hover:text-foreground'} {disabled ? 'pointer-events-none opacity-30' : ''}"
      onclick={() => { edgeMode = opt.value; }}
      aria-pressed={active}
      {disabled}
      title={opt.hint}
    >
      <span class="md:hidden">{opt.mobileLabel}</span>
      <span class="hidden md:inline">{opt.label}</span>
    </button>
  {/each}
  </div>
</div>
