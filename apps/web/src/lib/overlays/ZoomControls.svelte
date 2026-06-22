<script lang="ts">
  /**
   * ZoomControls — zoom in/out/fit buttons with percentage display.
   */
  interface Props {
    zoomPct: number;
    onZoomIn: () => void;
    onZoomOut: () => void;
    onFit: () => void;
  }

  let { zoomPct, onZoomIn, onZoomOut, onFit }: Props = $props();
</script>

<div class="flex items-center drop-shadow-[0_1px_2px_rgba(0,0,0,0.5)]" role="toolbar" aria-label="Map zoom">
  <button
    class="inline-flex size-6 items-center justify-center rounded-md text-foreground/60 hover:text-foreground active:scale-[0.97]"
    onclick={onZoomOut}
    aria-label="Zoom out"
    title="Zoom out (−)"
  >
    <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14"/></svg>
  </button>

  <span class="min-w-[2.5rem] px-0.5 text-center text-[0.7rem] font-medium tabular-nums text-foreground/60">
    {zoomPct}%
  </span>

  <button
    class="inline-flex size-6 items-center justify-center rounded-md text-foreground/60 hover:text-foreground active:scale-[0.97]"
    onclick={onZoomIn}
    aria-label="Zoom in"
    title="Zoom in (+)"
  >
    <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
  </button>

  <div class="mx-0.5 h-4 w-px bg-border/80" aria-hidden="true"></div>

  <button
    class="inline-flex h-6 items-center gap-1 rounded-md px-2 text-xs text-foreground/60 hover:text-foreground active:scale-[0.97]"
    onclick={onFit}
    aria-label="Fit to view"
    title="Fit to view (F)"
  >
    <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/>
      <line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/>
    </svg>
    <span class="hidden sm:inline">Fit</span>
  </button>
</div>
