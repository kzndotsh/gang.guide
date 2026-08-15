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

<div class="flex h-8 w-full items-center justify-center rounded-full bg-muted px-1 md:h-7 md:w-auto md:px-3">
  {#each EDGE_OPTIONS as opt}
    {@const disabled = opt.needsSelection && !selectedId}
    {@const active = edgeMode === opt.value}
    <button
      class="min-w-0 flex-1 rounded-full px-1.5 py-1 text-[0.65rem] font-medium transition-colors md:flex-none md:px-3 {active ? 'bg-background text-foreground' : 'text-muted-foreground hover:text-foreground'} {disabled ? 'opacity-30 pointer-events-none' : ''}"
      onclick={() => { edgeMode = opt.value; }}
      {disabled}
    >
      <span class="md:hidden">{opt.value === 'hover' ? 'Hover' : 'All'}</span>
      <span class="hidden md:inline">{opt.label}</span>
    </button>
  {/each}
</div>
