<script lang="ts">
  let x = $state(0);
  let y = $state(0);
  let visible = $state(false);
  let clicking = $state(false);

  function onMove(e: MouseEvent) {
    x = e.clientX;
    y = e.clientY;
    if (!visible) visible = true;
  }
</script>

<svelte:window onmousemove={onMove} onmousedown={() => clicking = true} onmouseup={() => clicking = false} onmouseleave={() => visible = false} onmouseenter={() => visible = true} />

{#if visible}
  <div
    class="pointer-events-none fixed z-[9999] rounded-full border-2 border-foreground/70 transition-transform duration-75 ease-out {clicking ? 'scale-75' : 'scale-100'}"
    style:left="{x}px"
    style:top="{y}px"
    style:width="20px"
    style:height="20px"
    style:transform="translate(-50%, -50%) {clicking ? 'scale(0.75)' : ''}"
  >
    <div class="absolute left-1/2 top-1/2 size-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-foreground/80"></div>
  </div>
{/if}
