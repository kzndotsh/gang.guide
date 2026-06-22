<script lang="ts">
  /**
   * EdgeModeToggle — minimal text toggles for edge display.
   */
  import { type EdgeMode } from '$lib/map/KonvaMap.svelte';
  import { EDGE_OPTIONS } from '$lib/map/mapViewOptions';

  interface Props {
    edgeMode: EdgeMode;
    selectedId: string | null;
  }

  let { edgeMode = $bindable(), selectedId }: Props = $props();
</script>

<div class="flex items-center gap-2 drop-shadow-[0_1px_2px_rgba(0,0,0,0.5)]">
  {#each EDGE_OPTIONS as opt}
    {@const disabled = opt.needsSelection && !selectedId}
    {@const active = edgeMode === opt.value}
    <button
      class="text-[0.7rem] transition-opacity {active ? 'text-foreground underline underline-offset-2' : 'text-foreground/60 hover:text-foreground'} {disabled ? 'opacity-30 pointer-events-none' : ''}"
      onclick={() => { edgeMode = opt.value; }}
      {disabled}
    >{opt.label}</button>
  {/each}
</div>
