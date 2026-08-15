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

<div class="flex h-8 shrink-0 items-center rounded-full bg-muted px-1 md:h-7 md:px-3" role="toolbar" aria-label="Map zoom">
  <button
    class="inline-flex size-8 items-center justify-center rounded-full text-muted-foreground hover:text-foreground active:scale-[0.97] md:size-6"
    onclick={onZoomOut}
    aria-label="Zoom out"
    title="Zoom out (−)"
  >
    <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14"/></svg>
  </button>

  <span class="hidden min-w-[2.5rem] px-0.5 text-center text-[0.65rem] font-medium tabular-nums text-muted-foreground md:inline">
    {zoomPct}%
  </span>

  <button
    class="inline-flex size-8 items-center justify-center rounded-full text-muted-foreground hover:text-foreground active:scale-[0.97] md:size-6"
    onclick={onZoomIn}
    aria-label="Zoom in"
    title="Zoom in (+)"
  >
    <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
  </button>

  <div class="mx-0.5 h-4 w-px bg-border/80" aria-hidden="true"></div>

  <button
    class="inline-flex size-8 items-center justify-center rounded-full px-0 text-muted-foreground hover:text-foreground active:scale-[0.97] md:h-6 md:w-auto md:gap-1 md:px-2 md:text-xs"
    onclick={onFit}
    aria-label="Fit to view"
    title="Fit to view (F)"
  >
    <svg class="size-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/>
      <line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/>
    </svg>
    <span class="hidden md:inline">Fit</span>
  </button>
</div>
