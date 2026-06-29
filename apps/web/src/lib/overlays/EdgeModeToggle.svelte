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

<div class="flex h-7 items-center rounded-full bg-muted px-3">
  {#each EDGE_OPTIONS as opt}
    {@const disabled = opt.needsSelection && !selectedId}
    {@const active = edgeMode === opt.value}
    <button
      class="rounded-full px-3 py-1 text-[0.65rem] font-medium transition-colors {active ? 'bg-background text-foreground' : 'text-muted-foreground hover:text-foreground'} {disabled ? 'opacity-30 pointer-events-none' : ''}"
      onclick={() => { edgeMode = opt.value; }}
      {disabled}
    >{opt.label}</button>
  {/each}
</div>
